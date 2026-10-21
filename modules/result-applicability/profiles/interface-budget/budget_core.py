"""Compose original per-view applicability with native interface relationships."""
import html
from budget_common import IDENTITY,VIEWS,audit,digest,number,read_json,require,result_exit,shape,text
from native_budget import SOURCES,load,snapshot
BASE_FIELDS={'scope.identity','implementation.source_sha256','library.source_sha256','physical_library.source_sha256','library.pvt','clock.definition','native.cases','reference.source','reference.target','selected.points','profile'}
ADMISSION_FIELDS=BASE_FIELDS-{'reference.target'}
LIMITS='One mapped scalar interface, one native mode/model corner, explicit ns/pF and reference edges. Native selected block/top paths and source-backed projection/budget agreement do not establish all-path timing, functional equivalence, extracted RC or signoff. Architectural latency is not automatically a timing constraint. No automatic SDC edits or frequency claim.'

def validate_contract(c):
    shape(c,{'format','packet_ref','scope_ref','owner_ref','requirements_ref','clock_mapping_ref','latency_intent_ref','projection_ref','views','handoff_deadline_ns','handoff_load_pF','capture_required_ns','launch_arrival_ns','maps','boundary'})
    require(c['format']=='opentools.interface-budget-contract.v1' and text(c['packet_ref']) and text(c['scope_ref']),'Explicit interface contract identity required')
    for k in ('owner_ref','requirements_ref','clock_mapping_ref','latency_intent_ref','projection_ref'):require(c[k] is None or text(c[k]),'Invalid original relationship/source')
    for k in ('handoff_deadline_ns','handoff_load_pF','capture_required_ns','launch_arrival_ns'):
        if c[k] is not None:number(c[k])
    shape(c['views'],VIEWS)
    for view,b in c['views'].items():
        shape(b,{'run_ref','identity','sources','command_sha256','required_fields'});require(b['run_ref'] is None or text(b['run_ref']),'Explicit selected run or null required');shape(b['identity'],IDENTITY);require(all(text(v) for v in b['identity'].values()),'Expected original view identity required');shape(b['sources'],SOURCES)
        for value in [*b['sources'].values(),b['command_sha256']]:require(value is None or isinstance(value,str) and len(value)==64 and all(ch in '0123456789abcdef' for ch in value),'Invalid expected SHA256')
        required=BASE_FIELDS|({'native.input_delay_ns','native.output_delay_ns','native.output_load'} if view!='top' else set());require(isinstance(b['required_fields'],dict) and required<=set(b['required_fields']) and len(b['required_fields'])<=32,'Do not omit model,reference,scope,point or relevant I/O conditions')
        for name,field in b['required_fields'].items():shape(field,{'value','evidence_ref'});require(text(name) and (field['evidence_ref'] is None or text(field['evidence_ref'])),'Invalid requested field/source')
    shape(c['maps'],{'upstream','downstream'});targets=[]
    for mapping in c['maps'].values():require(isinstance(mapping,dict) and 1<=len(mapping)<=64 and all(text(k) and text(v) for k,v in mapping.items()),'Explicit bounded one-to-one mapped cells required');targets+=list(mapping.values())
    require(len(targets)==len(set(targets)),'Block projections cannot share or duplicate a top cell')
    shape(c['boundary'],{'launch_pin','driver_pin','receiver_pin','capture_pin','launch_cell','capture_cell','capture_master'});require(all(text(v) for v in c['boundary'].values()),'Explicit native boundary identities required')

def partition(n,mapping,anchors):
    groups={}
    for name,p in n['pins'].items():
        cell,pin=name.split('/',1)
        if cell in mapping:
            require(p['net'] is not None,'Unconnected cone pin');groups.setdefault(p['net'],set()).add(mapping[cell]+'/'+pin+':'+p['direction'])
    for name,net in anchors.items():require(net is not None,'Missing boundary net');groups.setdefault(net,set()).add('@'+name)
    return sorted(sorted(v) for v in groups.values())

def projection(c,es):
    t=es['top']['native'];b=c['boundary'];result={'mapped_cones':{},'boundary_connected':False,'exact_top_population':False,'issues':[]}
    def issue(code,detail):result['issues'].append({'code':code,'detail':detail})
    expected=set(c['maps']['upstream'].values())|set(c['maps']['downstream'].values())|{b['launch_cell'],b['capture_cell']};result['exact_top_population']=set(t['cells'])==expected
    if not result['exact_top_population']:issue('top_population_not_projected','Native top cells differ from both complete block cones plus launch/capture state')
    if t['cells'].get(b['launch_cell'])!='ECO_DFF' or t['cells'].get(b['capture_cell'])!=b['capture_master']:issue('launch_capture_model_changed','Native launch/capture cell role differs')
    if not all(pin in t['pins'] for pin in (b['launch_pin'],b['driver_pin'],b['receiver_pin'],b['capture_pin'])):issue('boundary_pin_missing','Original native pin mapping absent');return result
    net=t['pins'][b['driver_pin']]['net'];result['boundary_connected']=net is not None and net==t['pins'][b['receiver_pin']]['net']
    if not result['boundary_connected']:issue('boundary_not_connected','Projected upstream/downstream native pins do not share a net')
    for view in ('upstream','downstream'):
        n=es[view]['native'];ctx=es[view]['context'];mapping=c['maps'][view];ok=set(mapping)==set(n['cells'])
        if not ok:issue('incomplete_block_projection',view)
        for old,new in mapping.items():
            if n['cells'].get(old)!='ECO_BUF' or n['cells'].get(old)!=t['cells'].get(new):ok=False;issue('block_model_not_projected',view+':'+old+'->'+new)
        source=ctx['setup']['input_port'];sink=ctx['setup']['output_port']
        if source not in n['ports'] or sink not in n['ports']:ok=False;issue('block_boundary_port_missing',view)
        if ok:
            up=view=='upstream';top_anchors={'IN':t['pins'][b['launch_pin'] if up else b['receiver_pin']]['net'],'OUT':t['pins'][b['driver_pin'] if up else b['capture_pin']]['net']}
            left=partition(n,{name:name for name in mapping},{'IN':n['ports'][source]['net'],'OUT':n['ports'][sink]['net']});right=partition(t,{new:old for old,new in mapping.items()},top_anchors)
            if left!=right:ok=False;issue('block_connectivity_not_projected',view)
        result['mapped_cones'][view]=ok
    result['complete']=result['exact_top_population'] and result['boundary_connected'] and all(result['mapped_cones'].get(v) for v in ('upstream','downstream')) and not result['issues'];return result

def review(root,c):
    validate_contract(c);findings=[];gaps=[];quarantine=[];views={};es={};admitted={};proj=None;relationships={};timeline={}
    def add(out,code,detail,view=None):out.append({'code':code,'view':view,'detail':detail})
    for key in ('owner_ref','requirements_ref','clock_mapping_ref','latency_intent_ref','projection_ref'):
        if c[key] is None:add(gaps,'missing_original_relationship',key)
    for view,b in c['views'].items():
        if b['run_ref'] is None:add(gaps,'missing_native_view',view);continue
        e=load(root,b['run_ref']);n=e['native'];s=snapshot(e);ctx=e['context'];valid=True
        for key in IDENTITY:
            if b['identity'][key]!=ctx[key]:add(quarantine,'foreign_native_identity',key,view);valid=False
        if ctx['packet_ref']!=c['packet_ref'] or ctx['scope_ref']!=c['scope_ref'] or ctx['view']!=view:add(quarantine,'foreign_interface_scope','Native run is outside requested interface/view',view);valid=False
        for key,value in b['sources'].items():
            if value is None:add(gaps,'missing_expected_source',key,view)
            elif value!=e['source_sha256'][key]:add(quarantine,'stale_or_foreign_source',key,view);valid=False
        if b['command_sha256'] is None:add(gaps,'missing_original_command','No original invocation binding',view)
        elif b['command_sha256']!=e['file_sha256']['command.json']:add(quarantine,'foreign_native_command','Invocation differs',view);valid=False
        if digest(c)!=e['execution']['contract_digest']:add(gaps,'contract_changed_after_execution','Inspect the original independent interface source',view)
        row={'context':ctx,'native_result':s['result'],'path':n['paths'][0],'report':n['report'],'port_cap':n['port_cap'],'bridge_net':n['bridge_net'],'sink_net':n['sink_net'],'admitted':valid,'audit':None};views[view]=row
        if not valid:continue
        request={'format':'opentools.result-request.v1','claim_id':c['packet_ref']+'/'+view,'claim':'Selected native view for the original interface budget and model/reference conditions.','scope_ref':c['scope_ref'],'required_fields':b['required_fields'],'required_outcome':'any_observed'};a=audit(s,request,base_dir=root);row['audit']=a
        if result_exit(a)==1:add(findings,'view_conditions_inapplicable','Actual model/reference/I/O conditions differ;original native outcome is retained',view)
        if a['unknowns']:add(gaps,'view_evidence_unresolved','Original field/result evidence is unresolved',view)
        if s['result']['outcome']=='fail':add(findings,'observed_selected_timing_failure','Native selected path has negative slack',view)
        observed={r['field']:r['status'] for r in a['fields']};admitted[view]=all(observed.get(key)=='equal' for key in ADMISSION_FIELDS);es[view]=e
    complete=len(es)==3
    if complete:
        proj=projection(c,es)
        for issue in proj['issues']:add(findings,issue['code'],issue['detail'])
        basis=all(c[k] is not None for k in ('clock_mapping_ref','projection_ref','requirements_ref','latency_intent_ref'))
        model_keys=('cells.lib','cells.lef')
        same_model=all(len({e['source_sha256'][key] for e in es.values()})==1 for key in model_keys) and len({digest(e['native']['pvt']) for e in es.values()})==1
        # Requested per-view values cannot authorize pooling unrelated actual
        # models or launch bases. Different clock names need the explicit map.
        clock_values=[next(iter(e['native']['clocks'].values())) for e in es.values()]
        same_launch=len({digest({k:e['native']['report']['source_edge'][k] for k in ('transition','time_ns')}) for e in es.values()})==1
        same_wave=len({digest({k:clock[k] for k in ('period_ns','waveform_ns')}) for clock in clock_values})==1
        relationships['actual_common_model']=same_model;relationships['actual_common_source_reference']=same_launch and same_wave
        if not same_model:add(findings,'native_cross_view_model_mismatch','Actual library/physical model bytes or selected PVT differ between views')
        if not same_launch or not same_wave:add(findings,'native_source_reference_mismatch','Actual source edge or clock waveform differs;first scope needs a common time basis')
        comparable=basis and same_model and same_launch and same_wave and all(admitted.values()) and proj.get('complete',False)
        relationships['native_model_and_projection_admitted']=comparable
        a,b,t=(es[v]['native'] for v in VIEWS);ap,bp,tp=(n['paths'][0] for n in (a,b,t));boundary=c['boundary']
        for label,pin in [('launch',boundary['launch_pin']),('handoff',boundary['driver_pin']),('capture',boundary['capture_pin'])]:
            values=t['report']['point_times_ns'].get(pin,[])
            if len(values)==1:timeline[label+'_arrival_ns']=values[0]
            else:add(gaps,'missing_distinct_top_data_point',label+':'+pin)
        timeline.update(upstream_arrival_ns=ap['arrival_ns'],upstream_deadline_ns=ap['required_ns'],downstream_assumed_arrival_ns=b['report']['source_edge']['time_ns']+b['report']['input_delay_ns'],downstream_required_ns=bp['required_ns'],top_required_ns=tp['required_ns'])
        if comparable:
            def check(name,left,right,code):
                if left is None or right is None:add(gaps,'missing_budget_obligation',name);relationships[name]=None;return
                match=abs(left-right)<.00002;relationships[name]=match
                if not match:add(findings,code,f'{name}: {left} versus {right}')
            check('handoff_deadline_matches_downstream_assumption',ap['required_ns'],timeline['downstream_assumed_arrival_ns'],'handoff_budget_disagrees')
            check('handoff_matches_original_allocation',ap['required_ns'],c['handoff_deadline_ns'],'original_handoff_allocation_not_met')
            check('capture_requirement_matches_top',bp['required_ns'],tp['required_ns'],'capture_reference_not_projected')
            check('capture_matches_original_requirement',tp['required_ns'],c['capture_required_ns'],'original_capture_requirement_not_met')
            check('launch_assumption_matches_top',a['report']['input_delay_ns'],timeline.get('launch_arrival_ns'),'launch_assumption_not_projected')
            check('launch_matches_original_intent',timeline.get('launch_arrival_ns'),c['launch_arrival_ns'],'original_launch_basis_not_met')
            for view,net in [('upstream',t['bridge_net']),('downstream',t['sink_net'])]:
                caps=es[view]['native']['port_cap']
                if net is None or set(caps)!={'min','max'}:add(gaps,'missing_native_load_projection',view);continue
                check(view+'_load_matches_top',caps['max']['pin_pF']+caps['max']['wire_pF'],net['total_cap_pF'],'external_load_not_projected')
                if view=='upstream':check('handoff_load_matches_original_intent',net['total_cap_pF'],c['handoff_load_pF'],'original_handoff_load_not_met')
                if net['drivers']!=1 or net['loads']!=1 or net['pins']!=2 or net['wire_cap_pF']!=0:add(findings,'unqualified_boundary_load_shape','First scope has one scalar driver/load with unannotated wire',view)
            if 'handoff_arrival_ns' in timeline:
                holds=timeline['handoff_arrival_ns']<=timeline['downstream_assumed_arrival_ns']+.00002;relationships['actual_handoff_meets_downstream_assumption']=holds
                if not holds:add(findings,'integrated_handoff_arrives_after_assumption','Actual top interface arrival exceeds the downstream block assumption')
        else:add(gaps,'cross_view_composition_unestablished','Do not pool unrelated models,source clocks,scopes or projections from passing views')
    else:add(gaps,'three_view_composition_incomplete','Both original blocks and the actual integrated path are required')
    status='BUDGET_REVIEW_REQUIRED' if findings else 'INCOMPLETE' if gaps or quarantine else 'BOUNDED_INTERFACE_AGREEMENT'
    return {'format':'opentools.interface-budget-review.v1','status':status,'exit_code':1 if findings else 2 if gaps or quarantine else 0,'packet_ref':c['packet_ref'],'scope_ref':c['scope_ref'],'contract_digest':digest(c),'owner_ref':c['owner_ref'],'requirements_ref':c['requirements_ref'],'native_views':views,'projection':proj,'relationships':relationships,'native_timeline_ns':timeline,'findings':findings,'gaps':gaps,'quarantine':quarantine,
      'counts':{'supplied_native_views':len(views),'admitted_identity_views':len(es),'native_failed_views':sum(v['native_result']['outcome']=='fail' for v in views.values())},'recheck_when':['interface allocation,owner or latency intent changes','reference edge,clock relation,mode/corner or load changes','mapped block/top cone or native evidence changes'],'limits':LIMITS}

def markdown(r):
    def esc(v):return html.escape(str(v)).replace('|','&#124;').replace('\n',' ').replace('\r',' ')
    lines=['# Interface timing budget review','',r['status'],'',f"Owner: {esc(r['owner_ref'])}; source: {esc(r['requirements_ref'])}.",'','| View | Original native result | Arrival ns | Required ns | Slack ns |','|---|---|---:|---:|---:|']
    for view,v in r['native_views'].items():lines.append('| '+' | '.join(esc(x) for x in (view,v['native_result']['native_status'],v['path']['arrival_ns'],v['path']['required_ns'],v['path']['slack_ns']))+' |')
    lines+=['','| Native timeline | ns |','|---|---:|']
    for name,value in r['native_timeline_ns'].items():lines.append('| '+esc(name.replace('_',' '))+' | '+esc(value)+' |')
    lines+=['','| Relationship | Holds |','|---|---|']
    for name,value in r['relationships'].items():lines.append('| '+esc(name.replace('_',' '))+' | '+esc('unknown' if value is None else 'yes' if value else 'no')+' |')
    lines.append('')
    for group in ('quarantine','findings','gaps'):
        for f in r[group]:lines.append('- '+group+': '+esc(f['code'])+' '+esc(f['view'] or '')+'; '+esc(f['detail']))
    return '\n'.join(lines+['',LIMITS,''])
