"""Saved experiment-plan/result correspondence; no inference or job launcher."""
import hashlib
import json
from pathlib import Path

ACTIONS=('inspect_existing','request_context','propose_run','stop')
KINDS=('observation','inconclusive','execution_failed','replay_diverged')


def require(condition,message):
    if not condition:
        raise ValueError(message)


def text(value):
    return isinstance(value,str) and bool(value.strip())


def nullable(value):
    return value is None or text(value)


def shape(value,keys,optional=()):
    require(isinstance(value,dict) and set(keys)<=set(value) and set(value)<=set(keys)|set(optional),
            'Invalid fields; expected '+', '.join(keys))


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def read_json(path):
    def unique(pairs):
        out={}
        for key,value in pairs:
            require(key not in out,'Duplicate JSON key: '+key)
            out[key]=value
        return out
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique,
        parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Nonfinite JSON: '+v)))


def strings(value):
    return isinstance(value,list) and all(text(v) for v in value)


def unique_list(value,keys,label):
    require(isinstance(value,list),label+' must be a list')
    seen=set()
    for item in value:
        shape(item,keys)
        require(text(item['id']) and item['id'] not in seen,'Unique '+label+' IDs required')
        seen.add(item['id'])
    return seen


def unknown(value):
    if value is None:return True
    if isinstance(value,dict):return any(unknown(v) for v in value.values())
    return isinstance(value,list) and any(unknown(v) for v in value)


def validate_plan(plan):
    shape(plan,('format','plan_ref','investigation_ref','original_run_ref','observation','question','hypotheses','variables',
                'required_observations','outcomes','next_action','stopping_condition','reproduction','prior_search','unknowns'),('provenance',))
    canonical(plan)
    require(plan['format']=='opentools.experiment-plan.v1' and text(plan['plan_ref']),'Unsupported experiment plan')
    require(all(nullable(plan[k]) for k in ('investigation_ref','original_run_ref','question','stopping_condition')) and strings(plan['unknowns']),
            'Invalid plan references/question/unknowns')
    shape(plan['observation'],('statement','evidence_ref'))
    require(all(nullable(v) for v in plan['observation'].values()),'Invalid initial observation')
    hypotheses=unique_list(plan['hypotheses'],('id','statement','basis_ref'),'hypothesis')
    require(all(nullable(v['statement']) and nullable(v['basis_ref']) for v in plan['hypotheses']),'Invalid hypothesis basis')
    names=set()
    require(isinstance(plan['variables'],list),'Variables must be a list')
    for item in plan['variables']:
        shape(item,('name','role','baseline','proposed','evidence_ref'))
        require(text(item['name']) and item['name'] not in names and item['role'] in ('fixed','intended','uncontrolled')
                and nullable(item['evidence_ref']),'Invalid/duplicate variable')
        names.add(item['name'])
    observations=unique_list(plan['required_observations'],('id','description','scope','attainability_ref'),'observation')
    require(all(all(nullable(v[k]) for k in ('description','scope','attainability_ref')) for v in plan['required_observations']),
            'Invalid required observation')
    unique_list(plan['outcomes'],('id','kind','condition','requires','effects','next_step','evidence_ref'),'outcome')
    for item in plan['outcomes']:
        require(item['kind'] in KINDS and all(nullable(item[k]) for k in ('condition','next_step','evidence_ref'))
                and strings(item['requires']) and len(item['requires'])==len(set(item['requires']))
                and set(item['requires'])<=observations,'Invalid outcome/observation mapping')
        seen=set()
        require(isinstance(item['effects'],list),'Hypothesis effects must be a list')
        for effect in item['effects']:
            shape(effect,('hypothesis_id','assessment'))
            require(effect['hypothesis_id'] in hypotheses and effect['hypothesis_id'] not in seen
                    and effect['assessment'] in ('supported','weakened','unresolved','not_tested'),'Invalid hypothesis effect')
            seen.add(effect['hypothesis_id'])
    action=plan['next_action']
    shape(action,('kind','summary','rationale','alternatives','evidence_ref'))
    require(action['kind'] in ACTIONS and all(nullable(action[k]) for k in ('summary','rationale','evidence_ref'))
            and isinstance(action['alternatives'],list),'Invalid next action')
    for item in action['alternatives']:
        shape(item,('kind','why_not','evidence_ref'))
        require(item['kind'] in ACTIONS and nullable(item['why_not']) and nullable(item['evidence_ref']),'Invalid alternative route')
    shape(plan['reproduction'],('kind','basis_ref','limits'))
    require(plan['reproduction']['kind'] in ('original_reproduction','exploratory','evidence_only')
            and nullable(plan['reproduction']['basis_ref']) and strings(plan['reproduction']['limits']),'Invalid reproduction basis')
    shape(plan['prior_search'],('performed','scope_ref','evidence_ref'))
    require(plan['prior_search']['performed'] is None or type(plan['prior_search']['performed']) is bool,'Invalid prior search flag')
    require(all(nullable(plan['prior_search'][k]) for k in ('scope_ref','evidence_ref')),'Invalid prior search basis')


def design_key(plan):
    """Exact declared design, excluding only its ID/provenance/acknowledged gaps."""
    return {k:v for k,v in plan.items() if k not in ('plan_ref','provenance','unknowns')}


def audit(plan,prior=()):
    validate_plan(plan)
    gaps=[];conflicts=[];warnings=[];repeats=[]
    for name in ('investigation_ref','original_run_ref','question','stopping_condition'):
        if not text(plan[name]):gaps.append('Missing '+name)
    for key in ('statement','evidence_ref'):
        if not text(plan['observation'][key]):gaps.append('Missing initial observation '+key)
    action=plan['next_action']
    for key in ('summary','rationale','evidence_ref'):
        if not text(action[key]):gaps.append('Missing next-action '+key)
    for item in action['alternatives']:
        if not text(item['why_not']) or not text(item['evidence_ref']):gaps.append('Unsourced alternative-route decision')
    if action['kind'] not in ('request_context','stop'):
        if len(plan['hypotheses'])<2:gaps.append('At least two grounded explanations are needed for this investigation step')
        if not plan['required_observations']:gaps.append('No required observations specified')
        if not plan['outcomes']:gaps.append('No outcome-to-decision map specified')
    for item in plan['hypotheses']:
        if not text(item['statement']) or not text(item['basis_ref']):gaps.append('Ungrounded hypothesis: '+item['id'])
    for item in plan['required_observations']:
        if any(not text(item[k]) for k in ('description','scope','attainability_ref')):
            gaps.append('Unestablished observation/attainability: '+item['id'])
    for item in plan['variables']:
        if not text(item['evidence_ref']):gaps.append('Unsourced variable: '+item['name'])
        if item['role']=='fixed':
            if unknown(item['baseline']) or unknown(item['proposed']):gaps.append('Unknown fixed variable: '+item['name'])
            elif canonical(item['baseline'])!=canonical(item['proposed']):conflicts.append('Fixed variable changes: '+item['name'])
        if item['role']=='uncontrolled':warnings.append('Uncontrolled variable retained: '+item['name'])
    for item in plan['outcomes']:
        if any(not text(item[k]) for k in ('condition','next_step','evidence_ref')):gaps.append('Incomplete outcome/decision: '+item['id'])
        if item['kind']=='observation' and not item['requires']:gaps.append('Observation outcome has no required evidence: '+item['id'])
        if item['kind']!='observation' and any(v['assessment'] in ('supported','weakened') for v in item['effects']):
            warnings.append('Review negative-outcome effect scope and evidence; execution failure/divergence does not by itself resolve the original engineering question: '+item['id'])
    if action['kind']=='propose_run':
        search=plan['prior_search']
        if search['performed'] is not True or not text(search['scope_ref']) or not text(search['evidence_ref']):
            gaps.append('Existing evidence/prior experiments have not been inspected within a stated scope')
        if not action['alternatives']:gaps.append('No cheaper existing-evidence/context route considered')
        if not plan['variables']:gaps.append('Run controls/intended changes are not recorded')
        kinds={v['kind'] for v in plan['outcomes']}
        for kind in ('inconclusive','execution_failed'):
            if kind not in kinds:gaps.append('No decision for '+kind)
        if plan['reproduction']['kind']=='original_reproduction' and 'replay_diverged' not in kinds:
            gaps.append('No decision for divergent replay')
    if not text(plan['reproduction']['basis_ref']):gaps.append('Reproduction/exploration evidence basis missing')
    if plan['reproduction']['kind']=='original_reproduction':
        warnings.append('Reproduction is planned, not established; identical seed does not establish scheduling/external-state correspondence')
    for old in prior:
        validate_plan(old)
        if old['plan_ref']==plan['plan_ref'] and fingerprint(old)!=fingerprint(plan):
            conflicts.append('Prior plan identity reused for different content: '+old['plan_ref'])
        if fingerprint(design_key(old))==fingerprint(design_key(plan)):
            repeats.append({'plan_ref':old['plan_ref'],'plan_sha256':fingerprint(old),'same_record':fingerprint(old)==fingerprint(plan)})
    if repeats:warnings.append('Exact declared design repeats; this alone does not prove redundancy or forbid intentional replication')
    return {'format':'opentools.experiment-plan-review.v1','status':'review_required' if conflicts else 'needs_context' if gaps else 'structured_plan',
            'plan_ref':plan['plan_ref'],'plan_sha256':fingerprint(plan),'design_sha256':fingerprint(design_key(plan)),
            'next_action':action,'conflicts':conflicts,'missing_context':gaps,'declared_unknowns':plan['unknowns'],
            'repeated_designs':repeats,'warnings':warnings,
            'limits':'Structure, declared controls and exact history correspondence only; no hypothesis plausibility, semantic discrimination, evidence truth, cost optimum or native execution proof.'}


def validate_result(value):
    shape(value,('format','result_ref','plan_sha256','state','actual_route','execution','outcome_id','actual_variables',
                 'observations','correspondence','interpretation','remaining_unknowns','cost_observations'),('provenance',))
    canonical(value)
    require(value['format']=='opentools.experiment-result.v1' and text(value['result_ref']) and nullable(value['plan_sha256']), 'Invalid result identity/binding')
    require(value['state'] in ('not_executed','observed','failed','inconclusive','diverged') and value['actual_route'] in ACTIONS
            and nullable(value['outcome_id']) and nullable(value['interpretation']) and strings(value['remaining_unknowns']),'Invalid actual result state')
    ex=value['execution'];shape(ex,('attempted','run_ref','exit_code','evidence_ref'))
    require((ex['attempted'] is None or type(ex['attempted']) is bool) and (ex['exit_code'] is None or type(ex['exit_code']) is int)
            and nullable(ex['run_ref']) and nullable(ex['evidence_ref']),'Invalid execution evidence')
    require(isinstance(value['actual_variables'],list),'Actual variables must be a list')
    names=set()
    for item in value['actual_variables']:
        shape(item,('name','value','evidence_ref'))
        require(text(item['name']) and item['name'] not in names and nullable(item['evidence_ref']),'Invalid actual variable')
        names.add(item['name'])
    unique_list(value['observations'],('id','value','complete','evidence_ref'),'actual observation')
    require(all((v['complete'] is None or type(v['complete']) is bool) and nullable(v['evidence_ref']) for v in value['observations']),
            'Invalid observation completeness')
    shape(value['correspondence'],('status','evidence_ref','limits'))
    require(value['correspondence']['status'] in ('matched_selected_observables','unknown','diverged','not_applicable')
            and nullable(value['correspondence']['evidence_ref']) and strings(value['correspondence']['limits']),'Invalid result correspondence')
    require(isinstance(value['cost_observations'],list),'Costs must be a list')
    for item in value['cost_observations']:
        shape(item,('metric','value','unit','scope_ref','basis','evidence_ref'))
        require(text(item['metric']) and nullable(item['value']) and all(nullable(item[k]) for k in ('unit','scope_ref','evidence_ref'))
                and item['basis'] in ('measured','estimated','unknown'),'Invalid scoped cost observation')


def review_result(plan,result):
    base=audit(plan);validate_result(result)
    conflicts=[];gaps=[]
    if result['plan_sha256'] is None:gaps.append('Result has no original plan binding')
    elif result['plan_sha256']!=fingerprint(plan):conflicts.append('Result does not bind this unchanged original plan')
    if result['actual_route']!=plan['next_action']['kind']:conflicts.append('Actual route differs; retain this plan and record the changed experiment separately')
    outcomes={v['id']:v for v in plan['outcomes']}
    chosen=outcomes.get(result['outcome_id'])
    state=result['state'];ex=result['execution']
    if state=='not_executed':
        if result['outcome_id'] is not None or ex['attempted'] is True or result['observations']:
            conflicts.append('Unexecuted plan is presented with an actual outcome/execution')
    else:
        if chosen is None:gaps.append('No mapped actual outcome')
        expected={'observed':'observation','failed':'execution_failed','inconclusive':'inconclusive','diverged':'replay_diverged'}[state]
        if chosen and chosen['kind']!=expected:conflicts.append('Actual state contradicts selected outcome kind')
    if state=='observed' and result['actual_route']=='propose_run':
        if ex['attempted'] is not True or not text(ex['run_ref']) or ex['exit_code']!=0 or not text(ex['evidence_ref']):
            gaps.append('Completed actual run evidence not established')
    if result['actual_route']=='inspect_existing' and ex['attempted'] is True:
        conflicts.append('Existing-evidence route claims a new run; do not hide execution')
    if ex['attempted'] is False and (ex['run_ref'] is not None or ex['exit_code'] is not None):
        conflicts.append('Execution identity/exit is supplied although no execution was attempted')
    if ex['attempted'] is True and (not text(ex['run_ref']) or not text(ex['evidence_ref'])):
        gaps.append('Actual execution identity/evidence missing')
    if ex['exit_code'] is not None and ex['exit_code']!=0 and state=='observed':
        conflicts.append('Failed execution is interpreted as a normal observed outcome')
    if plan['reproduction']['kind']=='original_reproduction' and state=='observed':
        corr=result['correspondence']
        if corr['status']=='diverged':conflicts.append('Divergent replay cannot update original-reproduction hypotheses as a normal outcome')
        elif corr['status']!='matched_selected_observables' or not text(corr['evidence_ref']):gaps.append('Original/replay correspondence is unestablished')
    actual={v['name']:v for v in result['actual_variables']}
    if state!='not_executed':
        for var in plan['variables']:
            if var['role']=='uncontrolled':continue
            value=actual.get(var['name'])
            if value is None or unknown(value['value']) or not text(value['evidence_ref']):
                if state=='observed':gaps.append('Missing actual control/change evidence: '+var['name'])
            elif not unknown(var['proposed']) and canonical(value['value'])!=canonical(var['proposed']):
                conflicts.append('Actual value differs from the planned controlled/intervention value: '+var['name'])
    observations={v['id']:v for v in result['observations']}
    known={v['id'] for v in plan['required_observations']}
    if set(observations)-known:conflicts.append('Actual observation IDs are not in this plan')
    if chosen and state!='not_executed':
        for name in chosen['requires']:
            value=observations.get(name)
            if value is None or value['complete'] is not True or unknown(value['value']) or not text(value['evidence_ref']):
                gaps.append('Outcome lacks complete sourced observation: '+name)
    if state!='not_executed' and not text(result['interpretation']):gaps.append('Actual interpretation missing')
    status='review_required' if conflicts or base['conflicts'] else 'needs_context' if gaps or base['missing_context'] else {
        'not_executed':'not_executed','observed':'recorded_outcome','failed':'execution_failed','inconclusive':'inconclusive','diverged':'replay_diverged'}[state]
    return {'format':'opentools.experiment-result-review.v1','status':status,'plan_review':base,
            'result_ref':result['result_ref'],'result_sha256':fingerprint(result),'actual_state':state,
            'selected_outcome':chosen,'execution':ex,'correspondence':result['correspondence'],
            'actual_variables':result['actual_variables'],'observations':result['observations'],
            'conflicts':conflicts,'missing_context':gaps,'interpretation':result['interpretation'],
            'remaining_unknowns':result['remaining_unknowns'],'cost_observations':result['cost_observations'],
            'limits':'Bindings, declared controls, coverage flags and mapped interpretation only; no automatic semantic classification, fact-checking or proof that the selected outcome/hypothesis effect is true.'}


def exit_code(report):
    return {'structured_plan':0,'recorded_outcome':0,'review_required':1,'execution_failed':1,'replay_diverged':1,
            'needs_context':2,'not_executed':2,'inconclusive':2}[report['status']]
