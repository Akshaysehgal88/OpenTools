"""Objective-specific offline campaign evidence; no scheduler or stopping action."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

STATES=('passed','failed','aborted','queued','running','not_run','unknown')
ACTIONS=('continue','inspect_effectiveness','redirect','seek_policy')


def require(value,message):
    if not value:raise ValueError(message)


def text(value):return isinstance(value,str) and bool(value.strip())
def nullable(value):return value is None or text(value)
def flag(value):return value is None or type(value) is bool
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def fingerprint(value):return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()
def strings(value):return isinstance(value,list) and all(text(v) for v in value) and len(set(value))==len(value)


def shape(value,keys,optional=()):
    require(isinstance(value,dict) and set(keys)<=set(value) and set(value)<=set(keys)|set(optional),'Expected fields: '+', '.join(keys))


def entries(value,keys,identity,optional=()):
    require(isinstance(value,list),'Expected entry list');seen=set()
    for item in value:
        shape(item,keys,optional)
        require(text(item[identity]) and item[identity] not in seen,'Duplicate/invalid '+identity)
        seen.add(item[identity])
    return seen


def read_json(path):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'Duplicate JSON key: '+key);result[key]=value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=pairs,
        parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Nonfinite JSON: '+v)))


def timestamp(value):
    if value is None:return None
    require(text(value),'Invalid snapshot timestamp')
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    require(result.tzinfo is not None,'Snapshot timestamps require a timezone')
    return result


def validate_contract(value):
    shape(value,('format','campaign_ref','scope_ref','configuration_ref','model_ref','population_ref','population_complete','required_run_refs','evidence_ref','objectives','policy'),('provenance',))
    require(value['format']=='opentools.campaign-contract.v1' and flag(value['population_complete']) and strings(value['required_run_refs'])
        and all(nullable(value[k]) for k in ('campaign_ref','scope_ref','configuration_ref','model_ref','population_ref','evidence_ref')),'Invalid campaign contract')
    entries(value['objectives'],('id','kind','description','basis_ref','policy_ref','eligible_states','target'), 'id')
    for item in value['objectives']:
        require(item['kind'] in ('execution','coverage','exposure','manual') and strings(item['eligible_states'])
                and set(item['eligible_states'])<=set(STATES) and all(nullable(item[k]) for k in ('description','basis_ref','policy_ref')),'Invalid objective')
        target=item['target']
        if item['kind']=='execution':
            require(item['eligible_states']==['passed'],'Execution objectives require recorded native checker passes')
            shape(target,('run_refs',));require(strings(target['run_refs']) and set(target['run_refs'])<=set(value['required_run_refs']),'Execution target must retain independent required IDs')
        elif item['kind']=='coverage':
            shape(target,('population_ids','required_ids'))
            require(strings(target['population_ids']) and strings(target['required_ids']) and set(target['required_ids'])<=set(target['population_ids']),'Invalid coverage population/target')
        elif item['kind']=='exposure':
            shape(target,('value','unit'));require(type(target['value']) is int and target['value']>=0 and nullable(target['unit']),'Invalid exposure target')
        else:require(nullable(target),'Manual objective target is a source-backed description or null')
    shape(value['policy'],('ref','evidence_ref','allowed_recommendations','limits'))
    require(nullable(value['policy']['ref']) and nullable(value['policy']['evidence_ref']) and strings(value['policy']['allowed_recommendations'])
            and set(value['policy']['allowed_recommendations'])<=set(ACTIONS) and strings(value['policy']['limits']),'Invalid recommendation policy')
    canonical(value)


def validate_snapshot(value):
    shape(value,('format','campaign_ref','snapshot_ref','scope_ref','captured_at','mode','complete','evidence_ref','runs'),('provenance',))
    require(value['format']=='opentools.campaign-snapshot.v1' and value['mode']=='cumulative' and flag(value['complete'])
        and all(nullable(value[k]) for k in ('campaign_ref','snapshot_ref','scope_ref','evidence_ref')),'Invalid cumulative snapshot')
    timestamp(value['captured_at'])
    entries(value['runs'],('run_ref','configuration_ref','model_ref','native_state','state','evidence_ref','measurements','resources'),'run_ref')
    for run in value['runs']:
        require(run['state'] in STATES and all(nullable(run[k]) for k in ('configuration_ref','model_ref','native_state','evidence_ref')),'Invalid native run context/state')
        entries(run['measurements'],('objective_id','basis_ref','evidence_ref','qualified','complete','data'),'objective_id')
        require(all(nullable(v['basis_ref']) and nullable(v['evidence_ref']) and flag(v['qualified']) and flag(v['complete']) for v in run['measurements']),'Invalid measurement qualification')
        require(isinstance(run['resources'],list),'Resource observations must be a list')
        for observation in run['resources']:
            shape(observation,('metric','value','unit','definition_ref','basis','evidence_ref'))
            require(text(observation['metric']) and all(nullable(observation[k]) for k in ('value','unit','definition_ref','evidence_ref'))
                    and observation['basis'] in ('measured','estimated','unknown'),'Invalid resource observation')
    canonical(value)


def range_union(ranges):
    groups={};duplicates=False;total=0
    for item in ranges:
        if item['start']==item['stop']:continue
        groups.setdefault(item['space_ref'],[]).append((item['start'],item['stop']))
    for values in groups.values():
        end=None
        for start,stop in sorted(values):
            if end is None or start>=end:total+=stop-start
            else:duplicates=True;total+=max(0,stop-end)
            end=max(end or 0,stop)
    return total,duplicates


def summarize(contract,snapshot):
    conflicts=[];gaps=[];warnings=[];objectives=[]
    bound=snapshot['campaign_ref']==contract['campaign_ref'] and snapshot['scope_ref']==contract['scope_ref'] and text(snapshot['campaign_ref']) and text(snapshot['scope_ref'])
    if not bound:conflicts.append('Snapshot campaign/scope does not bind this contract')
    for key in ('snapshot_ref','evidence_ref','captured_at'):
        if snapshot[key] is None:gaps.append('Missing snapshot '+key)
    if snapshot['complete'] is not True:gaps.append('Cumulative export completeness is unknown/incomplete')
    runs={v['run_ref']:v for v in snapshot['runs']};contexts={}
    missing=set(contract['required_run_refs'])-set(runs)
    if missing:
        (conflicts if snapshot['complete'] is True else gaps).append('Required run records absent: '+', '.join(sorted(missing)))
    objective_ids={v['id'] for v in contract['objectives']}
    for key,run in runs.items():
        same=bound
        for field in ('configuration_ref','model_ref'):
            if run[field] is None:gaps.append(key+': missing '+field);same=False
            elif run[field]!=contract[field]:conflicts.append(key+': foreign '+field);same=False
        if not text(run['native_state']) or not text(run['evidence_ref']):gaps.append(key+': native state/evidence missing');same=False
        if run['state']=='unknown':gaps.append(key+': execution state unknown')
        for resource in run['resources']:
            if resource['basis']!='unknown' and any(not text(resource[k]) for k in ('value','unit','definition_ref','evidence_ref')):
                gaps.append(key+': resource origin/value/unit is incomplete: '+resource['metric'])
        if {v['objective_id'] for v in run['measurements']}-objective_ids:conflicts.append(key+': measurement for absent objective')
        if run['state'] in ('queued','not_run') and any(v['qualified'] is True and v['data'] is not None for v in run['measurements']):
            conflicts.append(key+': nonexecuted state claims qualified executed measurements');same=False
        contexts[key]=same
    for objective in contract['objectives']:
        key=objective['id'];kind=objective['kind'];target=objective['target'];local=[];excluded=[];sources=[];hits=set();ranges=[]
        complete=snapshot['complete'] is True and not missing and bound
        for field in ('description','basis_ref','policy_ref'):
            if not text(objective[field]):local.append('Missing objective '+field);complete=False
        if kind=='manual':
            local.append('Manual objective needs an independently qualified engineering method');complete=False
        if kind in ('coverage','exposure') and not objective['eligible_states']:
            local.append('No eligible execution states defined');complete=False
        if kind=='execution':
            attained=[ref for ref in target['run_refs'] if ref in runs and contexts[ref] and runs[ref]['state']=='passed']
            remaining=[ref for ref in target['run_refs'] if ref not in attained]
            known=len(attained);goal=len(target['run_refs']);attained_target=not remaining
            if not target['run_refs']:local.append('Empty execution target');complete=False;attained_target=None
        elif kind in ('coverage','exposure'):
            for ref,run in runs.items():
                if not contexts[ref]:excluded.append({'run_ref':ref,'reason':'Unknown/foreign run context'});complete=False;continue
                if run['state']=='unknown':complete=False
                if run['state'] not in objective['eligible_states']:
                    excluded.append({'run_ref':ref,'reason':'State excluded by objective policy'});continue
                measurement=next((v for v in run['measurements'] if v['objective_id']==key),None)
                if measurement is None:local.append(ref+': required measurement absent');complete=False;continue
                if measurement['basis_ref']!=objective['basis_ref'] or measurement['qualified'] is not True or measurement['complete'] is not True or not text(measurement['evidence_ref']):
                    local.append(ref+': definition/qualification/completeness is unestablished');complete=False;continue
                data=measurement['data']
                if data is None:local.append(ref+': measured data missing');complete=False;continue
                if kind=='coverage':
                    shape(data,('population_ids','hit_ids'))
                    require(strings(data['population_ids']) and strings(data['hit_ids']),'Invalid named coverage measurement')
                    if set(data['population_ids'])!=set(target['population_ids']) or not set(data['hit_ids'])<=set(data['population_ids']):
                        local.append(ref+': changed/invalid coverage population; do not compare percentages');complete=False;continue
                    hits.update(data['hit_ids'])
                else:
                    shape(data,('unit','ranges'));require(nullable(data['unit']) and isinstance(data['ranges'],list),'Invalid exposure measurement')
                    if data['unit']!=target['unit'] or not text(data['unit']):local.append(ref+': exposure unit differs/unknown');complete=False;continue
                    valid=[]
                    for item in data['ranges']:
                        shape(item,('space_ref','start','stop','evidence_ref'))
                        require(nullable(item['space_ref']) and nullable(item['evidence_ref']) and type(item['start']) is int and type(item['stop']) is int
                                and 0<=item['start']<=item['stop'],'Invalid half-open effective event range')
                        if not text(item['space_ref']) or not text(item['evidence_ref']):local.append(ref+': event identity/source unknown');complete=False
                        else:valid.append(item)
                    ranges.extend(valid)
                sources.append({'run_ref':ref,'evidence_ref':measurement['evidence_ref']})
            if kind=='coverage':
                if not target['population_ids'] or not target['required_ids']:local.append('Empty named coverage population/target');complete=False
                attained=sorted(hits);remaining=sorted(set(target['required_ids'])-hits)
                known=len(hits & set(target['required_ids']));goal=len(target['required_ids'])
            else:
                known,overlap=range_union(ranges);goal=target['value'];remaining=max(0,goal-known);attained=ranges
                if overlap:warnings.append(key+': overlapping event ranges counted once per event space')
                if not text(target['unit']):local.append('Exposure target unit missing');complete=False
            attained_target=True if known>=goal and (kind=='exposure' or goal>0) else False if complete else None
        else:known=None;goal=target;remaining='Manual review required';attained=[];attained_target=None
        if local:gaps.extend(key+': '+v for v in local)
        objectives.append({'id':key,'kind':kind,'basis_ref':objective['basis_ref'],'policy_ref':objective['policy_ref'],
            'known_value':known,'target':goal,'recorded_target_attained':attained_target,'measurement_complete':complete,
            'attained':attained,'remaining':remaining,'sources':sources,'excluded_runs':excluded,'gaps':local})
    required=[{'run_ref':ref,'state':runs[ref]['state'] if ref in runs else 'record_absent','context_bound':contexts.get(ref,False),
        'recorded_pass':ref in runs and contexts[ref] and runs[ref]['state']=='passed'} for ref in contract['required_run_refs']]
    return {'snapshot_ref':snapshot['snapshot_ref'],'captured_at':snapshot['captured_at'],'sha256':fingerprint(snapshot),
        'state_counts':{state:sum(v['state']==state for v in runs.values()) for state in STATES},'required_population':required,
        'remaining_required_run_refs':[v['run_ref'] for v in required if not v['recorded_pass']],
        'objectives':objectives,'context_bound_run_refs':[ref for ref,same in contexts.items() if same],
        'conflicts':conflicts,'missing_context':gaps,'warnings':warnings,'runs':snapshot['runs']}


def review(contract,before,after):
    validate_contract(contract);validate_snapshot(before);validate_snapshot(after)
    conflicts=[];gaps=[]
    for key in ('campaign_ref','scope_ref','configuration_ref','model_ref','population_ref','evidence_ref'):
        if not text(contract[key]):gaps.append('Missing contract '+key)
    if contract['population_complete'] is not True:gaps.append('Independent required population is not declared complete')
    if not contract['required_run_refs']:gaps.append('Required population is empty; applicability needs explicit review')
    if not contract['objectives']:gaps.append('No declared objectives')
    if not text(contract['policy']['ref']) or not text(contract['policy']['evidence_ref']) or not contract['policy']['allowed_recommendations']:
        gaps.append('Recommendation policy is incomplete')
    earlier=timestamp(before['captured_at']);later=timestamp(after['captured_at'])
    if earlier is None or later is None:gaps.append('Review interval timestamps unknown')
    elif later<=earlier:conflicts.append('After snapshot must follow before snapshot')
    if before['snapshot_ref']==after['snapshot_ref']:conflicts.append('Snapshots need distinct identities')
    a=summarize(contract,before);b=summarize(contract,after)
    old={v['run_ref']:v for v in before['runs']};new={v['run_ref']:v for v in after['runs']}
    removed=sorted(set(old)-set(new))
    if removed:gaps.append('Cumulative records disappeared: '+', '.join(removed))
    changed=[]
    for ref in set(old)&set(new):
        if old[ref]['state'] in ('passed','failed','aborted') and fingerprint(old[ref])!=fingerprint(new[ref]):
            changed.append(ref);conflicts.append('Terminal execution changed under the same identity: '+ref)
    deltas=[]
    for previous,current in zip(a['objectives'],b['objectives']):
        comparable=previous['measurement_complete'] and current['measurement_complete'] and earlier is not None and later is not None and later>earlier and not changed and not removed and not conflicts
        numeric=type(previous['known_value']) is int and type(current['known_value']) is int
        delta=current['known_value']-previous['known_value'] if comparable and numeric else None
        if previous['kind']=='coverage':
            gained=sorted(set(current['attained'])-set(previous['attained'])) if comparable else None
            lost=sorted(set(previous['attained'])-set(current['attained'])) if comparable else None
            if lost:conflicts.append('Cumulative qualified coverage goals disappeared: '+previous['id'])
        else:gained=None;lost=None
        if previous['kind']=='exposure' and delta is not None and delta<0:
            conflicts.append('Cumulative qualified exposure decreased: '+previous['id'])
        deltas.append({'id':previous['id'],'kind':previous['kind'],'comparable':comparable,'known_value_delta':delta,
                       'newly_attained_goal_ids':gained,'lost_goal_ids':lost})
    all_conflicts=conflicts+['before: '+v for v in a['conflicts']]+['after: '+v for v in b['conflicts']]
    all_gaps=gaps+['before: '+v for v in a['missing_context']]+['after: '+v for v in b['missing_context']]
    failed=[v['run_ref'] for v in after['runs'] if v['state'] in ('failed','aborted') and v['run_ref'] in b['context_bound_run_refs']]
    status='review_required' if all_conflicts else 'execution_findings' if failed else 'needs_context' if all_gaps else 'recorded_progress'
    attained=all(v['recorded_target_attained'] is True for v in b['objectives']) and bool(b['objectives']) and not b['remaining_required_run_refs'] and not all_conflicts and not all_gaps
    return {'format':'opentools.campaign-progress-review.v1','status':status,'contract_sha256':fingerprint(contract),
        'contract':contract,'before':a,'after':b,'objective_changes':deltas,'removed_run_refs':removed,'changed_terminal_run_refs':sorted(changed),
        'current_failed_or_aborted_run_refs':failed,'conflicts':all_conflicts,'missing_context':all_gaps,
        'all_recorded_targets_attained':attained,'release_completeness':'not_established','recommendation':'AI/engineer must choose one justified recommendation under the declared policy; no action performed.',
        'limits':'Declared scope, named goal sets, qualified integer event-range union and explicit states only. No proof of evidence truth, independent trials, reliability/confidence, coverage-model equivalence, resource totals or stopping authority.'}


def markdown(report):
    def cell(value):return str(value).replace('|','\\|').replace('\n',' ')
    lines=['# Campaign progress review','', 'Status: `'+report['status']+'`. Release completeness: not established.','',
        '| Objective | Earlier known | Current known | Target | Comparable delta |', '|---|---:|---:|---|---:|']
    for a,b,d in zip(report['before']['objectives'],report['after']['objectives'],report['objective_changes']):
        lines.append('| '+' | '.join(cell(v) for v in (b['id'],a['known_value'],b['known_value'],b['target'],d['known_value_delta']))+' |')
    lines+=['','Current required runs without a bound recorded pass: '+', '.join(report['after']['remaining_required_run_refs'])+'.','',
        'Current states: '+', '.join(k+'='+str(v) for k,v in report['after']['state_counts'].items())+'.','',
        '## Evidence gaps and findings','']
    findings=report['conflicts']+report['missing_context']+report['before']['warnings']+report['after']['warnings']
    lines += ['- '+cell(v) for v in findings] or ['No structural gap reported; semantic adequacy still requires review.']
    lines+=['','## Engineering decision','',report['recommendation'],'','Allowed recommendations: '+', '.join(report['contract']['policy']['allowed_recommendations'])+'.','',
        'No elapsed-time/seed-based statistical assurance or automatic termination is inferred. Inspect retained JSON for raw states, measurements, sources and resource observations.','']
    return '\n'.join(lines)


def exit_code(value):return {'recorded_progress':0,'review_required':1,'execution_findings':1,'needs_context':2}[value['status']]
