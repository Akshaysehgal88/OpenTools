"""Review native setup masking against independent intent; reuse waiver records."""
import html,json
from reach_common import IDENTITY,PROFILE,VERSION,compare,digest,shape,text,require
from native_reach import SOURCES,revalidate

LIMITS='Selected native maximum-setup endpoint-pair observations under one plain false path in a fresh closed loader. Not all structural paths, hold reach, multicycle precedence, CDC/protocol safety or STA signoff. Intent, independence, rationale and ownership require source review; matching reach does not approve an exception.'

def validate_contract(c):
    shape(c,{'format','expected','exception','intent','intent_basis_ref','owner_ref'})
    require(c['format']=='opentools.sta-exception-contract.v1','Unsupported intent contract')
    x=c['expected'];shape(x,{*IDENTITY,'sources','command_sha256'})
    require(all(text(x[k]) for k in IDENTITY),'Expected run/configuration identities required');shape(x['sources'],SOURCES)
    for v in [*x['sources'].values(),x['command_sha256']]:require(v is None or isinstance(v,str) and len(v)==64 and all(ch in '0123456789abcdef' for ch in v),'Invalid original SHA256')
    for k in ('intent_basis_ref','owner_ref'):require(c[k] is None or text(c[k]),'Invalid source/owner reference')
    e=c['exception'];shape(e,{'id','rationale_revision','rationale_ref','approval_ref','allowed_role_pairs','case_premises'})
    require(text(e['id']) and text(e['rationale_revision']),'Exception ID/revision required')
    for k in ('rationale_ref','approval_ref'):require(e[k] is None or text(e[k]),'Invalid rationale reference')
    require(isinstance(e['allowed_role_pairs'],list),'Explicit allowed semantic roles required')
    for pair in e['allowed_role_pairs']:require(isinstance(pair,list) and len(pair)==2 and all(text(v) for v in pair),'Invalid permitted role pair')
    require(isinstance(e['case_premises'],dict),'Explicit case premises required')
    for k,v in e['case_premises'].items():require(text(k) and type(v) is int and v in (0,1),'Invalid case premise')
    require(isinstance(c['intent'],list) and len(c['intent'])<=64,'Bounded independent endpoint intent required');ids=set();roles=set()
    for p in c['intent']:
        shape(p,{'startpoint','endpoint','source_role','destination_role','timing_required','source_clock','destination_clock','basis_ref'})
        require(text(p['startpoint']) and text(p['endpoint']),'Explicit endpoint identities required');key=path_id(p);require(key not in ids,'Duplicate intended pair');ids.add(key)
        require(p['timing_required'] is None or type(p['timing_required']) is bool,'Explicit timing requirement or null required')
        for k in ('source_role','destination_role','source_clock','destination_clock','basis_ref'):require(p[k] is None or text(p[k]),'Invalid independent path intent')

def path_id(p):return p['startpoint']+'->'+p['endpoint']
def clocks_for(n,pin):
    instance=pin.split('/')[0];pins=[p for p in n['clock_pins'] if p.split('/')[0]==instance]
    if len(pins)!=1:return None
    names=sorted(k for k,c in n['clocks'].items() if pins[0] in c['pins'])
    return names[0] if len(names)==1 else None

def inspect(c,e,run_dir):
    validate_contract(c);revalidate(e,run_dir);n=e['native'];ctx=e['context'];x=c['expected'];findings=[];gaps=[];quarantine=[]
    def add(out,code,detail,path=None):out.append({'code':code,'path':path,'detail':detail})
    for k in IDENTITY:
        if x[k]!=ctx[k]:add(quarantine,'native_identity_mismatch',k)
    for k in SOURCES:
        if x['sources'][k] is None:add(gaps,'missing_expected_source',k)
        elif x['sources'][k]!=e['source_sha256'][k]:add(quarantine,'stale_or_foreign_source',k)
    if x['command_sha256'] is None:add(gaps,'missing_expected_command','Original invocation not supplied')
    elif x['command_sha256']!=e['file_sha256']['command.json']:add(quarantine,'stale_or_foreign_command','Original invocation differs')
    rows=[];complete=not quarantine
    if not quarantine:
        for field,value in [('intent_basis_ref',c['intent_basis_ref']),('owner_ref',c['owner_ref']),*[(k,c['exception'][k]) for k in ('rationale_ref','approval_ref')]]:
            if value is None:add(gaps,'missing_review_basis',field)
        if digest(c)!=e['execution']['contract_digest']:add(gaps,'intent_changed_after_capture','Review against the original source/revision; a matching edit is not independent intent')
        trace=n['trace'];apps=list(n['applications'].values())
        supported=trace['active']==0 and trace['ended']==1 and len(apps)==1
        if supported:
            a=apps[0];supported=a['min_max']=='max' and a['through_count']==0 and a['from']['instances']==n['selectors']['from'] and a['to']['instances']==n['selectors']['to']
            for side in ('from','to'):supported=supported and a[side]['pins']==[] and a[side]['clocks']==[] and a[side]['rf']=='rise_fall' and a[side]['end_rf']==('rise_fall' if side=='to' else '')
        if not supported:add(gaps,'unresolved_applied_exception','Require one journaled resolved plain setup false path with no through/reset/other exception family')
        before=n['phases']['before'];after=n['phases']['after']
        for k in ('cases','clocks','clock_pins','data_pins','output_pins'):
            if before[k]!=after[k]:add(gaps,'native_context_changed','Before/after '+k+' differ')
        for instance in set(n['selectors']['from']+n['selectors']['to']):
            if any(len([p for p in before[k] if p.split('/')[0]==instance])!=1 for k in ('clock_pins','data_pins','output_pins')):add(gaps,'unsupported_selected_register_shape','Require one native clock, data and output pin for '+instance)
        intent={path_id(p):p for p in c['intent']};pre={path_id(p):p for p in before['paths']};post={path_id(p):p for p in after['paths']}
        for key in sorted(set(post)-set(pre)):add(gaps,'unexpected_post_exception_path','Native before/after correspondence differs',key)
        for key in sorted(set(intent)-set(pre)):add(gaps,'intended_pair_not_observed','No native pre-exception representative; do not infer removal',key)
        for port,expected in c['exception']['case_premises'].items():
            observed=before['cases'].get(port)
            if observed in (None,'X'):add(gaps,'missing_mode_premise',port)
            elif observed!=str(expected):add(findings,'mode_premise_false',port+' expected '+str(expected)+'; native '+observed)
        if not c['exception']['allowed_role_pairs'] or not c['exception']['case_premises']:add(gaps,'missing_exception_premises','Explicit rationale roles and mode premise required')
        for key,p in sorted(pre.items()):
            intended=intent.get(key);masked=key not in post;sc=clocks_for(before,p['startpoint']);dc=clocks_for(before,p['endpoint'])
            row={'id':key,'startpoint':p['startpoint'],'endpoint':p['endpoint'],'setup_masked':masked,'source_clock':sc,'destination_clock':dc,'intent':intended};rows.append(row)
            if p['startpoint'] not in before['output_pins'] or p['endpoint'] not in before['data_pins']:add(gaps,'unsupported_path_endpoint','Representative is not an observed register output-to-data pair',key)
            if sc is None or dc is None:add(gaps,'unresolved_native_clock_pair','Require single native clock per selected register',key)
            if intended is None:add(gaps,'path_missing_independent_intent','Keep the native path; obtain its requirement and role source',key);continue
            for k in ('source_role','destination_role','timing_required','source_clock','destination_clock','basis_ref'):
                if intended[k] is None:add(gaps,'missing_path_intent',k,key)
            for k,observed in [('source_clock',sc),('destination_clock',dc)]:
                if intended[k] is not None and observed is not None and intended[k]!=observed:add(findings,'clock_premise_changed',k+': expected '+intended[k]+'; native '+observed,key)
            if masked:
                if intended['timing_required'] is True:add(findings,'required_setup_pair_masked','Independent current intent requires setup timing for this native pair',key)
                if intended['source_role'] is not None and intended['destination_role'] is not None and [intended['source_role'],intended['destination_role']] not in c['exception']['allowed_role_pairs']:add(findings,'masked_pair_outside_rationale','Native suppression reaches a role outside the recorded exception premise',key)
            else:add(findings,'selected_pair_still_timed','Native setup representative remains after the selected exception',key)
        if not pre:add(findings,'empty_observed_population','No pre-exception setup pair observed; no automatic removal decision')
        complete=not gaps
    status='QUARANTINED' if quarantine else 'REACH_REVIEW_REQUIRED' if findings else 'INCOMPLETE' if gaps else 'BOUNDED_REACH_ACCOUNTED'
    return {'format':'opentools.sta-exception-review.v1','status':status,'exit_code':2 if quarantine or gaps and not findings else 1 if findings else 0,
      'contract_digest':digest(c),'evidence_digest':digest(e),'scope':{k:x[k] for k in IDENTITY},'native_status':'completed','population_complete':complete,
      'counts':{'from_instances':len(n['selectors']['from']),'to_instances':len(n['selectors']['to']),'queried_pairs':len(n['phases']['before']['pairs']),'before_setup_pairs':len({path_id(p) for p in n['phases']['before']['paths']}),'after_setup_pairs':len({path_id(p) for p in n['phases']['after']['paths']}),'before_native_representatives':len(n['phases']['before']['paths']),'after_native_representatives':len(n['phases']['after']['paths']),'masked_setup_pairs':sum(r['setup_masked'] for r in rows)},
      'paths':rows,'findings':findings,'gaps':gaps,'quarantine':quarantine,'limits':LIMITS}

def snapshot(c,e,r):
    require(not r['quarantine'],'Foreign evidence cannot enter a comparable snapshot')
    exception=c['exception'];configuration={};premises=[]
    for port,value in exception['case_premises'].items():
        key='case::'+port;native=e['native']['phases']['before']['cases'].get(port);configuration[key]=int(native) if native in ('0','1') else None
        premises.append({'key':key,'equals':value,'evidence_ref':exception['rationale_ref'] or 'unresolved-rationale'})
    paths=[]
    for row in r['paths']:
        p=row['intent'];meaning={k:p.get(k) if p else None for k in ('source_role','destination_role','timing_required')}
        if row['setup_masked']:paths.append({'id':row['id'],'object':row['id'],'rule':'NATIVE_SETUP_ENDPOINT_PAIR_MASKED','message':json.dumps(meaning,sort_keys=True),'evidence_ref':e['context']['run_ref']+'/native.jsonl','kind':'native-masking-observation-not-a-tool-violation'})
    definition={'id':exception['id'],'rationale_revision':exception['rationale_revision'],'setup':True,'from_pattern':e['context']['setup']['from_pattern'],'to_pattern':e['context']['setup']['to_pattern'],'allowed_role_pairs':exception['allowed_role_pairs'],'case_premises':exception['case_premises']}
    s={'format':'opentools.waiver-snapshot.v1','run_id':e['context']['run_ref'],'scope':e['context']['scope_ref'],'configuration_ref':e['context']['configuration_ref'],'identity_basis':'native-flat-setup-endpoint-pair.v1','configuration_basis':'native-case-values.v1','configuration':configuration,
      'tool':{'name':'OpenROAD-OpenSTA','version':VERSION,'ruleset':PROFILE},'population_complete':r['population_complete'],'capture':{'profile':PROFILE,'top':'top','population_basis':'max-setup-endpoint-pairs-single-clock-per-selected-register.v1'},
      'waivers':[{'id':exception['id'],'definition_sha256':digest(definition),'complete':r['population_complete'],'findings':paths}]}
    return s,{'format':'opentools.waiver-policy.v1','waivers':[{'id':exception['id'],'premises':premises}]}

def drift(bc,be,brun,cc,ce,crun,mapping=None):
    before=inspect(bc,be,brun);after=inspect(cc,ce,crun);a,_=snapshot(bc,be,before);b,p=snapshot(cc,ce,after);audit=compare(a,b,p,mapping)
    review=bool(before['findings'] or after['findings'] or audit['review_required']);incomplete=bool(before['gaps'] or after['gaps'] or audit['status']=='incomplete')
    return {'format':'opentools.sta-exception-drift.v1','status':'incomplete' if incomplete else 'review_required' if review else 'unchanged_within_scope','review_required':review,'exit_code':2 if incomplete else 1 if review else 0,
      'baseline':before,'current':after,'baseline_snapshot':a,'current_snapshot':b,'policy':p,'audit':audit,'identity_map_digest':digest(mapping) if mapping is not None else None,'limits':LIMITS}

def markdown(r):
    def clean(v):return html.escape(str(v)).replace('|','&#124;').replace('\n',' ').replace('\r',' ')
    lines=['# Timing exception review','',r['status'],'']
    reviews=[('baseline',r['baseline']),('current',r['current'])] if r['format']=='opentools.sta-exception-drift.v1' else [('current',r)]
    for side,value in reviews:
        lines += [side+': '+str(value['counts']),'','| Native setup pair | Masked | Source clock | Destination clock |','|---|---|---|---|']
        for p in value['paths']:lines.append('| '+' | '.join(clean(p[k]) for k in ('id','setup_masked','source_clock','destination_clock'))+' |')
        lines.append('')
        for group in ('findings','gaps','quarantine'):
            for f in value[group]:lines.append('- '+side+' '+group+': '+clean(f['code'])+' '+clean(f['path'] or '')+'; '+clean(f['detail']))
    if 'audit' in r:
        for w in r['audit']['waivers']:
            for i in w['issues']:lines.append('- population: '+clean(i['code'])+'; '+clean(i['message']))
    return '\n'.join(lines+['',LIMITS,''])
