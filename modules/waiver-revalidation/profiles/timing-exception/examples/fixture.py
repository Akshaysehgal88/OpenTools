"""Owned shift-only and clock-boundary contexts for the same review activity."""
from reach_common import digest
CASES=('baseline','expanded','renamed','wrong-mode','untraced','unknown-mode','retarget')
FAMILIES=('shift-window','clock-boundary')

def context(family,case):
    asynchronous=family=='clock-boundary';port='independent_mode' if asynchronous else 'shift_mode'
    clocks=[{'name':'launch_root' if asynchronous else 'root','port':'launch_clk' if asynchronous else 'clk','period_ns':10}]
    if asynchronous:clocks.append({'name':'capture_root','port':'capture_clk','period_ns':17})
    return {'format':'opentools.sta-exception-context.v1','run_ref':family+'-'+case,'scope_ref':family+'/top','design_ref':family+'/netlist/'+case,'configuration_ref':family+'/configuration/'+case,'mode_ref':family+'/mode/'+case,
      'setup':{'clocks':clocks,'cases':{'reset_n':1,port:0 if case=='wrong-mode' else None if case=='unknown-mode' else 1},'from_pattern':'launch','to_pattern':'capture*','trace':case!='untraced'}}

def target(family,case):
    return 'capture_serial' if family=='shift-window' and case=='renamed' else 'capture_boundary' if case=='renamed' else 'capture_func' if case=='retarget' else 'capture_async' if family=='clock-boundary' else 'capture_shift'

def design(family,case):
    asynchronous=family=='clock-boundary';ports='input launch_clk,input capture_clk,input independent_mode' if asynchronous else 'input clk,input shift_mode';clock='launch_clk' if asynchronous else 'clk';capclock='selected_clock' if asynchronous else 'clk';dest=target(family,case)
    extra=',output qfunc' if case=='expanded' else ''
    text=f'module top({ports},input reset_n,input data,output qsource,output qcapture{extra});\nwire payload;\n'
    if asynchronous:text+='wire selected_clock,nmode,launch_leg,capture_leg;\nECO_INV invert_mode(.A(independent_mode),.Y(nmode));\nECO_AND choose_launch(.A(launch_clk),.B(nmode),.Y(launch_leg));\nECO_AND choose_capture(.A(capture_clk),.B(independent_mode),.Y(capture_leg));\nECO_OR clock_mux(.A(launch_leg),.B(capture_leg),.Y(selected_clock));\n'
    text+=f'ECO_DFF launch(.CK({clock}),.RN(reset_n),.D(data),.Q(qsource));\nECO_BUF buffer(.A(qsource),.Y(payload));\nECO_DFF {dest}(.CK({clock if case=="retarget" else capclock}),.RN(reset_n),.D(payload),.Q(qcapture));\n'
    if case=='expanded':text+=f'ECO_DFF capture_func(.CK({clock}),.RN(reset_n),.D(payload),.Q(qfunc));\n'
    return text+'endmodule\n'

def requirements(family,case):
    asynchronous=family=='clock-boundary';source='launch_root' if asynchronous else 'root';dest=target(family,case);role='async_boundary' if asynchronous else 'shift_state';expected_clock='capture_root' if asynchronous else 'root'
    rows=[{'startpoint':'launch/Q','endpoint':dest+'/D','source_role':'data_source','destination_role':'functional_state' if case=='retarget' else role,'timing_required':case in ('wrong-mode','retarget'),'source_clock':source,'destination_clock':source if case=='retarget' else expected_clock,'basis_ref':'owned/'+family+'/requirements#'+('functional' if case=='retarget' else 'original-boundary')}]
    if case=='expanded':rows.append({'startpoint':'launch/Q','endpoint':'capture_func/D','source_role':'data_source','destination_role':'functional_state','timing_required':True,'source_clock':source,'destination_clock':source,'basis_ref':'owned/'+family+'/requirements#functional'})
    return {'format':'opentools.sta-exception-requirements-example.v1','intent':rows,'intent_basis_ref':'owned/'+family+'/requirements',
      'owner_ref':'owned/'+family+'/review-owner','exception':{'id':'selected-setup-exception','rationale_revision':'original-v1','rationale_ref':'owned/'+family+'/rationale#'+('independence-premise' if asynchronous else 'shift-only-premise'),'approval_ref':'owned/'+family+'/example-owner-record','allowed_role_pairs':[['data_source',role]],'case_premises':{'independent_mode' if asynchronous else 'shift_mode':1}},
      'source_notes':'Owned fixture premise, not a production approval. '+('Architecture declares independent source/capture roots only in independent_mode=1; native clock membership cannot prove physical CDC safety.' if asynchronous else 'Setup exclusion is justified only during shift_mode=1 for the selected shift state; new functional state still requires timing.')}

def original_contract(ctx,sources,command_sha):
    req=requirements(ctx['scope_ref'].split('/')[0],ctx['run_ref'].split(ctx['scope_ref'].split('/')[0]+'-',1)[1])
    return {'format':'opentools.sta-exception-contract.v1','expected':{**{k:ctx[k] for k in ('run_ref','scope_ref','design_ref','configuration_ref','mode_ref')},'sources':sources,'command_sha256':command_sha},**{k:req[k] for k in ('exception','intent','intent_basis_ref','owner_ref')}}

def rename_map(family,case='renamed'):
    return {'format':'opentools.waiver-identity-map.v1','mappings':[{'waiver_id':'selected-setup-exception','from':'launch/Q->'+target(family,'baseline')+'/D','to':'launch/Q->'+target(family,case)+'/D','evidence_ref':'owned/'+family+'/reviewed-correspondence/'+case}]}
