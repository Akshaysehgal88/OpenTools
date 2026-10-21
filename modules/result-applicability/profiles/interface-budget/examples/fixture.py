"""Independent one-interface budgets with full-cycle and opposite-edge contexts."""
from pathlib import Path
from budget_common import IDENTITY,PROFILE,sha
HERE=Path(__file__).resolve().parent
FAMILIES={'rising-cycle':{'period_ns':1.0,'capture':'rise','capture_master':'ECO_DFF'},'opposite-edge':{'period_ns':2.0,'capture':'fall','capture_master':'ECO_DFFN'}}
CASES=('permissive','coherent-slow','coherent','wrong-load','wrong-reference','wrong-model','unknown-mode')

def depth(case):return 5 if case in ('permissive','coherent-slow') else 3
def assumptions(family,case,view,required=False):
    target=FAMILIES[family]['capture'];permissive=case=='permissive' and not required
    i,o=(.05,.10) if permissive else (.02,.55) if view=='upstream' else (.45,.02)
    if view=='top':i=o=None
    if case=='wrong-reference' and view=='downstream' and not required:target='fall' if target=='rise' else 'rise'
    return {'input':i,'output':o,'load':.10 if case=='wrong-load' and view=='upstream' and not required else .05,'target':target}

def context(family,case,view):
    f=FAMILIES[family];n=depth(case);a=assumptions(family,case,view);ref=family+'-'+case+'-'+view;cases={'mode':None if case=='unknown-mode' and view=='top' else 1}
    if view=='top':cases['reset_n']=1
    return {'format':'opentools.interface-budget-context.v1','run_ref':ref,'packet_ref':family+'-'+case,'scope_ref':family+'/interface','design_ref':family+'/'+view+'/depth'+str(n),'configuration_ref':family+'/'+case,'mode_ref':family+'/functional','corner_ref':'owned/nominal-v1','view':view,
      'setup':{'clock_name':'core_clock' if view=='top' else 'budget_clock','clock_port':'clk' if view=='top' else None,'period_ns':f['period_ns'],
        'input_port':None if view=='top' else 'din','output_port':None if view=='top' else 'dout','input_delay_ns':a['input'],'output_delay_ns':a['output'],'output_fall':a['target']=='fall','load_pF':None if view=='top' else a['load'],
        'from_kind':'pin' if view=='top' else 'port','from':'launch/Q' if view=='top' else 'din','to_kind':'pin' if view=='top' else 'port','to':'capture/D' if view=='top' else 'dout','bridge_net':'handoff' if view=='top' else None,'sink_net':'payload' if view=='top' else None,'cases':cases}}

def chain(prefix,n,start,end):
    lines=[]
    for index in range(n):
        source=start if index==0 else prefix+'_n'+str(index-1);target=end if index==n-1 else prefix+'_n'+str(index)
        if index<n-1:lines.append('wire '+target+';')
        lines.append(f'ECO_BUF {prefix}{index}(.A({source}),.Y({target}));')
    return '\n'.join(lines)+'\n'

def design(family,case,view):
    n=depth(case)
    if view!='top':return 'module top(input din,input mode,output dout);\n'+chain('u' if view=='upstream' else 'd',n,'din','dout')+'endmodule\n'
    master=FAMILIES[family]['capture_master']
    return 'module top(input clk,input reset_n,input mode,input data,output qcapture);\nwire launched,handoff,payload;\nECO_DFF launch(.CK(clk),.RN(reset_n),.D(data),.Q(launched));\n'+chain('a',n,'launched','handoff')+chain('b',n,'handoff','payload')+f'{master} capture(.CK(clk),.RN(reset_n),.D(payload),.Q(qcapture));\nendmodule\n'

def required_fields(ctx,sources,library_sha):
    family=ctx['scope_ref'].split('/')[0];case=ctx['configuration_ref'].split('/')[-1];view=ctx['view'];f=FAMILIES[family];a=assumptions(family,case,view,True);clock='core_clock' if view=='top' else 'budget_clock';basis='owned/'+family+'/independent-interface-contract';fact=lambda v:{'value':v,'evidence_ref':basis};pvt={'process':1.0,'voltage_V':1.0,'temperature_C':25.0}
    values={'scope.identity':{k:ctx[k] for k in IDENTITY[1:]},'implementation.source_sha256':sources['design.v'],'library.source_sha256':library_sha,'physical_library.source_sha256':sources['cells.lef'],'library.pvt':{'min':pvt,'max':pvt},
      'clock.definition':{'name':clock,'period_ns':f['period_ns'],'sources':['clk'] if view=='top' else [],'waveform_ns':[0.0,f['period_ns']/2]},
      'native.cases':{'mode':1,**({'reset_n':1} if view=='top' else {})},'reference.source':{'clock':clock,'transition':'rise','time_ns':0.0},'reference.target':{'clock':clock,'transition':f['capture'],'time_ns':1.0},'selected.points':{'startpoint':'launch/Q' if view=='top' else 'din','endpoint':'capture/D' if view=='top' else 'dout'},'profile':PROFILE}
    if view!='top':values.update({'native.input_delay_ns':a['input'],'native.output_delay_ns':a['output'],'native.output_load':{selector:{'pin_pF':.05,'wire_pF':0.0} for selector in ('min','max')}})
    return {k:fact(v) for k,v in values.items()}

def original_contract(family,case,descriptors):
    n=depth(case);basis='owned/'+family+'/independent-interface-contract';library_sha=sha(HERE/'cells.lib')
    bindings={}
    for view,d in descriptors.items():bindings[view]={'run_ref':d['context']['run_ref'],'identity':{k:d['context'][k] for k in IDENTITY},'sources':d['sources'],'command_sha256':d['command_sha256'],'required_fields':required_fields(d['context'],d['sources'],library_sha)}
    return {'format':'opentools.interface-budget-contract.v1','packet_ref':family+'-'+case,'scope_ref':family+'/interface','owner_ref':basis+'#budget-owner','requirements_ref':basis,'clock_mapping_ref':basis+'#virtual-to-core-clock-reference','latency_intent_ref':basis+'#one-native-capture-window','projection_ref':basis+'#mapped-buffer-cones','views':bindings,
      'handoff_deadline_ns':.45,'handoff_load_pF':.05,'capture_required_ns':.98,'launch_arrival_ns':.02,'maps':{'upstream':{'u'+str(i):'a'+str(i) for i in range(n)},'downstream':{'d'+str(i):'b'+str(i) for i in range(n)}},
      'boundary':{'launch_pin':'launch/Q','driver_pin':'a'+str(n-1)+'/Y','receiver_pin':'b0/A','capture_pin':'capture/D','launch_cell':'launch','capture_cell':'capture','capture_master':FAMILIES[family]['capture_master']}}
