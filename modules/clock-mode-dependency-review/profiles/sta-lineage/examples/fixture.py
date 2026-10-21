"""Owned boot/wake timing trees and original mode contracts."""
from copy import deepcopy
CASES=('complete','missing-generated','wrong-mode','wrong-divide','ideal','gate-off','unknown-case','untraced','auto-master')
FAMILIES={
 'boot-divider':{'root':'ref_clk','reset':'reset_n','mode':'boot_sel','enable':'clock_enable','data':'payload','period':10,'stages':1,'select':0,'reset_value':1,'leaf':'leaf_clock','names':['half_rate']},
 'wake-divider':{'root':'root_clock','reset':'reset','mode':'wake_select','enable':'power_ok','data':'data_input','period':16,'stages':2,'select':1,'reset_value':0,'leaf':'wake_clock','names':['divide_two','divide_four']}}
def design(c):
    lines=['module top(input '+','.join(c[k] for k in ('root','reset','mode','enable','data'))+',output q0,q1);','wire released,selected_n,b0,b1,mixed,'+c['leaf']+';']
    lines+=['ECO_INV reset_inverter(.A('+c['reset']+'),.Y(released));'] if c['reset_value']==0 else ['assign released='+c['reset']+';']
    for i in range(c['stages']):
        lines+=['wire div'+str(i)+', next'+str(i)+';', 'ECO_INV feedback'+str(i)+'(.A(div'+str(i)+'),.Y(next'+str(i)+'));',
          'ECO_DFF divider'+str(i)+'(.CK('+(c['root'] if i==0 else 'div'+str(i-1))+'),.RN(released),.D(next'+str(i)+'),.Q(div'+str(i)+'));']
    lines+=['ECO_INV selection_inverter(.A('+c['mode']+'),.Y(selected_n));']
    divsel='selected_n' if c['select']==0 else c['mode'];rootsel=c['mode'] if c['select']==0 else 'selected_n'
    lines+=['ECO_AND select_divided(.A(div'+str(c['stages']-1)+'),.B('+divsel+'),.Y(b0));',
      'ECO_AND select_root(.A('+c['root']+'),.B('+rootsel+'),.Y(b1));','ECO_OR combine(.A(b0),.B(b1),.Y(mixed));',
      'ECO_AND leaf_gate(.A(mixed),.B('+c['enable']+'),.Y('+c['leaf']+'));',
      'ECO_DFF launch(.CK('+c['leaf']+'),.RN(released),.D('+c['data']+'),.Q(q0));',
      'ECO_DFF capture(.CK('+c['leaf']+'),.RN(released),.D(q0),.Q(q1));','endmodule','']
    return '\n'.join(lines)
def generators(c):
    return [{'name':name,'target_pin':'divider'+str(i)+'/Q','reference_source':c['root'] if i==0 else 'divider'+str(i-1)+'/Q',
       'reference_kind':'port' if i==0 else 'pin','master':'root' if i==0 else c['names'][i-1],'divide_by':2} for i,name in enumerate(c['names'])]
def context(family,case):
    c=FAMILIES[family];base='owned/'+family;g=generators(c)
    if case=='missing-generated':g=g[:-1]
    if case=='wrong-divide':g[-1]['divide_by']=3
    if case=='auto-master':g[-1]['master']=None
    mode=(1-c['select']) if case=='wrong-mode' else None if case=='unknown-case' else c['select']
    return {'format':'opentools.sta-lineage-context.v1','run_ref':family+'-'+case,'scope_ref':base,'design_ref':base+'/clock-tree-r1',
       'configuration_ref':base+'/configuration-r1','mode_ref':base+'/selected-divided-mode',
       **{k:base+'/'+k for k in ('mode_basis_ref','clock_availability_ref','reset_basis_ref','power_basis_ref','consumer_basis_ref','lineage_basis_ref','timing_basis_ref','owner_ref')},
       'setup':{'root':{'name':'root','port':c['root'],'period_ns':c['period']},'generated':g,
          'cases':{c['reset']:c['reset_value'],c['mode']:mode,c['enable']:0 if case=='gate-off' else 1},
          'propagate':case!='ideal','trace':case!='untraced','data_port':c['data'],'endpoint':'capture/D'}}
def original_contract(ctx,sources):
    family=ctx['run_ref'].split('-'+next(case for case in CASES if ctx['run_ref'].endswith('-'+case)))[0];c=FAMILIES[family]
    clocks={'root':{'period_ns':float(c['period']),'is_generated':0,'is_propagated':1,'targets':[c['root']],
                    'waveform_ns':[0.0,c['period']/2],'lineage':None}}
    consumers={'divider0/CK':['root']}
    for i,g in enumerate(generators(c)):
        period=c['period']*(2**(i+1));clocks[g['name']]={'period_ns':float(period),'is_generated':1,'is_propagated':1,
          'targets':[g['target_pin']],'waveform_ns':[0.0,period/2],
          'lineage':{k:g[k] for k in ('master','reference_source','divide_by')}}
        if i<c['stages']-1:consumers['divider'+str(i+1)+'/CK']=[g['name']]
    consumers.update({'launch/CK':[c['names'][-1]],'capture/CK':[c['names'][-1]]})
    from lineage_common import BASIS,CLAIMS,IDENTITY
    return {'format':'opentools.sta-lineage-contract.v1','identity':{k:ctx[k] for k in IDENTITY[1:]},
       'claim':'Review required native clock definitions, lineage and register clock coverage in this selected divided-clock mode.',
       'source_ref':ctx['run_ref']+'/contract.json','owner_ref':ctx['owner_ref'],'basis':{k:ctx[k] for k in BASIS},
       'inputs_complete':True,'design_sources':{k:sources[k] for k in ('design.v','cells.lef','cells.lib')},
       'required_claims':{k:False for k in CLAIMS},'cases':{c['reset']:c['reset_value'],c['mode']:c['select'],c['enable']:1},
       'clocks':clocks,'clock_pin_requirements':consumers,'require_selected_path':True}
