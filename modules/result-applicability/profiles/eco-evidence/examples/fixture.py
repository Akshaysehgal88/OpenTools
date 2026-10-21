"""Owned endpoint-rewire contexts and independent report obligations."""
FAMILIES={
 'test-control':{'wake':False,'period':10,'reset_asserted':0,'cycles':8,
  'ports':{'clock':'clk','reset':'reset_n','a':'fun_enable','b':'test_mode','da':'da','db':'db','gclk':'gclk_obs','q0':'q0','q1':'q1'},
  'cells':{'allow':'allow','gate':'gate','buffer':'buffer','launch':'launch','capture':'capture','invert_a':None,'invert_reset':None}},
 'wake-control':{'wake':True,'period':16,'reset_asserted':1,'cycles':8,
  'ports':{'clock':'ref_clock','reset':'reset','a':'sleep_req','b':'wake_test','da':'source_a','db':'source_b','gclk':'clock_observed','q0':'first_state','q1':'second_state'},
  'cells':{'allow':'wake_join','gate':'clock_switch','buffer':'data_forward','launch':'producer','capture':'consumer','invert_a':'sleep_inverse','invert_reset':'reset_inverse'}}
}
CASES=('before','unchanged','data-eco','control-eco','phase-change')

def mode(c,case):
    if case=='phase-change':return (0 if c['wake'] else 1),0
    return (1 if c['wake'] else 0),1

def cells_lib():
    lines=['library (owned_eco) {','delay_model : table_lookup;','time_unit : "1ns"; voltage_unit : "1V"; current_unit : "1mA";','pulling_resistance_unit : "1kohm"; capacitive_load_unit (1,pf);','input_threshold_pct_rise : 50; input_threshold_pct_fall : 50;','output_threshold_pct_rise : 50; output_threshold_pct_fall : 50;','slew_lower_threshold_pct_rise : 20; slew_lower_threshold_pct_fall : 20;','slew_upper_threshold_pct_rise : 80; slew_upper_threshold_pct_fall : 80;','nom_process : 1; nom_temperature : 25; nom_voltage : 1;']
    for name,inputs,expr in [('ECO_AND',('A','B'),'A & B'),('ECO_OR',('A','B'),'A | B'),('ECO_INV',('A',),'!A'),('ECO_BUF',('A',),'A')]:
        lines+=['cell ('+name+') { area : 1;']
        for pin in inputs:lines+=['pin ('+pin+') { direction : input; capacitance : 0.001; }']
        lines+=['pin (Y) { direction : output; function : "'+expr+'";']
        for pin in inputs:lines+=['timing () { related_pin : "'+pin+'"; timing_type : combinational; timing_sense : '+('negative_unate' if name=='ECO_INV' else 'positive_unate')+'; cell_rise (scalar) { values ("0.02"); } cell_fall (scalar) { values ("0.02"); } rise_transition (scalar) { values ("0.01"); } fall_transition (scalar) { values ("0.01"); } }']
        lines+=['}','}']
    lines+=['cell (ECO_DFF) { area : 1;','ff (IQ,IQN) { clocked_on : "CK"; clear : "!RN"; next_state : "D"; }','pin (CK) { direction : input; capacitance : 0.001; clock : true; }','pin (RN) { direction : input; capacitance : 0.001; }','pin (D) { direction : input; capacitance : 0.001; timing () { related_pin : "CK"; timing_type : setup_rising; rise_constraint (scalar) { values ("0.01"); } fall_constraint (scalar) { values ("0.01"); } } }','pin (Q) { direction : output; function : "IQ"; timing () { related_pin : "CK"; timing_type : rising_edge; cell_rise (scalar) { values ("0.01"); } cell_fall (scalar) { values ("0.01"); } rise_transition (scalar) { values ("0.01"); } fall_transition (scalar) { values ("0.01"); } } }','}','}']
    return '\n'.join(lines+[''])

def cells_lef():
    lines=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;','UNITS DATABASE MICRONS 1000 ; END UNITS','MANUFACTURINGGRID 0.005 ;','LAYER metal1 TYPE ROUTING ; DIRECTION HORIZONTAL ; PITCH 0.2 ; WIDTH 0.1 ; SPACING 0.1 ; END metal1','SITE core CLASS CORE ; SIZE 1 BY 1 ; SYMMETRY Y ; END core']
    for name,pins in [('ECO_AND',('A','B','Y')),('ECO_OR',('A','B','Y')),('ECO_INV',('A','Y')),('ECO_BUF',('A','Y')),('ECO_DFF',('CK','RN','D','Q'))]:
        lines+=['MACRO '+name,'CLASS CORE ;','ORIGIN 0 0 ;','SIZE 1 BY 1 ;','SYMMETRY X Y ;','SITE core ;']
        for pin in pins:lines+=['PIN '+pin,'DIRECTION '+('OUTPUT' if pin in ('Y','Q') else 'INPUT')+' ;','USE '+('CLOCK' if pin=='CK' else 'SIGNAL')+' ;','PORT LAYER metal1 ; RECT 0.1 0.1 0.2 0.2 ; END','END '+pin]
        lines+=['END '+name]
    return '\n'.join(lines+['END LIBRARY',''])

def design(c,case):
    p=c['ports'];n=c['cells'];lines=['module top('+','.join(('output' if role in ('q0','q1','gclk') else 'input')+' '+name for role,name in p.items())+');','wire qualified_enable,data_buffer,active_base,reset_released;']
    if c['wake']:
        lines+=['ECO_INV '+n['invert_a']+'(.A('+p['a']+'),.Y(active_base));','ECO_INV '+n['invert_reset']+'(.A('+p['reset']+'),.Y(reset_released));']
    else:lines+=['assign active_base='+p['a']+';assign reset_released='+p['reset']+';']
    gate='active_base' if case=='control-eco' else 'qualified_enable';data=p['db'] if case=='data-eco' else p['q0']
    lines+=['ECO_OR '+n['allow']+'(.A(active_base),.B('+p['b']+'),.Y(qualified_enable));','ECO_AND '+n['gate']+'(.A('+p['clock']+'),.B('+gate+'),.Y('+p['gclk']+'));','ECO_BUF '+n['buffer']+'(.A('+data+'),.Y(data_buffer));','ECO_DFF '+n['launch']+'(.CK('+p['gclk']+'),.RN(reset_released),.D('+p['da']+'),.Q('+p['q0']+'));','ECO_DFF '+n['capture']+'(.CK('+p['gclk']+'),.RN(reset_released),.D(data_buffer),.Q('+p['q1']+'));','endmodule','']
    return '\n'.join(lines)

def header(c,case):
    a,b=mode(c,case)
    return '\n'.join(['#define P_'+k.upper()+' '+v for k,v in c['ports'].items()]+['#define RESET_ASSERTED '+str(c['reset_asserted']),'#define MODE_A '+str(a),'#define MODE_B '+str(b),'#define CYCLES '+str(c['cycles']),''])

def context(family,c,case):
    base='owned/'+family;a,b=mode(c,case)
    return {'format':'opentools.eco-context.v1','run_ref':family+'-'+case,'scope_ref':base,'design_ref':base+'/design-r1','configuration_ref':base+'/configuration-r1',
      'phase_ref':base+('/functional-phase' if case=='phase-change' else '/override-phase'),'ports':c['ports'],'cells':c['cells'],'wake':c['wake'],
      'clock_name':'root','period':c['period'],'reset_asserted':c['reset_asserted'],'mode_a':a,'mode_b':b,'cycles':c['cycles'],
      **{k:base+'/'+k for k in ('change_basis_ref','identity_basis_ref','functional_intent_ref','clock_scope_ref','test_scope_ref','power_scope_ref','approval_basis_ref','owner_ref')}}

def config(ctx):
    p=ctx['ports'];pairs=[('run_ref',ctx['run_ref']),('clock_name',ctx['clock_name']),('clock_port',p['clock']),('period',ctx['period']),('data_a',p['da']),('data_b',p['db']),('capture_cell',ctx['cells']['capture'])]
    return '\n'.join('set '+k+' '+str(v) for k,v in pairs)+'\nset phase_cases {'+' '.join(map(str,(p['reset'],1-ctx['reset_asserted'],p['a'],ctx['mode_a'],p['b'],ctx['mode_b'])))+'}\n'
