"""Review transaction observation correspondence; reuse existing campaign accounting."""
import html
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from progress_core import canonical,fingerprint,require,shape,summarize,text,validate_contract,validate_snapshot
from native_capture import revalidate

EXPECTED={'run_ref','campaign_ref','scope_ref','configuration_ref','model_ref','clock_ref','edge','sampling','reset_ref','reset_active','checker_ref','port_map','source_sha256'}
def known(value):
    if value is None or isinstance(value,str) and not text(value):return False
    if isinstance(value,dict):return bool(value) and all(known(v) for v in value.values())
    if isinstance(value,list):return all(known(v) for v in value)
    return True
def intent(value):
    shape(value,{'format','claim_id','claim','owner_ref','basis_ref','expected','required_modes','mode_basis_ref','policy_ref'})
    require(value['format']=='opentools.checker-observation-intent.v1' and text(value['claim_id']) and text(value['claim']),'Invalid observation intent')
    require(all(value[k] is None or text(value[k]) for k in ('owner_ref','basis_ref','mode_basis_ref','policy_ref')),'Invalid independent intent reference')
    shape(value['expected'],EXPECTED);m=value['required_modes']
    require(m is None or isinstance(m,list) and m and all(type(v) is int and v in (0,1) for v in m) and m==sorted(set(m)),'Required modes must be sorted unique0/1 or null')
    canonical(value)
def events(evidence):
    ctx=evidence['context'];accepted=[];completed=[];stimulus=[];cancelled=[];pending={};problems=[];epoch=0;in_reset=False
    for row in evidence['edges']:
        if row['reset']==ctx['reset_active']:
            if not in_reset:epoch+=1
            cancelled.extend(dict(v,cancel_tick=row['tick']) for v in pending.values());pending.clear();in_reset=True;continue
        in_reset=False
        if row['req_valid']:stimulus.append({'sequence':len(stimulus),'tick':row['tick'],'mode':row['mode']})
        if row['rsp_valid'] and row['rsp_ready']:
            key=(epoch,row['rsp_id']);origin=pending.pop(key,None)
            c={'sequence':len(completed),'tick':row['tick'],'epoch':epoch,'id':row['rsp_id'],'mode':row['mode'],'data':row['rsp_data'],'accepted_sequence':None if origin is None else origin['sequence'],'enabled':row['enabled']}
            completed.append(c)
            if origin is None:problems.append({'mode':row['mode'],'message':'Completion has no unique accepted transaction in the current reset epoch at tick '+str(row['tick'])})
        if row['req_valid'] and row['req_ready']:
            key=(epoch,row['req_id']);a={'sequence':len(accepted),'epoch':epoch,'tick':row['tick'],'id':row['req_id'],'mode':row['mode'],'data':row['req_data']};accepted.append(a)
            if key in pending:problems.append({'mode':row['mode'],'message':'Accepted ID reused while still outstanding at tick '+str(row['tick'])})
            pending[key]=a
    return {'stimulus':stimulus,'accepted':accepted,'completed':completed,'cancelled':cancelled,'outstanding':list(pending.values()),'problems':problems}
def accounting(evidence,roster,qualified_checks,required_modes):
    """Keep exposure ranges in the parent format and let its existing summarizer count them."""
    ctx=evidence['context'];basis='observation:'+fingerprint({'sources':evidence['source_sha256'],'clock':ctx['clock_ref'],'scope':ctx['scope_ref'],'sampling':ctx['sampling'],'checked_completion_modes':required_modes})
    qualified=ctx['dependencies_complete'] is True and all(text(ctx[k]) for k in ('scope_basis_ref','instrumentation_review_ref','oracle_ref','dependency_basis_ref'))
    values={k:[v['sequence'] for v in roster[k]] for k in ('stimulus','accepted','completed')};values['checked']=qualified_checks
    objectives=[{'id':k,'kind':'exposure','description':k+' event observations only; no sufficiency target','basis_ref':basis,'policy_ref':basis,
                 'eligible_states':['passed','failed'],'target':{'value':0,'unit':'events'}} for k in values]
    contract={'format':'opentools.campaign-contract.v1','campaign_ref':ctx['campaign_ref'],'scope_ref':ctx['scope_ref'],'configuration_ref':ctx['configuration_ref'],'model_ref':ctx['model_ref'],
              'population_ref':ctx['run_ref'],'population_complete':True,'required_run_refs':[ctx['run_ref']],'evidence_ref':basis,'objectives':objectives,
              'policy':{'ref':basis,'evidence_ref':basis,'allowed_recommendations':['inspect_effectiveness','seek_policy'],'limits':['Observation counts do not establish adequacy, closure, independent trials or stopping authority.']}}
    snapshot={'format':'opentools.campaign-snapshot.v1','campaign_ref':ctx['campaign_ref'],'snapshot_ref':ctx['run_ref']+':observation','scope_ref':ctx['scope_ref'],
              'captured_at':None,'mode':'cumulative','complete':True,'evidence_ref':ctx['window_ref'],'runs':[{'run_ref':ctx['run_ref'],'configuration_ref':ctx['configuration_ref'],'model_ref':ctx['model_ref'],
              'native_state':evidence['native']['status'],'state':'failed' if evidence['native']['status']=='FAIL' else 'passed','evidence_ref':ctx['checker_source_ref'],
              'measurements':[{'objective_id':k,'basis_ref':basis,'evidence_ref':ctx['window_ref'],'qualified':qualified,'complete':True,
                               'data':{'unit':'events','ranges':[{'space_ref':ctx['run_ref']+':'+k,'start':v,'stop':v+1,'evidence_ref':ctx['window_ref']} for v in ids]}} for k,ids in values.items()],
              'resources':[]}]}
    validate_contract(contract);validate_snapshot(snapshot);summary=summarize(contract,snapshot)
    # No wall-clock capture time is inferred from a simulation tick or file mtime.
    return {'contract':contract,'snapshot':snapshot,'summary':summary,'limits':'Timestamp unknown: these counts are reusable observations, not an interval-rate or campaign completion claim. Zero targets are accounting placeholders, not acceptance criteria.'}
def review(request,evidence,root='.'):
    intent(request);findings=[];gaps=[]
    report={'format':'opentools.checker-observation-review.v1','claim_id':request['claim_id'],'claim':request['claim'],'findings':findings,'gaps':gaps,'events':None,'native':None,'accounting':None,
            'fingerprints':{'intent':fingerprint(request),'evidence':fingerprint(evidence)},
            'limits':'Bounded single-positive-edge accepted/completed/check correspondence and explicit mode/reset scope. Supplied instrumentation/oracle/owner references are not authenticated. C++ measurement code and oracle adequacy require source review. No verification completeness, liveness, arbitrary UVM format or release claim.'}
    def finish():
        report['status']='review_required' if findings else 'incomplete' if gaps else 'observation_consistent_with_declared_contract';return report
    for key in ('owner_ref','basis_ref','policy_ref','mode_basis_ref'):
        if not text(request[key]):gaps.append('Independent intent missing '+key)
    try:revalidate(evidence,root)
    except (ValueError,OSError,KeyError,TypeError) as exc:gaps.append('Original native evidence unresolved: '+str(exc));return finish()
    ctx=evidence['context'];actual={k:evidence['source_sha256'] if k=='source_sha256' else ctx[k] for k in EXPECTED}
    for key,value in request['expected'].items():
        if not known(value):gaps.append('Independent expected '+key+' unknown')
        elif canonical(value)!=canonical(actual[key]):findings.append('Foreign/different '+key+'; native conclusions quarantined')
    if findings or any(v.startswith('Independent expected') for v in gaps):return finish()
    for key in ('scope_basis_ref','instrumentation_review_ref','oracle_ref','dependency_basis_ref'):
        if not text(ctx[key]):gaps.append('Native source/scope declaration missing '+key)
    if ctx['dependencies_complete'] is not True:gaps.append('Dependency capture not established complete')
    modes=request['required_modes']
    if modes is None:gaps.append('Required completion modes unknown');return finish()
    roster=events(evidence);report['events']=roster;report['native']=evidence['native'];valid=[];per_mode=[]
    for problem in roster['problems']:
        if problem['mode'] in modes:findings.append(problem['message'])
    completed_by_tick={c['tick']:c for c in roster['completed']};matches={};outside=[]
    for check in evidence['checks']:
        row=evidence['edges'][check['tick']];c=completed_by_tick.get(check['tick'])
        if row['mode'] not in modes:outside.append(check);continue
        if row['reset']==ctx['reset_active'] or c is None or check['id']!=c['id']:
            findings.append('Checker action is not the declared completion identity at tick '+str(check['tick']));continue
        if not row['enabled']:findings.append('Checker emitted an action while its measured enable is false at tick '+str(check['tick']))
        if check['observed']!=c['data']:findings.append('Checker observed data differs from the native completion at tick '+str(check['tick']));continue
        if c['sequence'] in matches:findings.append('Duplicate checker action for completion at tick '+str(check['tick']));continue
        matches[c['sequence']]=check
        if c['accepted_sequence'] is not None and row['enabled']:valid.append(c['sequence'])
    for mode in modes:
        required=[c for c in roster['completed'] if c['mode']==mode];missing=[c['sequence'] for c in required if c['sequence'] not in matches]
        disabled=[c['sequence'] for c in required if not c['enabled']]
        if missing:findings.append('Required completions lack checker actions in mode '+str(mode)+': '+str(missing))
        if disabled:findings.append('Checker disabled at required completions in mode '+str(mode)+': '+str(disabled))
        if not required:gaps.append('No completed work observed in required mode '+str(mode))
        per_mode.append({'mode':mode,'completed_sequences':[c['sequence'] for c in required],'checked_sequences':[c['sequence'] for c in required if c['sequence'] in valid],
                         'missing_sequences':missing,'disabled_sequences':disabled})
    if any(v['mode'] in modes for v in roster['outstanding']):gaps.append('Accepted work remains outstanding at the window end; completion/liveness is unresolved')
    report['mode_review']=per_mode;report['outside_requested_mode_checks']=outside
    # Counts stay useful even when there are observation findings; only matched identities qualify as checked exposure.
    report['accounting']=accounting(evidence,roster,valid,modes)
    return finish()
def exit_code(report):return {'observation_consistent_with_declared_contract':0,'review_required':1,'incomplete':2}[report['status']]
def markdown(report):
    def esc(v):return html.escape(str(v)).replace('|','&#124;').replace('\n','<br>')
    lines=['# Checker observation review','','Status: **'+report['status']+'**','',esc(report['claim']),'']
    if report['native']:lines+=['Native selected-checker result: **'+report['native']['status']+'**. Observation validity and functional outcome are separate.','']
    if report['accounting']:
        lines+=['| Observation | Qualified count |','| --- | --- |']+['| '+esc(v['id'])+' | '+str(v['known_value'])+' |' for v in report['accounting']['summary']['objectives']]+['']
    for title,key in [('Findings','findings'),('Missing evidence','gaps')]:lines+=['## '+title,'']+(['- '+esc(v) for v in report[key]] or ['None within the declared profile.'])+['']
    return '\n'.join(lines+[esc(report['limits']),''])
