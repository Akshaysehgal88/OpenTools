"""Review explicit retained-resource waits and conditional blocking observations."""
import hashlib
import json
from pathlib import Path

PREMISES=('closed_resource_census','release_paths_complete','autonomous_updates_absent','external_actions_absent')


def require(condition,message):
    if not condition:raise ValueError(message)


def text(value,label):require(isinstance(value,str) and bool(value.strip()),label+' required')


def boolean(value,label):require(type(value) is bool or value is None,label+' must be boolean or null')


def uint(value,maximum,label,nullable=False):
    require(nullable and value is None or type(value) is int and 0<=value<=maximum,label+' outside unsigned range')


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()


def read_json(path):
    def unique(pairs):
        result={}
        for key,value in pairs:require(key not in result,'Duplicate JSON key: '+key);result[key]=value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique,
                      parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON value')))


def cycles(graph):
    """Bounded SCC search. Components are candidates, not deadlock proofs."""
    counter=0;stack=[];active=set();indices={};low={};result=[]
    def visit(node):
        nonlocal counter
        indices[node]=low[node]=counter;counter+=1;stack.append(node);active.add(node)
        for other in sorted(graph[node]):
            if other not in indices:visit(other);low[node]=min(low[node],low[other])
            elif other in active:low[node]=min(low[node],indices[other])
        if indices[node]==low[node]:
            group=[]
            while True:
                item=stack.pop();active.remove(item);group.append(item)
                if item==node:break
            if len(group)>1 or node in graph[node]:result.append(sorted(group))
    for node in sorted(graph):
        if node not in indices:visit(node)
    return sorted(result)


def review(model,journal,policy):
    for record,kind in ((model,'model'),(journal,'journal'),(policy,'policy')):
        require(isinstance(record,dict) and record.get('format')=='opentools.progress.'+kind+'.v1','Unsupported '+kind+' format')
        require(isinstance(record.get('scope'),dict) and set(record['scope'])=={'project','configuration','mode','episode_ref','traffic_class_ref'},'Exact episode scope required')
        for value in record['scope'].values():text(value,'scope')
        text(record.get('basis_ref'),'basis_ref');require(type(record.get('inputs_complete')) is bool,'Boolean inputs_complete required')
    report={'format':'opentools.progress.report.v1','scope':model['scope'],
        'bindings':{name+'_sha256':digest(value) for name,value in (('model',model),('journal',journal),('policy',policy))},
        'candidate_cycles':[],'observations':[],'blocking_witnesses':[],'findings':[],'gaps':[],
        'limits':['Static SCCs are candidate retained-resource cycles; no reachability, fairness or deadlock proof follows from a graph alone.',
                  'Conditional observed blocking depends on a complete source-reviewed census, release/environment premises and reachable prefix. Hashes do not establish those facts.',
                  'One finite selected episode/class. No general coherence, RTL equivalence, starvation, livelock or unbounded liveness signoff.']}
    def gap(kind,**details):report['gaps'].append(dict(kind=kind,**details))
    def finding(kind,**details):report['findings'].append(dict(kind=kind,**details))
    bound=True
    for record,name in ((journal,'journal'),(policy,'policy')):
        if record['scope']!=model['scope'] or record['basis_ref']!=model['basis_ref'] or record.get('model_sha256')!=digest(model):gap('scope_or_model_binding',record=name);bound=False
    for record in (journal,policy):text(record.get('window_ref'),'window_ref')
    if policy['window_ref']!=journal['window_ref'] or policy.get('journal_sha256')!=digest(journal):gap('journal_or_window_binding');bound=False
    if not bound:report['status']='incomplete';return report
    for record,name in ((model,'model'),(journal,'journal'),(policy,'policy')):
        if not record['inputs_complete']:gap('partial_inputs',record=name)
    require(model.get('semantics')=='finite-retained-resource-episode','Unsupported resource semantics')
    premises=model.get('premises');require(isinstance(premises,dict) and set(premises)==set(PREMISES),'Exact closure/release premises required')
    for key,value in premises.items():
        boolean(value,key)
        if value is None:gap('premise_unknown',premise=key)
        elif value is False and key!='external_actions_absent':gap('closed_model_premise_not_satisfied',premise=key)
    text(model.get('premises_evidence_ref'),'premise evidence')
    require('fair_scheduling' in model,'Explicit fairness premise required');boolean(model['fair_scheduling'],'fair_scheduling')
    report['fair_scheduling_premise']=model['fair_scheduling']
    for key in ('window_closed','observations_complete','reachable_prefix_confirmed'):
        require(key in journal,'Explicit '+key+' required');boolean(journal[key],key)
        if journal[key] is not True:gap(key+'_unqualified')
    if journal.get('reachability_basis_ref') is None:gap('reachability_basis_absent')
    else:text(journal['reachability_basis_ref'],'reachability basis')
    resources={};actors={}
    for key,target in (('resources',resources),('actors',actors)):
        require(isinstance(model.get(key),list) and 0<len(model[key])<=64,'Select 1 to 64 '+key)
        for item in model[key]:
            text(item.get('id'),key+' id');require(item['id'] not in target,'Duplicate '+key);text(item.get('evidence_ref'),'definition evidence')
            if item.get('role_ref') is None:gap('definition_role_unknown',entity=item['id'])
            else:text(item['role_ref'],'role')
            if key=='resources':
                require('capacity' in item,'Explicit capacity required');uint(item['capacity'],4096,'capacity',True)
                require(item['capacity'] is None or item['capacity']>0,'Positive resource capacity required');text(item.get('unit'),'resource unit')
                if item['capacity'] is None:gap('capacity_unknown',resource=item['id'])
            target[item['id']]=item
    for key,definitions in (('required_resources',resources),('required_actors',actors)):
        roster=policy.get(key);require(isinstance(roster,list) and roster,'Independent '+key+' required');seen=set()
        for item in roster:
            text(item.get('id'),'required entity');require(item['id'] not in seen,'Duplicate required entity');seen.add(item['id'])
            text(item.get('role_ref'),'expected role');text(item.get('evidence_ref'),'intent evidence')
            if key=='required_resources':text(item.get('unit'),'expected resource unit')
            if item['id'] not in definitions:gap('required_definition_absent',entity=item['id'])
            elif any(item[k]!=definitions[item['id']].get(k) for k in (('role_ref','unit') if key=='required_resources' else ('role_ref',))):gap('required_definition_mismatch',entity=item['id'])
        for entity in definitions.keys()-seen:gap('definition_not_in_required_roster',entity=entity)
    required_actors={a['id'] for a in policy['required_actors']}
    for key in ('start_seq','end_seq'):uint(policy.get(key),(1<<64)-1,key)
    require(0<=policy['end_seq']-policy['start_seq']<=4096,'Bound observation window to 4097 samples')
    require(type(policy.get('require_completion_at_end')) is bool,'Explicit finite completion obligation required')
    require(isinstance(model.get('waits'),list) and len(model['waits'])<=256,'Explicit wait census required')
    graph={r:set() for r in resources};active_edges=set();wait_ids=set()
    for wait in model['waits']:
        for key in ('id','actor_ref','held_resource_ref','requested_resource_ref','mode_ref','release_condition_ref','evidence_ref'):text(wait.get(key),'wait '+key)
        require(wait['id'] not in wait_ids,'Duplicate wait id');wait_ids.add(wait['id'])
        for key in ('active','retains_until_acquire'):
            require(key in wait,'Explicit wait premise required');boolean(wait[key],key)
            if wait[key] is None:gap('wait_premise_unknown',wait=wait['id'],premise=key)
        actor,held,wanted=wait['actor_ref'],wait['held_resource_ref'],wait['requested_resource_ref']
        if actor not in actors or held not in resources or wanted not in resources:gap('wait_definition_absent',wait=wait['id']);continue
        if wait['active'] is True and wait['retains_until_acquire'] is True:
            graph[held].add(wanted);active_edges.add((actor,held,wanted))
    report['candidate_cycles']=cycles(graph)
    escapes=model.get('external_actions');require(isinstance(escapes,list),'Explicit external action census required');escape_ids=set()
    for escape in escapes:
        text(escape.get('id'),'external action');text(escape.get('evidence_ref'),'external action evidence')
        require(escape['id'] not in escape_ids,'Duplicate external action');escape_ids.add(escape['id'])
        require(isinstance(escape.get('may_release'),list) and escape['may_release'],'External release resources required')
        for resource in escape['may_release']:
            if resource not in resources:gap('external_resource_definition_absent',resource=resource)
    if premises['external_actions_absent'] is True and escapes:gap('external_census_contradicts_absence')
    if premises['external_actions_absent'] is False and not escapes:gap('external_actions_unenumerated')
    samples=journal.get('samples');require(isinstance(samples,list) and samples,'Observed samples required')
    sample_map={};previous_seq=previous_time=-1
    for sample in samples:
        for key in ('seq','time_tick'):uint(sample.get(key),(1<<64)-1,key)
        require(sample['seq']>previous_seq and sample['time_tick']>=previous_time,'Samples must be ordered');previous_seq,previous_time=sample['seq'],sample['time_tick']
        text(sample.get('evidence_ref'),'sample evidence');sample_map[sample['seq']]=sample
        require(isinstance(sample.get('actors'),list),'Observed actor states required');observed={}
        for actor in sample['actors']:
            text(actor.get('actor_ref'),'observed actor');require(actor['actor_ref'] not in observed,'Duplicate observed actor');observed[actor['actor_ref']]=actor
            text(actor.get('state_ref'),'source state');text(actor.get('evidence_ref'),'actor evidence')
            for key in ('pending','complete','release_enabled','advance_enabled'):
                require(key in actor,'Explicit actor flags required');boolean(actor[key],key)
            for key in ('held','requested'):
                require(isinstance(actor.get(key),dict),'Explicit resource counts required')
                for resource,count in actor[key].items():text(resource,'resource ref');uint(count,4096,'resource count',True)
        require(isinstance(sample.get('external_enabled'),dict),'External enable observations required')
        for key,value in sample['external_enabled'].items():text(key,'external ref');boolean(value,'external enable')
    for seq in range(policy['start_seq'],policy['end_seq']+1):
        if seq not in sample_map:gap('required_sample_absent',seq=seq)
    for seq in sample_map:
        if not policy['start_seq']<=seq<=policy['end_seq']:gap('sample_outside_window',seq=seq)
    # Global premises and coverage gate conditional observations, never inferred from an SCC.
    global_qualified=not report['gaps'] and all(premises[k] is True for k in PREMISES)
    report['closed_model_premises_qualified']=global_qualified
    for sample in samples:
        seq=sample['seq'];gap_start=len(report['gaps']);finding_start=len(report['findings'])
        observed={a['actor_ref']:a for a in sample['actors']}
        for entity in required_actors-observed.keys():gap('required_actor_observation_absent',actor=entity,seq=seq)
        for entity in observed.keys()-actors.keys():gap('observed_actor_unmapped',actor=entity,seq=seq)
        for entity in actors.keys()-observed.keys():gap('model_actor_observation_absent',actor=entity,seq=seq)
        available={}
        for resource,definition in resources.items():
            quantities=[]
            for actor in observed.values():
                for field in ('held','requested'):
                    for unknown in actor[field].keys()-resources.keys():gap('observed_resource_unmapped',resource=unknown,seq=seq)
                    if resource not in actor[field] or actor[field][resource] is None:gap('resource_count_unknown',actor=actor['actor_ref'],resource=resource,field=field,seq=seq)
                quantities.append(actor['held'].get(resource))
            capacity=definition['capacity']
            if capacity is None or any(v is None for v in quantities) or set(observed)!=set(actors):available[resource]=None
            else:
                available[resource]=capacity-sum(quantities)
                if available[resource]<0:finding('occupancy_exceeds_capacity',resource=resource,seq=seq)
        runtime_graph={r:set() for r in resources};can_progress={};pending=[];runtime_waits=[]
        for entity,actor in observed.items():
            for key in ('pending','complete','release_enabled','advance_enabled'):
                if actor[key] is None:gap('actor_flag_unknown',actor=entity,field=key,seq=seq)
            if actor['pending'] is True:pending.append(entity)
            if actor['pending'] is True and actor['complete'] is True:finding('actor_pending_and_complete',actor=entity,seq=seq)
            requests=actor['requested'];counts=[requests.get(r) for r in resources]
            known=set(requests)==set(resources) and all(v is not None for v in counts) and all(v is not None for v in available.values())
            wanted=bool(known and any(v>0 for v in counts))
            can_acquire=known and wanted and all(requests[r]<=available[r] for r in resources)
            if actor['release_enabled'] is True:enabled=True
            elif known and actor['release_enabled'] is False:enabled=bool(can_acquire)
            else:enabled=None
            can_progress[entity]=enabled
            if enabled is not None and actor['advance_enabled'] is not None and enabled!=actor['advance_enabled']:finding('advance_enable_mismatch',actor=entity,seq=seq)
            if actor['pending'] is True and known and not wanted and actor['release_enabled'] is False:gap('pending_without_request_or_release',actor=entity,seq=seq)
            if wanted and not can_acquire and actor['release_enabled'] is False:
                blocked_resources=[r for r in resources if requests[r]>available[r]]
                for held,quantity in actor['held'].items():
                    if held not in resources or quantity is None or quantity==0:continue
                    for wanted_resource in blocked_resources:
                        runtime_graph[held].add(wanted_resource);runtime_waits.append([entity,held,wanted_resource])
                        if (entity,held,wanted_resource) not in active_edges:gap('observed_wait_not_in_active_contract',actor=entity,held=held,requested=wanted_resource,seq=seq)
        for key in escape_ids-sample['external_enabled'].keys():gap('external_enable_unknown',action=key,seq=seq)
        for key in sample['external_enabled'].keys()-escape_ids:gap('external_observation_unmapped',action=key,seq=seq)
        for key,value in sample['external_enabled'].items():
            if value is None:gap('external_enable_unknown',action=key,seq=seq)
        runtime_cycles=cycles(runtime_graph)
        no_enabled=bool(pending) and all(v is False for v in can_progress.values()) and set(observed)==set(actors)
        external_enabled=any(v is True for v in sample['external_enabled'].values())
        observation={'seq':seq,'available':available,'pending':sorted(pending),'enabled_progress':can_progress,
                     'external_enabled':external_enabled,'observed_waits':runtime_waits,'candidate_cycles':runtime_cycles,
                     'no_enabled_internal_progress':no_enabled,'conditional_cycle_blocking':False}
        qualified=global_qualified and len(report['gaps'])==gap_start and len(report['findings'])==finding_start
        if no_enabled and runtime_cycles and not external_enabled:
            if qualified:
                observation['conditional_cycle_blocking']=True
                report['blocking_witnesses'].append({'seq':seq,'actors':sorted(pending),'cycles':runtime_cycles,'evidence_ref':sample['evidence_ref'],
                    'qualification':'Observed reachable snapshot under supplied complete closed finite-model premises; native/model applicability still requires source review.'})
            else:gap('blocking_observation_unqualified',seq=seq)
        report['observations'].append(observation)
    if report['blocking_witnesses']:finding('conditional_observed_cycle_blocking',first_seq=report['blocking_witnesses'][0]['seq'])
    if policy['require_completion_at_end']:
        final=sample_map.get(policy['end_seq'])
        if final is not None:
            states={a['actor_ref']:a for a in final['actors']}
            for entity in required_actors:
                if entity in states:
                    if states[entity]['complete'] is False:finding('completion_not_seen_by_window_end',actor=entity,seq=policy['end_seq'])
                    elif states[entity]['complete'] is None:gap('completion_outcome_unknown',actor=entity)
    report['status']='review_required' if report['findings'] or report['candidate_cycles'] else 'incomplete' if report['gaps'] else 'within_observed_contract'
    return report


def exit_code(report):return {'within_observed_contract':0,'review_required':1,'incomplete':2}[report['status']]
