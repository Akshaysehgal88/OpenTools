"""Review one selected macro's native views against independent intake intent."""
from macro_common import BASIS,IDENTITY,digest,integer,number,require,text
CLAIMS=('timing_polarity','liberty_pg_associations','memory_behavior','clock_waveform_safety','DRC_LVS')

def overlap(a,b):return max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3])
def policy_box(value):
    require(isinstance(value,list) and len(value)==4,'Invalid access box')
    for v in value:integer(v,-(1<<63),(1<<63)-1,'access coordinate')
    require(value[0]<value[2] and value[1]<value[3],'Empty access box');return value

def review(evidence,policy):
    require(evidence.get('format')=='opentools.macro-evidence.v1' and policy.get('format')=='opentools.macro-policy.v1','Unsupported evidence/contract')
    result={'format':'opentools.macro-review.v1','status':'incomplete','scope':{k:evidence['context'][k] for k in IDENTITY},
            'native_result':evidence['native_result'],'findings':[],'gaps':[],'pins':[],'access_windows':[],
            'owner_ref':policy.get('owner_ref'),'evidence_sha256':digest(evidence),'policy_sha256':digest(policy),
            'recheck_when':['macro revision/corner or selected library changes','pin correspondence or logical wrapper changes',
                            'supply ownership changes','footprint/orientation/access constraints change','test/repair roles change'],
            'limits':'Selected macro-view intake only. Import success, revision labels and byte hashes do not establish source authority, freshness or receiving acceptance. Physical/timing/library facts remain separate; no memory/clock behavior, characterized timing, DRC/LVS or routability signoff.'}
    def finding(kind,**data):result['findings'].append(dict(kind=kind,**data))
    def gap(kind,**data):result['gaps'].append(dict(kind=kind,**data))
    def finish():
        result['status']='findings' if result['findings'] else 'incomplete' if result['gaps'] else 'aligned'
        return result
    admitted=True
    for k in IDENTITY:
        if policy.get('identity',{}).get(k)!=evidence['context'][k]:gap('scope_not_admitted',field=k);admitted=False
    for k in ('instance','logical_instance','logical_unit','library_cell'):
        if policy.get('selection',{}).get(k)!=evidence['context'][k]:gap('selected_object_not_admitted',field=k);admitted=False
    actual_bindings={'source_sha256':evidence['source_sha256'],'database_sha256':evidence['file_sha256']['native.odb'],
                     'native_export_sha256':evidence['file_sha256']['native.jsonl'],'logical_xml_sha256':evidence['file_sha256']['logical.xml'],
                     'native_command_sha256':evidence['file_sha256']['native.command.json'],'logical_command_sha256':evidence['file_sha256']['logical.command.json']}
    for key,actual in actual_bindings.items():
        if policy.get(key)!=actual:gap('artifact_not_admitted',field=key);admitted=False
    if not admitted:return finish()
    if evidence.get('qualified_batch_loader') is not True:gap('native_loader_unqualified');return finish()
    for k in BASIS:
        if not evidence['context'].get(k):gap('missing_view_basis',field=k)
    for k in ('source_ref','owner_ref'):
        if policy.get(k) is None:gap('missing_intake_basis',field=k)
        else:text(policy[k],k)
    if policy.get('inputs_complete') is not True:gap('incomplete_view_set')
    claims=policy.get('required_claims',{})
    for claim in CLAIMS:
        if claim not in claims:gap('requested_claim_scope_unspecified',claim=claim)
        else:
            require(type(claims[claim]) is bool,'Claim requirements must be explicit booleans')
            if claims[claim]:gap('requested_claim_unqualified',claim=claim)
    native=evidence['native'];logical=evidence['logical'];instance=native['instance'];lib=native['timing_library'];geometry=policy['geometry']
    for key,observed in [('database_units_per_micron',native['database_units_per_micron']),('width',native['master']['width']),('height',native['master']['height'])]:
        expected=integer(geometry[key],1,1<<40,key)
        if expected!=observed:finding('macro_geometry_mismatch',field=key,expected=expected,observed=observed)
    if policy.get('master')!=instance['master']:finding('physical_master_mismatch',expected=policy.get('master'),observed=instance['master'])
    if policy.get('library_cell')!=lib['library']+'/'+lib['cell']:finding('timing_cell_mismatch',expected=policy.get('library_cell'),observed=lib['library']+'/'+lib['cell'])
    allowed=policy['allowed_orientations'];require(isinstance(allowed,list) and allowed,'Allowed orientations required')
    orientations=('R0','R90','R180','R270','MX','MY','MXR90','MYR90');require(all(o in orientations for o in allowed),'Unsupported orientation')
    orient=instance['orientation'];require(orient in orientations,'Unsupported native orientation')
    if orient not in allowed:finding('orientation_outside_contract',observed=orient,allowed=allowed)
    sym=native['master']['symmetry'];legal={'R0'}
    if sym['X']:legal.add('MX')
    if sym['Y']:legal.add('MY')
    if sym['X'] and sym['Y'] or sym['R90']:legal.add('R180')
    if sym['R90']:
        legal.update(('R90','R270'))
        if sym['X'] or sym['Y']:legal.update(('MXR90','MYR90','MX','MY'))
    if orient not in legal:finding('orientation_not_supported_by_master_symmetry',observed=orient)
    if instance['placement_status']!='PLACED':gap('selected_placement_unavailable',observed=instance['placement_status'])
    point=lib['operating_point'];expected_point=policy['operating_point'];tolerances={'process':1e-6,'voltage':1e-6,'temperature':1e-4}
    if point is None:gap('native_operating_point_missing')
    else:
        for k in tolerances:
            expected=number(expected_point[k],k)
            if abs(expected-point[k])>tolerances[k]:finding('selected_characterization_point_mismatch',field=k,expected=expected,observed=point[k],tolerance=tolerances[k])
    mapping=policy['pin_map'];require(isinstance(mapping,list) and mapping,'Independent pin correspondence required')
    physical_used=set();logical_used=set();timing_used=set();power_count=ground_count=0
    for p in mapping:
        physical=text(p['physical'],'physical pin');require(physical not in physical_used,'Duplicate physical correspondence');physical_used.add(physical)
        text(p['role'],'pin role');direction=p['direction'];kind=p['signal_type'];require(direction in ('INPUT','OUTPUT','INOUT') and kind in ('SIGNAL','CLOCK','POWER','GROUND'),'Invalid pin contract')
        if p.get('source_ref') is None:gap('pin_correspondence_basis_missing',pin=physical)
        else:text(p['source_ref'],'pin source')
        facts=native['physical_pins'].get(physical);terminal=native['instance_terminals'].get(physical)
        row={'physical':physical,'role':p['role'],'logical':p.get('logical'),'timing':p.get('timing'),'observed_net':terminal['net'] if terminal else None};result['pins'].append(row)
        if facts is None:finding('required_physical_pin_missing',pin=physical);continue
        if (facts['direction'],facts['signal_type'])!=(direction,kind):finding('physical_pin_role_mismatch',pin=physical,expected=[direction,kind],observed=[facts['direction'],facts['signal_type']])
        if not facts['boxes']:gap('physical_pin_geometry_missing',pin=physical)
        text(p['net'],'expected net')
        if terminal is None or terminal['net']!=p['net']:finding('instance_pin_connection_mismatch',pin=physical,expected=p['net'],observed=terminal['net'] if terminal else None)
        if kind in ('POWER','GROUND'):
            power_count+=kind=='POWER';ground_count+=kind=='GROUND'
            require(p.get('logical') is None and p.get('timing') is None,'PG association outside the supported signal-pin correspondence')
            if not p.get('supply_owner_ref'):gap('supply_owner_unestablished',pin=physical)
            else:text(p['supply_owner_ref'],'supply owner')
            if terminal and terminal['net_signal_type']!=kind:finding('supply_net_type_mismatch',pin=physical,expected=kind,observed=terminal['net_signal_type'])
            continue
        lname=text(p.get('logical'),'logical pin');tname=text(p.get('timing'),'timing pin');require(lname not in logical_used and tname not in timing_used,'Non-distinct signal correspondence');logical_used.add(lname);timing_used.add(tname)
        lp=logical['ports'].get(lname);tp=lib['pins'].get(tname)
        expected_width=integer(p['width'],1,1<<20,'logical width')
        if lp is None:finding('required_logical_pin_missing',pin=lname)
        else:
            if lp['width'] is None:gap('logical_width_unqualified',pin=lname)
            elif lp['width']!=expected_width:finding('logical_width_mismatch',pin=lname,expected=expected_width,observed=lp['width'])
            if lp['direction']!=direction.lower():finding('logical_pin_direction_mismatch',pin=lname)
            conn=lp['connection']
            if lp['width']!=1 or conn['kind']!='varref' or conn['width']!=1:gap('non_scalar_or_expression_correspondence_unqualified',pin=lname)
            elif conn['name']!=p['net']:finding('logical_connection_mismatch',pin=lname,expected=p['net'],observed=conn['name'])
        if tp is None:finding('required_timing_pin_missing',pin=tname)
        elif tp['direction']!=direction.lower():finding('timing_pin_direction_mismatch',pin=tname)
        elif tp['is_bus']:gap('timing_bus_correspondence_unqualified',pin=tname)
    if power_count!=1 or ground_count!=1:gap('single_supply_profile_not_established',power_pins=power_count,ground_pins=ground_count)
    unmapped_physical=sorted(set(native['physical_pins'])-physical_used);unmapped_logical=sorted(set(logical['ports'])-logical_used)
    unmapped_timing=sorted(name for name,v in lib['pins'].items() if v['direction']!='internal' and name not in timing_used)
    for key,values in [('physical',unmapped_physical),('logical',unmapped_logical),('timing',unmapped_timing)]:
        if values:gap('unreviewed_pin_population',view=key,pins=values)
    required_arcs=policy.get('required_arcs');require(isinstance(required_arcs,list),'Required timing endpoints must be explicit')
    arcs={(a['from'],a['to']) for a in lib['arcs']}
    for arc in required_arcs:
        a=text(arc['from'],'arc source');b=text(arc['to'],'arc target')
        if arc.get('source_ref') is None:gap('required_arc_basis_missing',from_pin=a,to_pin=b)
        else:text(arc['source_ref'],'required arc source')
        if (a,b) not in arcs:finding('required_timing_endpoints_missing',from_pin=a,to_pin=b)
    for window in policy['access_windows']:
        pin=text(window['pin'],'access pin');layer=text(window['layer'],'access layer');box=policy_box(window['box']);require(type(window['require_pin_intersection']) is bool,'Explicit access intersection rule needed')
        if window.get('source_ref') is None:gap('access_rule_basis_missing',pin=pin)
        else:text(window['source_ref'],'access rule source')
        candidates=native['physical_pins'].get(pin,{}).get('boxes',[])
        pin_intersects=any(p['layer']==layer and overlap(box,p['box']) for p in candidates)
        obstructing=[o for o in native['obstructions'] if o['layer']==layer and overlap(box,o['box'])]
        if window['require_pin_intersection'] and not pin_intersects:finding('selected_pin_access_window_missed',pin=pin)
        if obstructing:finding('selected_access_window_obstructed',pin=pin,obstructions=obstructing)
        result['access_windows'].append({'pin':pin,'layer':layer,'master_local_box':box,'pin_intersects':pin_intersects,'obstructions':obstructing,'rule':'Explicit selected clear window; not DRC/routability'})
    return finish()
