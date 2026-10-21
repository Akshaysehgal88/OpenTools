"""Reconcile independent state intent, native scan members and explicit exclusions."""
from scan_common import compare,digest,known,require,shape,text
from native_inventory import BASES,IDENTITY,PROFILE,SOURCES,revalidate
DOCUMENT_IDS=IDENTITY[1:]

def documents(e):
    p=e['population'];shape(p,{'format',*DOCUMENT_IDS,'source_ref','complete','states'})
    require(p['format']=='opentools.scan-population.v1' and all(text(p[k]) for k in DOCUMENT_IDS),'Explicit required population identities required')
    require(p['source_ref'] is None or text(p['source_ref']),'Invalid population source')
    require(p['complete'] is None or type(p['complete']) is bool,'Explicit population completeness required')
    require(isinstance(p['states'],list) and len(p['states'])<=256,'Required state list needed')
    ids=set();instances=set()
    for s in p['states']:
        shape(s,{'id','instance','scan_required','role','clock','power_group','basis_ref'})
        require(text(s['id']) and text(s['instance']) and s['id'] not in ids and s['instance'] not in instances,'Distinct state identities and one-to-one native instances required');ids.add(s['id']);instances.add(s['instance'])
        require(s['scan_required'] is None or type(s['scan_required']) is bool,'scan_required must be Boolean/null')
        require(all(s[k] is None or text(s[k]) for k in ('role','clock','power_group','basis_ref')),'Invalid independent state role/group/source')
    policy=e['exclusions'];shape(policy,{'format',*DOCUMENT_IDS,'records'});require(policy['format']=='opentools.scan-exclusions.v1' and all(text(policy[k]) for k in DOCUMENT_IDS),'Explicit exclusion identities required')
    require(isinstance(policy['records'],list),'Exclusion records required');ids=set();instances=set()
    for x in policy['records']:
        shape(x,{'id','instance','reason','rationale_revision','approval_ref','basis_ref','required_role','required_clock','required_power_group'})
        require(text(x['id']) and text(x['instance']) and x['id'] not in ids and x['instance'] not in instances,'Distinct exclusion IDs and one exclusion per state required');ids.add(x['id']);instances.add(x['instance'])
        require(all(x[k] is None or text(x[k]) for k in x if k not in ('id','instance')),'Invalid exclusion basis/premise')
    return p,policy

def contract(c):
    shape(c,{'format','expected','requirements_basis_ref','owner_ref'})
    require(c['format']=='opentools.scan-contract.v1' and all(c[k] is None or text(c[k]) for k in ('requirements_basis_ref','owner_ref')),'Invalid scan contract')
    x=c['expected'];shape(x,{*IDENTITY,'sources','command_sha256','native_profile'})
    require(all(text(x[k]) for k in IDENTITY) and x['native_profile']==PROFILE,'Explicit expected native identities required')
    shape(x['sources'],SOURCES)
    for value in list(x['sources'].values())+[x['command_sha256']]:require(value is None or isinstance(value,str) and len(value)==64 and all(ch in '0123456789abcdef' for ch in value),'Invalid expected SHA256')

def review(c,e,root):
    contract(c);require(e.get('format')=='opentools.scan-evidence.v1','Unsupported native evidence');revalidate(e,root);population,policy=documents(e)
    findings=[];gaps=[];quarantine=[];rows=[];ctx=e['context'];expected=c['expected']
    def add(target,code,detail,instance=None):target.append({'code':code,'instance':instance,'detail':detail})
    for k in IDENTITY:
        if expected[k]!=ctx[k]:add(quarantine,'native_identity_mismatch',k)
    for k in SOURCES:
        value=expected['sources'][k]
        if value is None:add(gaps,'missing_expected_source',k)
        elif value!=e['sources'][k]:add(quarantine,'stale_or_foreign_source',k)
    if expected['command_sha256'] is None:add(gaps,'missing_expected_command','Original run command identity absent')
    elif expected['command_sha256']!=e['command_sha256']:add(quarantine,'stale_or_foreign_command','Original run command differs')
    for k in DOCUMENT_IDS:
        if population[k]!=ctx[k]:add(quarantine,'foreign_required_population',k)
    if not quarantine:
        for k in ('requirements_basis_ref','owner_ref'):
            if not known(c[k]):add(gaps,'missing_review_basis',k)
        for k in BASES:
            if not known(ctx[k]):add(gaps,'missing_native_mapping_basis',k)
        if not known(population['source_ref']):add(gaps,'missing_population_source','No independent requirement source')
        if population['complete'] is not True:add(gaps,'population_not_declared_complete','Required-state source is partial or unknown')
        states={s['instance']:s for s in population['states']};native=set(e['pre']['sequential']);members=set(e['membership']['members']);exclusions={x['instance']:x for x in policy['records']}
        current_policy=all(policy[k]==ctx[k] for k in DOCUMENT_IDS)
        if not current_policy:add(gaps,'stale_or_foreign_exclusion_scope','Exclusion identity differs; no records admitted as current exemptions')
        for instance in sorted(native-set(states)):add(gaps,'native_state_missing_from_required_source','Native state has no independently defined intent',instance)
        for instance in sorted(set(states)-native):add(findings,'intent_state_absent_from_native','Independent state source expects an absent functional state',instance)
        for instance in sorted(set(exclusions)-set(states)):add(gaps,'exclusion_outside_required_source','Exclusion has no current required-state mapping',instance)
        chain_for={name:chain for chain,value in e['membership']['chains'].items() for name in value['order']}
        for instance,s in sorted(states.items()):
            if instance not in native:continue
            actual_clock=e['pre']['pins'][instance][ctx['pins']['clock']];member=instance in members;x=exclusions.get(instance);admitted=False
            for k in ('scan_required','role','clock','power_group','basis_ref'):
                if not known(s[k]):add(gaps,'missing_state_intent',k,instance)
            if known(s['clock']) and s['clock']!=actual_clock:add(findings,'clock_group_mismatch',f"Required {s['clock']}; native mapped clock net {actual_clock}",instance)
            if not member:
                if s['scan_required'] is True:add(findings,'required_state_unscanned','Required functional state is absent from all stitched scan chains',instance)
                if x and current_policy:
                    missing=[k for k in x if k not in ('id','instance') and not known(x[k])]
                    if missing:add(gaps,'incomplete_exclusion_basis',', '.join(missing),instance)
                    wrong=[]
                    for required,observed in [('required_role',s['role']),('required_clock',actual_clock),('required_power_group',s['power_group'])]:
                        if known(x[required]) and known(observed) and x[required]!=observed:wrong.append(required)
                    if wrong:add(findings,'exclusion_premise_false',', '.join(wrong),instance)
                    admitted=not missing and not wrong and s['scan_required'] is False
                if s['scan_required'] is False and not admitted:add(gaps,'unresolved_non_scan_exemption','Non-required intent alone does not establish a current justified exclusion',instance)
            rows.append({'id':s['id'],'instance':instance,'scan_required':s['scan_required'],'native_clock_net':actual_clock,'required_clock':s['clock'],'power_group':s['power_group'],'role':s['role'],'scan_member':member,'chain':chain_for.get(instance),'exclusion_id':x['id'] if x else None,'exclusion_admitted':admitted,'native_pre_master':e['pre']['cells'][instance],'native_post_master':e['post']['cells'][instance]})
    status='QUARANTINED' if quarantine else 'MEMBERSHIP_REVIEW_REQUIRED' if findings else 'INCOMPLETE' if gaps else 'BOUNDED_POPULATION_ACCOUNTED'
    return {'format':'opentools.scan-review.v1','status':status,'exit_code':2 if quarantine or not findings and gaps else 1 if findings else 0,'contract_sha256':digest(c),'evidence_sha256':digest(e),'scope':{k:expected[k] for k in IDENTITY},'native_status':e['native']['status'],'counts':{'native_sequential':len(e['pre']['sequential']),'scan_members':len(e['membership']['members']),'native_unscanned':len(e['membership']['unscanned']),'intent_states':len(population['states']),'admitted_exclusions':sum(r['exclusion_admitted'] for r in rows)},'states':rows,'findings':findings,'gaps':gaps,'quarantine':quarantine,'owner_ref':c['owner_ref'],'limits':'Selected flat scalar scan-population/exclusion review only. Native insertion completion is retained separately. Required roles, logical power grouping, rationale and owner references are supplied and require source review. Membership is not fault coverage, ATPG observability, defect detection or signoff.'}

def exclusion_snapshot(e):
    population,policy=documents(e);ctx=e['context'];require(all(population[k]==policy[k]==ctx[k] for k in DOCUMENT_IDS),'Current matching scope required for historical exclusion comparison')
    require(policy['records'],'Select actual exclusions for drift comparison; no synthetic empty waiver is created')
    states={s['instance']:s for s in population['states']};waivers=[];policies=[];configuration={}
    for x in policy['records']:
        instance=x['instance'];s=states.get(instance,{});native_clock=e['pre']['pins'].get(instance,{}).get(ctx['pins']['clock']);premises=[]
        for field,observed in [('role',s.get('role')),('clock',native_clock),('power_group',s.get('power_group'))]:
            key=x['id']+'::'+field;configuration[key]=observed
            if known(x['required_'+field]):premises.append({'key':key,'equals':x['required_'+field],'evidence_ref':x['basis_ref'] or 'unresolved-exclusion-source'})
        observations=[]
        if instance in e['membership']['unscanned']:observations=[{'id':instance,'object':instance,'rule':'SELECTED_UNSCANNED_STATE','message':'Native sequential state is outside the stitched scan chains.','evidence_ref':e['provenance']['workdir']+'/post.txt','kind':'native-membership-record-not-a-tool-violation'}]
        complete=population['complete'] is True and set(states)==set(e['pre']['sequential'])
        waivers.append({'id':x['id'],'definition_sha256':digest(x),'complete':complete,'findings':observations});policies.append({'id':x['id'],'premises':premises})
    snapshot={'format':'opentools.waiver-snapshot.v1','run_id':ctx['run_ref'],'scope':ctx['scope'],'configuration_ref':ctx['configuration_ref'],'configuration_basis':'declared-current-role-and-native-clock-net.v1','configuration':configuration,'tool':{'name':'openroad-inventory','version':e['native']['version'],'ruleset':'explicit-native-sequential-membership.v1'},'identity_basis':'flat-native-instance.v1','population_complete':population['complete'] is True and set(states)==set(e['pre']['sequential']),'waivers':waivers}
    return snapshot,{'format':'opentools.waiver-policy.v1','waivers':policies}

def drift(before,after,root):
    revalidate(before,root);revalidate(after,root);a,_=exclusion_snapshot(before);b,p=exclusion_snapshot(after);result=compare(a,b,p);gaps=[]
    for label,e in [('baseline',before),('current',after)]:
        for x in e['exclusions']['records']:
            missing=[k for k in x if k not in ('id','instance') and not known(x[k])]
            if missing:gaps.append({'side':label,'exclusion_id':x['id'],'missing':missing})
    return {'format':'opentools.scan-exclusion-drift.v1','status':'incomplete' if gaps else result['status'],'baseline_evidence_sha256':digest(before),'current_evidence_sha256':digest(after),'audit':result,'basis_gaps':gaps,'limits':'Parent comparator tracks explicitly selected exclusion membership and declared/native premises. Inventory observations are not fabricated native tool violations. This historical comparison cannot replace the independent required-state membership review or approve an exclusion.'}

def markdown(r):
    def clean(v):return str(v).replace('|','&#124;').replace('\n',' ').replace('\r',' ')
    lines=['# Scan population review','',r['status'],'',f"Native insertion: {r['native_status']}. Sequential states: {r['counts']['native_sequential']}; scan members: {r['counts']['scan_members']}; admitted exclusions: {r['counts']['admitted_exclusions']}.",'','| State | Clock net | Scan member | Chain | Exclusion admitted |','|---|---|---|---|---|']
    for s in r['states']:lines.append('| '+' | '.join(clean(s[k]) for k in ('instance','native_clock_net','scan_member','chain','exclusion_admitted'))+' |')
    lines.append('')
    for group in ('quarantine','findings','gaps'):
        for f in r[group]:lines.append(f"- {group}: {clean(f['code'])} ({clean(f['instance'] or 'scope')}): {clean(f['detail'])}")
    return '\n'.join(lines+['',r['limits'],''])
