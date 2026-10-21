"""Owned sequential-storage and clock-control view-intake contracts."""
import json
FAMILIES={
 'storage':{'cell':'OWNED_STORE','library':'owned_storage_r1','voltage':0.8,'width':4000,'height':2000,
  'pins':[('CLK','INPUT','CLOCK'),('D0','INPUT','SIGNAL'),('Q0','OUTPUT','SIGNAL'),('TEST_EN','INPUT','SIGNAL'),('REPAIR_LOAD','INPUT','SIGNAL')],
  'logical':{'CLK':'clock','D0':'data','Q0':'result','TEST_EN':'test_mode','REPAIR_LOAD':'repair_load'},
  'control':'REPAIR_LOAD','from':'CLK','to':'Q0','other_from':'D0','supply':'VDD','ground':'VSS'},
 'clock-control':{'cell':'OWNED_CLOCK','library':'owned_clock_r1','voltage':1.2,'width':6000,'height':3000,
  'pins':[('REFCLK','INPUT','CLOCK'),('ENABLE','INPUT','SIGNAL'),('RESET_N','INPUT','SIGNAL'),('TEST_MODE','INPUT','SIGNAL'),('CLKOUT','OUTPUT','CLOCK'),('LOCKED','OUTPUT','SIGNAL')],
  'logical':{'REFCLK':'ref_input','ENABLE':'gate_enable','RESET_N':'reset_n','TEST_MODE':'mode_select','CLKOUT':'clock_output','LOCKED':'ready_output'},
  'control':'TEST_MODE','from':'REFCLK','to':'CLKOUT','other_from':'ENABLE','supply':'VDDA','ground':'VSSA'}
}
CASES=('good','wrong-supply','voltage-change','wrong-direction','wrong-orientation','blocked-window','arc-change','footprint-change','wrong-connection','valid-mirror')

def boxes(c):
    return {name:[100,200+300*i,200,300+300*i] for i,(name,_,_) in enumerate(c['pins'])}

def lef(c,case):
    w=c['width']+(1000 if case=='footprint-change' else 0)
    lines=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;','UNITS DATABASE MICRONS 1000 ; END UNITS','MANUFACTURINGGRID 0.005 ;','LAYER metal1 TYPE ROUTING ; DIRECTION HORIZONTAL ; PITCH 0.2 ; WIDTH 0.1 ; SPACING 0.1 ; END metal1','MACRO '+c['cell'],'CLASS BLOCK ;','ORIGIN 0 0 ;',f'SIZE {w/1000} BY {c["height"]/1000} ;','SYMMETRY X Y ;']
    locations=boxes(c)
    for name,direction,kind in [*c['pins'],(c['supply'],'INOUT','POWER'),(c['ground'],'INOUT','GROUND')]:
        direction='OUTPUT' if case=='wrong-direction' and name==c['control'] else direction
        box=locations.get(name,[1000,100,1100,200] if kind=='POWER' else [2000,100,2100,200])
        lines+=['PIN '+name,'DIRECTION '+direction+' ;','USE '+kind+' ;','PORT LAYER metal1 ; RECT '+' '.join(str(v/1000) for v in box)+' ; END','END '+name]
    b=locations[c['control']];ob=[b[0]-50,b[1]-50,b[2]+50,b[3]+50] if case=='blocked-window' else [2500,400,3500,700]
    return '\n'.join(lines+['OBS LAYER metal1 ; RECT '+' '.join(str(v/1000) for v in ob)+' ; END','END '+c['cell'],'END LIBRARY',''])

def liberty(c,case):
    voltage=c['voltage']+(0.2 if case=='voltage-change' else 0);from_pin=c['other_from'] if case=='arc-change' else c['from']
    timing_type='rising_edge' if c['cell']=='OWNED_STORE' and case!='arc-change' else 'combinational'
    lines=['library ('+c['library']+') {','delay_model : table_lookup;','time_unit : "1ns"; voltage_unit : "1V"; current_unit : "1mA";','pulling_resistance_unit : "1kohm"; capacitive_load_unit (1,pf);','input_threshold_pct_rise : 50; input_threshold_pct_fall : 50;','output_threshold_pct_rise : 50; output_threshold_pct_fall : 50;','slew_lower_threshold_pct_rise : 20; slew_lower_threshold_pct_fall : 20;','slew_upper_threshold_pct_rise : 80; slew_upper_threshold_pct_fall : 80;',f'nom_process : 1; nom_temperature : 25; nom_voltage : {voltage};',f'operating_conditions (PVT) {{ process : 1; temperature : 25; voltage : {voltage}; }}','default_operating_conditions : PVT;','cell ('+c['cell']+') {','area : '+str(c['width']*c['height']/1e6)+';']
    for name,kind in [(c['supply'],'primary_power'),(c['ground'],'primary_ground')]:lines+=['pg_pin ('+name+') { voltage_name : '+name+'; pg_type : '+kind+'; }']
    if c['cell']=='OWNED_STORE':lines+=['ff (IQ,IQN) { clocked_on : "CLK"; next_state : "D0"; }']
    for name,direction,kind in c['pins']:
        lines+=['pin ('+name+') { direction : '+direction.lower()+';']
        if direction=='INPUT':lines+=['capacitance : 0.001;']
        if name==c['from']:lines+=['clock : true;']
        if direction=='OUTPUT':
            function='IQ' if c['cell']=='OWNED_STORE' else 'REFCLK & ENABLE & RESET_N' if name=='CLKOUT' else 'ENABLE & RESET_N'
            lines+=['function : "'+function+'";']
        if name==c['to']:
            lines+=['timing () { related_pin : "'+from_pin+'"; timing_type : '+timing_type+';','cell_rise (scalar) { values ("0.01"); } cell_fall (scalar) { values ("0.01"); }','rise_transition (scalar) { values ("0.01"); } fall_transition (scalar) { values ("0.01"); }','}']
        lines+=['}']
    return '\n'.join(lines+['}','}',''])

def wrapper(c,case='good'):
    ports=[('input' if direction=='INPUT' else 'output')+' wire '+c['logical'][name] for name,direction,_ in c['pins']]
    mapping=dict(c['logical'])
    if case=='wrong-connection':mapping[c['control']]=c['logical'][c['pins'][1][0]]
    return 'module top('+','.join(ports)+');\n'+c['cell']+' u_macro('+','.join('.'+name+'('+mapping[name]+')' for name,_,_ in c['pins'])+');\nendmodule\n'

def model(c):
    ports=[('input logic ' if direction=='INPUT' else 'output logic ')+name for name,direction,_ in c['pins']]
    body='always_ff @(posedge CLK) Q0<=D0;' if c['cell']=='OWNED_STORE' else 'assign CLKOUT=REFCLK & ENABLE & RESET_N;assign LOCKED=ENABLE & RESET_N;'
    return 'module '+c['cell']+'('+','.join(ports)+');\n'+body+'\nendmodule\n'

def selection(c,case):
    rail='VDD_AUX' if case=='wrong-supply' else 'VDD_CORE';orient='R90' if case=='wrong-orientation' else 'MX' if case=='valid-mirror' else 'R0'
    return '\n'.join(['read_lef macro.lef','read_verilog netlist.v','read_liberty macro.lib','link_design top','add_global_connection -net '+rail+' -inst_pattern u_macro -pin_pattern '+c['supply']+' -power','add_global_connection -net VSS_CORE -inst_pattern u_macro -pin_pattern '+c['ground']+' -ground','global_connect','set inst [[ord::get_db_block] findInst u_macro]','$inst setOrient '+orient,'$inst setLocation 10000 20000','$inst setPlacementStatus PLACED','source export_views.tcl','opentools_export_macro u_macro '+c['library']+'/'+c['cell']+' native.jsonl native.odb',''])

def context(family,c,case):
    base='owned/'+family
    return {'format':'opentools.macro-context.v1','run_ref':family+'-'+case,'scope_ref':base,'configuration_ref':base+'/configuration-r1','macro_ref':base+'/instance','revision_ref':base+'/accepted-interface-r1','corner_ref':base+'/selected-PVT',
            'instance':'u_macro','logical_instance':'u_macro','logical_unit':c['cell'],'library_cell':c['library']+'/'+c['cell'],
            **{k:base+'/'+k for k in ('view_basis_ref','revision_basis_ref','corner_basis_ref','pin_correspondence_ref','supply_basis_ref','placement_basis_ref','access_basis_ref','wrapper_basis_ref','owner_ref')}}
