"""Two owned endpoint-role maps for one recurring timing completeness stage."""
CASES=('complete','missing-output','unclocked','wrong-delay','role-changed','role-fixed','wrong-constant','unknown-mode')
FAMILIES={'block-interface':{'clock':'bus_clk','period':12.0,'reset':'reset_n','reset_released':1,'power':'power_ok','enable':'run_enable','functional':'ack','diagnostic':'trace','constant':'strap','delay':2.0,'diagnostic_role':'diagnostic_trace'},
 'macro-interface':{'clock':'macro_clk','period':20.0,'reset':'reset_active','reset_released':0,'power':'macro_on','enable':'clock_enable','functional':'ready','diagnostic':'test_status','constant':'override_zero','delay':1.5,'diagnostic_role':'test_observation'}}

def context(family,case):
    f=FAMILIES[family];ref=family+'-'+case;basis='owned/'+family+'/current-operating-contract';cases={f['reset']:f['reset_released'],f['power']:1,f['enable']:0 if case=='unclocked' else None if case=='unknown-mode' else 1};delays={}
    if case!='missing-output':delays[f['functional']]=f['delay']+(0.5 if case=='wrong-delay' else 0)
    if case=='role-fixed':delays[f['diagnostic']]=3.0
    return {'format':'opentools.sta-endpoint-context.v1','run_ref':ref,'scope_ref':family+'/top','design_ref':family+'/netlist/'+('tie-high' if case=='wrong-constant' else 'normal'),'configuration_ref':family+'/configuration/'+case,'mode_ref':family+'/functional','power_ref':family+'/active','mode_basis_ref':basis+'#mode','power_basis_ref':basis+'#power',
      'setup':{'clock_name':'root','clock_port':f['clock'],'period_ns':f['period'],'cases':cases,'input_delays':{'data':0.2},'output_delays':delays}}

def design(family,case):
    f=FAMILIES[family];s=f"module top(input {f['clock']},input {f['reset']},input {f['power']},input {f['enable']},input data,output {f['functional']},output {f['diagnostic']},output {f['constant']});\nwire allow_clock,gclk,reset_n_internal,payload,q0,q1;\n"
    if family=='macro-interface':s+=f"ECO_INV reset_invert(.A({f['reset']}),.Y(reset_n_internal));\nwire data_mid;\nECO_BUF buffer0(.A(q0),.Y(data_mid));\nECO_BUF buffer1(.A(data_mid),.Y(payload));\n";launch=f['clock']
    else:s+=f"assign reset_n_internal={f['reset']};\nECO_BUF buffer(.A(q0),.Y(payload));\n";launch='gclk'
    s+=f"ECO_AND allow(.A({f['power']}),.B({f['enable']}),.Y(allow_clock));\nECO_AND gate(.A({f['clock']}),.B(allow_clock),.Y(gclk));\nECO_DFF launch(.CK({launch}),.RN(reset_n_internal),.D(data),.Q(q0));\nECO_DFF capture(.CK(gclk),.RN(reset_n_internal),.D(payload),.Q(q1));\nassign {f['functional']}=q1;assign {f['diagnostic']}=q0;\nECO_TIE{'HI' if case=='wrong-constant' else 'LO'} tie(.Y({f['constant']}));\nendmodule\n"
    return s

def original_contract(ctx,sources,command_sha,case):
    family=ctx['scope_ref'].split('/')[0];f=FAMILIES[family];basis='owned/'+family+'/independent-timing-intent';changed=case in ('role-changed','role-fixed');rows=[]
    def endpoint(name,kind,role,timed,delay=None,constant=None):
        return {'endpoint':name,'kind':kind,'role':role,'timing_required':timed,'source_clock':'root' if timed else None,'target_clock':'root' if timed else None,'output_delay_ns':delay,'constant_value':constant,'basis_ref':basis+'#'+name}
    rows=[endpoint(f['functional'],'output','functional_interface',True,f['delay']),endpoint(f['diagnostic'],'output','boot_release' if changed else f['diagnostic_role'],changed,3.0 if changed else None),endpoint(f['constant'],'output','static_override_zero',False,constant=0),endpoint('launch/D','data','functional_launch_state',True),endpoint('capture/D','data','functional_capture_state',True)]
    policy=[]
    for name,role,constant in [(f['diagnostic'],f['diagnostic_role'],None),(f['constant'],'static_override_zero',0)]:
        if name==f['diagnostic'] and case=='role-fixed':continue
        policy.append({'endpoint':name,'role':role,'mode_ref':ctx['mode_ref'],'power_ref':ctx['power_ref'],'reason':'Owned selected-mode non-timed interface rationale.','approval_ref':basis+'#fixture-owner-record','basis_ref':basis+'#original-exemption','constant_value':constant})
    return {'format':'opentools.sta-endpoint-contract.v1','expected':{**{k:ctx[k] for k in ('run_ref','scope_ref','design_ref','configuration_ref','mode_ref','power_ref')},'sources':sources,'command_sha256':command_sha},'requirements_ref':basis,'owner_ref':basis+'#timing-owner',
      'clock':{'name':'root','period_ns':f['period'],'sources':[f['clock']],'propagated':1,'basis_ref':basis+'#clock'},'cases':{f['reset']:f['reset_released'],f['power']:1,f['enable']:1},'input_delays':{'data':0.2},'endpoints':rows,'exemptions':policy}
