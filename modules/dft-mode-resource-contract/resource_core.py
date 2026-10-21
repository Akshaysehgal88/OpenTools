"""Compare independent DFT resource requirements with source-bound native evidence."""
from dft_common import digest,known,require,shape,text
from native_capture import BASES,SOURCES,context,revalidate

IDENTITY=('run_ref','scope_ref','configuration_ref','design_ref','mode_ref','domain_ref')
PHASES=('shift','capture','unload')
BASE_KEYS=BASES|{'requirements_basis_ref','owner_ref'}

def contract(c):
    shape(c,{'format','expected','phases','clock_period','require_propagated_reset'}|BASE_KEYS)
    require(c['format']=='opentools.dft-resource-contract.v1','Unsupported resource contract')
    e=c['expected'];shape(e,set(IDENTITY)|{'sources','mode_sdc_sha256','command_sha256','chain','role_map'})
    require(all(text(e[k]) for k in IDENTITY),'Independent mode/design/run selectors required')
    require(isinstance(e['sources'],dict) and set(e['sources'])==set(SOURCES),'Independent source identities required')
    for v in list(e['sources'].values())+[e['mode_sdc_sha256'],e['command_sha256']]:
        require(v is None or isinstance(v,str) and len(v)==64 and all(x in '0123456789abcdef' for x in v),'Invalid expected SHA256')
    # Reuse selector validation without accepting captured sources as the requirement.
    context({'format':'opentools.dft-resource-context.v1',**{k:e[k] for k in IDENTITY},'chain':e['chain'],'role_map':e['role_map'],'wrapper_instance':'contract_selector','dependencies_complete':None,**{k:None for k in BASES}})
    require(all(c[k] is None or text(c[k]) for k in BASE_KEYS),'Invalid independent source references')
    require(type(c['require_propagated_reset']) is bool,'Choose a propagated-reset requirement explicitly')
    require(c['clock_period'] is None or type(c['clock_period']) in (int,float) and 0<c['clock_period']<1e12,'Invalid required clock period')
    shape(c['phases'],PHASES)
    for p,row in c['phases'].items():
        shape(row,{'min_steps','clock_input','reset_level','scan_enable','test_mode','manufacturing','power','isolation','basis_ref'})
        require(type(row['min_steps']) is int and row['min_steps']>=1 and row['clock_input'] in ('tclk','fclk'),'Invalid phase samples/clock')
        require(all(type(row[k]) is int and row[k] in (0,1) for k in ('reset_level','scan_enable','test_mode','manufacturing','power','isolation')),'Invalid phase resource level')
        require(row['basis_ref'] is None or text(row['basis_ref']),'Invalid phase basis')
        require(row['test_mode']==row['manufacturing']==row['power']==1 and row['isolation']==0,'This profile reviews available manufacturing test resources')
        require(row['reset_level']==e['chain']['reset_released'] and row['scan_enable']==int(p!='capture'),'This profile requires released reset and shift/capture/unload enable semantics')

def review(c,e,root):
    contract(c);require(e.get('format')=='opentools.dft-resource-evidence.v1','Unsupported evidence');revalidate(e,root)
    findings=[];gaps=[];foreign=[];phase_rows=[]
    def add(target,code,detail,phase=None):target.append({'code':code,'phase':phase,'detail':detail})
    x=c['expected'];ctx=e['context']
    for k in IDENTITY+('chain','role_map'):
        if x[k]!=ctx[k]:add(foreign,'identity_mismatch',k)
    for k in ('sources','mode_sdc_sha256','command_sha256'):
        if not known(x[k]):add(gaps,'missing_expected_identity',k)
        elif x[k]!=e[k]:add(foreign,'stale_or_foreign_source',k)
    # Quarantine foreign evidence before attributing any observed failure to this mode.
    if not foreign:
        for k in BASE_KEYS:
            if not known(c[k]):add(gaps,'missing_requirement_basis',k)
        for k in BASES:
            if not known(ctx[k]):add(gaps,'missing_evidence_basis',k)
        if ctx['dependencies_complete'] is not True:add(gaps,'open_resource_dependencies','Dependency closure has not been established')
        if c['clock_period'] is None:add(gaps,'missing_clock_period','No independent timing scenario period')
        else:
            period=e['inventory']['clocks'].get(x['chain']['clock_name'])
            if period is None:add(gaps,'missing_native_clock','Selected native clock absent')
            elif period!=c['clock_period']:add(findings,'clock_period_mismatch',f"Required {c['clock_period']}; native {period}")
        runs=e['steps'];observed=[]
        for row in runs:
            if not observed or observed[-1]!=row['phase']:observed.append(row['phase'])
        if observed!=list(PHASES):add(gaps,'incomplete_phase_cycle','Need one contiguous shift/capture/unload cycle')
        for phase in PHASES:
            requirement=c['phases'][phase];rows=[r for r in runs if r['phase']==phase];n=len(rows)
            if not known(requirement['basis_ref']):add(gaps,'missing_phase_basis','No independent phase source',phase)
            minimum=max(requirement['min_steps'],e['chain']['width'] if phase!='capture' else 1)
            if n<minimum:add(gaps,'insufficient_phase_samples',f'{n} samples; at least {minimum} required',phase)
            native_cases=e['inventory']['cases'].get(phase,{})
            for role,port in [('reset_level',x['chain']['reset_port']),('scan_enable',x['chain']['enable_port'])]:
                v=native_cases.get(port,'X')
                if v=='X':add(gaps,'unknown_native_case',port,phase)
                elif int(v)!=requirement[role]:add(findings,'native_case_mismatch',f"{port}: required {requirement[role]}, native case {v}",phase)
                if rows and any(r[role]!=requirement[role] for r in rows):add(findings,'observed_resource_mismatch',role,phase)
                if v!='X' and rows and any(r[role]!=int(v) for r in rows):add(findings,'constraint_behavior_disagreement',port,phase)
            for role in ('test_mode','manufacturing','power','isolation'):
                if e['config'][role]!=requirement[role]:add(findings,'mode_availability_mismatch',role,phase)
            clock=requirement['clock_input']
            if rows and any(r[clock]!=1 or r['chain_clock']!=1 for r in rows):add(findings,'clock_observation_mismatch',clock+' and chain clock must witness the selected edge',phase)
            phase_rows.append({'phase':phase,'samples':n,'minimum':minimum,'root_cases':native_cases,'leaf_sim':e['inventory']['leaf_sim'].get(phase,{}),'observed_reset_levels':sorted({r['reset_level'] for r in rows}),'observed_scan_enables':sorted({r['scan_enable'] for r in rows})})
            if c['require_propagated_reset']:
                values=e['inventory']['leaf_sim'].get(phase,{})
                expected_pins={name+'/'+x['chain']['pin_map']['reset'] for name in x['chain']['instances']}
                if set(values)!=expected_pins or any(v=='X' for v in values.values()):add(gaps,'unresolved_propagated_reset','Complete native leaf propagation unavailable',phase)
                elif any(int(v)!=requirement['reset_level'] for v in values.values()):add(findings,'propagated_reset_mismatch','Native leaf value differs',phase)
        if e['native']['status']=='FAIL':add(findings,'native_behavior_failure',str(e['native']['counts']))
        # Useful finite witnesses: good counters alone can hide ineffective stimulus.
        shifts=[r for r in runs if r['phase']=='shift'];captures=[r for r in runs if r['phase']=='capture'];unloads=[r for r in runs if r['phase']=='unload']
        if len({r['raw_state'] for r in shifts})<2:add(gaps,'ineffective_shift_witness','No changing shift state')
        if not shifts or not captures or captures[0]['raw_state']==shifts[-1]['raw_state']:add(gaps,'ineffective_capture_witness','No distinct captured state')
        if len({r['serial_before'] for r in unloads})<2:add(gaps,'ineffective_unload_witness','No varying observed serial data')
        if any(r['visible_state']!=r['raw_state'] for r in runs):add(findings,'isolated_observation','Visible state differs from raw chain state')
    status='QUARANTINED' if foreign else 'RESOURCE_MISMATCH' if findings else 'INCOMPLETE' if gaps else 'BOUNDED_RESOURCES_SUPPORTED'
    return {'format':'opentools.dft-resource-review.v1','status':status,'exit_code':2 if foreign or not findings and gaps else 1 if findings else 0,'contract_sha256':digest(c),'evidence_sha256':digest(e),'scope':{k:x[k] for k in IDENTITY},'native_status':e['native']['status'],'native_counts':e['native']['counts'],'chain':e['chain'],'phases':phase_rows,'findings':findings,'gaps':gaps,'quarantine':foreign,'owner_ref':c['owner_ref'],'limits':'Bounded mode-resource review for the selected native chain and finite cycle. Supplied references require owner review. No ATPG coverage, access authorization, electrical/power, clock-tree, timing or production signoff.'}

def markdown(r):
    lines=['# DFT mode resource review','',r['status'],'',f"Native behavior: {r['native_status']}; {r['native_counts']['checks']} checks, {r['native_counts']['failures']} mismatches.",'','| Phase | Samples / minimum | Observed reset | Observed scan enable |','|---|---:|---|---|']
    for p in r['phases']:lines.append(f"| {p['phase']} | {p['samples']} / {p['minimum']} | {p['observed_reset_levels']} | {p['observed_scan_enables']} |")
    lines+=['']
    for label in ('quarantine','findings','gaps'):
        for f in r[label]:lines.append(f"- {label}: {f['code']} ({f['phase'] or 'mode'}): {f['detail']}")
    lines+=['',r['limits'],''];return '\n'.join(lines)
