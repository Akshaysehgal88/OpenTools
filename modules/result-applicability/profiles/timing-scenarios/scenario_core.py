"""Reconcile independently required scenarios with actual applicable native runs."""
import html
from scenario_common import REQUIRED_FIELDS,audit,digest,folder,read_json,require,result_exit,shape,text
from native_scenario import load,snapshot
from applicability_core import known
LIMITS='Coverage of the independently declared scenario obligations using a qualified selected maximum-setup observation. Counts, a clean sampled path and model PVT labels cannot establish all scenarios, hold timing, physical power/RC validity or STA signoff. Applicability/exclusion and ownership references require source review.'

def validate_plan(p):
    shape(p,{'format','scope_ref','design_ref','configuration_ref','requirements_ref','owner_ref','obligations'})
    require(p['format']=='opentools.sta-scenario-plan.v1' and all(text(p[k]) for k in ('scope_ref','design_ref','configuration_ref')),'Explicit plan identity required')
    for k in ('requirements_ref','owner_ref'):require(p[k] is None or text(p[k]),'Invalid plan source/owner')
    require(isinstance(p['obligations'],list) and 1<=len(p['obligations'])<=32,'Independent bounded obligation roster required');ids=set()
    for o in p['obligations']:
        shape(o,{'id','applicability','reason','basis_ref','exclusion_ref','required_fields'})
        require(text(o['id']) and o['id'] not in ids,'Distinct obligation IDs required');ids.add(o['id'])
        require(o['applicability'] in ('required','not_applicable',None),'Explicit applicability or unknown required')
        for k in ('reason','basis_ref','exclusion_ref'):require(o[k] is None or text(o[k]),'Invalid applicability basis')
        require(isinstance(o['required_fields'],dict) and REQUIRED_FIELDS<=set(o['required_fields']) and len(o['required_fields'])<=32,'Do not omit native/model/mode/power/clock/RC identity obligations')
        for name,v in o['required_fields'].items():
            shape(v,{'value','evidence_ref'});require(text(name) and (v['evidence_ref'] is None or text(v['evidence_ref'])),'Invalid original requirement field')
        require(text(o['required_fields']['scenario.mode']['value']) and text(o['required_fields']['scenario.corner']['value']),'Explicit mode/corner selection key required')

def review(root,plan,corpus):
    validate_plan(plan);shape(corpus,{'format','runs'});require(corpus['format']=='opentools.sta-scenario-corpus.v1' and isinstance(corpus['runs'],list) and len(corpus['runs'])<=64,'Explicit selected native inventory required')
    require(all(text(r) for r in corpus['runs']) and len(set(corpus['runs']))==len(corpus['runs']),'Distinct actual run IDs required; aliases do not add evidence')
    findings=[];gaps=[];quarantine=[];native=[];rows=[];records={}
    def add(out,code,detail,obligation=None,run_ref=None):out.append({'code':code,'obligation':obligation,'run_ref':run_ref,'detail':detail})
    for k in ('requirements_ref','owner_ref'):
        if plan[k] is None:add(gaps,'missing_plan_basis',k)
    for ref in corpus['runs']:
        e=load(root,ref);s=snapshot(e);ctx=e['context'];admitted=True
        for k in ('scope_ref','design_ref','configuration_ref'):
            if ctx[k]!=plan[k]:add(quarantine,'foreign_native_scope',k,run_ref=ref);admitted=False
        native.append({'run_ref':ref,'context':ctx,'native_status':s['result']['native_status'],'native_outcome':s['result']['outcome'],'native_complete':s['result']['complete'],'native_cases':e['native']['cases'],'effective_pvt':e['native']['operating'],'parasitics':e['native']['parasitics'],'paths':e['native']['paths'],'admitted':admitted})
        if admitted:records[ref]=s
    for o in plan['obligations']:
        row={'id':o['id'],'applicability':o['applicability'],'reason':o['reason'],'basis_ref':o['basis_ref'],'exclusion_ref':o['exclusion_ref'],'status':'unresolved','covered':False,'native_matches':[],'candidate_audits':[]};rows.append(row)
        missing=[k for k in ('reason','basis_ref') if o[k] is None]
        if missing:add(gaps,'missing_applicability_source',', '.join(missing),o['id'])
        if o['applicability'] is None:add(gaps,'unknown_scenario_applicability','Original source must determine whether the combination is required',o['id']);continue
        if o['applicability']=='not_applicable':
            if any(not known(v) for v in o['required_fields'].values()):add(gaps,'unresolved_exclusion_identity','An exclusion cannot account for an unidentified mode/model/power/clock/RC combination',o['id']);continue
            if o['exclusion_ref'] is None:add(gaps,'missing_scenario_exclusion','No explicit source-backed nonapplicability decision',o['id'])
            elif not missing:row['status']='source_declared_not_applicable'
            continue
        wanted=o['required_fields'];candidates=[]
        for ref,s in records.items():
            if all(s['fields'][k]['value']==wanted[k]['value'] for k in ('scenario.mode','scenario.corner')):candidates.append((ref,s))
        if not candidates:row['status']='missing';add(findings,'required_scenario_missing','No selected native run has this required mode/corner; other runs and duplicates cannot fill it',o['id']);continue
        request={'format':'opentools.result-request.v1','claim_id':o['id'],'claim':'Selected setup evidence for the independently required timing scenario.','scope_ref':plan['scope_ref'],'required_fields':wanted,'required_outcome':'any_observed'}
        for ref,s in candidates:
            a=audit(s,request,base_dir=root);row['candidate_audits'].append(a)
            if result_exit(a)==0:
                row['native_matches'].append(ref)
                if s['result']['outcome']=='fail':add(findings,'observed_selected_setup_violation','Native selected-path timing failure remains visible even though scenario evidence is present',o['id'],ref)
            elif a['status']=='inapplicable':add(findings,'selected_scenario_inapplicable','Mode/corner label matches but original source/model/clock/power/RC fields differ',o['id'],ref)
            else:add(gaps,'scenario_evidence_unresolved','Native outcome, observation completeness or required identity is unresolved',o['id'],ref)
        row['covered']=bool(row['native_matches']) and not missing;row['status']='selected_native_evidence_present' if row['covered'] else 'unresolved' if any(a['unknowns'] for a in row['candidate_audits']) else 'inapplicable'
    required=sum(o['applicability']=='required' for o in plan['obligations']);covered=sum(r['covered'] for r in rows)
    status='SCENARIO_REVIEW_REQUIRED' if findings else 'INCOMPLETE' if gaps or quarantine else 'DECLARED_SCENARIOS_ACCOUNTED'
    return {'format':'opentools.sta-scenario-review.v1','status':status,'exit_code':1 if findings else 2 if gaps or quarantine else 0,'scope':{k:plan[k] for k in ('scope_ref','design_ref','configuration_ref')},'plan_digest':digest(plan),'corpus_digest':digest(corpus),'requirements_ref':plan['requirements_ref'],'owner_ref':plan['owner_ref'],
      'counts':{'selected_runs':len(corpus['runs']),'admitted_runs':len(records),'required_obligations':required,'covered_obligations':covered,'source_declared_nonapplicable':sum(r['status']=='source_declared_not_applicable' for r in rows)},'obligations':rows,'native_runs':native,'findings':findings,'gaps':gaps,'quarantine':quarantine,
      'recheck_when':['required operating modes or power states change','model PVT, libraries, RC or clock/test conditions change','scenario exclusions or source correspondence change','native evidence/outcomes or requested analysis scope change'],'limits':LIMITS}

def markdown(r):
    def esc(v):return html.escape(str(v)).replace('|','&#124;').replace('\n',' ').replace('\r',' ')
    lines=['# Timing scenario coverage','',r['status'],'',f"Owner: {esc(r['owner_ref'])}; requirements: {esc(r['requirements_ref'])}.",'',str(r['counts']),'','| Obligation | Applicability | Evidence | Native runs |','|---|---|---|---|']
    for o in r['obligations']:lines.append('| '+' | '.join(esc(o[k]) for k in ('id','applicability','status','native_matches'))+' |')
    lines+=['','| Run | Original selected-setup result |','|---|---|']
    for run in r['native_runs']:lines.append('| '+esc(run['run_ref'])+' | '+esc(run['native_status'])+' |')
    for group in ('findings','gaps','quarantine'):
        for f in r[group]:lines.append('- '+group+': '+esc(f['code'])+' '+esc(f['obligation'] or f['run_ref'] or '')+'; '+esc(f['detail']))
    return '\n'.join(lines+['',LIMITS,''])
