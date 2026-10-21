"""Compare independent LOC/shift intent with selected native timing and observed controls."""
from occ_common import digest,known,require,shape,text
from native_occ import BASES,BSOURCES,IDENTITY,MAPPING,PROFILE,SSOURCES,close,context,revalidate

def pulse_spans(frames,role):
    result=[];rise=None;previous=frames[0][role]
    for frame in frames[1:]:
        value=frame[role]
        if value and not previous:rise=frame['tick_ns']
        elif previous and not value and rise is not None:result.append({'rise_ns':rise,'fall_ns':frame['tick_ns']});rise=None
        previous=value
    if rise is not None:result.append({'rise_ns':rise,'fall_ns':None})
    return result

def contract(c):
    shape(c,{'format','expected','recipe'});require(c['format']=='opentools.occ-contract.v1','Unsupported handoff contract');x=c['expected'];shape(x,{*IDENTITY,'mapping','behavior_sources','sta_sources','run_command_sha256','sta_command_sha256','native_profile'})
    require(x['native_profile']==PROFILE and all(text(x[k]) for k in IDENTITY),'Explicit expected context required');shape(x['mapping'],MAPPING)
    context({'format':'opentools.occ-context.v1',**{k:x[k] for k in IDENTITY},**x['mapping'],**{k:None for k in BASES},'native_atpg_scenario_ref':None,'native_atpg_basis_ref':None})
    shape(x['behavior_sources'],BSOURCES);shape(x['sta_sources'],SSOURCES)
    for value in list(x['behavior_sources'].values())+list(x['sta_sources'].values())+[x['run_command_sha256'],x['sta_command_sha256']]:require(value is None or isinstance(value,str) and len(value)==64 and all(v in '0123456789abcdef' for v in value),'Invalid expected SHA256')
    r=c['recipe'];shape(r,{'format','recipe_ref','phase','scheme','source_period_ns','pulse_edge_indices','control_guard_ns','reset_released','scan_enable','allow_selected_false_path','require_selected_timed_path','require_native_atpg','selected_path','source_ref','owner_ref'})
    require(r['format']=='opentools.occ-recipe.v1' and text(r['recipe_ref']) and r['phase'] in ('shift','capture') and r['scheme']==('launch-on-capture' if r['phase']=='capture' else 'shift-control'),'Choose the qualified LOC/shift scheme explicitly')
    require(type(r['source_period_ns']) is int and 2<=r['source_period_ns']<=4096 and r['source_period_ns']%2==0 and type(r['control_guard_ns']) is int and 1<=r['control_guard_ns']<=1000000,'Integer-ns source/guard required')
    indices=r['pulse_edge_indices'];require(isinstance(indices,list) and indices and len(indices)<=256 and all(type(v) is int and 0<=v<=255 for v in indices) and indices==sorted(set(indices)),'Explicit increasing source-edge recipe required')
    if r['phase']=='capture':require(len(indices)==2 and indices[1]==indices[0]+1,'This LOC profile requires two consecutive source edges')
    require(type(r['reset_released']) is int and r['reset_released'] in (0,1) and type(r['scan_enable']) is int and r['scan_enable']==int(r['phase']=='shift'),'Explicit phase/reset levels required')
    require(all(type(r[k]) is bool for k in ('allow_selected_false_path','require_selected_timed_path','require_native_atpg')),'Explicit claim flags required')
    require(r['allow_selected_false_path']==(r['phase']=='shift') and r['require_selected_timed_path']==(r['phase']=='capture'),'A selected required capture path cannot be declared shift-exempt')
    shape(r['selected_path'],{'from_cell','to_cell'});require(all(text(v) for v in r['selected_path'].values()) and all(r[k] is None or text(r[k]) for k in ('source_ref','owner_ref')),'Explicit path/source/owner required')

def review(c,e,root):
    contract(c);require(e.get('format')=='opentools.occ-evidence.v1','Unsupported evidence');revalidate(e,root);x=c['expected'];ctx=e['context'];r=c['recipe'];findings=[];gaps=[];foreign=[];edges=[];guards=[];widths=[]
    def add(target,code,detail,tick=None):target.append({'code':code,'tick_ns':tick,'detail':detail})
    for k in IDENTITY:
        if x[k]!=ctx[k]:add(foreign,'identity_mismatch',k)
    if x['mapping']!={k:ctx[k] for k in MAPPING}:add(foreign,'foreign_signal_mapping','Expected native/observed roles differ')
    for side in ('behavior_sources','sta_sources'):
        for name,value in x[side].items():
            if value is None:add(gaps,'missing_expected_source',side+'/'+name)
            elif value!=e[side][name]:add(foreign,'stale_or_foreign_source',side+'/'+name)
    for key in ('run_command_sha256','sta_command_sha256'):
        if x[key] is None:add(gaps,'missing_expected_command',key)
        elif x[key]!=e[key]:add(foreign,'stale_or_foreign_command',key)
    if e['sta_sources']['unit.v']!=e['behavior_sources']['unit.v']:add(foreign,'different_shared_unit','STA and simulated path sources differ')
    native=e['sta']['export'];sdc=e['sta']['consumed_sdc'];labels=native['labels']
    for label,key in [('RUN','sta_run_ref'),('SCENARIO','sta_scenario_ref'),('PHASE','phase'),('MODULE','unit_module')]:
        if labels[label]!=ctx[key]:add(foreign,'foreign_sta_scenario',label)
    if r['phase']!=ctx['phase'] or r['recipe_ref']!=ctx['recipe_ref']:add(foreign,'foreign_recipe','Selected recipe identity differs')
    if not foreign:
        for k in BASES:
            if not known(ctx[k]):add(gaps,'missing_evidence_basis',k)
        for k in ('source_ref','owner_ref'):
            if not known(r[k]):add(gaps,'missing_recipe_basis',k)
        if r['require_native_atpg']:add(gaps,'native_atpg_not_qualified','This reader qualifies an owned recipe; native ATPG scenario labels do not supply a validated ATPG artifact')
        if r['selected_path']!={'from_cell':ctx['from_cell'],'to_cell':ctx['to_cell']}:add(foreign,'foreign_required_path','Recipe selects another functional path')
    if not foreign:
        names=ctx['clock_names'];ports=ctx['role_map'];period=r['source_period_ns']
        if set(native['clocks'])!=set(names):add(gaps,'selected_clock_collection_incomplete','Need selected root and generated clock')
        for i,name in enumerate(names):
            clock=native['clocks'].get(name)
            if clock is None:continue
            if clock['is_generated']!=i:add(findings,'clock_kind_mismatch',name)
            if clock['sources']!=[ports['clock'] if i==0 else ctx['gate_pin']]:add(findings,'clock_binding_mismatch',name)
            if not close(clock['period_ns'],period):add(findings,'sta_period_mismatch',f"{name}: native {clock['period_ns']}ns; required {period}ns")
            if not clock['waveform_valid'] or len(clock['waveform_ns'])!=2:add(gaps,'native_waveform_unresolved',name)
            elif not close(clock['waveform_ns'][1]-clock['waveform_ns'][0],period/2):add(findings,'sta_waveform_mismatch',name)
        source=sdc['source_clock'];generated=sdc['generated_clock']
        if source['name']!=names[0] or source['port']!=ports['clock'] or generated!={'name':names[1],'source_port':ports['clock'],'divide_by':1,'pin':ctx['gate_pin']}:add(findings,'consumed_clock_definition_mismatch','Native consumed root/generated clock relationship differs')
        elif names[0] in native['clocks'] and not close(source['period_ns'],native['clocks'][names[0]]['period_ns']):add(findings,'native_clock_export_disagreement','Consumed source period and native property differ')
        if native['collections']['FROM']!=[ctx['from_cell']] or native['collections']['TO']!=[ctx['to_cell']]:add(gaps,'selected_path_collection_unresolved','Resolved native cells do not match required path')
        false_paths=sdc['false_paths']
        if false_paths and not r['allow_selected_false_path']:add(findings,'shift_exception_in_capture','Consumed false path masks the selected required capture path')
        if r['require_selected_timed_path'] and native['paths']['with_consumed_constraints']==0:
            if false_paths and native['paths']['without_selected_exception']>0:add(findings,'native_path_suppression_witness','Selected path exists without the exception and disappears under consumed capture constraints')
            else:add(gaps,'selected_timed_path_not_observed','No qualified selected-path timing witness')
        wanted_cases={ports['enable']:1,ports['reset']:r['reset_released'],ports['scan_enable']:r['scan_enable'],ports['shift']:int(r['phase']=='shift')}
        for name,wanted in wanted_cases.items():
            value=native['cases'].get(name,'X')
            if value=='X':add(gaps,'unknown_native_mode_case',name)
            elif int(value)!=wanted:add(findings,'sta_mode_case_mismatch',name)
        frames=e['behavior']['frames'];previous=None;source_edges=[];changes={k:None for k in ('reset','reset_n','scan_enable')}
        for frame in frames:
            if previous:
                for k in changes:
                    if frame[k]!=previous[k]:changes[k]=frame['tick_ns']
                if frame['clock'] and not previous['clock']:source_edges.append(frame['tick_ns'])
                if frame['generated_clock'] and not previous['generated_clock']:
                    tick=frame['tick_ns'];edges.append(tick);bad=[];unknown=[]
                    for role,wanted in [('reset',r['reset_released']),('reset_n',1),('scan_enable',r['scan_enable'])]:
                        if frame[role]!=wanted:bad.append(role+' level')
                        if changes[role] is not None and changes[role]>tick-r['control_guard_ns']:bad.append(role+' guard')
                        elif tick<r['control_guard_ns']:unknown.append(role+' guard history')
                    if frame['enable']!=1:bad.append('enable')
                    if bad:add(findings,'observed_control_mismatch',', '.join(bad),tick)
                    if unknown:add(gaps,'control_history_short',', '.join(unknown),tick)
                    guards.append({'tick_ns':tick,'required_guard_ns':r['control_guard_ns'],'last_observed_changes_ns':dict(changes),'mismatches':bad,'unknowns':unknown})
            previous=frame
        if not source_edges:add(gaps,'missing_source_clock_witness','No observed source edges')
        if any(b-a!=period for a,b in zip(source_edges,source_edges[1:])):add(findings,'observed_source_period_mismatch','Measured source spacing differs from recipe')
        for role in ('clock','generated_clock'):
            for span in pulse_spans(frames,role):
                if span['fall_ns'] is None:add(gaps,'pulse_fall_not_observed',role,span['rise_ns'])
                elif span['fall_ns']-span['rise_ns']!=period//2:add(findings,'observed_logical_width_mismatch',role,span['rise_ns'])
                if role=='generated_clock':widths.append(span)
        indices=[]
        for tick in edges:
            if tick not in source_edges:add(findings,'generated_edge_not_on_source','Generated rise is not a selected source rise',tick)
            else:indices.append(source_edges.index(tick))
        covered=[i for i in r['pulse_edge_indices'] if i<len(source_edges)]
        if len(covered)!=len(r['pulse_edge_indices']):add(gaps,'recipe_window_short','Required source edges extend beyond the sampled window')
        if indices!=covered:add(findings,'pulse_recipe_mismatch',f"Required observed-window source indices {covered}; actual {indices}")
        if any(frame['shift']!=int(r['phase']=='shift') for frame in frames):add(findings,'observed_phase_mismatch','Observed controller mode differs from selected phase')
        if all(frame['reset']!=r['reset_released'] or frame['reset_n']!=1 for frame in frames):add(findings,'reset_held_for_window','Observed reset is unavailable throughout selected window')
        if e['behavior']['status']=='FAIL':add(findings,'native_behavior_failure',str(e['behavior']['counts']))
    status='QUARANTINED' if foreign else 'ALIGNMENT_REVIEW_REQUIRED' if findings else 'INCOMPLETE' if gaps else 'BOUNDED_RECIPE_ALIGNED'
    return {'format':'opentools.occ-review.v1','status':status,'exit_code':2 if foreign or not findings and gaps else 1 if findings else 0,'contract_sha256':digest(c),'evidence_sha256':digest(e),'scope':{k:x[k] for k in IDENTITY},'native_sta_status':e['sta']['status'],'native_behavior_status':e['behavior']['status'],'native_counts':e['behavior']['counts'],'native_selected_path_probe':native['paths'],'observed_pulses_ns':edges,'observed_logical_pulse_spans':widths,'control_guards':guards,'findings':findings,'gaps':gaps,'quarantine':foreign,'owner_ref':r['owner_ref'],'limits':'Bounded1ns LOC/shift recipe, selected STA path and static clock/exception alignment. Native ATPG, fault coverage, characterized timing, between-sample behavior and physical pulse quality remain outside this reader. Supplied source/mapping/owner references require review.'}

def markdown(r):
    def clean(v):return str(v).replace('|','&#124;').replace('\n',' ').replace('\r',' ')
    lines=['# At-speed handoff review','',r['status'],'',f"STA: {r['native_sta_status']}; observed behavior: {r['native_behavior_status']}.",f"Generated pulse timestamps (ns): {r['observed_pulses_ns']}.",f"Selected path without exception / under consumed constraints: {r['native_selected_path_probe']['without_selected_exception']} / {r['native_selected_path_probe']['with_consumed_constraints']}.",'','| Pulse (ns) | Guard (ns) | Mismatches | Unknowns |','|---:|---:|---|---|']
    for row in r['control_guards']:lines.append('| '+' | '.join(clean(row[k]) for k in ('tick_ns','required_guard_ns','mismatches','unknowns'))+' |')
    lines+=['']
    for group in ('quarantine','findings','gaps'):
        for f in r[group]:lines.append(f"- {group}: {clean(f['code'])} ({f['tick_ns'] if f['tick_ns'] is not None else 'scenario'}): {clean(f['detail'])}")
    return '\n'.join(lines+['',r['limits'],''])
