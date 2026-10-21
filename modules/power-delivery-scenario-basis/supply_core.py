"""Scenario correspondence, native status and unsupported claims remain separate."""
from supply_common import BASIS,CLAIMS,IDENTITY,digest,exit_code,known,require
def binding(e):
    return {'identity':{k:e['context'][k] for k in IDENTITY},'context_sha256':digest(e['context']),
            'source_sha256':e['source_sha256'],'original_artifacts':e['execution']['artifacts'],
            'command_sha256':e['execution']['command_sha256'],'tool_sha256':e['execution']['tool_sha256']}
def observed(e):
    c=e['context']
    return {**{'source/'+k:e['source_sha256'][k] for k in ('cells.lef','cells.lib','design.def')},
            'setup':c['setup'],'scenario':c['scenario'],'tool_sha256':e['execution']['tool_sha256'],
            'configuration':{k:c[k] for k in ('design_ref','configuration_ref')},'point':e['native']['point']}
def review(e,request,expected_binding):
    require(request.get('format')=='opentools.supply-request.v1','Unsupported scenario request')
    result={'format':'opentools.supply-review.v1','status':'incomplete','scope':e['context'],'claim':request.get('claim'),
      'request_sha256':digest(request),'original_native_status':e['native_status'],'original_voltage_points':e['reports']['voltage.csv'],
      'original_physical_supply':e['native'],
      'resolved_native_sources':None,'resolved_native_currents':None,'fields':[],'findings':[],'gaps':[],
      'owner_ref':request.get('owner_ref'),'next_actions':[],
      'recheck_when':['physical supply or source mapping changes','corner, resistance or library changes','load/activity scope or annotation changes',
                      'domain state, concurrency or sequence changes','native analysis artifacts or requested claim changes'],
      'limits':'Static-scenario correspondence only. Solver completion, a low reported drop and matching supplied assumptions are not IR acceptance, dynamic wake validation, EM lifetime, load-model correctness or full-chip signoff. References and byte identities are not authenticated authority.'}
    def gap(kind,**d):result['gaps'].append(dict(kind=kind,**d))
    def finding(kind,**d):result['findings'].append(dict(kind=kind,**d))
    def finish():
        result['exit_code']=exit_code(result);result['status']='scenario_mismatch_or_native_failure' if result['findings'] else 'incomplete' if result['gaps'] else 'static_scenario_corresponds';return result
    if expected_binding!=binding(e):gap('selected_evidence_not_admitted');return finish()
    if request.get('scope_ref')!=e['context']['scope_ref']:gap('foreign_request_scope');return finish()
    for k in ('claim_id','claim','source_ref','owner_ref'):
        if not known(request.get(k)):gap('missing_original_request_basis',field=k)
    if request.get('inputs_complete') is not True:gap('incomplete_supply_or_scenario_inventory')
    for k in BASIS:
        if not known(e['context'].get(k)):gap('missing_observed_relationship_basis',field=k)
        if not known(request.get('basis',{}).get(k)):gap('missing_required_relationship_basis',field=k)
    for k in CLAIMS:
        required=request.get('required_claims',{}).get(k)
        if type(required) is not bool:gap('required_claim_strength_unknown',claim=k)
        elif required:gap('required_claim_outside_static_analysis',claim=k)
    facts=observed(e);wanted=request.get('fields');require(isinstance(wanted,dict) and set(wanted)==set(facts),'Full static scenario field roster required')
    for name,old in facts.items():
        new=wanted[name];status='unknown' if not known(old) or not known(new) else 'equal' if old==new else 'mismatch'
        if name=='point' and known(old) and known(new):
            require(set(new)==set(old)=={'process','voltage','temperature'},'Point needs process,voltage,temperature')
            status='equal' if all(type(new[k]) in (int,float) and abs(old[k]-new[k])<=1e-6 for k in new) else 'mismatch'
        result['fields'].append({'field':name,'observed':old,'required':new,'status':status})
        if status=='unknown':gap('scenario_field_unknown',field=name)
        elif status=='mismatch':finding('scenario_field_differs',field=name)
    for problem in e['report_gaps']:gap(**problem)
    statuses=e['native_status']
    if statuses['connectivity']!={'tcl_catch':0,'native_result':'1'}:finding('native_physical_connectivity_failed',native_result=statuses['connectivity'])
    if statuses['analysis']['tcl_catch']!=0:gap('native_static_analysis_not_completed',native_result=statuses['analysis'])
    if e['native_corner'] is not None and e['native_corner']!=e['context']['setup']['corner']:gap('native_corner_not_bound_to_setup')
    voltages=e['reports']['voltage.csv'];network=e['reports']['network.sp'];n=e['native'];s=e['context']['setup']
    if voltages is None:gap('original_voltage_result_unavailable')
    else:
        if set(voltages)!=set(n['iterms']):gap('native_voltage_population_incomplete')
        for name,pin in n['iterms'].items():
            if not pin['position_known'] or pin['status'] not in ('PLACED','FIRM','LOCKED'):gap('native_load_location_unestablished',terminal=name)
            elif name in voltages and any(abs(v*n['units']-x)>1 for v,x in zip(voltages[name]['xy_um'],pin['xy_dbu'])):gap('native_voltage_to_terminal_mapping_unestablished',terminal=name)
    if network is None:gap('original_resolved_network_unavailable')
    else:
        result['resolved_native_sources']=network['sources'];result['resolved_native_currents']=network['sinks']
        sinks={v['terminal']:v for v in network['sinks'].values()}
        if len(sinks)!=len(network['sinks']) or set(sinks)!=set(n['iterms']):gap('native_current_population_unqualified')
        for terminal,sink in sinks.items():
            if terminal not in n['iterms']:continue
            pin=n['iterms'][terminal];expected=s['powers_W'][pin['instance']]/s['net_voltage_V'];tol=max(1e-9,abs(expected)*5.1e-4)
            if abs(sink['value']-expected)>tol:gap('native_current_to_power_override_unestablished',terminal=terminal)
            node='ITermNode_'+voltages[terminal]['layer']+'_'+'_'.join(map(str,pin['xy_dbu'])) if voltages is not None and terminal in voltages else None
            if node is None or sink['node']!=node:gap('native_current_to_voltage_mapping_unestablished',terminal=terminal)
        requested=sorted(row[3] for row in s['source_rows_um_V']);resolved=sorted(v['value'] for v in network['sources'].values())
        if len(requested)!=len(resolved) or any(abs(a-b)>1e-6 for a,b in zip(requested,resolved)):gap('native_source_population_outside_qualified_profile')
    if result['findings']:result['next_actions'].append({'action':'resolve_the_changed_scenario_or_physical_grid_and_check_retained_matching_results'})
    if result['gaps']:result['next_actions'].append({'action':'recover_specific_original_basis_or_obtain_the_required_native_analysis','gaps':[g['kind'] for g in result['gaps']]})
    return finish()
