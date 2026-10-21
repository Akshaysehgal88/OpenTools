"""Separate notice applicability,observed efficacy,interaction and approval scope."""
from erratum_common import IDENTITY,audit,audit_exit,canonical,digest,known,read_json,require,shape,text,uint,validate_fields
from native_erratum import SOURCES,fields,load,snapshot
from predicates import evaluate,validate as validate_predicate
BASE={'scope.identity','source.kind','source.model_sha256','firmware.image_sha256','native.guard_need'}
LIMITS='One supplied synthetic notice and selected owned model path. Applicability,current checker outcome,workaround efficacy,interaction premises and supplied approval correspondence are separate. No unpublished-erratum discovery,real silicon or firmware ISA qualification,silicon safety,release approval or automatic workaround application/removal.'

def validate_notice(n):
    shape(n,{'format','notice_id','revision','source_ref','owner_ref','predicate','profiles','mitigation','interaction'})
    require(n['format']=='opentools.erratum-notice.v1' and text(n['notice_id']) and text(n['revision']),'Versioned supplied notice required')
    for k in ('source_ref','owner_ref'):require(n[k] is None or text(n[k]),'Notice source/owner or null required')
    validate_predicate(n['predicate']);require(isinstance(n['profiles'],dict) and 1<=len(n['profiles'])<=8,'Bounded notice profiles required')
    for name,p in n['profiles'].items():
        require(text(name),'Notice profile required');shape(p,{'scope_ref','min_guard_ticks','basis_ref'});require(text(p['scope_ref']) and uint(p['min_guard_ticks'],4)>0,'Scoped positive guard interval required');require(p['basis_ref'] is None or text(p['basis_ref']),'Guard basis or null required')
    m=n['mitigation'];shape(m,{'guard_field','required_fields','source_ref'});require(m['guard_field']=='workaround.guard_ticks','Qualified guard semantic role required');validate_fields(m['required_fields']);require({'firmware.wa_ordered','workaround.force_clock'}<=set(m['required_fields']),'Do not omit ordering/clock mitigation premises');require(m['source_ref'] is None or text(m['source_ref']),'Mitigation source or null required')
    i=n['interaction'];shape(i,{'id','enabled_field','required_fields','source_ref','owner_ref'});require(text(i['id']) and text(i['enabled_field']) and i['required_fields'],'One explicit interaction premise required');validate_fields(i['required_fields'])
    for k in ('source_ref','owner_ref'):require(i[k] is None or text(i[k]),'Interaction owner/source or null required')

def validate_request(q):
    shape(q,{'format','claim_ref','scope_ref','run_ref','owner_ref','requirements_ref','review_cut_ref','intent','notice_profile','notice_sha256','binding','required_fields','approval'})
    require(q['format']=='opentools.erratum-request.v1' and text(q['claim_ref']) and text(q['scope_ref']) and text(q['notice_profile']),'Independent review scope required')
    require(q['run_ref'] is None or text(q['run_ref']),'Selected original run or null required');require(q['intent'] in ('apply','retain','remove'),'Explicit maintenance intent required')
    for k in ('owner_ref','requirements_ref','review_cut_ref'):require(q[k] is None or text(q[k]),'Owner,requirements and current review cut or null required')
    shape(q['binding'],{'identity','sources','context_sha256','command_sha256'});shape(q['binding']['identity'],IDENTITY);require(all(text(v) for v in q['binding']['identity'].values()),'Expected native identity required');shape(q['binding']['sources'],SOURCES)
    for v in [q['notice_sha256'],*q['binding']['sources'].values(),q['binding']['context_sha256'],q['binding']['command_sha256']]:require(v is None or isinstance(v,str) and len(v)==64 and all(ch in '0123456789abcdef' for ch in v),'Expected SHA256 or null required')
    validate_fields(q['required_fields']);require(BASE<=set(q['required_fields']) and len(q['required_fields'])<=32,'Do not omit selected source/model/image and guard scope')
    if q['approval'] is not None:
        a=q['approval'];shape(a,{'status','source_ref','decision_ref','cut_ref','notice_sha256','scope_ref','mode_ref','image_sha256','intent'})
        require(a['status'] in ('approved','pending','withdrawn',None),'Explicit supplied approval status required')
        for k in set(a)-{'status'}:require(a[k] is None or text(a[k]),'Approval field or null required')

def review(root,n,q):
    validate_notice(n);validate_request(q);findings=[];gaps=[];quarantine=[];base=None;pred=None;mitigation=None;interaction=None;approval=None;native_result=None;implementation=None;captured=None;notice_changed=request_changed=None
    def add(out,code,detail):out.append({'code':code,'detail':detail})
    def finish():
        invalid=quarantine or base is not None and audit_exit(base)==1
        status='INAPPLICABLE_EVIDENCE' if invalid else 'REVIEW_REQUIRED' if findings else 'INCOMPLETE' if gaps else 'REVIEW_PACKET_ACCOUNTED'
        return {'format':'opentools.erratum-review.v1','status':status,'exit_code':1 if invalid or findings else 2 if gaps else 0,'claim_ref':q['claim_ref'],'scope_ref':q['scope_ref'],'intent':q['intent'],'owner_ref':q['owner_ref'],'requirements_ref':q['requirements_ref'],'notice_id':n['notice_id'],'notice_revision':n['revision'],'notice_digest':digest(n),'request_digest':digest(q),'notice_changed':notice_changed,'request_changed':request_changed,'captured_sources':captured,'source_comparison':base,'native_result':native_result,'implementation_observation':implementation,'applicability':pred,'mitigation':mitigation,'interaction':interaction,'supplied_approval':approval,'findings':findings,'gaps':gaps,'quarantine':quarantine,'recheck_when':['notice,stepping/fuses,feature,firmware baseline or operating mode changes','workaround implementation,guard/clock behavior or dependent exception changes','selected evidence,maintenance intent,approval scope or current review cut changes'],'limits':LIMITS}
    for k in ('owner_ref','requirements_ref','review_cut_ref'):
        if q[k] is None:add(gaps,'missing_review_basis',k)
    for k in ('source_ref','owner_ref'):
        if n[k] is None:add(gaps,'missing_notice_basis',k)
    if q['notice_sha256'] is None:add(gaps,'missing_expected_notice','Original requested notice version is missing')
    elif q['notice_sha256']!=digest(n):add(quarantine,'notice_not_requested','Supplied notice does not match the independently selected version')
    p=n['profiles'].get(q['notice_profile'])
    if p is None:add(quarantine,'notice_profile_missing','No scoped rule for the requested review');return finish()
    if p['scope_ref']!=q['scope_ref']:add(quarantine,'foreign_notice_scope','Notice profile belongs to a different condition scope')
    if p['basis_ref'] is None:add(gaps,'missing_guard_basis','Required active-clock interval needs its original source')
    if q['run_ref'] is None:add(gaps,'missing_native_observation','No selected original result');return finish()
    e=load(root,q['run_ref']);c=e['context'];s=snapshot(e);f=fields(e);native_result=s['result'];captured={'notice':e['capture_notice'],'request':e['capture_request']};notice_changed=digest(n)!=digest(e['capture_notice']);request_changed=digest(q)!=digest(e['capture_request'])
    implementation={k:f[k] for k in ('firmware.base_ordered','firmware.wa_ordered','workaround.requested_guard_ticks','workaround.guard_ticks','workaround.force_clock')}
    for k in IDENTITY:
        if c[k]!=q['binding']['identity'][k]:add(quarantine,'foreign_native_identity',k)
    if c['scope_ref']!=q['scope_ref']:add(quarantine,'foreign_native_scope','Native result is outside the review scope')
    for k,v in q['binding']['sources'].items():
        if v is None:add(gaps,'missing_expected_source',k)
        elif v!=e['source_sha256'][k]:add(quarantine,'stale_or_foreign_source',k)
    for k,name in [('context_sha256','context.json'),('command_sha256','command.json')]:
        if q['binding'][k] is None:add(gaps,'missing_original_binding',name)
        elif q['binding'][k]!=e['file_sha256'][name]:add(quarantine,'foreign_context_or_invocation',name)
    req={'format':'opentools.result-request.v1','claim_id':q['claim_ref'],'claim':'Selected owned delivery checker and native source/model/image conditions for supplied erratum maintenance.','scope_ref':q['scope_ref'],'required_fields':q['required_fields'],'required_outcome':'any_observed'}
    base=audit(s,req,base_dir=root)
    if base['unknowns']:add(gaps,'source_comparison_unknown',base['unknowns'])
    if native_result['outcome']=='fail':add(findings,'observed_delivery_check_failure','Actual selected delivery/data check failed;this alone does not identify an erratum cause')
    mandatory={v['field']:v['status'] for v in base['fields']};admitted=not quarantine and all(mandatory.get(k)=='equal' for k in BASE)
    if admitted:
        pred=evaluate(n['predicate'],f)
        if pred['truth'] is None:add(gaps,'applicability_unresolved','Do not infer underlying applicability from current checker PASS/FAIL')
        if pred['truth'] is True:
            m=n['mitigation'];a=audit(s,{'format':'opentools.result-request.v1','claim_id':q['claim_ref']+'/mitigation','claim':'Supplied workaround ordering and clock premises.','scope_ref':q['scope_ref'],'required_fields':m['required_fields'],'required_outcome':'any_observed'},base_dir=root)
            guard=f.get(m['guard_field']);guard_ok=None if not known(guard) else type(guard['value']) is int and guard['value']>=p['min_guard_ticks']
            mitigation={'premise_comparison':a,'observed_guard':guard,'required_guard_ticks':p['min_guard_ticks'],'guard_corresponds':guard_ok,'selected_checker_passed':native_result['outcome']=='pass','effective_within_selected_model':audit_exit(a)==0 and guard_ok is True and native_result['outcome']=='pass'}
            if m['source_ref'] is None:add(gaps,'missing_mitigation_source','Do not infer mitigation obligations from an enabled flag')
            if audit_exit(a)==1:add(findings,'workaround_premise_not_met',a['mismatches'])
            if a['unknowns'] or guard_ok is None:add(gaps,'workaround_efficacy_unresolved','Ordering,clock or guard evidence missing')
            if guard_ok is False:add(findings,'workaround_guard_too_short','Actual active interval is below the original scoped requirement')
            if q['intent']=='remove':add(findings,'removal_conditions_not_established','Underlying conditions remain affected;passing with the workaround enabled is not removal evidence')
        elif pred['truth'] is False:mitigation={'state':'not_required_by_this_notice_in_selected_conditions','limits':'Does not establish safety after feature,mode,image or scope changes.'}
        i=n['interaction'];enabled=f.get(i['enabled_field'])
        if not known(enabled):interaction={'state':'unknown','enabled':enabled};add(gaps,'interaction_enable_unknown','Missing actual dependent-exception condition')
        elif enabled['value'] is True:
            a=audit(s,{'format':'opentools.result-request.v1','claim_id':q['claim_ref']+'/interaction','claim':'Independent current clock/power exception premise after workaround changes.','scope_ref':q['scope_ref'],'required_fields':i['required_fields'],'required_outcome':'any_observed'},base_dir=root);interaction={'state':'premise_holds' if audit_exit(a)==0 else 'premise_false' if audit_exit(a)==1 else 'unknown','id':i['id'],'comparison':a}
            if audit_exit(a)==1:add(findings,'workaround_invalidates_dependent_premise',a['mismatches'])
            if a['unknowns']:add(gaps,'interaction_premise_unresolved',a['unknowns'])
            if i['source_ref'] is None or i['owner_ref'] is None:add(gaps,'missing_interaction_basis','Original exception source/owner required')
        elif enabled['value'] is False:interaction={'state':'not_enabled_in_selected_context','id':i['id']}
        else:interaction={'state':'unknown','enabled':enabled};add(gaps,'interaction_enable_type_unknown','Boolean selected exception state required')
    else:add(gaps,'native_composition_unestablished','Do not compose foreign or unresolved model/image/scope evidence')
    a=q['approval']
    if a is None:approval={'state':'missing'};add(gaps,'current_approval_missing','Obtain the existing scoped decision;no approval is inferred')
    else:
        mismatches=[];unknowns=[]
        for k,v in {'cut_ref':q['review_cut_ref'],'notice_sha256':digest(n),'scope_ref':q['scope_ref'],'mode_ref':c['mode_ref'],'image_sha256':e['source_sha256']['firmware.txt'],'intent':q['intent']}.items():
            if a[k] is None or v is None:unknowns.append(k)
            elif a[k]!=v:mismatches.append(k)
        for k in ('source_ref','decision_ref'):
            if a[k] is None:unknowns.append(k)
        if a['status'] in (None,'pending'):unknowns.append('status')
        if a['status']=='withdrawn':mismatches.append('status_withdrawn')
        approval={'state':'does_not_correspond' if mismatches else 'unresolved' if unknowns else 'supplied_record_corresponds','record':a,'mismatched_fields':mismatches,'unknown_fields':unknowns,'limits':'Supplied decision correspondence only;not authenticated authority or permission to apply/remove software.'}
        if mismatches:add(findings,'approval_record_does_not_correspond',mismatches)
        if unknowns:add(gaps,'approval_record_unresolved',unknowns)
    return finish()

def markdown(r):
    import html
    def esc(v):return html.escape(str(v)).replace('|','&#124;').replace('\n',' ').replace('\r',' ')
    p=r['applicability'];lines=['# Erratum and workaround review','',r['status'],'',f"Notice: {esc(r['notice_id'])} revision {esc(r['notice_revision'])}; owner: {esc(r['owner_ref'])}.",'',f"Requested intent: {esc(r['intent'])}; underlying applicability: {esc(p['state'] if p else 'unestablished')}.",f"Native observation: {esc(r['native_result']['native_status'] if r['native_result'] else 'missing')}.",'',f"Supplied approval: {esc(r['supplied_approval']['state'] if r['supplied_approval'] else 'unestablished')}.",f"Changed notice/question: {esc(r['notice_changed'])}/{esc(r['request_changed'])}.",'']
    if p:
        lines+=['| Predicate | Source field | Truth |','|---|---|---|']
        for v in p['nodes']:lines.append('| '+esc(v['path'])+' | '+esc(v.get('field',v['op']))+' | '+esc(v['truth'])+' |')
    if r['mitigation']:lines+=['',f"Mitigation: {esc(r['mitigation'].get('state',r['mitigation'].get('effective_within_selected_model')))}."]
    if r['interaction']:lines+=['',f"Dependent premise: {esc(r['interaction']['state'])}."]
    lines.append('')
    for group in ('quarantine','findings','gaps'):
        for v in r[group]:lines.append('- '+group+': '+esc(v['code'])+'; '+esc(v['detail']))
    return '\n'.join(lines+['',LIMITS,''])
