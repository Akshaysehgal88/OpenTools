"""Compare native STA clock setup with the original selected-mode contract."""
from lineage_common import BASIS,CLAIMS,IDENTITY,digest,exit_code,number,require
def binding(e):
    return {'context_sha256':digest(e['context']),'source_sha256':e['source_sha256'],
            'original_artifacts':e['execution']['artifacts'],'command_sha256':e['execution']['command_sha256'],'tool_sha256':e['execution']['tool_sha256']}
def review(e,contract,expected_binding):
    require(contract.get('format')=='opentools.sta-lineage-contract.v1','Unsupported mode contract')
    n=e['native'];result={'format':'opentools.sta-lineage-review.v1','status':'incomplete','scope':e['context'],
      'original_native_objects':n,'findings':[],'gaps':[],'endpoint_review':[],'clock_review':[],'owner_ref':contract.get('owner_ref'),
      'contract_sha256':digest(contract),'next_actions':[],
      'recheck_when':['clock definitions or native lineage change','mux/gate cases, mode, reset or power premises change',
                      'required consumer population changes','source/library/tool/report identity changes','requested claim or receiving ownership changes'],
      'limits':'One mode/tree native STA setup review. Clock definition and endpoint association do not establish physical edges, power/reset readiness, waveform safety, CDC/RDC, other modes or timing signoff. Supplied references and hashes do not authenticate authority.'}
    def gap(kind,**d):result['gaps'].append(dict(kind=kind,**d))
    def finding(kind,**d):result['findings'].append(dict(kind=kind,**d))
    def finish():
        result['exit_code']=exit_code(result);result['status']='review_required' if result['findings'] else 'incomplete' if result['gaps'] else 'clock_contract_corresponds';return result
    if expected_binding!=binding(e):gap('selected_evidence_not_admitted');return finish()
    if contract.get('identity')!={k:e['context'][k] for k in IDENTITY[1:]}:gap('foreign_mode_or_configuration');return finish()
    for k in ('source_ref','owner_ref','claim'):
        if not isinstance(contract.get(k),str) or not contract[k].strip():gap('missing_original_contract_basis',field=k)
    if contract.get('inputs_complete') is not True:gap('incomplete_clock_or_consumer_inventory')
    for k in BASIS:
        if not e['context'].get(k):gap('missing_observed_relationship_basis',field=k)
        if not contract.get('basis',{}).get(k):gap('missing_required_relationship_basis',field=k)
    for claim in CLAIMS:
        v=contract.get('required_claims',{}).get(claim)
        if type(v) is not bool:gap('required_claim_strength_unknown',claim=claim)
        elif v:gap('required_claim_outside_native_setup',claim=claim)
    sources=contract.get('design_sources');require(isinstance(sources,dict) and set(sources)=={'design.v','cells.lef','cells.lib'},'Full design/library source roster required')
    for k,wanted in sources.items():
        if wanted is None:gap('required_source_identity_unknown',file=k)
        elif wanted!=e['source_sha256'][k]:finding('design_or_library_identity_differs',file=k)
    cases=contract['cases'];require(isinstance(cases,dict) and set(cases)==set(n['cases']),'Complete mode-port inventory required')
    for port,wanted in cases.items():
        if wanted is None or n['cases'][port] not in ('0','1'):gap('mode_case_unestablished',port=port,observed=n['cases'][port],required=wanted)
        else:
            require(type(wanted) is int and wanted in (0,1),'Required case must be binary/null')
            if int(n['cases'][port])!=wanted:finding('selected_mode_case_differs',port=port,observed=n['cases'][port],required=wanted)
    clocks=contract['clocks'];require(isinstance(clocks,dict) and clocks,'Required clock inventory missing')
    for name in sorted(set(clocks)-set(n['clocks'])):finding('required_clock_missing',clock=name)
    for name in sorted(set(n['clocks'])-set(clocks)):finding('unexpected_clock_in_selected_tree',clock=name)
    events={}
    for event in n['generated_events']:events.setdefault(event['name'],[]).append(event)
    for name in set(events)-{k for k,v in n['clocks'].items() if v['is_generated']}:gap('creation_lifecycle_outside_final_clock_inventory',clock=name)
    for name,wanted in clocks.items():
        require(set(wanted)=={'period_ns','is_generated','is_propagated','targets','waveform_ns','lineage'},'Complete clock contract fields required')
        actual=n['clocks'].get(name)
        if actual is None:continue
        if not wanted['is_generated']:require(wanted['lineage'] is None,'Root contract cannot declare generated lineage')
        if actual['waveform_valid']!=1:gap('native_constraint_waveform_unresolved',clock=name)
        for key in ('period_ns','is_generated','is_propagated','targets','waveform_ns'):
            expected=wanted[key];observed=actual[key]
            if expected is None:gap('clock_requirement_unknown',clock=name,field=key);continue
            if key=='period_ns':equal=abs(number(expected,'required period')-observed)<=1e-6
            elif key=='waveform_ns':equal=isinstance(expected,list) and len(expected)==len(observed) and all(abs(number(a,'required edge')-b)<=1e-6 for a,b in zip(expected,observed))
            else:equal=expected==observed
            if not equal:finding('native_clock_field_differs',clock=name,field=key,observed=observed,required=expected)
        if actual['is_generated']:
            journal=events.get(name,[])
            if n['trace']!={'initialized':1,'active':0,'ended':1,'initial_clocks':0} or len(journal)!=1:gap('native_lineage_capture_incomplete_or_ambiguous',clock=name)
            else:
                event=journal[0];lineage=wanted['lineage']
                if event['master'] is None or not event['current_object_matches']:gap('native_explicit_master_or_object_unestablished',clock=name)
                elif event['master'] not in n['clocks']:gap('native_master_outside_final_clock_inventory',clock=name)
                if event['targets']!=actual['targets']:gap('native_creation_targets_differ_from_final_objects',clock=name)
                if event['multiply_by'] or event['invert'] or event['combinational'] or event['add'] or event['native_edges'] or event['native_shifts'] or event['duty_cycle']:gap('generation_outside_single_pass_divide_profile',clock=name)
                if lineage is None:gap('required_lineage_unknown',clock=name)
                else:
                    require(set(lineage)=={'master','reference_source','divide_by'},'Explicit master/reference/divide required')
                    for key,value in lineage.items():
                        if value is None:gap('required_lineage_unknown',clock=name,field=key)
                        elif event[key] is not None and event[key]!=value:finding('resolved_native_lineage_differs',clock=name,field=key,observed=event[key],required=value)
        result['clock_review'].append({'clock':name,'native':actual,'required':wanted,'creation_events':events.get(name,[])})
    endpoints=contract['clock_pin_requirements'];require(isinstance(endpoints,dict) and endpoints and all(isinstance(v,list) and v for v in endpoints.values()),'Every required register clock pin needs explicit clock names')
    for pin in sorted(set(endpoints)-set(n['register_clock_pins'])):finding('required_register_clock_pin_missing',pin=pin)
    for pin in sorted(set(n['register_clock_pins'])-set(endpoints)):finding('native_consumer_missing_from_contract',pin=pin)
    for pin,required in endpoints.items():
        associated=sorted(name for name,c in n['clocks'].items() if pin in c['clock_pins'])
        if associated!=sorted(required):finding('required_consumer_clock_coverage_differs',pin=pin,observed=associated,required=required)
        result['endpoint_review'].append({'pin':pin,'native_clocks':associated,'required_clocks':required})
    require(type(contract['require_selected_path']) is bool,'Explicit selected-path requirement needed')
    if contract['require_selected_path'] and not n['path_count']:finding('required_selected_path_context_absent',endpoint=n['endpoint'])
    if result['findings']:result['next_actions'].append({'action':'review_the_specific_definition_mode_or_consumer_mismatch_and_retained_control','owner_ref':contract.get('owner_ref')})
    if result['gaps']:result['next_actions'].append({'action':'recover_missing_original_intent_or_native_lineage_basis','gaps':[g['kind'] for g in result['gaps']]})
    return finish()
