"""Review one explicit scalar producer-to-consumer visibility and ownership handoff."""
import hashlib
import json
from pathlib import Path


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


def review(inventory,journal,policy):
    for record,kind in ((inventory,'inventory'),(journal,'journal'),(policy,'policy')):
        require(isinstance(record,dict) and record.get('format')=='opentools.handoff.'+kind+'.v1','Unsupported '+kind+' format')
        require(isinstance(record.get('scope'),dict) and set(record['scope'])=={'project','configuration','mode','handoff_ref'},'Exact handoff scope required')
        for value in record['scope'].values():text(value,'scope')
        text(record.get('basis_ref'),'basis_ref');require(type(record.get('inputs_complete')) is bool,'Boolean inputs_complete required')
    report={'format':'opentools.handoff.report.v1','scope':inventory['scope'],
        'bindings':{key+'_sha256':digest(value) for key,value in (('inventory',inventory),('journal',journal),('policy',policy))},
        'findings':[],'gaps':[],'publications':[],'reads':[],'ownership':[],
        'limits':['One selected scalar producer-to-consumer handoff, reviewed mappings and complete ordered events. Source meanings and coverage require review.',
                  'Coherent control is separate from payload visibility. No universal maintenance recipe, ISA/compiler ordering, IOMMU, cache-line sharing or full coherence qualification.']}
    def gap(kind,**details):report['gaps'].append(dict(kind=kind,**details))
    def finding(kind,**details):report['findings'].append(dict(kind=kind,**details))
    bound=True
    for record,name in ((journal,'journal'),(policy,'policy')):
        if record['scope']!=inventory['scope'] or record['basis_ref']!=inventory['basis_ref'] or record.get('inventory_sha256')!=digest(inventory):gap('scope_or_inventory_binding',record=name);bound=False
    for record in (journal,policy):text(record.get('window_ref'),'window_ref')
    if journal['window_ref']!=policy['window_ref'] or policy.get('journal_sha256')!=digest(journal):gap('journal_or_window_binding');bound=False
    if not bound:report['status']='incomplete';return report
    for record,name in ((inventory,'inventory'),(journal,'journal'),(policy,'policy')):
        if not record['inputs_complete']:gap('partial_inputs',record=name)
    for key in ('epoch_isolated','window_closed','events_complete'):
        require(key in journal,'Explicit '+key+' required');boolean(journal[key],key)
        if journal[key] is not True:gap(key+'_unqualified')
    for key in ('mapping_epoch_ref','producer_ref','consumer_ref','maintenance_agent_ref','platform_contract_ref'):text(inventory.get(key),key)
    require(len({inventory[k] for k in ('producer_ref','consumer_ref','maintenance_agent_ref')})==3,'Separate producer, consumer and maintenance roles required')
    for key in ('payload_ref','control_ref','payload_mapping_ref','control_mapping_ref','producer_ref','consumer_ref','maintenance_agent_ref','mapping_epoch_ref','ordering_contract_ref','completion_contract_ref','expected_write_ref','publish_ref','read_ref','completion_ref','reclaim_ref'):text(policy.get(key),key)
    for key in ('producer_ref','consumer_ref','maintenance_agent_ref','mapping_epoch_ref'):
        if policy[key]!=inventory[key]:gap('required_contract_definition_mismatch',field=key)
    require(type(policy.get('require_release_order')) is bool,'Explicit ordering obligation required')
    for key in ('expected_version','expected_value'):
        require(key in policy,'Explicit expected '+key+' required');uint(policy[key],(1<<4096)-1 if key=='expected_value' else (1<<64)-1,key,True)
        if policy[key] is None:gap('expected_payload_unknown',field=key)
    objects={};mappings={}
    require(isinstance(inventory.get('objects'),list) and 0<len(inventory['objects'])<=256,'Select 1 to 256 objects')
    for obj in inventory['objects']:
        for key in ('id','role_ref','evidence_ref'):text(obj.get(key),'object '+key)
        require(obj['id'] not in objects,'Duplicate object');uint(obj.get('width_bits'),4096,'object width')
        require(obj['width_bits']>0 and obj['width_bits']%8==0,'Byte-sized scalar required')
        uint(obj.get('physical_address'),(1<<64)-1,'physical address');uint(obj.get('line_bytes'),4096,'cache line bytes')
        require(obj['line_bytes']>0 and obj['line_bytes']&(obj['line_bytes']-1)==0 and obj['width_bits']//8<=obj['line_bytes'],'Whole scalar cache line required')
        require(obj['physical_address']%obj['line_bytes']==0 and obj['physical_address']+obj['width_bits']//8<=1<<64,'Invalid physical object range')
        objects[obj['id']]=obj
    ranges=sorted((obj['physical_address'],obj['physical_address']+obj['width_bits']//8,obj['id']) for obj in objects.values())
    for previous,current in zip(ranges,ranges[1:]):
        if current[0]<previous[1]:gap('overlapping_physical_object_definitions',objects=[previous[2],current[2]])
    require(isinstance(inventory.get('mappings'),list) and inventory['mappings'],'Explicit mappings required')
    for mapping in inventory['mappings']:
        for key in ('id','agent_ref','object_ref','mapping_epoch_ref','evidence_ref'):text(mapping.get(key),'mapping '+key)
        require(mapping['id'] not in mappings,'Duplicate mapping');uint(mapping.get('address'),(1<<64)-1,'mapped address')
        require('coherent' in mapping,'Explicit coherence required');boolean(mapping['coherent'],'mapping coherence')
        require(mapping.get('cacheability') in ('write-back','uncached','unknown'),'Explicit cacheability required')
        for key in ('shareability_ref','path_ref'):
            if mapping.get(key) is None:gap('mapping_definition_unknown',mapping=mapping['id'],field=key)
            else:text(mapping[key],key)
        if mapping['coherent'] is None or mapping['cacheability']=='unknown':gap('mapping_attributes_unknown',mapping=mapping['id'])
        if mapping['mapping_epoch_ref']!=policy['mapping_epoch_ref']:gap('mapping_epoch_mismatch',mapping=mapping['id'])
        if mapping['object_ref'] not in objects:gap('mapping_object_absent',mapping=mapping['id'])
        mappings[mapping['id']]=mapping
    for key,definitions,fields in (('required_objects',objects,('role_ref','width_bits')),('required_mappings',mappings,('agent_ref','object_ref','mapping_epoch_ref','coherent','path_ref'))):
        roster=policy.get(key);require(isinstance(roster,list) and roster,'Independent '+key+' required');seen=set()
        for item in roster:
            text(item.get('id'),'required identity');require(item['id'] not in seen,'Duplicate required identity');seen.add(item['id']);text(item.get('evidence_ref'),'requirement evidence')
            require(all(field in item for field in fields),'Expected definition fields required')
            if key=='required_objects':
                text(item['role_ref'],'expected object role');uint(item['width_bits'],4096,'expected width');require(item['width_bits']>0 and item['width_bits']%8==0,'Expected byte-sized width required')
            else:
                for field in ('agent_ref','object_ref','mapping_epoch_ref'):text(item[field],'expected mapping '+field)
                boolean(item['coherent'],'expected coherence')
                if item['path_ref'] is not None:text(item['path_ref'],'expected path')
            if item['id'] not in definitions:gap('required_definition_absent',entity=item['id'])
            elif any(definitions[item['id']][field]!=item[field] for field in fields):gap('required_definition_mismatch',entity=item['id'])
        for entity in definitions.keys()-seen:gap('selected_definition_unreviewed',entity=entity)
    for key in ('payload_ref','control_ref'):
        if policy[key] not in objects:gap('handoff_object_absent',role=key)
    payload_mapping=mappings.get(policy['payload_mapping_ref']);control_mapping=mappings.get(policy['control_mapping_ref'])
    for mapping,role,obj in ((payload_mapping,'payload',policy['payload_ref']),(control_mapping,'control',policy['control_ref'])):
        if mapping is None:gap('consumer_mapping_absent',role=role)
        elif mapping['object_ref']!=obj or mapping['agent_ref']!=policy['consumer_ref']:gap('consumer_mapping_identity_mismatch',role=role)
    if policy['payload_ref'] in objects and policy['expected_value'] is not None:uint(policy['expected_value'],(1<<objects[policy['payload_ref']]['width_bits'])-1,'expected payload')
    owner=journal.get('initial_owner_ref')
    if owner is None:gap('initial_ownership_unknown')
    else:text(owner,'initial owner')
    if owner is not None and owner!=policy['producer_ref']:finding('initial_owner_not_producer')
    events=journal.get('events');require(isinstance(events,list) and events,'Ordered handoff events required')
    event_map={};previous_seq=previous_time=-1
    for event in events:
        for key in ('event_ref','actor_ref','object_ref','evidence_ref'):text(event.get(key),'event '+key)
        require(event['event_ref'] not in event_map,'Duplicate event ref');event_map[event['event_ref']]=event
        for key in ('seq','time_tick'):uint(event.get(key),(1<<64)-1,key)
        require(event['seq']>previous_seq and event['time_tick']>=previous_time,'Events must be ordered');previous_seq,previous_time=event['seq'],event['time_tick']
        require(event.get('kind') in ('initial','write','clean_request','clean_complete','release_order','publish','read','complete','reclaim'),'Unsupported handoff event')
        for key in ('accepted','effect_observed','control_seen'):
            require(key in event,'Explicit '+key+' required');boolean(event[key],key)
        for key in ('value','version','address'):
            require(key in event,'Explicit '+key+' required');uint(event[key],(1<<4096)-1 if key=='value' else (1<<64)-1,key,True)
        if event['object_ref'] in objects and event['value'] is not None:uint(event['value'],(1<<objects[event['object_ref']]['width_bits'])-1,'event scalar value')
        require('mapping_ref' in event,'Explicit mapping_ref required')
        if event['mapping_ref'] is not None:text(event['mapping_ref'],'mapping ref')
        require('owner_after_ref' in event,'Explicit observed owner required')
        if event['owner_after_ref'] is not None:text(event['owner_after_ref'],'observed owner')
    for key in ('start_seq','end_seq'):uint(policy.get(key),(1<<64)-1,key)
    require(0<=policy['end_seq']-policy['start_seq']<=4096,'Bound handoff observation window')
    observed_sequences={e['seq'] for e in events}
    for seq in range(policy['start_seq'],policy['end_seq']+1):
        if seq not in observed_sequences:gap('required_event_sample_absent',seq=seq)
    if any(not policy['start_seq']<=s<=policy['end_seq'] for s in observed_sequences):gap('event_outside_window')
    for key,kind in (('expected_write_ref','write'),('publish_ref','publish'),('read_ref','read'),('completion_ref','complete'),('reclaim_ref','reclaim')):
        event=event_map.get(policy[key])
        if event is None or event['kind']!=kind:gap('required_milestone_absent',milestone=key)
        elif event['accepted'] is False or event['effect_observed'] is False:finding('required_milestone_not_observed',event_ref=event['event_ref'])
        elif event['accepted'] is None or event['effect_observed'] is None:gap('milestone_observation_unknown',event_ref=event['event_ref'])
    requests={};cleaned={};unknown_cleaned=set();ordered_version=None;ordered_seen=False;expected_written=False;published=False;read_seen=False;completed=False;qualified_completion=False;versions={}
    mapping_qualified=payload_mapping is not None and payload_mapping['object_ref']==policy['payload_ref'] and payload_mapping['agent_ref']==policy['consumer_ref'] and payload_mapping['mapping_epoch_ref']==policy['mapping_epoch_ref'] and payload_mapping['shareability_ref'] is not None and payload_mapping['path_ref'] is not None and payload_mapping['cacheability']!='unknown'
    coherent_payload=payload_mapping['coherent'] if mapping_qualified else None
    for event in events:
        ref,kind,obj=event['event_ref'],event['kind'],event['object_ref']
        def issue(name,**details):finding(name,event_ref=ref,**details)
        def missing(name,**details):gap(name,event_ref=ref,**details)
        if obj not in objects:missing('event_object_absent',object_ref=obj)
        mapping=None
        if event['mapping_ref'] is not None:
            mapping=mappings.get(event['mapping_ref'])
            if mapping is None:missing('event_mapping_absent')
            elif mapping['object_ref']!=obj or mapping['address']!=event['address']:issue('event_mapping_identity_mismatch')
            elif kind!='clean_complete' and mapping['agent_ref']!=event['actor_ref']:issue('mapping_actor_mismatch')
        elif kind in ('write','clean_request','clean_complete','publish','read'):missing('addressed_event_mapping_absent')
        for key in ('accepted','effect_observed'):
            if event[key] is None:missing('event_effect_unknown',field=key)
        if event['accepted'] is True and event['effect_observed'] is True:
            if kind in ('write','clean_request','release_order','publish','reclaim') and event['actor_ref']!=policy['producer_ref']:issue('producer_action_owner_mismatch')
            if kind in ('read','complete') and event['actor_ref']!=policy['consumer_ref']:issue('consumer_action_owner_mismatch')
            if kind=='clean_complete' and event['actor_ref']!=policy['maintenance_agent_ref']:issue('maintenance_agent_mismatch')
            if kind=='write':
                if owner is None:missing('producer_write_ownership_unknown')
                elif owner!=policy['producer_ref']:issue('producer_write_while_consumer_owned')
                if event['value'] is None or event['version'] is None:missing('producer_write_value_or_version_unknown')
                if obj in versions and event['version'] is not None and event['version']<=versions[obj]:issue('producer_version_not_advanced')
                if event['version'] is not None:versions[obj]=event['version']
                if ref==policy['expected_write_ref']:
                    expected_written=True
                    if obj!=policy['payload_ref']:issue('expected_write_object_mismatch')
                    for key,expected in (('value',policy['expected_value']),('version',policy['expected_version'])):
                        if event[key] is not None and expected is not None and event[key]!=expected:issue('producer_write_intent_mismatch',field=key,expected=expected,observed=event[key])
            elif kind=='clean_request':
                if owner!=policy['producer_ref']:issue('maintenance_issued_without_producer_ownership') if owner is not None else missing('maintenance_ownership_unknown')
                if event['value'] is None or event['version'] is None:missing('maintenance_capture_unknown')
                requests[ref]=event
            elif kind=='clean_complete':
                request=requests.get(event.get('request_ref'))
                if request is None:missing('maintenance_request_absent');unknown_cleaned.add(obj)
                elif [event[k] for k in ('object_ref','mapping_ref','version','value')]!=[request[k] for k in ('object_ref','mapping_ref','version','value')]:issue('maintenance_completion_capture_mismatch')
                elif event['version'] is not None and event['value'] is not None:cleaned[obj]=(event['version'],event['value'])
                else:unknown_cleaned.add(obj);missing('maintenance_completed_image_unknown')
            elif kind=='release_order':
                if obj!=policy['payload_ref']:issue('release_order_object_mismatch')
                ordered_version=event['version'];ordered_seen=True
                if ordered_version is None:missing('release_order_version_unknown')
            elif kind=='publish':
                if published:missing('multiple_publications_outside_selected_handoff')
                if obj!=policy['control_ref']:issue('publication_control_identity_mismatch')
                if owner is not None and owner!=policy['producer_ref']:issue('publication_without_producer_ownership')
                if expected_written is False:issue('publication_before_expected_write')
                elif expected_written is None:missing('expected_write_observation_unknown')
                if policy['require_release_order']:
                    if not ordered_seen:issue('publication_without_required_release_order')
                    elif ordered_version is None or policy['expected_version'] is None:missing('publication_order_version_unknown')
                    elif ordered_version!=policy['expected_version']:issue('publication_without_required_release_order')
                if coherent_payload is None:missing('payload_coherency_path_unknown')
                elif coherent_payload is False:
                    if policy['expected_value'] is None or policy['expected_version'] is None or policy['payload_ref'] in unknown_cleaned:missing('publication_maintenance_image_unknown')
                    elif cleaned.get(policy['payload_ref'])!=(policy['expected_version'],policy['expected_value']):issue('publication_before_payload_maintenance_complete')
                published=True;owner=policy['consumer_ref']
                report['publications'].append({'event_ref':ref,'payload_coherent':coherent_payload,'ordered_version':ordered_version,'completed_payload_image':cleaned.get(policy['payload_ref'])})
            elif kind=='read':
                if published is False:issue('consumer_read_before_publication')
                elif published is None:missing('publication_observation_unknown')
                if owner is None:missing('consumer_read_ownership_unknown')
                elif owner!=policy['consumer_ref']:issue('consumer_read_without_consumer_ownership')
                if ref==policy['read_ref']:
                    if obj!=policy['payload_ref'] or event['mapping_ref']!=policy['payload_mapping_ref']:issue('consumer_payload_identity_mismatch')
                    for key,expected in (('value',policy['expected_value']),('version',policy['expected_version'])):
                        if event[key] is None:missing('consumer_payload_observation_unknown',field=key)
                        elif expected is not None and event[key]!=expected:issue('consumer_payload_mismatch',field=key,expected=expected,observed=event[key])
                    if event['control_seen'] is False:issue('consumer_control_not_observed')
                    elif event['control_seen'] is None:missing('consumer_control_observation_unknown')
                    if event.get('control_mapping_ref')!=policy['control_mapping_ref']:missing('consumer_control_mapping_unqualified')
                    read_seen=True
                report['reads'].append({'event_ref':ref,'object_ref':obj,'mapping_ref':event['mapping_ref'],'value':event['value'],'version':event['version'],'control_seen':event['control_seen']})
            elif kind=='complete':
                if read_seen is False:issue('completion_before_required_consumption')
                elif read_seen is None:missing('completion_consumption_observation_unknown')
                if owner is not None and owner!=policy['consumer_ref']:issue('completion_without_consumer_ownership')
                completed=True;qualified_completion=read_seen
            elif kind=='reclaim':
                if completed is None or qualified_completion is None:missing('reclaim_completion_observation_unknown')
                elif not completed or not qualified_completion:issue('reclaim_without_qualified_completion')
                owner=policy['producer_ref']
        elif event['accepted'] is None or event['effect_observed'] is None:
            if ref==policy['expected_write_ref']:expected_written=None
            if kind=='publish':published=None;owner=None
            elif kind=='reclaim':owner=None
            elif kind=='release_order':ordered_seen=True;ordered_version=None
            elif kind=='clean_complete':unknown_cleaned.add(obj)
            elif kind=='read' and ref==policy['read_ref']:read_seen=None
            elif kind=='complete':completed=None;qualified_completion=None
        if event['owner_after_ref'] is None:missing('observed_ownership_unknown')
        elif owner is not None and event['owner_after_ref']!=owner:issue('ownership_history_mismatch',expected=owner,observed=event['owner_after_ref'])
        report['ownership'].append({'event_ref':ref,'owner_ref':owner})
    report['status']='review_required' if report['findings'] else 'incomplete' if report['gaps'] else 'within_observed_contract'
    return report


def exit_code(report):return {'within_observed_contract':0,'review_required':1,'incomplete':2}[report['status']]
