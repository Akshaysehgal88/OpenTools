"""Review one physical intervention against retained independent region intent."""
from physical_common import BASIS,CLAIMS,IDENTITY,box,digest,exit_code,overlap,require,text

def binding(e):
    return {'identity':{k:e['context'][k] for k in IDENTITY},'setup_sha256':digest(e['context']['setup']),
            'source_sha256':e['source_sha256'],'native_export_sha256':e['file_sha256']['native.jsonl'],
            'database_sha256':e['file_sha256']['native.odb'],'sdc_sha256':e['file_sha256']['consumed.sdc'],
            'command_sha256':e['file_sha256']['native.command.json'],'tool_sha256':e['execution']['tool_sha256']}

def metric(e):
    n=e['native'];problems=[];points=[]
    if n['net_bterms']:problems.append('boundary_terminal_geometry_not_qualified')
    for name in n['net_terms']:
        pin=n['pins'][name]
        if not pin['position_known']:problems.append('selected_pin_position_unknown')
        else:points.append(pin['xy'])
    if not points:problems.append('selected_net_has_no_observed_pin_positions')
    if points:
        xs,ys=zip(*points);observed=[min(xs),min(ys),max(xs),max(ys)]
        if observed!=n['net_bbox']:problems.append('selected_terminal_bbox_correspondence_unestablished')
    b=n['net_bbox'];value=b[2]-b[0]+b[3]-b[1]
    return {'definition':'selected-net terminal bounding-box half perimeter; not routed wirelength',
            'native_bbox_dbu':b,'derived_value_dbu':value,'database_units_per_um':n['units'],
            'geometry_gaps':sorted(set(problems)),'source_ref':e['context']['run_ref']+'/native.jsonl#NET_BBOX'}

def review(before,after,policy):
    require(policy.get('format')=='opentools.physical-policy.v1','Unsupported physical policy')
    require(before.get('format')==after.get('format')=='opentools.physical-evidence.v1','Unsupported native evidence')
    result={'format':'opentools.physical-review.v1','status':'incomplete',
            'before':before['context'],'after':after['context'],'changed_instances':[],
            'native_placement':{'before':before['native']['placement_check'],'after':after['native']['placement_check']},
            'native_paths':{'before':before['native']['paths'],'after':after['native']['paths']},
            'experiment':{'conditions':[],'qualification':'unestablished'},'region_review':None,'metric':None,
            'findings':[],'gaps':[],'next_actions':[],'owner_ref':policy.get('owner_ref'),'policy_sha256':digest(policy),
            'recheck_when':['region, access or boundary intent changes','proposal, placement or blockage changes',
                            'net/pin/object correspondence changes','clock/domain, performance, power or analysis conditions change',
                            'native reports, libraries, tool, source or receiving ownership changes'],
            'limits':'One physical intervention review. Matching geometry/conditions and native placement success do not establish congestion, routed wirelength, timing/throughput, macro access, isolation or physical signoff. Sources and approval are supplied, not authenticated.'}
    def gap(kind,**d):result['gaps'].append(dict(kind=kind,**d))
    def finding(kind,**d):result['findings'].append(dict(kind=kind,**d))
    def finish():
        result['exit_code']=exit_code(result);result['status']='findings' if result['findings'] else 'incomplete' if result['gaps'] else 'within_declared_review_scope';return result
    admitted=True
    for side,e in (('before',before),('after',after)):
        if policy.get(side+'_binding')!=binding(e):gap('proposal_evidence_not_admitted',side=side);admitted=False
        if e.get('qualified_batch_loader') is not True:gap('native_loader_not_qualified',side=side);admitted=False
        for k in BASIS:
            if not e['context'].get(k):gap('missing_relationship_basis',side=side,field=k)
    if not admitted:return finish()
    for k in ('claim_id','claim','scope_ref','source_ref','owner_ref'):
        if policy.get(k) is None:gap('missing_original_review_basis',field=k)
        else:text(policy[k],k)
    if policy.get('inputs_complete') is not True:gap('incomplete_region_or_obligation_inventory')
    for claim in CLAIMS:
        v=policy.get('required_claims',{}).get(claim)
        if type(v) is not bool:gap('required_claim_strength_unspecified',claim=claim)
        elif v:gap('required_claim_outside_bounded_observations',claim=claim)
    if not policy.get('correspondence_ref'):gap('object_correspondence_unestablished');return finish()
    a,b=before['native'],after['native'];ca,cb=before['context'],after['context']
    for k in IDENTITY[1:]:
        if ca[k]!=cb[k]:gap('foreign_or_changed_configuration',field=k);return finish()
    if policy['scope_ref']!=ca['scope_ref']:gap('requested_scope_not_admitted');return finish()
    selection=policy.get('selection',{})
    if selection.get('net')!=a['selected_net'] or selection.get('net')!=b['selected_net'] or selection.get('endpoint_names')!=a['net_terms'] or selection.get('endpoint_names')!=b['net_terms']:
        gap('original_net_or_endpoint_selection_not_admitted');return finish()
    conditions=result['experiment']['conditions']
    def fixed(name,old,new):
        equal=old==new;conditions.append({'field':name,'before':old,'after':new,'status':'fixed_equal' if equal else 'fixed_difference'})
        if not equal:gap('experiment_condition_changed',field=name)
    for name in ('design.v','cells.lef','cells.lib','loader.tcl','export_region.tcl'):fixed('source/'+name,before['source_sha256'][name],after['source_sha256'][name])
    fixed('native_tool',before['execution']['tool_sha256'],after['execution']['tool_sha256'])
    for k in ('units','die','core','clock','clock_sources','cases','selected_net','endpoint'):fixed(k,a[k],b[k])
    fixed('declared_analysis',{k:v for k,v in ca['setup'].items() if k not in ('placements','blockages')},
          {k:v for k,v in cb['setup'].items() if k not in ('placements','blockages')})
    fixed('boundary_ports',a['ports'],b['ports'])
    if set(a['instances'])!=set(b['instances']) or set(a['pins'])!=set(b['pins']):gap('native_population_correspondence_unestablished');return finish()
    topology=lambda n:{k:{f:p[f] for f in ('instance','pin','direction','signal_type','net')} for k,p in n['pins'].items()}
    fixed('native_pin_connectivity',topology(a),topology(b));fixed('selected_native_endpoints',a['net_terms'],b['net_terms'])
    allowed=policy.get('allowed_moved_instances');require(isinstance(allowed,list) and len(allowed)==1 and allowed[0] in a['instances'],'Select one known intervention instance')
    fixed('native_masters_orientations',{k:[v['master'],v['orientation'],v['box'][2]-v['box'][0],v['box'][3]-v['box'][1]] for k,v in a['instances'].items()},
          {k:[v['master'],v['orientation'],v['box'][2]-v['box'][0],v['box'][3]-v['box'][1]] for k,v in b['instances'].items()})
    fixed('placements_outside_proposal',{k:v for k,v in a['instances'].items() if k not in allowed},{k:v for k,v in b['instances'].items() if k not in allowed})
    for name,old in sorted(a['instances'].items()):
        new=b['instances'][name]
        if old==new:continue
        result['changed_instances'].append({'instance':name,'before':old,'after':new})
        if name not in allowed:finding('unplanned_placement_change',instance=name)
        if any(old[k]!=new[k] for k in ('master','orientation')) or [old['box'][2]-old['box'][0],old['box'][3]-old['box'][1]]!=[new['box'][2]-new['box'][0],new['box'][3]-new['box'][1]]:gap('change_outside_translation_profile',instance=name)
    for side,n in (('before',a),('after',b)):
        for name,inst in n['instances'].items():
            if inst['status']!='PLACED' or inst['box'][0]>=inst['box'][2] or inst['box'][1]>=inst['box'][3]:gap('instance_geometry_unestablished',side=side,instance=name)
        if n['path_count']==0:gap('selected_native_path_absent',side=side)
    if a['placement_check']['return_code']!=0:gap('baseline_native_placement_check_failed')
    if b['placement_check']['return_code']!=0:finding('candidate_native_placement_check_failed',native_result=b['placement_check'])
    region=policy['region'];r=box(region['box_dbu'],'original required region')
    require(type(region['require_hard_blockage']) is bool and type(region['require_clear_instances']) is bool,'Explicit original constraint requirements needed')
    for key in ('source_ref','rationale_ref','anchor_ref'):
        if not region.get(key):gap('original_region_basis_missing',field=key)
    contains=lambda outer,inner:outer[0]<=inner[0] and outer[1]<=inner[1] and outer[2]>=inner[2] and outer[3]>=inner[3]
    if not contains(a['die'],r):gap('original_region_outside_observed_die')
    hard=lambda n:[x for x in n['blockages'] if not x['soft'] and contains(x['box'],r)]
    fixed('constraints_outside_selected_region',[x for x in a['blockages'] if x not in hard(a)],[x for x in b['blockages'] if x not in hard(b)])
    old_intruders=[k for k,v in a['instances'].items() if overlap(v['box'],r)]
    new_intruders=[k for k,v in b['instances'].items() if overlap(v['box'],r)]
    if region['require_hard_blockage']:
        if not hard(a):gap('original_required_blockage_not_observed')
        if not hard(b):finding('required_region_protection_removed')
    if region['require_clear_instances']:
        if old_intruders:gap('baseline_already_violates_original_clear_region',instances=old_intruders)
        if new_intruders:finding('candidate_intrudes_required_region',instances=new_intruders)
    result['region_review']={'original_region':region,'before_protecting_hard_blockages':hard(a),'after_protecting_hard_blockages':hard(b),
                             'before_intruding_instances':old_intruders,'after_intruding_instances':new_intruders,
                             'native_constraint_change':a['blockages']!=b['blockages'],'rule':'Positive-area overlap; touching edges are allowed. Not detailed pin-access/routing or electrical validation.'}
    ma,mb=metric(before),metric(after)
    for side,m in (('before',ma),('after',mb)):
        for problem in m['geometry_gaps']:gap(problem,side=side)
    comparable=all(c['status']=='fixed_equal' for c in conditions) and not ma['geometry_gaps'] and not mb['geometry_gaps']
    result['experiment']['qualification']='comparable_for_selected_geometry' if comparable else 'unqualified_reported_difference'
    result['metric']={'before':ma,'after':mb,'reported_delta_dbu':mb['derived_value_dbu']-ma['derived_value_dbu'] if a['units']==b['units'] else None,
                      'qualification':result['experiment']['qualification'],'interpretation':'A smaller selected terminal bbox is a geometric observation. Intent acceptance and native placement status are separate. No congestion, route or timing benefit follows.'}
    if result['findings']:result['next_actions'].append({'action':'review_constraint_preserving_control_or_correct_the_proposal','owner_ref':policy.get('owner_ref')})
    if result['gaps']:result['next_actions'].append({'action':'recover_specific_original_intent_or_native_basis_for_each_gap','gaps':[g['kind'] for g in result['gaps']]})
    return finish()
