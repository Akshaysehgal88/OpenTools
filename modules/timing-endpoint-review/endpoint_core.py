"""Reconcile the native endpoint denominator with independent timing intent."""
import html
from endpoint_common import IDENTITY,digest,number,require,shape,text
from native_endpoints import SOURCES,revalidate
LIMITS='Selected flat scalar endpoint timing-intent review using native unconstrained reports, path classes, clock associations and simulated constants. Exclusions and role/power/mode references require source review. Not complete STA, hold, CDC/RDC, physical-power, all-mode or signoff evidence; an unconstrained object is not automatically a hardware defect.'

def validate_contract(c):
    shape(c,{'format','expected','requirements_ref','owner_ref','clock','cases','input_delays','endpoints','exemptions'})
    require(c['format']=='opentools.sta-endpoint-contract.v1','Unsupported independent contract')
    x=c['expected'];shape(x,{*IDENTITY,'power_ref','sources','command_sha256'});require(all(text(x[k]) for k in (*IDENTITY,'power_ref')),'Expected identities required');shape(x['sources'],SOURCES)
    for v in [*x['sources'].values(),x['command_sha256']]:require(v is None or isinstance(v,str) and len(v)==64 and all(ch in '0123456789abcdef' for ch in v),'Invalid expected SHA256')
    for k in ('requirements_ref','owner_ref'):require(c[k] is None or text(c[k]),'Invalid source/owner')
    clock=c['clock'];shape(clock,{'name','period_ns','sources','propagated','basis_ref'});require(text(clock['name']) and number(clock['period_ns'])>0 and type(clock['propagated']) is int and clock['propagated'] in (0,1),'Invalid independent clock intent')
    require(isinstance(clock['sources'],list) and clock['sources'] and all(text(v) for v in clock['sources']) and (clock['basis_ref'] is None or text(clock['basis_ref'])),'Clock source/basis required')
    require(isinstance(c['cases'],dict) and c['cases'] and all(text(k) and (v is None or type(v) is int and v in (0,1)) for k,v in c['cases'].items()),'Explicit mode/reset/power cases required')
    require(isinstance(c['input_delays'],dict) and all(text(k) and type(v) in (int,float) for k,v in c['input_delays'].items()),'Explicit consumed input-delay assumptions required')
    for v in c['input_delays'].values():number(v)
    require(isinstance(c['endpoints'],list) and 1<=len(c['endpoints'])<=128,'Independent endpoint roster required');seen=set()
    for r in c['endpoints']:
        shape(r,{'endpoint','kind','role','timing_required','source_clock','target_clock','output_delay_ns','constant_value','basis_ref'})
        require(text(r['endpoint']) and r['endpoint'] not in seen and r['kind'] in ('output','data'),'Distinct native endpoint identities required');seen.add(r['endpoint'])
        require(r['timing_required'] is None or type(r['timing_required']) is bool,'Explicit timing requirement or null required')
        for k in ('role','source_clock','target_clock','basis_ref'):require(r[k] is None or text(r[k]),'Invalid path role/clock/source')
        if r['output_delay_ns'] is not None:number(r['output_delay_ns'])
        require(r['constant_value'] is None or type(r['constant_value']) is int and r['constant_value'] in (0,1),'Binary expected constant or null required')
        require(r['kind']=='output' or r['output_delay_ns'] is None,'Register check margin is not an output delay')
    require(isinstance(c['exemptions'],list),'Explicit exemption records required');seen=set()
    for r in c['exemptions']:
        shape(r,{'endpoint','role','mode_ref','power_ref','reason','approval_ref','basis_ref','constant_value'})
        require(text(r['endpoint']) and r['endpoint'] not in seen,'One exemption per native endpoint');seen.add(r['endpoint'])
        for k in ('role','mode_ref','power_ref','reason','approval_ref','basis_ref'):require(r[k] is None or text(r[k]),'Invalid exemption basis')
        require(r['constant_value'] is None or type(r['constant_value']) is int and r['constant_value'] in (0,1),'Binary exemption constant or null required')

def review(c,e,run_dir):
    validate_contract(c);revalidate(e,run_dir);n=e['native'];ctx=e['context'];findings=[];gaps=[];quarantine=[];rows=[]
    def add(out,code,detail,endpoint=None):out.append({'code':code,'endpoint':endpoint,'detail':detail})
    for k in (*IDENTITY,'power_ref'):
        if c['expected'][k]!=ctx[k]:add(quarantine,'native_identity_mismatch',k)
    for k in SOURCES:
        expected=c['expected']['sources'][k]
        if expected is None:add(gaps,'missing_expected_source',k)
        elif expected!=e['source_sha256'][k]:add(quarantine,'stale_or_foreign_source',k)
    if c['expected']['command_sha256'] is None:add(gaps,'missing_expected_command','Original invocation missing')
    elif c['expected']['command_sha256']!=e['file_sha256']['command.json']:add(quarantine,'stale_or_foreign_command','Original invocation differs')
    if not quarantine:
        for k in ('requirements_ref','owner_ref'):
            if c[k] is None:add(gaps,'missing_review_basis',k)
        for k in ('mode_basis_ref','power_basis_ref'):
            if ctx[k] is None:add(gaps,'missing_mode_power_source',k)
        if digest(c)!=e['execution']['contract_digest']:add(gaps,'contract_changed_after_run','Check the frozen original intent rather than rewriting it to match the export')
        actual_clock=next(iter(n['clocks']));clock=n['clocks'][actual_clock]
        for k,actual in [('name',actual_clock),('period_ns',clock['period_ns']),('sources',clock['sources']),('propagated',clock['propagated'])]:
            if c['clock'][k]!=actual:add(findings,'clock_definition_mismatch',k)
        if c['clock']['basis_ref'] is None:add(gaps,'missing_clock_intent_source','Original clock-role basis missing')
        if set(c['cases'])!=set(n['cases']):add(gaps,'mode_case_inventory_mismatch','Expected versus native case-port inventory differs')
        for port,value in c['cases'].items():
            actual=n['cases'].get(port)
            if value is None or actual is None:add(gaps,'unknown_mode_condition',port)
            elif actual!=value:add(findings,'mode_condition_false',port)
        mode_established=set(c['cases'])==set(n['cases']) and all(v is not None and n['cases'].get(k)==v for k,v in c['cases'].items())
        if c['input_delays']!=ctx['setup']['input_delays']:add(findings,'input_delay_assumption_mismatch','Original input contract differs from the bound single-pass consumed setup; not a generic posthoc input-delay getter')
        intent={r['endpoint']:r for r in c['endpoints']};exemptions={r['endpoint']:r for r in c['exemptions']}
        for name in sorted(set(n['endpoints'])-set(intent)):add(gaps,'native_endpoint_missing_intent','Native census object has no independent current role',name)
        for name in sorted(set(intent)-set(n['endpoints'])):add(findings,'expected_endpoint_absent','Required object absent; no identity rename or resolution inferred',name)
        for name in sorted(set(exemptions)-set(intent)):add(gaps,'exemption_outside_intent','No independently mapped current endpoint',name)
        for name,r in sorted(intent.items()):
            if name not in n['endpoints']:continue
            a=n['endpoints'][name];paths=a['paths'];x=exemptions.get(name);admitted=False
            if r['kind']!=a['kind']:add(findings,'endpoint_kind_changed','Native endpoint category differs',name)
            for k in ('role','timing_required','basis_ref'):
                if r[k] is None:add(gaps,'missing_endpoint_intent',k,name)
            if len(paths)>1:add(gaps,'unsupported_multiple_path_groups','Keep all native records; first scalar single-clock scope is unresolved',name)
            if r['constant_value'] is not None and a['simulated']!=str(r['constant_value']):
                add(gaps if a['simulated'] in ('X','Z') else findings,'constant_intent_unestablished' if a['simulated'] in ('X','Z') else 'constant_intent_false','Native simulated value '+a['simulated']+'; expected '+str(r['constant_value']),name)
            if x:
                missing=[k for k in ('role','mode_ref','power_ref','reason','approval_ref','basis_ref') if x[k] is None]
                if missing:add(gaps,'missing_exemption_basis',', '.join(missing),name)
                wrong=[k for k,observed in [('role',r['role']),('mode_ref',ctx['mode_ref']),('power_ref',ctx['power_ref'])] if x[k] is not None and x[k]!=observed]
                constant_unknown=x['constant_value'] is not None and a['simulated'] in ('X','Z')
                if constant_unknown:add(gaps,'exemption_constant_unestablished','No known native simulated constant for the exemption premise',name)
                elif x['constant_value'] is not None and a['simulated']!=str(x['constant_value']):wrong.append('constant_value')
                if wrong:add(findings,'exemption_premise_false',', '.join(wrong),name)
                if r['timing_required'] is True:add(findings,'required_endpoint_has_exemption','Current independent intent requires timing; old record cannot exempt it',name)
                admitted=not missing and not wrong and not constant_unknown and mode_established and r['timing_required'] is False
            if r['timing_required'] is True:
                if a['reported_unconstrained']:add(findings,'required_endpoint_unconstrained','Native unconstrained population includes a currently timed endpoint',name)
                if not paths:add(gaps,'required_endpoint_has_no_path','No native timing representative; absence alone proves neither a valid tie-off nor timing closure',name)
                for k in ('source_clock','target_clock'):
                    if r[k] is None:add(gaps,'missing_required_clock_role',k,name)
                if r['kind']=='output' and r['output_delay_ns'] is None:add(gaps,'missing_output_timing_contract','No original external timing requirement',name)
                for p in paths:
                    for k in ('source_clock','target_clock'):
                        if r[k] is not None and r[k]!=p[k]:add(findings,'required_clock_association_missing',k+' expected '+r[k]+'; native '+str(p[k]),name)
                    if r['kind']=='output' and not p['output_delay']:add(findings,'required_output_delay_missing','Native path is not an output-delay end',name)
                    if r['kind']=='data' and not p['check']:add(findings,'required_register_check_missing','Native path is not a register timing-check end',name)
                    if r['kind']=='output' and p['output_delay'] and r['output_delay_ns'] is not None and round(p['margin_ns'],6)!=round(float(r['output_delay_ns']),6):add(findings,'output_delay_contract_mismatch','Native output-delay margin differs from independent interface requirement',name)
                    if p['slack_native_ns'] not in ('INF','-INF') and float(p['slack_native_ns'])<0:add(findings,'observed_selected_timing_failure','Native selected representative has negative slack; no all-path conclusion',name)
            elif r['timing_required'] is False and a['reported_unconstrained'] and not admitted:add(gaps,'unresolved_non_timed_exemption','Non-timed intent alone is not a current justified exemption',name)
            rows.append({'endpoint':name,'intent':r,'native':a,'exemption':x,'exemption_admitted':admitted})
    status='QUARANTINED' if quarantine else 'ENDPOINT_REVIEW_REQUIRED' if findings else 'INCOMPLETE' if gaps else 'BOUNDED_ENDPOINT_INTENT_ACCOUNTED'
    return {'format':'opentools.sta-endpoint-review.v1','status':status,'exit_code':2 if quarantine or gaps and not findings else 1 if findings else 0,'contract_digest':digest(c),'evidence_digest':digest(e),'scope':{k:c['expected'][k] for k in (*IDENTITY,'power_ref')},'requirements_ref':c['requirements_ref'],'owner_ref':c['owner_ref'],'native_status':'completed; unconstrained report is not a pass/fail verdict',
      'counts':{'native_endpoints':len(n['endpoints']),'reported_unconstrained':len(n['reported_unconstrained']),'native_path_representatives':sum(len(p['paths']) for p in n['endpoints'].values()),'independent_endpoints':len(c['endpoints']),'admitted_exemptions':sum(r['exemption_admitted'] and r['native']['reported_unconstrained'] for r in rows)},
      'endpoints':rows,'findings':findings,'gaps':gaps,'quarantine':quarantine,'recheck_when':['endpoint role/interface requirement changes','clock/reset/mode/power assumptions change','exemption premise or approval/source changes','native source,tool,scope or constraint changes'],'limits':LIMITS}

def markdown(r):
    def esc(v):return html.escape(str(v)).replace('|','&#124;').replace('\n',' ').replace('\r',' ')
    lines=['# Timing endpoint review','',r['status'],'',f"Owner: {esc(r['owner_ref'])}; requirements: {esc(r['requirements_ref'])}.",'',str(r['counts']),'','| Endpoint | Current role | Timing required | Native unconstrained | Exemption admitted |','|---|---|---|---|---|']
    for x in r['endpoints']:lines.append('| '+' | '.join(esc(v) for v in (x['endpoint'],x['intent']['role'],x['intent']['timing_required'],x['native']['reported_unconstrained'],x['exemption_admitted']))+' |')
    for group in ('quarantine','findings','gaps'):
        for f in r[group]:lines.append('- '+group+': '+esc(f['code'])+' '+esc(f['endpoint'] or '')+'; '+esc(f['detail']))
    return '\n'.join(lines+['',LIMITS,''])
