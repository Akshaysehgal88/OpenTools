"""Owned LOC/shift contexts. Instance names are qualification fixtures, not tools."""
ROLES=('clock','reset','shift','variant','start','data','scan_enable','serial_in','enable','generated_clock','launch','capture','reset_n','slot')
FAMILIES={
 'scan-window':{'module':'scan_clock_path','period':10,'reset_released':1,'gate':'clock_gate','launch':'launch_ff','capture':'capture_ff','clocks':['functional_clock','occ_clock']},
 'test-window':{'module':'test_clock_path','period':16,'reset_released':0,'gate':'pulse_gate','launch':'state_a','capture':'state_b','clocks':['reference_clock','capture_clock']}}
STA={
 'capture':('capture',0,False,False,False),
 'capture-leak':('capture',0,True,False,False),
 'capture-period':('capture',2,False,False,False),
 'capture-reset-x':('capture',0,False,True,False),
 'capture-se-x':('capture',0,False,False,True),
 'shift':('shift',0,True,False,False),
 'shift-conservative':('shift',0,False,False,False)}
# phase is selected by STA profile; pulse variant0/1/2/3=two/gap/one/three.
CASES={
 'capture-good':('capture',0,0,0),
 'capture-shift-exception':('capture-leak',0,0,0),
 'capture-gap':('capture',1,0,0),
 'capture-missing':('capture',2,0,0),
 'capture-extra':('capture',3,0,0),
 'capture-scan-enable':('capture',0,1,0),
 'capture-late-release':('capture',0,2,0),
 'capture-reset-held':('capture',0,0,1),
 'capture-wrong-sta-period':('capture-period',0,0,0),
 'capture-unknown-reset':('capture-reset-x',0,0,0),
 'capture-unknown-se':('capture-se-x',0,0,0),
 'capture-release-boundary':('capture',0,3,0),
 'shift-valid':('shift',0,0,0),
 'shift-conservative':('shift-conservative',0,0,0)}
def roles(family):
    values=('clock_in','reset_control','shift_mode','pulse_variant','start_window','parallel_data','scan_control','serial_in','window_enable','generated_clock','launch_state','capture_state','effective_reset_n','slot')
    return dict(zip(ROLES,values if family=='scan-window' else ['port_'+v for v in values]))
def unit(family,c):
    r=roles(family);inputs=('clock','reset','shift','data','scan_enable','serial_in','enable');outputs=('generated_clock','launch','capture','reset_n');lines=[f"module {c['module']}("+', '.join(r[k] for k in inputs+outputs)+');']
    lines+=['input '+r[k]+';' for k in inputs]+['output '+r[k]+';' for k in outputs]
    if c['reset_released']==1:lines+=['assign '+r['reset_n']+' = '+r['reset']+';']
    else:lines += [f"INV_CELL reset_inverter (.A({r['reset']}),.Y({r['reset_n']}));"]
    lines += [f"AND_CELL {c['gate']} (.A({r['clock']}),.B({r['enable']}),.Y({r['generated_clock']}));",f"SCANR_CELL {c['launch']} (.CK({r['generated_clock']}),.RN({r['reset_n']}),.D({r['data']}),.SI({r['serial_in']}),.SE({r['scan_enable']}),.Q({r['launch']}));",f"SCANR_CELL {c['capture']} (.CK({r['generated_clock']}),.RN({r['reset_n']}),.D({r['launch']}),.SI({r['launch']}),.SE({r['scan_enable']}),.Q({r['capture']}));",'endmodule','']
    return '\n'.join(lines)
def wrapper(family,c):
    r=roles(family);inputs=ROLES[:8];outputs=ROLES[8:];lines=['module top('+', '.join(('input '+('[1:0] ' if k=='variant' else '')+r[k]) for k in inputs)+', '+', '.join(('output '+('[3:0] ' if k=='slot' else '')+r[k]) for k in outputs)+');','reg active;','reg [3:0] count;',f"assign {r['slot']} = count;",f"always @(negedge {r['clock']} or negedge {r['reset_n']})",f" if(!{r['reset_n']}) begin active<=0;count<=0;end",f" else if({r['start']}) begin active<=1;count<=0;end",' else if(active) begin if(count==7) active<=0;else count<=count+1;end',f"assign {r['enable']} = {r['shift']} || (active && (count==1 || ({r['variant']}==0 && count==2) || ({r['variant']}==1 && count==3) || ({r['variant']}==3 && (count==2 || count==3))));"]
    ports=[k for k in ROLES if k not in ('variant','start','slot')];lines += [f"{c['module']} dut ("+', '.join('.'+r[k]+'('+r[k]+')' for k in ports)+');','endmodule',''];return '\n'.join(lines)
def header(family,c):
    return ''.join('#define P_'+k.upper()+' '+v+'\n' for k,v in roles(family).items())+f"#define FAST_PERIOD {c['period']}\n#define RESET_RELEASED {c['reset_released']}\n"
def sta_script(family,c,key):
    phase,delta,exception,reset_x,se_x=STA[key];r=roles(family);p=c['period']*(4 if phase=='shift' else 1)+delta;source,generated=c['clocks'];case={'enable':1,'reset':c['reset_released'],'scan_enable':int(phase=='shift'),'shift':int(phase=='shift')}
    lines=['read_verilog unit.v','read_lef cells.lef','read_liberty cells.lib','link_design '+c['module'],f'create_clock -name {source} -period {p} [get_ports {r["clock"]}]',f'create_generated_clock -name {generated} -source [get_ports {r["clock"]}] -divide_by 1 [get_pins {c["gate"]}/Y]']
    for role,value in case.items():
        if (role=='reset' and reset_x) or (role=='scan_enable' and se_x):continue
        lines.append(f'set_case_analysis {value} [get_ports {r[role]}]')
    lines += [f'set selected_from [get_cells {c["launch"]}]',f'set selected_to [get_cells {c["capture"]}]','set before [llength [find_timing_paths -from $selected_from -to $selected_to -path_delay max]]']
    if exception:lines+=['set_false_path -from $selected_from -to $selected_to']
    lines += ['set after [llength [find_timing_paths -from $selected_from -to $selected_to -path_delay max]]','write_sdc consumed.sdc','report_clock_properties [all_clocks]','report_checks -path_delay max -format full_clock_expanded','set output [open resources.txt w]','puts $output "FORMAT opentools.occ-sta.v1"',f'puts $output "RUN owned/{family}/sta/{key}"',f'puts $output "SCENARIO owned/{family}/scenario/{key}"',f'puts $output "PHASE {phase}"',f'puts $output "MODULE {c["module"]}"','sta::update_generated_clks']
    lines += [f'''foreach name {{{source} {generated}}} {{
  set clock [get_clocks $name]
  set edges {{}}
  foreach edge [sta::Clock_waveform $clock] {{ lappend edges [sta::format_time $edge 6] }}
  puts $output "CLOCK $name [get_property $clock period] [get_property $clock is_generated] [sta::Clock_waveform_valid $clock] [llength $edges] [join $edges {{ }}]"
  set pins {{}}
  foreach pin [get_property $clock sources] {{ lappend pins [get_full_name $pin] }}
  puts $output "SOURCES $name [llength $pins] [join $pins {{ }}]"
}}''']
    for role in case:
        lines += [f'set pin [sta::get_port_pin [get_ports {r[role]}]]',f'puts $output "CASE {r[role]} [sta::pin_case_logic_value $pin]"']
    lines += ['set names {}','foreach cell $selected_from { lappend names [get_full_name $cell] }','puts $output "FROM [llength $names] [join $names { }]"','set names {}','foreach cell $selected_to { lappend names [get_full_name $cell] }','puts $output "TO [llength $names] [join $names { }]"','puts $output "PATHS $before $after"','puts $output "OPENTOOLS_NATIVE_OCC_STA_COMPLETE"','close $output','puts "OPENTOOLS_NATIVE_OCC_STA_COMPLETE"','exit',''];return '\n'.join(lines)
def selections(family,c,case):
    key,variant,se_kind,reset_hold=CASES[case];phase=STA[key][0];base='owned/'+family;r=roles(family);period=c['period']*(4 if phase=='shift' else 1)
    context={'format':'opentools.occ-context.v1','run_ref':family+'-'+case,'scope_ref':base,'design_ref':base+'/shared-clock-path','configuration_ref':base+'/profile-r1','domain_ref':base+'/single-domain','phase':phase,'recipe_ref':base+'/recipe/'+phase,'sta_run_ref':base+'/sta/'+key,'sta_scenario_ref':base+'/scenario/'+key,'unit_module':c['module'],'unit_instance':'dut','role_map':r,'clock_names':c['clocks'],'gate_pin':c['gate']+'/Y','from_cell':c['launch'],'to_cell':c['capture'],'reset_released':c['reset_released'],'native_atpg_scenario_ref':None,'native_atpg_basis_ref':None,**{k:base+'/'+k for k in ('mapping_basis_ref','model_basis_ref','instrumentation_basis_ref','timing_basis_ref','pattern_basis_ref')}}
    recipe={'format':'opentools.occ-recipe.v1','recipe_ref':context['recipe_ref'],'phase':phase,'scheme':'launch-on-capture' if phase=='capture' else 'shift-control','source_period_ns':period,'pulse_edge_indices':[2,3] if phase=='capture' else list(range(9)),'control_guard_ns':period if case=='capture-release-boundary' else period//2,'reset_released':c['reset_released'],'scan_enable':int(phase=='shift'),'allow_selected_false_path':phase=='shift','require_selected_timed_path':phase=='capture','require_native_atpg':False,'selected_path':{'from_cell':c['launch'],'to_cell':c['capture']},'source_ref':base+'/independent-recipe-table/'+case,'owner_ref':base+'/fixture-receiving-owner'}
    return context,recipe,[int(phase=='shift'),variant,se_kind,reset_hold],key
