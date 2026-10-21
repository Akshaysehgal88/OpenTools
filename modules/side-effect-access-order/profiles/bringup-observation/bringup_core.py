"""Compare a qualified diagnostic source receipt with an independent question."""
import html
from bringup_common import IDENTITY,SELECTION,digest,known,number,require,shape,text,uint
from native_bringup import SOURCES,conditions,load
REQUIRED={'source.kind','source.model_sha256','silicon.revision','silicon.fuses','firmware.image_sha256','board.power_on','clock.identity','clock.period_ns','reset.entry','reset.recovery','diagnostic.effects'}
LIMITS='Owned sampled device emulation and one monotonic counter/time correlation only. Raw bits, diagnostic receipt validity and comparison to the requested observation are distinct. No real silicon, instrument/calibration, firmware ISA, physical power/reset, root-cause, all-mode or signoff qualification.'

def validate(c):
    shape(c,{'format','claim_ref','scope_ref','run_ref','owner_ref','requirements_ref','expectation_ref','clock_mapping_ref','binding','selection','required_conditions','window_ns','uncertainty_ns','expected_answer'})
    require(c['format']=='opentools.bringup-request.v1' and text(c['claim_ref']) and text(c['scope_ref']),'Independent comparison question required')
    require(c['run_ref'] is None or text(c['run_ref']),'Explicit selected run or null required')
    for k in ('owner_ref','requirements_ref','expectation_ref','clock_mapping_ref'):require(c[k] is None or text(c[k]),'Source/owner reference or null required')
    shape(c['binding'],{'identity','sources','command_sha256','context_sha256'});shape(c['binding']['identity'],IDENTITY);require(all(text(v) for v in c['binding']['identity'].values()),'Expected observation identity required');shape(c['binding']['sources'],SOURCES)
    for v in [*c['binding']['sources'].values(),c['binding']['command_sha256'],c['binding']['context_sha256']]:require(v is None or isinstance(v,str) and len(v)==64 and all(x in '0123456789abcdef' for x in v),'Expected SHA256 or null required')
    shape(c['selection'],SELECTION)
    for v in c['selection'].values():uint(v)
    require(c['selection']['fault_mask']==1,'One scalar diagnostic bit qualified')
    require(c['expected_answer'] in ('present','absent_in_observed_prefix'),'Explicit bounded comparison expectation required')
    require(isinstance(c['required_conditions'],dict) and REQUIRED<=set(c['required_conditions']) and len(c['required_conditions'])<=32,'Do not omit model,image,device,reset,clock or diagnostic conditions')
    for k,v in c['required_conditions'].items():shape(v,{'value','evidence_ref'});require(text(k) and (v['evidence_ref'] is None or text(v['evidence_ref'])),'Independent condition/source required')
    require(isinstance(c['window_ns'],list) and len(c['window_ns'])==2,'Explicit relative observation window required')
    for v in c['window_ns']:
        if v is not None:number(v)
    if known(c['window_ns']):require(c['window_ns'][0]<=c['window_ns'][1],'Observation window reversed')
    if c['uncertainty_ns'] is not None:require(number(c['uncertainty_ns'])>=0,'Nonnegative correlation uncertainty required')

def review(root,c):
    validate(c);findings=[];gaps=[];quarantine=[];comparisons=[];measurement=None;timing=None;original=None;source_observation=None;changed=None
    def add(out,code,detail):out.append({'code':code,'detail':detail})
    for k in ('owner_ref','requirements_ref','expectation_ref','clock_mapping_ref'):
        if c[k] is None:add(gaps,'missing_independent_basis',k)
    def finish():
        if quarantine or any(f['code'] in ('condition_mismatch','selection_differs_from_capture') for f in findings):status='INAPPLICABLE'
        elif findings:status='REVIEW_REQUIRED'
        elif gaps:status='INCONCLUSIVE'
        elif measurement['report']['evidence_answer']!=c['expected_answer']:status='CONTRADICTED_WITHIN_EMULATION'
        else:status='SUPPORTED_WITHIN_EMULATION'
        code=1 if status in ('INAPPLICABLE','REVIEW_REQUIRED','CONTRADICTED_WITHIN_EMULATION') else 2 if gaps else 0
        return {'format':'opentools.bringup-review.v1','status':status,'exit_code':code,'claim_ref':c['claim_ref'],'scope_ref':c['scope_ref'],'owner_ref':c['owner_ref'],'requirements_ref':c['requirements_ref'],'expectation_ref':c['expectation_ref'],'expected_answer':c['expected_answer'],'request_digest':digest(c),'captured_question':original,'question_changed':changed,'diagnostic':measurement,'source_observation':source_observation,'timing':timing,'conditions':comparisons,'findings':findings,'gaps':gaps,'quarantine':quarantine,'recheck_when':['device revision/fuses,image,board or reset/power sequence changes','diagnostic access/capture history or observation selection changes','clock correlation,time window or pre-silicon expectation changes'],'limits':LIMITS}
    if c['run_ref'] is None:add(gaps,'missing_observation','No selected original observation packet');return finish()
    e=load(root,c['run_ref']);ctx=e['context'];original=e['capture_question'];changed=digest(c)!=digest(original);measurement=e['diagnostic']
    for k in IDENTITY:
        if ctx[k]!=c['binding']['identity'][k]:add(quarantine,'foreign_observation_identity',k)
    if ctx['scope_ref']!=c['scope_ref']:add(quarantine,'foreign_question_scope','Packet is outside the requested scope')
    for k,value in c['binding']['sources'].items():
        if value is None:add(gaps,'missing_expected_source',k)
        elif value!=e['source_sha256'][k]:add(quarantine,'stale_or_foreign_source',k)
    for k,name in [('command_sha256','command.json'),('context_sha256','context.json')]:
        value=c['binding'][k]
        if value is None:add(gaps,'missing_original_binding',name)
        elif value!=e['file_sha256'][name]:add(quarantine,'foreign_invocation_or_context',name)
    if c['selection']!=ctx['selection']:add(findings,'selection_differs_from_capture','Retain original target epoch,required prefix and selected read')
    observed=conditions(e)
    for name,wanted in sorted(c['required_conditions'].items()):
        actual=observed.get(name);row={'field':name,'requested':wanted,'observed':actual,'status':'unknown'};comparisons.append(row)
        if actual is None or not known(actual['value']) or not known(wanted['value']) or not text(wanted['evidence_ref']):add(gaps,'condition_evidence_unknown',name)
        elif digest(actual['value'])!=digest(wanted['value']):row['status']='different';add(findings,'condition_mismatch',name)
        else:row['status']='equal'
    d=measurement['report'];selected=d['selected_observation']
    for f in d['findings']:add(findings,'diagnostic_'+f['kind'],f)
    for g in d['gaps']:add(gaps,'diagnostic_'+g['kind'],g)
    if d['evidence_answer']=='unknown':add(gaps,'original_epoch_observation_unestablished','Do not use post-clear zero to refute a prior fault')
    if selected:
        source=next((r for r in e['native']['rows'] if r['tick']==selected['origin_seq']),None);viewer=next((r for r in e['native']['rows'] if r['tick']==selected['seq']),None);entry=e['native']['rows'][1]
        if source and viewer:
            source_observation={'returned_value':selected['data'],'cause_bit_set':d['selected_cause_bit_set'],'evidence_answer':d['evidence_answer'],'origin_tick':source['tick'],'loaded_tick':viewer['tick'],'source_host_ns':source['host_ns'],'loaded_host_ns':viewer['host_ns'],'entry_reset':entry['op'],'entry_host_ns':entry['host_ns'],'source_ref':ctx['run_ref']+'/native.stdout.txt#tick='+str(source['tick']),'loaded_ref':selected['evidence_ref']}
            if c['clock_mapping_ref'] is None or c['uncertainty_ns'] is None or not known(c['window_ns']):add(gaps,'time_correlation_unestablished','Need the original time mapping,uncertainty and target window')
            else:
                delta=source['host_ns']-entry['host_ns'];u=2*c['uncertainty_ns'];interval=[delta-u,delta+u];window=c['window_ns'];within=window[0]<=interval[0] and interval[1]<=window[1]
                timing={'origin_relative_ns':delta,'interval_ns':interval,'required_window_ns':window,'entire_interval_within_window':within,'mapping_ref':c['clock_mapping_ref'],'anchors':e['native']['anchors'],'basis':'Source read time relative to actual entry reset;two timestamp uncertainties,not later load time.'}
                if not within:add(gaps,'source_capture_outside_or_overlapping_window','A qualified value outside the complete required interval does not decide the comparison')
        else:add(gaps,'original_source_read_time_missing','No matching retained origin/viewer response')
    return finish()

def markdown(r):
    def esc(v):return html.escape(str(v)).replace('|','&#124;').replace('\n',' ').replace('\r',' ')
    d=r['diagnostic'];answer=d['report']['evidence_answer'] if d else 'unknown'
    lines=['# Bring-up observation comparison','',r['status'],'',f"Owner: {esc(r['owner_ref'])}; requirement: {esc(r['requirements_ref'])}.",'',f"Expected: {esc(r['expected_answer'])}; qualified diagnostic answer: {esc(answer)}.",'',f"Question differs from captured question: {esc(r['question_changed'])}.",'','| Condition | Correspondence |','|---|---|']
    for v in r['conditions']:lines.append('| '+esc(v['field'])+' | '+esc(v['status'])+' |')
    if r['source_observation']:lines+=['','| Observation | Value |','|---|---|']+['| '+esc(k)+' | '+esc(v)+' |' for k,v in r['source_observation'].items()]
    if r['timing']:lines+=['',f"Source-read interval: {esc(r['timing']['interval_ns'])} ns; required: {esc(r['timing']['required_window_ns'])} ns."]
    lines.append('')
    for group in ('quarantine','findings','gaps'):
        for f in r[group]:lines.append('- '+group+': '+esc(f['code'])+'; '+esc(f['detail']))
    return '\n'.join(lines+['',LIMITS,''])
