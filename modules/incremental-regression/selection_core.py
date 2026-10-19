"""Explainable advisory selection and retained campaign feedback; no runner."""
import hashlib
import json
from pathlib import Path


def require(value,message):
    if not value:raise ValueError(message)


def text(value):return isinstance(value,str) and bool(value.strip())
def nullable(value):return value is None or text(value)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def fingerprint(value):return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def read_json(path):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'Duplicate JSON key: '+key)
            result[key]=value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON: '+value)))


def shape(value,keys,optional=()):
    require(isinstance(value,dict) and set(keys)<=set(value) and set(value)<=set(keys)|set(optional),
            'Expected fields: '+', '.join(keys))


def string_list(value):return isinstance(value,list) and all(text(v) for v in value) and len(set(value))==len(value)
def flag(value):return value is None or type(value) is bool


def entries(value,keys,identity):
    require(isinstance(value,list),'Expected entry list')
    seen=set()
    for item in value:
        shape(item,keys)
        require(text(item[identity]) and item[identity] not in seen,'Duplicate/invalid '+identity)
        seen.add(item[identity])
    return seen


def validate(universe,changes,mapping,policy):
    shape(universe,('format','universe_ref','revision_ref','scope_ref','source_ref','complete','tests'),('provenance',))
    require(universe['format']=='opentools.test-universe.v1' and all(nullable(universe[k]) for k in ('universe_ref','revision_ref','scope_ref','source_ref'))
            and flag(universe['complete']),'Invalid independent universe')
    entries(universe['tests'],('id','name','configuration_ref','execution_ref','available','evidence_ref'),'id')
    for test in universe['tests']:
        require(all(nullable(test[k]) for k in ('name','configuration_ref','execution_ref','evidence_ref')) and flag(test['available']),'Invalid test entry')
    shape(changes,('format','change_ref','base_revision_ref','revision_ref','scope_ref','diff_ref','complete','items'),('provenance',))
    require(changes['format']=='opentools.regression-change.v1' and flag(changes['complete'])
            and all(nullable(changes[k]) for k in ('change_ref','base_revision_ref','revision_ref','scope_ref','diff_ref')),'Invalid change inventory')
    entries(changes['items'],('id','path','category','evidence_ref'),'id')
    require(all(all(nullable(v[k]) for k in ('path','category','evidence_ref')) for v in changes['items']),'Invalid changed item')
    shape(mapping,('format','mapping_ref','scope_ref','source_ref','universe_sha256','change_sha256','entries'),('provenance',))
    require(mapping['format']=='opentools.test-mapping.v1' and all(nullable(mapping[k]) for k in ('mapping_ref','scope_ref','source_ref','universe_sha256','change_sha256')),'Invalid mapping')
    entries(mapping['entries'],('change_id','test_ids','complete','evidence_ref'),'change_id')
    require(all(string_list(v['test_ids']) and flag(v['complete']) and nullable(v['evidence_ref']) for v in mapping['entries']),'Invalid mapping entry')
    shape(policy,('format','policy_ref','scope_ref','source_ref','universe_sha256','stage','mandatory_ids','required_ids','defer_ids','later_stage_ref','broaden_categories','unknown_impact'),('provenance',))
    require(policy['format']=='opentools.regression-policy.v1' and all(nullable(policy[k]) for k in ('policy_ref','scope_ref','source_ref','universe_sha256','stage','later_stage_ref'))
            and all(string_list(policy[k]) for k in ('mandatory_ids','required_ids','defer_ids','broaden_categories'))
            and policy['unknown_impact'] in ('broaden_all','record_gap'),'Invalid selection policy')
    for value in (universe,changes,mapping,policy):canonical(value)


def plan(universe,changes,mapping,policy):
    validate(universe,changes,mapping,policy)
    conflicts=[];gaps=[];impact=[];warnings=[]
    ids=[v['id'] for v in universe['tests']];known=set(ids)
    changed={v['id']:v for v in changes['items']}
    hashes={'universe':fingerprint(universe),'changes':fingerprint(changes),'mapping':fingerprint(mapping),'policy':fingerprint(policy)}
    reasons={key:[] for key in ids}
    def all_tests(reason):
        for values in reasons.values():values.append(reason)
    def uncertainty(change_id,reason):
        broaden=policy['unknown_impact']=='broaden_all'
        impact.append({'change_id':change_id,'reason':reason,'resolution':'all_known_tests_selected' if broaden else 'unresolved'})
        if broaden:all_tests({'kind':'unknown_impact_broadening','change_id':change_id,'evidence_ref':reason})
        else:gaps.append('Unresolved impact: '+str(change_id)+': '+reason)
    for record,names,label in [(universe,('universe_ref','revision_ref','scope_ref','source_ref'),'universe'),
                               (changes,('change_ref','base_revision_ref','revision_ref','scope_ref','diff_ref'),'changes'),
                               (mapping,('mapping_ref','source_ref'),'mapping'),(policy,('policy_ref','source_ref','stage','later_stage_ref'),'policy')]:
        for name in names:
            if not text(record[name]):gaps.append('Missing '+label+' '+name)
    if universe['complete'] is not True:gaps.append('Independent applicable universe is not declared complete')
    if not ids:gaps.append('Empty universe does not establish a useful regression stage')
    if changes['complete'] is not True:uncertainty(None,'Change/dependency inventory is incomplete')
    for label,value in [('changes',changes),('mapping',mapping),('policy',policy)]:
        if value['scope_ref']!=universe['scope_ref'] or not text(value['scope_ref']):
            conflicts.append(label+' scope does not bind the universe scope');all_tests({'kind':'scope_mismatch_broadening','evidence_ref':label})
    if changes['revision_ref']!=universe['revision_ref']:
        conflicts.append('Universe and current change revision differ');all_tests({'kind':'revision_mismatch_broadening','evidence_ref':'changes/universe'})
    mapping_bound=True
    for key,expected in [('universe_sha256',hashes['universe']),('change_sha256',hashes['changes'])]:
        if mapping[key]!=expected:
            mapping_bound=False;conflicts.append('Mapping '+key+' is stale/foreign')
    if not mapping_bound:uncertainty(None,'Mapping does not bind these exact universe/change records')
    if policy['universe_sha256']!=hashes['universe']:
        conflicts.append('Policy does not bind this exact independent universe');all_tests({'kind':'policy_mismatch_broadening','evidence_ref':'policy'})
    for key in ('mandatory_ids','required_ids','defer_ids'):
        missing=set(policy[key])-known
        if missing:
            conflicts.append('Policy '+key+' contains nonexistent tests: '+', '.join(sorted(missing)))
            all_tests({'kind':'policy_missing_test_broadening','evidence_ref':key})
    if not set(policy['mandatory_ids'])<=set(policy['required_ids']):conflicts.append('Mandatory stage tests must remain in required obligations')
    for key in set(policy['mandatory_ids']) & known:reasons[key].append({'kind':'mandatory_stage_policy','evidence_ref':policy['source_ref']})
    by_change={v['change_id']:v for v in mapping['entries']}
    dangling=set(by_change)-set(changed)
    if dangling:
        conflicts.append('Mapping refers to absent changed items: '+', '.join(sorted(dangling)))
        uncertainty(None,'Mapping inventory contains absent change IDs')
    for item in changes['items']:
        key=item['id'];entry=by_change.get(key)
        if any(not text(item[k]) for k in ('path','category','evidence_ref')):uncertainty(key,'Changed item context is incomplete')
        if item['category'] in policy['broaden_categories']:
            all_tests({'kind':'broad_impact_category','change_id':key,'evidence_ref':item['evidence_ref']})
        if not mapping_bound:continue
        if entry is None:
            uncertainty(key,'No explicit current mapping');continue
        unknown_ids=set(entry['test_ids'])-known
        if unknown_ids:
            conflicts.append('Mapping contains nonexistent/renamed tests: '+', '.join(sorted(unknown_ids)))
            uncertainty(key,'Mapped test identity is absent; no fuzzy rename is inferred')
        if entry['complete'] is not True or not text(entry['evidence_ref']):uncertainty(key,'Mapping impact scope is incomplete/unsourced')
        for test_id in set(entry['test_ids']) & known:
            reasons[test_id].append({'kind':'explicit_change_mapping','change_id':key,'evidence_ref':entry['evidence_ref']})
    population=[]
    for test in universe['tests']:
        key=test['id'];selected=bool(reasons[key])
        disposition='selected' if selected else 'deferred' if key in policy['defer_ids'] else 'unselected'
        if selected and key in policy['defer_ids']:warnings.append('Selection overrides requested deferral: '+key)
        if any(not text(test[k]) for k in ('name','configuration_ref','execution_ref','evidence_ref')):
            gaps.append('Incomplete universe test metadata: '+key)
        if selected and test['available'] is not True:gaps.append('Selected test is unavailable or availability unknown: '+key)
        population.append({**test,'disposition':disposition,'reasons':reasons[key],'required':key in policy['required_ids'],
                           'execution':'not_executed','later_stage_ref':policy['later_stage_ref']})
    report={'format':'opentools.regression-selection.v1','status':'review_required' if conflicts else 'needs_context' if gaps else 'advisory_selection',
        'stage':policy['stage'],'input_hashes':hashes,'population':population,
        'selected_ids':[v['id'] for v in population if v['disposition']=='selected'],
        'deferred_ids':[v['id'] for v in population if v['disposition']=='deferred'],
        'unselected_ids':[v['id'] for v in population if v['disposition']=='unselected'],
        'unavailable_ids':[v['id'] for v in population if v['available'] is False],
        'availability_unknown_ids':[v['id'] for v in population if v['available'] is None],
        'remaining_required_ids':[v['id'] for v in population if v['required']],
        'impact_gaps':impact,'conflicts':conflicts,'missing_context':gaps,'warnings':warnings,
        'release_completeness':'not_established','limits':'Caller-declared exact identities/mappings/policy only; no proof of dependency truth, semantic impact, test adequacy, scheduling, native execution or release completeness.'}
    return report


def validate_results(value):
    shape(value,('format','campaign_ref','kind','scope_ref','source_ref','universe_sha256','change_sha256','selection_sha256','complete','attempts'),('provenance',))
    require(value['format']=='opentools.regression-results.v1' and value['kind'] in ('targeted','full') and flag(value['complete'])
            and all(nullable(value[k]) for k in ('campaign_ref','scope_ref','source_ref','universe_sha256','change_sha256','selection_sha256')),'Invalid campaign results')
    entries(value['attempts'],('attempt_ref','test_id','state','run_ref','evidence_ref','wall_ns'),'attempt_ref')
    require(all(text(v['test_id']) and v['state'] in ('pass','fail','error','skipped','not_run') and nullable(v['run_ref']) and nullable(v['evidence_ref'])
        and (v['wall_ns'] is None or type(v['wall_ns']) is int and v['wall_ns']>=0) for v in value['attempts']),'Invalid test attempt')
    canonical(value)


def feedback(universe,changes,mapping,policy,results,full=None):
    selection=plan(universe,changes,mapping,policy)
    conflicts=[];gaps=[];known={v['id'] for v in universe['tests']};selected=set(selection['selected_ids'])
    records=[('primary',results)]+([('full_comparison',full)] if full is not None else [])
    indexed={};summaries=[]
    for label,record in records:
        validate_results(record)
        local_conflicts=[];local_gaps=[];by_test={key:[] for key in known};bound=True
        for key,expected in [('universe_sha256',fingerprint(universe)),('change_sha256',fingerprint(changes)),('scope_ref',universe['scope_ref'])]:
            if record[key]!=expected:
                local_conflicts.append('Foreign/unknown result '+key);bound=False
        if record['kind']=='targeted' and record['selection_sha256']!=fingerprint(selection):
            local_conflicts.append('Targeted results do not bind this exact selection');bound=False
        if record['kind']=='full' and record['selection_sha256'] is not None and record['selection_sha256']!=fingerprint(selection):
            local_conflicts.append('Full results assert a foreign selection binding');bound=False
        if label=='full_comparison' and record['kind']!='full':
            local_conflicts.append('Comparison packet is not an independently enumerated full campaign');bound=False
        for key in ('campaign_ref','source_ref'):
            if not text(record[key]):local_gaps.append('Missing result '+key)
        for attempt in record['attempts']:
            key=attempt['test_id']
            if key not in known:local_conflicts.append('Result has absent/renamed test ID: '+key);continue
            usable=text(attempt['evidence_ref']) and (attempt['state'] in ('skipped','not_run') or text(attempt['run_ref']))
            if not usable:local_gaps.append('Unsourced attempt: '+attempt['attempt_ref'])
            by_test[key].append({**attempt,'usable':usable})
        present={key for key,values in by_test.items() if values}
        expected=known if record['kind']=='full' else selected
        if record['kind']=='targeted' and present-selected:local_conflicts.append('Targeted packet includes tests outside its claimed selection; retain them in a separate full/extended campaign')
        if record['complete'] is True and expected-present:local_conflicts.append('Declared complete result export omits expected test IDs')
        if record['complete'] is not True:local_gaps.append('Result export completeness is not established')
        eligible=bound and not any(not text(record[k]) for k in ('campaign_ref','source_ref'))
        indexed[label]={key:[v for v in values if eligible and v['usable']] for key,values in by_test.items()}
        summaries.append({'label':label,'kind':record['kind'],'campaign_ref':record['campaign_ref'],'sha256':fingerprint(record),
            'eligible_for_bound_feedback':eligible,'export_population_present':expected<=present,'declared_complete':record['complete'],
            'present_ids':sorted(present),'missing_ids':sorted(expected-present),'attempts':record['attempts'],
            'conflicts':local_conflicts,'missing_context':local_gaps})
        conflicts.extend(label+': '+v for v in local_conflicts);gaps.extend(label+': '+v for v in local_gaps)
    def states(label,key):return [v['state'] for v in indexed.get(label,{}).get(key,[])]
    def passed(values):return 'pass' in values and not any(v in ('fail','error') for v in values)
    primary_pass=[key for key in selection['selected_ids'] if passed(states('primary',key))]
    selected_pending=[key for key in selection['selected_ids'] if key not in primary_pass]
    observations=[];failed=[];errors=[];mixed=[];missed=[];outside_errors=[];remaining=[]
    for test in selection['population']:
        key=test['id'];a=states('primary',key);b=states('full_comparison',key);combined=a+b
        if 'fail' in combined:failed.append(key)
        if 'error' in combined:errors.append(key)
        if 'pass' in combined and any(v in ('fail','error') for v in combined):mixed.append(key)
        full_states=b if full is not None else a if results['kind']=='full' else []
        if key not in selected and 'fail' in full_states:missed.append(key)
        if key not in selected and 'error' in full_states:outside_errors.append(key)
        satisfied=passed(combined)
        if test['required'] and not satisfied:remaining.append(key)
        observations.append({'id':key,'disposition':test['disposition'],'required':test['required'],'primary_states':a,
                             'full_comparison_states':b,'recorded_pass_without_failure':satisfied,'still_requires_action':test['required'] and not satisfied})
    if selected_pending:gaps.append('Selected tests lack clean sourced passes: '+', '.join(selected_pending))
    status='review_required' if conflicts or selection['conflicts'] else 'failures_observed' if failed or errors else 'needs_context' if gaps or selection['missing_context'] else 'recorded_feedback'
    return {'format':'opentools.regression-feedback.v1','status':status,'selection':selection,'selection_sha256':fingerprint(selection),
            'campaigns':summaries,'population':observations,'selected_pass_ids':primary_pass,'selected_pending_ids':selected_pending,
            'failed_ids':failed,'error_ids':errors,'mixed_attempt_ids':mixed,'failures_outside_selection':missed,'errors_outside_selection':outside_errors,
            'remaining_required_ids':remaining,'conflicts':conflicts,'missing_context':gaps,'release_completeness':'not_established',
            'limits':'Source/binding/population and declared attempt labels only. Every retry remains visible; a later pass does not erase a failure. No automatic release, semantic checker validity, total effort or savings proof.'}


def exit_code(report):
    return {'advisory_selection':0,'recorded_feedback':0,'review_required':1,'failures_observed':1,'needs_context':2}[report['status']]
