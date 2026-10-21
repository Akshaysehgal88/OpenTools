"""Source/epoch-qualified obligations for one accepted exclusive-handoff frontier."""
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


def review(model,journal,policy):
    for record,kind in ((model,'model'),(journal,'journal'),(policy,'policy')):
        require(isinstance(record,dict) and record.get('format')=='opentools.transition.'+kind+'.v1','Unsupported '+kind+' format')
        require(isinstance(record.get('scope'),dict) and set(record['scope'])=={'project','configuration','mode','protocol_ref','transaction_ref','epoch_ref'},'Exact transaction scope required')
        for value in record['scope'].values():text(value,'scope')
        text(record.get('basis_ref'),'basis_ref');require(type(record.get('inputs_complete')) is bool,'Boolean inputs_complete required')
    report={'format':'opentools.transition.report.v1','scope':model['scope'],
        'bindings':{key+'_sha256':digest(value) for key,value in (('model',model),('journal',journal),('policy',policy))},
        'findings':[],'gaps':[],'grants':[],'reads':[],'ignored_messages':[],'duplicate_receipts':[],'ledger':[],
        'limits':['One source-reviewed exclusive-handoff contract and transaction epoch; token acceptance, rights and acknowledgement classes must have the declared meanings.',
                  'Stable-state labels and counts are observations, not completion authority. No arbitrary coherence/ring protocol, retry/cancel/reset overlap or unbounded liveness proof.']}
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
    require(model.get('semantics')=='accepted-exclusive-handoff','Unsupported transition semantics')
    for key in ('epoch_isolated','window_closed','events_complete'):
        require(key in journal,'Explicit '+key+' required');boolean(journal[key],key)
        if journal[key] is not True:gap(key+'_unqualified')
    for key in ('resource_ref','grantor_ref','requestor_ref','request_class_ref','grant_class_ref','completion_class_ref','protocol_contract_ref'):
        text(model.get(key),key);text(policy.get(key),'required '+key)
        if model[key]!=policy[key]:gap('required_contract_definition_mismatch',field=key)
    for key in ('transaction_id','epoch'):
        uint(model.get(key),(1<<64)-1,key);uint(policy.get(key),(1<<64)-1,'required '+key)
        if model[key]!=policy[key]:gap('required_transaction_identity_mismatch',field=key)
    require(type(policy.get('check_returned_data')) is bool,'Explicit returned-data obligation required')
    require('expected_data' in policy,'Explicit expected_data required');uint(policy['expected_data'],(1<<4096)-1,'expected_data',True)
    if policy['check_returned_data'] and policy['expected_data'] is None:gap('expected_data_unknown')
    participants={}
    require(isinstance(model.get('participants'),list) and 0<len(model['participants'])<=64,'Select 1 to 64 participants')
    for participant in model['participants']:
        for key in ('id','role_ref','evidence_ref'):text(participant.get(key),'participant '+key)
        require(participant['id'] not in participants,'Duplicate participant');participants[participant['id']]=participant
    roster=policy.get('required_participants');require(isinstance(roster,list) and roster,'Independent participant roster required');seen=set()
    for item in roster:
        for key in ('id','role_ref','evidence_ref'):text(item.get(key),'required participant '+key)
        require(item['id'] not in seen,'Duplicate required participant');seen.add(item['id'])
        if item['id'] not in participants:gap('required_participant_absent',participant=item['id'])
        elif item['role_ref']!=participants[item['id']]['role_ref']:gap('participant_role_mismatch',participant=item['id'])
    for entity in participants.keys()-seen:gap('participant_not_in_required_roster',participant=entity)
    obligations={}
    for key,target in (('obligations',{}),('required_obligations',obligations)):
        record=model if key=='obligations' else policy
        require(isinstance(record.get(key),list) and 0<len(record[key])<=64,'Explicit 1 to 64 '+key+' required')
        for item in record[key]:
            for field in ('id','source_ref','message_class_ref','evidence_ref'):text(item.get(field),field)
            require(item['id'] not in target and item.get('kind') in ('release','data'),'Unique typed obligation required');target[item['id']]=item
            if item['source_ref'] not in participants:gap('obligation_source_absent',obligation=item['id'])
        if key=='obligations':declared=target
    for identity,item in obligations.items():
        if identity not in declared:gap('required_obligation_absent',obligation=identity)
        elif any(item[k]!=declared[identity][k] for k in ('source_ref','message_class_ref','kind')):gap('obligation_definition_mismatch',obligation=identity)
    for identity in declared.keys()-obligations.keys():gap('declared_obligation_unreviewed',obligation=identity)
    signatures=[(o['kind'],o['source_ref'],o['message_class_ref']) for o in obligations.values()]
    require(len(signatures)==len(set(signatures)),'Receipt must identify one obligation, not multiple identical entries')
    for key,record in (('initial_holders',model),('required_initial_holders',policy)):
        require(isinstance(record.get(key),list) and record[key] and len(set(record[key]))==len(record[key]),'Unique initial holder census required')
        for entity in record[key]:text(entity,'holder');require(entity!=policy['requestor_ref'],'Requestor must not hold old claim in this profile')
    holders=set(policy['required_initial_holders'])
    if set(model['initial_holders'])!=holders:gap('initial_holder_census_mismatch')
    release_sources={o['source_ref'] for o in obligations.values() if o['kind']=='release'}
    if release_sources!=holders:gap('holder_release_obligations_incomplete')
    initial=journal.get('initial_holders');require(isinstance(initial,dict),'Initial permission observations required')
    if set(initial)!=holders:gap('initial_holder_observations_incomplete')
    for entity,value in initial.items():
        boolean(value,'initial holder permission')
        if value is None:gap('initial_permission_unknown',participant=entity)
        elif entity in holders and not value:finding('required_initial_holder_not_observed',participant=entity)
    events=journal.get('events');require(isinstance(events,list) and events,'Ordered transition events required')
    event_map={};previous_seq=previous_time=-1
    for event in events:
        for key in ('event_ref','source_ref','message_class_ref','resource_ref','state_label','evidence_ref'):text(event.get(key),'event '+key)
        require(event['event_ref'] not in event_map,'Duplicate event ref');event_map[event['event_ref']]=event
        for key in ('seq','time_tick'):uint(event.get(key),(1<<64)-1,key)
        require(event['seq']>previous_seq and event['time_tick']>=previous_time,'Events must be ordered');previous_seq,previous_time=event['seq'],event['time_tick']
        require(event.get('kind') in ('initial','idle','request','data','release','grant','new_read','new_write','old_read','finish'),'Unsupported transition event')
        for key in ('accepted','offered','requestor_permission','data_valid','active','read_valid','write_committed'):
            require(key in event,'Explicit '+key+' required');boolean(event[key],key)
        for key in ('message_id','message_epoch','reported_pending_count','data_value','read_value'):
            require(key in event,'Explicit '+key+' required');uint(event[key],(1<<4096)-1 if key in ('data_value','read_value') else (1<<64)-1,key,True)
        for key in ('holders','reported_pending'):
            require(isinstance(event.get(key),dict),'Explicit '+key+' required')
            for entity,value in event[key].items():text(entity,'observed participant');boolean(value,key)
    for key in ('start_seq','end_seq'):uint(policy.get(key),(1<<64)-1,key)
    require(0<=policy['end_seq']-policy['start_seq']<=4096,'Bound transition window')
    sequences={e['seq'] for e in events}
    for seq in range(policy['start_seq'],policy['end_seq']+1):
        if seq not in sequences:gap('required_sample_absent',seq=seq)
    if any(not policy['start_seq']<=s<=policy['end_seq'] for s in sequences):gap('event_outside_window')
    required=policy.get('required_events');require(isinstance(required,list) and required,'Independent milestone roster required');required_ids=set()
    for item in required:
        text(item.get('event_ref'),'required event');require(item['event_ref'] not in required_ids,'Duplicate required event');required_ids.add(item['event_ref'])
        require(item.get('kind') in ('request','grant','new_read','new_write','finish'),'Supported required milestone kind required')
        text(item.get('evidence_ref'),'milestone evidence');event=event_map.get(item['event_ref'])
        if event is None or event['kind']!=item['kind']:gap('required_milestone_absent',event_ref=item['event_ref'])
        elif event['accepted'] is False:finding('required_milestone_not_accepted',event_ref=item['event_ref'])
        elif event['accepted'] is None:gap('milestone_acceptance_unknown',event_ref=item['event_ref'])
    coverage_qualified=all(r['inputs_complete'] for r in (model,journal,policy)) and all(journal[k] is True for k in ('epoch_isolated','window_closed','events_complete')) and sequences==set(range(policy['start_seq'],policy['end_seq']+1))
    pending=set() if coverage_qualified else set(obligations);uncertain=set(pending);started=False if coverage_qualified else None;granted=False;finished=False
    for event in events:
        ref,kind=event['event_ref'],event['kind']
        def issue(name,**details):finding(name,event_ref=ref,**details)
        def missing(name,**details):gap(name,event_ref=ref,**details)
        if event['source_ref'] not in participants:missing('event_source_unmapped')
        identity_known=event['message_id'] is not None and event['message_epoch'] is not None
        matches=identity_known and event['message_id']==policy['transaction_id'] and event['message_epoch']==policy['epoch'] and event['resource_ref']==policy['resource_ref']
        for field in ('accepted','offered','requestor_permission','data_valid','active','read_valid','write_committed'):
            if event[field] is None:missing('event_flag_unknown',field=field)
        if set(event['holders'])!=holders:missing('holder_observation_incomplete')
        if set(event['reported_pending'])!=holders:missing('pending_source_observations_incomplete')
        for entity in holders:
            if event['holders'].get(entity) is None:missing('holder_permission_unknown',participant=entity)
            if event['reported_pending'].get(entity) is None:missing('pending_source_unknown',participant=entity)
        if event['accepted'] is True:
            if kind in ('request','data','release','grant','finish') and not identity_known:
                missing('message_identity_unknown')
                if kind=='request':started=None;pending=set(obligations);uncertain=set(obligations)
                elif kind=='grant':granted=None
                elif kind=='finish':finished=None
                else:uncertain.update(key for key,o in obligations.items() if o['kind']==kind and o['source_ref']==event['source_ref'] and o['message_class_ref']==event['message_class_ref'])
            elif kind in ('request','data','release','grant','finish') and not matches:
                report['ignored_messages'].append({'event_ref':ref,'kind':kind,'reason':'foreign_transaction_epoch_or_resource'})
            elif kind=='request':
                if started:missing('multiple_transactions_outside_selected_epoch')
                if event['source_ref']!=policy['requestor_ref'] or event['message_class_ref']!=policy['request_class_ref']:issue('request_definition_mismatch')
                started=True;pending=set(obligations);uncertain=set() if coverage_qualified else set(obligations)
            elif kind in ('data','release'):
                if started is False or finished is True:issue('receipt_outside_active_transfer')
                elif started is None or finished is None:missing('receipt_transfer_phase_unknown')
                candidates=[key for key,o in obligations.items() if o['kind']==kind and o['source_ref']==event['source_ref'] and o['message_class_ref']==event['message_class_ref']]
                if not candidates:
                    if kind=='release':missing('receipt_obligation_unmapped')
                else:
                    obligation=candidates[0];admitted=True
                    if kind=='release':
                        observed=event['holders'].get(event['source_ref'])
                        if observed is True:issue('release_ack_without_permission_release');admitted=False
                        elif observed is None:missing('release_permission_unknown');admitted=False;uncertain.add(obligation)
                    else:
                        if event['data_valid'] is False:issue('data_receipt_without_availability');admitted=False
                        elif event['data_valid'] is None:missing('returned_data_availability_unknown');admitted=False;uncertain.add(obligation)
                        if policy['check_returned_data']:
                            if event['data_value'] is None:missing('returned_data_unknown')
                            elif policy['expected_data'] is not None and event['data_value']!=policy['expected_data']:issue('returned_data_mismatch',expected=policy['expected_data'],observed=event['data_value'])
                    if admitted and started and not finished:
                        if obligation in pending:pending.remove(obligation);uncertain.discard(obligation)
                        else:report['duplicate_receipts'].append({'event_ref':ref,'obligation':obligation})
            elif kind=='grant':
                if event['source_ref']!=policy['grantor_ref'] or event['message_class_ref']!=policy['grant_class_ref']:issue('grant_definition_mismatch')
                if started is False:issue('grant_without_request')
                elif started is None:missing('grant_request_observation_unknown')
                if granted is True:issue('multiple_accepted_grants')
                if pending-uncertain:issue('grant_with_pending_obligations',pending=sorted(pending-uncertain))
                if pending&uncertain:missing('grant_obligations_unknown',obligations=sorted(pending&uncertain))
                if event['offered'] is False:issue('grant_accepted_without_offer')
                elif event['offered'] is None:missing('grant_offer_unknown')
                granted=True;report['grants'].append({'event_ref':ref,'pending':sorted(pending),'unknown':sorted(pending&uncertain),'state_label':event['state_label']})
            elif kind=='finish':
                if event['source_ref']!=policy['requestor_ref'] or event['message_class_ref']!=policy['completion_class_ref']:issue('completion_definition_mismatch')
                if granted is False:issue('finish_without_accepted_grant')
                elif granted is None:missing('finish_grant_observation_unknown')
                if pending-uncertain:issue('finish_with_pending_obligations',pending=sorted(pending-uncertain))
                if pending&uncertain:missing('finish_obligations_unknown',obligations=sorted(pending&uncertain))
                finished=True
        elif event['accepted'] is None:
            if kind=='request':started=None;pending=set(obligations);uncertain=set(obligations)
            elif kind=='grant':granted=None
            elif kind=='finish':finished=None
            elif kind in ('release','data'):
                uncertain.update(key for key,o in obligations.items() if o['kind']==kind and o['source_ref']==event['source_ref'] and o['message_class_ref']==event['message_class_ref'])
        elif event['accepted'] is False and kind in ('data','release') and identity_known and not matches:
            report['ignored_messages'].append({'event_ref':ref,'kind':kind,'reason':'foreign_transaction_epoch_or_resource'})
        if event['requestor_permission'] is True:
            if granted is False:issue('permission_without_accepted_grant')
            elif granted is None:missing('permission_grant_frontier_unknown')
            overlapping=sorted(entity for entity,value in event['holders'].items() if value is True)
            if overlapping:issue('exclusive_permission_overlaps_old_holders',holders=overlapping)
        release_pending={obligations[key]['source_ref'] for key in pending if obligations[key]['kind']=='release'}
        uncertain_sources={obligations[key]['source_ref'] for key in pending&uncertain if obligations[key]['kind']=='release'}
        if started is True:
            for entity,value in event['reported_pending'].items():
                if entity in holders and entity not in uncertain_sources and value is not None and value!=(entity in release_pending):issue('reported_pending_source_mismatch',participant=entity)
            count=event['reported_pending_count']
            if count is None:missing('reported_pending_count_unknown')
            elif uncertain_sources:missing('pending_count_comparison_unqualified')
            elif count!=len(release_pending):issue('reported_pending_count_mismatch',expected=len(release_pending),observed=count)
        if kind in ('new_read','new_write'):
            if event['source_ref']!=policy['requestor_ref']:issue('consumer_source_mismatch')
            if not identity_known:missing('consumer_transaction_identity_unknown')
            elif not matches:issue('consumer_transaction_identity_mismatch')
            consumed=event['read_valid'] if kind=='new_read' else event['write_committed']
            if consumed is True and (granted is False or event['requestor_permission'] is False):issue('consumer_use_without_accepted_permission')
            elif consumed is True and granted is None:missing('consumer_permission_frontier_unknown')
            if kind=='new_read' and consumed is True and policy['check_returned_data']:
                if event['read_value'] is None:missing('consumer_read_data_unknown')
                elif policy['expected_data'] is not None and event['read_value']!=policy['expected_data']:issue('consumer_data_mismatch',expected=policy['expected_data'],observed=event['read_value'])
        if kind=='old_read':
            if event['source_ref'] not in holders:missing('old_reader_not_in_holder_census')
            elif event['read_valid'] is True:
                permission=event['holders'].get(event['source_ref'])
                if permission is False:issue('old_holder_read_without_permission')
                elif permission is None:missing('old_read_permission_unknown')
        if kind in ('old_read','new_read'):report['reads'].append({'event_ref':ref,'source_ref':event['source_ref'],'valid':event['read_valid'],'value':event['read_value']})
        report['ledger'].append({'event_ref':ref,'pending':sorted(pending),'unknown':sorted(pending&uncertain),'accepted_grant':granted,'finished':finished})
    if started and pending:gap('unresolved_obligations_at_window_end',obligations=sorted(pending))
    report['status']='review_required' if report['findings'] else 'incomplete' if report['gaps'] else 'within_observed_contract'
    return report


def exit_code(report):return {'within_observed_contract':0,'review_required':1,'incomplete':2}[report['status']]
