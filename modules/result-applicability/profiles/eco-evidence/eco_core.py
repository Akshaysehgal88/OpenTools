"""Bounded changed-object review and exact report reuse through the parent audit."""
from pathlib import Path
from eco_common import BASIS,CLAIMS,IDENTITY,REPORTS,audit,canonical,data_file,digest,file_hash,folder,read_json,require,result_exit,text,validate_snapshot
from eco_records import fields,observed_phase,request,snapshot
from native_eco import capture,projection

def load(root,ref):
    path=folder(root,ref);ctx=read_json(data_file(path,'context.json'));require(ctx['run_ref']==ref,'Run directory/producer identity mismatch');e=capture(path,ctx);records={}
    for kind in REPORTS:
        p=data_file(path,kind+'.snapshot.json',optional=True)
        if p is None:
            records[kind]=snapshot(e,kind) if e['reports'][kind] is not None else None
            continue
        record=read_json(p);validate_snapshot(record)
        require(record['run_ref']==ref+'/'+kind and record['result']['producer_run_ref']==record['run_ref'],'Original report producer mismatch')
        require(record['result']['artifact']=={'path':ref+'/'+('sta.txt' if kind=='sta' else 'clock.stdout.txt'),'sha256':e['execution']['artifacts']['sta.txt' if kind=='sta' else 'clock.stdout.txt']},'Original artifact binding differs from retained execution')
        if e['reports'][kind] is not None:require(canonical(record)==canonical(snapshot(e,kind)),'Original snapshot differs from native source/scope/result')
        else:
            phase=record['fields'].get('scope.native_phase',{}).get('value')
            require(canonical(record['fields'])==canonical(fields(e,kind,phase)),'Original snapshot source/scope correspondence changed')
        records[kind]=record
    return e,records

def changes(before,after):
    a,b=before['graph'],after['graph'];items=[];unsupported=[]
    if a['cells']!=b['cells']:unsupported.append('native_instance_correspondence_or_master_changed')
    if a['placement']!=b['placement']:unsupported.append('physical_change_outside_endpoint_rewire_profile')
    if set(a['pins'])!=set(b['pins']):unsupported.append('native_pin_correspondence_changed')
    if a['ports']!=b['ports']:unsupported.append('native_boundary_correspondence_changed')
    for pin in sorted(set(a['pins'])|set(b['pins'])):
        old=a['pins'].get(pin);new=b['pins'].get(pin)
        if old==new:continue
        items.append({'native_pin':pin,'before':old,'after':new})
        if old is None or new is None or any(old[k]!=new[k] for k in ('cell','pin','direction','signal_type')):unsupported.append('pin_role_or_identity_change_outside_profile')
    return items,sorted(set(unsupported))

def review(root,policy):
    require(policy.get('format')=='opentools.eco-policy.v1','Unsupported ECO policy')
    before,b_records=load(root,policy['before']);after,a_records=load(root,policy['after'])
    result={'format':'opentools.eco-review.v1','status':'incomplete','before':before['context'],'after':after['context'],
            'changed_objects':[],'reports':[],'findings':[],'gaps':[],'next_actions':[],
            'native_counts':{'before_cells':len(before['graph']['cells']),'after_cells':len(after['graph']['cells'])},
            'owner_ref':policy.get('owner_ref'),'policy_sha256':digest(policy),
            'recheck_when':['object or role correspondence changes','report dependency, required phase or native model changes',
                            'selected evidence or approval conditions change','functional intent or power/clock/test assumptions change'],
            'limits':'Scoped evidence consequence/reuse review, not complete ECO signoff. Changed graph is not by itself a functional failure; unchanged scoped graph does not establish complete equivalence, parasitics, route legality or approval.'}
    def finding(kind,**d):result['findings'].append(dict(kind=kind,**d))
    def gap(kind,**d):result['gaps'].append(dict(kind=kind,**d))
    def finish():
        result['status']='review_required' if result['findings'] else 'incomplete' if result['gaps'] else 'selected_evidence_corresponds'
        result['exit_code']=1 if result['findings'] else 2 if result['gaps'] else 0;return result
    admitted=True
    for label,e in [('before',before),('after',after)]:
        binding=policy.get(label+'_binding',{})
        for k in IDENTITY:
            if binding.get('identity',{}).get(k)!=e['context'][k]:gap('scope_not_admitted',side=label,field=k);admitted=False
        selection={k:e['context'][k] for k in ('ports','cells','wake','clock_name','period','reset_asserted','mode_a','mode_b','cycles')}
        if canonical(binding.get('selection'))!=canonical(selection):gap('selected_objects_or_phase_not_admitted',side=label);admitted=False
        for k,actual in [('source_sha256',e['source_sha256']),('graph_sha256',e['file_sha256']['graph.txt']),('binary_sha256',e['execution']['binary_sha256']),('tools',e['execution']['tools'])]:
            if binding.get(k)!=actual:gap('artifact_not_admitted',side=label,field=k);admitted=False
        records=b_records if label=='before' else a_records
        for kind in REPORTS:
            if records[kind] is not None and binding.get('report_record_fingerprints',{}).get(kind)!=digest(records[kind]):gap('original_snapshot_not_admitted',side=label,report=kind);admitted=False
        for k in BASIS:
            if not e['context'].get(k):gap('missing_relationship_basis',side=label,field=k)
    if not admitted:return finish()
    for k in ('claim_id','claim','scope_ref','source_ref','owner_ref'):text(policy.get(k),k)
    if policy.get('inputs_complete') is not True:gap('incomplete_ECO_or_report_inventory')
    for claim in CLAIMS:
        value=policy.get('required_claims',{}).get(claim)
        if type(value) is not bool:gap('required_claim_strength_unknown',claim=claim)
        elif value:gap('required_claim_outside_qualified_reports',claim=claim)
    if policy.get('correspondence_ref') is None:gap('object_correspondence_unestablished');return finish()
    text(policy['correspondence_ref'],'correspondence source')
    items,unsupported=changes(before,after);result['changed_objects']=items
    for problem in unsupported:gap(problem)
    if unsupported:return finish()
    for k in ('scope_ref','design_ref','configuration_ref'):
        if before['context'][k]!=after['context'][k]:gap('cross_configuration_change_unqualified',field=k);return finish()
    obligations=policy.get('reports');require(isinstance(obligations,dict) and set(obligations)==set(REPORTS),'Both independently required report types must remain present')
    for kind in REPORTS:
        ob=obligations[kind];selected=ob.get('selected');require(selected in ('before','after'),'Select an original before/after report')
        record=b_records[kind] if selected=='before' else a_records[kind];source=before if selected=='before' else after
        req=request(after,kind,policy);rules=None;bridge=None;eligible=False;approval=ob.get('reviewed_reuse')
        if record is None:
            gap('selected_report_missing',report=kind)
            current=audit(a_records[kind],req,base_dir=Path(root)) if a_records[kind] is not None else None
            result['reports'].append({'report_type':kind,'selected':selected,'applicability':None,'current_cached_applicability':current,'request':req,'reuse_rule':None})
            result['next_actions'].append({'report':kind,'action':'use_matching_retained_current_result' if current and result_exit(current)==0 else 'locate_original_report_snapshot'})
            continue
        unqualified=sorted(set(record['fields']['scope.native_projection']['value']['unqualified_dependencies']+req['required_fields']['scope.native_projection']['value']['unqualified_dependencies']))
        if unqualified:gap('report_dependency_scope_unqualified',report=kind,reasons=unqualified)
        same_scope=canonical(record['fields']['scope.native_projection']['value'])==canonical(req['required_fields']['scope.native_projection']['value']) and canonical(record['fields']['scope.native_phase']['value'])==canonical(req['required_fields']['scope.native_phase']['value']) and record['fields']['scope.phase_ref']['value']==req['required_fields']['scope.phase_ref']['value']
        protected=('models.source_sha','library.source_sha','physical_library.source_sha','checker.source_sha','tools.profile','scope.context','scope.profile')
        stable=all(canonical(record['fields'][k]['value'])==canonical(req['required_fields'][k]['value']) for k in protected)
        eligible=same_scope and stable and not unqualified
        if selected=='before' and approval:
            pairs={k:{'observed':record['fields'][k]['value'],'requested':req['required_fields'][k]['value']} for k in ('implementation.netlist_sha','build.report_producer') if record['fields'][k]['value']!=req['required_fields'][k]['value']}
            exact=approval.get('run_ref')==record['run_ref'] and approval.get('after_run_ref')==after['context']['run_ref'] and approval.get('report_type')==kind and canonical(approval.get('pairs'))==canonical(pairs)
            refs=all(isinstance(approval.get(k),str) and approval[k].strip() for k in ('rule_ref','approved_by','basis_ref','reason'))
            if eligible and exact and refs and pairs:
                exceptions=[dict(field=key,**pair,**{k:approval[k] for k in ('rule_ref','approved_by','basis_ref','reason')}) for key,pair in pairs.items()]
                rules={'format':'opentools.result-reuse.v1','claim_id':req['claim_id'],'run_ref':record['run_ref'],'exceptions':exceptions};bridge='supplied_exact_pair_rule'
            elif not exact or not refs:gap('reuse_approval_missing_stale_or_unestablished',report=kind)
        compared=audit(record,req,rules,base_dir=Path(root));current=audit(a_records[kind],req,base_dir=Path(root)) if a_records[kind] is not None else None
        entry={'report_type':kind,'selected':selected,'dependency_projection_unchanged':same_scope,'protected_conditions_unchanged':stable,'conditional_reuse_eligible':eligible,'bridge':bridge,'applicability':compared,'current_cached_applicability':current,'request':req,'reuse_rule':rules}
        result['reports'].append(entry)
        if result_exit(compared)==1:finding('selected_report_inapplicable',report=kind,mismatches=compared['mismatches'])
        elif result_exit(compared)==2:gap('selected_report_unresolved',report=kind,unknowns=compared['unknowns'])
        if result_exit(compared)!=0:
            if current and result_exit(current)==0 and not unqualified:result['next_actions'].append({'report':kind,'action':'use_matching_retained_current_result','run_ref':after['context']['run_ref']})
            elif current and current['native_result']['outcome']=='fail':result['next_actions'].append({'report':kind,'action':'correct_proposal_or_required_condition_then_revalidate','native_result':current['native_result']})
            else:result['next_actions'].append({'report':kind,'action':'obtain_the_specific_missing_scope_or_native_result'})
    return finish()
