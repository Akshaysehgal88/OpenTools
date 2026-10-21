"""Audit an explicit interaction roster against retained scenario/checker evidence."""
import html
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from progress_core import canonical,fingerprint,read_json,require,shape,summarize,text,validate_contract,validate_snapshot
from saved_native import FIELDS,contained,file_hash,revalidate
EXPECT={'run_ref','scope_ref','configuration_ref','model_ref','scenario_ref','clock_ref','reset_ref','reset_active','port_map','sources','command_sha256'}
RELATION={'resource_ref','producer_ref','consumer_ref','risk_ref','source_ref','revision_ref','design_source_sha256','configuration_ref'}
def known(value):
    if value is None or isinstance(value,str) and not text(value):return False
    if isinstance(value,dict):return bool(value) and all(known(v) for v in value.values())
    if isinstance(value,list):return all(known(v) for v in value)
    return True
def validate(plan,corpus):
    shape(plan,{'format','review_ref','claim','scope_ref','configuration_ref','model_ref','owner_ref','population_ref','population_complete','basis_ref','scope_facts','runs','obligations'})
    require(plan['format']=='opentools.interaction-obligations.v1' and text(plan['review_ref']) and text(plan['claim']),'Invalid interaction roster')
    require(all(plan[k] is None or text(plan[k]) for k in ('scope_ref','configuration_ref','model_ref','owner_ref','population_ref','basis_ref')) and (plan['population_complete'] is None or type(plan['population_complete']) is bool),'Invalid independent scope')
    require(isinstance(plan['scope_facts'],dict) and set(plan['scope_facts'])<={'retain'} and isinstance(plan['runs'],list) and isinstance(plan['obligations'],list),'Invalid scope facts/roster')
    for v in plan['scope_facts'].values():shape(v,{'value','basis_ref'});require(v['value'] is None or type(v['value']) is int and v['value'] in (0,1),'Invalid Boolean applicability fact');require(v['basis_ref'] is None or text(v['basis_ref']),'Invalid fact source')
    ids=[]
    for v in plan['runs']:
        shape(v,EXPECT);require(text(v['run_ref']),'Original run identity required');ids.append(v['run_ref'])
    require(len(ids)==len(set(ids)),'Duplicate requested run')
    ids=[]
    for o in plan['obligations']:
        shape(o,{'id','title','definition_ref','owner_ref','relationship','applicability','trigger','after','checkers'})
        require(text(o['id']) and text(o['title']) and all(o[k] is None or text(o[k]) for k in ('definition_ref','owner_ref')),'Invalid named interaction');ids.append(o['id'])
        shape(o['relationship'],RELATION);require(all(v is None or text(v) for v in o['relationship'].values()),'Invalid risk relationship')
        a=o['applicability'];shape(a,{'status','facts','basis_ref','reviewer_ref','reason'})
        require(a['status'] in ('applicable','not_applicable','unknown') and isinstance(a['facts'],dict) and set(a['facts'])<=set(plan['scope_facts']) and all(type(v) is int and v in (0,1) for v in a['facts'].values()) and all(a[k] is None or text(a[k]) for k in ('basis_ref','reviewer_ref','reason')),'Invalid reviewed applicability')
        require(isinstance(o['trigger'],list) and o['trigger'] and type(o['after']) is int and 0<=o['after']<=64,'Explicit trigger/window required')
        for term in o['trigger']:
            shape(term,{'field','offset','equals'});require(term['field'] in set(FIELDS)-{'tick','pre_clock','post_clock','enabled'} and type(term['offset']) is int and term['offset'] in (-1,0) and type(term['equals']) is int and term['equals'] in (0,1),'Unsupported typed trigger term')
        require(isinstance(o['checkers'],list) and o['checkers'],'Explicit checker links required');labels=[]
        for c in o['checkers']:
            shape(c,{'id','observed','basis_ref'});require(text(c['id']) and c['observed'] in ('post_pending','post_visible') and (c['basis_ref'] is None or text(c['basis_ref'])),'Invalid checker observation link');labels.append(c['id'])
        require(len(labels)==len(set(labels)),'Duplicate checker link')
    require(len(ids)==len(set(ids)),'Duplicate interaction ID')
    shape(corpus,{'format','complete','evidence_ref','runs'});require(corpus['format']=='opentools.interaction-evidence-corpus.v1' and (corpus['complete'] is None or type(corpus['complete']) is bool) and (corpus['evidence_ref'] is None or text(corpus['evidence_ref'])) and isinstance(corpus['runs'],list),'Invalid evidence corpus')
    paths=[]
    for r in corpus['runs']:
        shape(r,{'path','sha256'});require(text(r['path']) and isinstance(r['sha256'],str) and len(r['sha256'])==64 and all(c in '0123456789abcdef' for c in r['sha256']),'Invalid receipt identity');paths.append(r['path'])
    require(len(paths)==len(set(paths)),'Duplicate corpus receipt');canonical(plan);canonical(corpus)
def matches(terms,frames,tick):
    return all(tick+t['offset']>=0 and frames[tick+t['offset']][t['field']]==t['equals'] for t in terms)
def coverage_accounting(plan,runs,rows):
    population=[o['id'] for o in plan['obligations']];required=[r['id'] for r in rows if r['applicability']=='applicable'];basis='interaction:'+fingerprint(plan)
    contract={'format':'opentools.campaign-contract.v1','campaign_ref':plan['review_ref'],'scope_ref':plan['scope_ref'],'configuration_ref':plan['configuration_ref'],'model_ref':plan['model_ref'],
              'population_ref':plan['population_ref'],'population_complete':plan['population_complete'],'required_run_refs':[r['context']['run_ref'] for r in runs],'evidence_ref':plan['basis_ref'],
              'objectives':[{'id':'selected-interactions','kind':'coverage','description':'Only independently reviewed required interactions with complete passing native checker windows','basis_ref':basis,'policy_ref':plan['basis_ref'],
                             'eligible_states':['passed','failed'],'target':{'population_ids':population,'required_ids':required}}],
              'policy':{'ref':plan['basis_ref'],'evidence_ref':plan['basis_ref'],'allowed_recommendations':['inspect_effectiveness','seek_policy'],'limits':['Explicit finite roster only; no exhaustive interaction generation or release authority.']}}
    native_runs=[]
    for e in runs:
        ref=e['context']['run_ref'];hits=[r['id'] for r in rows if r['status']=='observed_pass' and any(w['run_ref']==ref and w['status']=='pass' for w in r['witnesses'])]
        native_runs.append({'run_ref':ref,'configuration_ref':plan['configuration_ref'],'model_ref':plan['model_ref'],'native_state':e['native']['status'],'state':'passed' if e['native']['status']=='PASS' else 'failed','evidence_ref':e['context']['window_ref'],
                            'measurements':[{'objective_id':'selected-interactions','basis_ref':basis,'evidence_ref':e['context']['window_ref'],'qualified':True,'complete':True,'data':{'population_ids':population,'hit_ids':hits}}],'resources':[]})
    snapshot={'format':'opentools.campaign-snapshot.v1','campaign_ref':plan['review_ref'],'snapshot_ref':plan['review_ref']+':selected-observations','scope_ref':plan['scope_ref'],'captured_at':None,'mode':'cumulative','complete':True,'evidence_ref':basis,'runs':native_runs}
    validate_contract(contract);validate_snapshot(snapshot);return {'contract':contract,'snapshot':snapshot,'summary':summarize(contract,snapshot),'limits':'Unknown wall-clock capture time and empty target sets retain parent gaps. Native failure in any selected witness prevents that obligation from being recorded as closure, even when another run passes.'}
def review(plan,corpus,root='.'):
    validate(plan,corpus);findings=[];gaps=[];rows=[];accepted=[];raw=[]
    report={'format':'opentools.interaction-obligation-review.v1','review_ref':plan['review_ref'],'claim':plan['claim'],'findings':findings,'gaps':gaps,'obligations':rows,'native_runs':raw,'accounting':None,
            'fingerprints':{'plan':fingerprint(plan),'corpus':fingerprint(corpus)},'limits':'Audits the supplied source-backed interaction roster and finite native checker windows only. Applicability/ownership/source review references are supplied, not authenticated. Trigger matching locates existing events, not a new verification engine or test-plan generator. No exhaustive coverage, oracle adequacy, liveness, physical-reset or signoff claim.'}
    def finish():report['status']='review_required' if findings else 'incomplete' if gaps else 'selected_obligations_supported';return report
    for key in ('scope_ref','configuration_ref','model_ref','owner_ref','population_ref','basis_ref'):
        if not text(plan[key]):gaps.append('Independent roster missing '+key)
    if plan['population_complete'] is not True or not plan['obligations']:gaps.append('Independent required interaction population is empty or not established complete')
    if corpus['complete'] is not True or not text(corpus['evidence_ref']):gaps.append('Scenario corpus completeness/source unknown')
    for name,fact in plan['scope_facts'].items():
        if not known(fact):gaps.append('Independent applicability fact unknown: '+name)
    expected={r['run_ref']:r for r in plan['runs']};seen=set()
    for receipt in corpus['runs']:
        try:
            path=contained(root,receipt['path']);require(file_hash(path)==receipt['sha256'],'Receipt hash differs');e=read_json(path);revalidate(e,path.parent);ctx=e['context'];ref=ctx['run_ref'];require(ref not in seen,'Duplicate native run identity');seen.add(ref)
        except (ValueError,OSError,KeyError,TypeError) as exc:gaps.append('Original scenario evidence unresolved: '+str(exc));continue
        record={'run_ref':ref,'native':e['native'],'context':ctx,'receipt':receipt,'quarantined':False};raw.append(record)
        request=expected.get(ref)
        if request is None:findings.append('Unexpected native run identity; quarantined: '+ref);record['quarantined']=True;continue
        actual={k:e['sources'] if k=='sources' else e['native']['command_sha256'] if k=='command_sha256' else ctx[k] for k in EXPECT}
        bad=False
        for key,value in request.items():
            if not known(value):gaps.append(ref+': requested '+key+' unknown');bad=True
            elif canonical(value)!=canonical(actual[key]):findings.append(ref+': foreign/different '+key+'; native conclusions quarantined');bad=True
        if request['scope_ref']!=plan['scope_ref'] or request['model_ref']!=plan['model_ref'] or request['configuration_ref']!=plan['configuration_ref']:
            findings.append(ref+': requested run does not bind independent roster scope/model/configuration');bad=True
        for key in ('scenario_basis_ref','instrumentation_review_ref','oracle_ref','scope_basis_ref','dependency_basis_ref'):
            if not text(ctx[key]):gaps.append(ref+': source/scope missing '+key);bad=True
        if ctx['dependencies_complete'] is not True:gaps.append(ref+': dependencies incomplete');bad=True
        for key,fact in plan['scope_facts'].items():
            if known(fact) and any(f[key]!=fact['value'] for f in e['frames']):findings.append(ref+': native applicability fact differs: '+key);bad=True
        record['quarantined']=bad
        if not bad:accepted.append(e)
    for ref in set(expected)-seen:gaps.append('Requested native scenario absent: '+ref)
    if not expected:gaps.append('No original scenario/run population supplied')
    for o in plan['obligations']:
        a=o['applicability'];row={'id':o['id'],'title':o['title'],'relationship':o['relationship'],'applicability':a['status'],'status':'unresolved','witnesses':[]};rows.append(row);local=[]
        if not all(known(v) for v in o['relationship'].values()) or not text(o['definition_ref']) or not text(o['owner_ref']):local.append('Independent risk relationship/definition/owner missing')
        if known(o['relationship']['configuration_ref']) and o['relationship']['configuration_ref']!=plan['configuration_ref']:
            findings.append(o['id']+': risk relationship belongs to a different configuration');local.append('Risk relationship scope conflicts with request')
        if known(o['relationship']['design_source_sha256']) and any(e['sources']['top.sv']!=o['relationship']['design_source_sha256'] for e in accepted):
            findings.append(o['id']+': stale risk relationship design identity; native conclusions quarantined');local.append('Risk relationship does not bind the compared design')
        if not all(text(a[k]) for k in ('basis_ref','reviewer_ref','reason')):local.append('Independent applicability review/source missing')
        if a['status']=='unknown':local.append('Applicability unresolved')
        for key,value in a['facts'].items():
            if not known(plan['scope_facts'][key]):local.append('Applicability fact source unknown: '+key)
            elif plan['scope_facts'][key]['value']!=value:findings.append(o['id']+': reviewed applicability contradicts independent fact '+key);local.append('Applicability conflicts with scope')
        if a['status']=='not_applicable' and not a['facts']:local.append('Nonapplicability requires an explicit source-backed scope fact')
        if any(not text(c['basis_ref']) for c in o['checkers']):local.append('Native checker-to-obligation source link missing')
        if local:gaps.extend(o['id']+': '+v for v in local);continue
        if a['status']=='not_applicable':row['status']='reviewed_not_applicable';continue
        for e in accepted:
            frames=e['frames'];lookup={(c['tick'],c['id']):c for c in e['checks']};ref=e['context']['run_ref']
            for t,frame in enumerate(frames):
                if frame['reset']==e['context']['reset_active'] or not matches(o['trigger'],frames,t):continue
                w={'run_ref':ref,'trigger_tick':t,'through_tick':t+o['after'],'status':'pass','failures':[],'gaps':[]};row['witnesses'].append(w)
                if w['through_tick']>=len(frames):w['gaps'].append('Native window ends before the declared observation span')
                for tick in range(t,min(len(frames),w['through_tick']+1)):
                    f=frames[tick]
                    if f['reset']==e['context']['reset_active']:w['gaps'].append('Initialization reset interrupts the declared observation span at tick '+str(tick))
                    if not f['enabled']:w['failures'].append('Checker disabled at required tick '+str(tick))
                    for link in o['checkers']:
                        c=lookup.get((tick,link['id']))
                        if c is None:w['gaps'].append('Required checker action absent at tick '+str(tick)+': '+link['id']);continue
                        if c['observed']!=f[link['observed']]:w['failures'].append('Checker observation does not bind native '+link['observed']+' at tick '+str(tick))
                        elif c['ok']==0:w['failures'].append('Native '+link['id']+' comparison failed at tick '+str(tick))
                w['status']='failure' if w['failures'] else 'incomplete' if w['gaps'] else 'pass'
        failed=[w for w in row['witnesses'] if w['status']=='failure'];incomplete=[w for w in row['witnesses'] if w['status']=='incomplete']
        if failed:row['status']='observed_failure';findings.append(o['id']+': native failure/invalid checking in selected combined observation window')
        elif row['witnesses'] and not incomplete:row['status']='observed_pass'
        if not row['witnesses']:gaps.append(o['id']+': no existing scenario demonstrates the declared combined trigger')
        for w in incomplete:gaps.extend(o['id']+': '+v for v in w['gaps'])
        # Preserve gaps even when a failure already establishes review is required.
        for w in failed:gaps.extend(o['id']+': '+v for v in w['gaps'])
    if not any(r['applicability']=='applicable' for r in rows):gaps.append('No independently applicable interaction in the selected roster')
    if all(text(plan[k]) for k in ('scope_ref','configuration_ref','model_ref','population_ref','basis_ref')) and plan['obligations']:report['accounting']=coverage_accounting(plan,accepted,rows)
    return finish()
def exit_code(r):return {'selected_obligations_supported':0,'review_required':1,'incomplete':2}[r['status']]
def markdown(r):
    def esc(v):return html.escape(str(v)).replace('|','&#124;').replace('\n','<br>')
    lines=['# Interaction obligation review','','Status: **'+r['status']+'**','',esc(r['claim']),'','| Interaction | Applicability | Observation |','| --- | --- | --- |']
    lines+=['| '+esc(o['title'])+' | '+esc(o['applicability'])+' | '+esc(o['status'])+' |' for o in r['obligations']]
    for title,key in [('Findings','findings'),('Missing evidence','gaps')]:lines+=['','## '+title,'']+(['- '+esc(v) for v in r[key]] or ['None within the selected scope.'])
    return '\n'.join(lines+['',esc(r['limits']),''])
