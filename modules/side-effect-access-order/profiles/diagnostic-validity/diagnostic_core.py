"""Review one diagnostic observation across destructive access and recovery."""
import hashlib
import json
from pathlib import Path

def require(condition,message):
    if not condition:raise ValueError(message)
def text(value,label):require(isinstance(value,str) and bool(value.strip()),label+' required')
def boolean(value,label):require(value is None or type(value) is bool,label+' must be boolean or null')
def uint(value,label,maximum=(1<<64)-1,nullable=False):require(nullable and value is None or type(value) is int and 0<=value<=maximum,label+' outside unsigned range')
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def read_json(path):
    def unique(pairs):
        result={}
        for key,value in pairs:require(key not in result,'Duplicate JSON key: '+key);result[key]=value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique,
                      parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON value')))

def review(spec,journal,policy):
    for record,name in ((spec,'spec'),(journal,'journal'),(policy,'policy')):
        require(isinstance(record,dict) and record.get('format')=='opentools.diagnostic.'+name+'.v1','Unsupported '+name+' format')
        require(isinstance(record.get('scope'),dict) and set(record['scope'])=={'project','configuration','recovery_ref','mode'},'Exact diagnostic scope required')
        for value in record['scope'].values():text(value,'scope')
        text(record.get('basis_ref'),'basis ref');require(type(record.get('inputs_complete')) is bool,'Boolean inputs_complete required')
    result={'format':'opentools.diagnostic.report.v1','scope':spec['scope'],
        'bindings':{key+'_sha256':digest(value) for key,value in (('spec',spec),('journal',journal),('policy',policy))},
        'findings':[],'gaps':[],'erasures':[],'selected_observation':None,'selected_cause_bit_set':None,
        'evidence_answer':'unknown','negative_through_seq':None,
        'limits':['One selected sticky-cause bank, destructive reads/recovery and one saved read receipt. Supplied source semantics and coverage require native/AI review.',
                  'Observed pending bits, target-epoch applicability and bounded negative evidence are different claims. No fault bucketization, silicon root cause or universal crash/retention qualification.']}
    def gap(kind,**details):result['gaps'].append(dict(kind=kind,**details))
    def finding(kind,**details):result['findings'].append(dict(kind=kind,**details))
    def next_epoch(current,event_ref):
        if current is None:return None
        if current==(1<<64)-1:gap('epoch_capacity_unqualified',event_ref=event_ref);return None
        return current+1
    bound=True
    for record,name in ((journal,'journal'),(policy,'policy')):
        if record['scope']!=spec['scope'] or record['basis_ref']!=spec['basis_ref'] or record.get('spec_sha256')!=digest(spec):gap('scope_or_spec_binding',record=name);bound=False
    if policy.get('journal_sha256')!=digest(journal):gap('journal_binding');bound=False
    if not bound:result['status']='incomplete';return result
    for record,name in ((spec,'spec'),(journal,'journal'),(policy,'policy')):
        if not record['inputs_complete']:gap('partial_inputs',record=name)
    for record in (spec,policy):text(record.get('source_revision_ref'),'source revision')
    if spec['source_revision_ref']!=policy['source_revision_ref']:gap('source_revision_mismatch')
    status=spec.get('status');saved_spec=spec.get('record');require(isinstance(status,dict) and isinstance(saved_spec,dict),'Status and saved-record contracts required')
    for entry in (status,saved_spec):
        text(entry.get('id'),'owner id');text(entry.get('evidence_ref'),'owner evidence')
        require(entry.get('reset_effect') in ('clear','retain','unknown'),'Explicit reset effect required')
    uint(status.get('width'),'status width',4096);require(status['width']>0,'Positive status width required');maximum=(1<<status['width'])-1
    require(status.get('onread') in ('clear','none','unknown'),'Explicit read effect required')
    require(status.get('latch_kind') in ('sticky-cause','unknown'),'Explicit latching semantics required')
    uint(policy.get('fault_mask'),'selected cause mask',maximum);require(policy['fault_mask'] and policy['fault_mask']&(policy['fault_mask']-1)==0,'One selected sticky cause bit required')
    mask=policy['fault_mask']
    for key in ('consumer_ref','selected_read_ref','requirements_ref'):text(policy.get(key),key)
    actors=policy.get('allowed_capture_actors');require(isinstance(actors,list) and actors and len(set(actors))==len(actors),'Independent capture actors required')
    for actor in actors:text(actor,'allowed actor')
    uint(policy.get('target_epoch'),'target epoch');uint(policy.get('required_through_seq'),'required prefix')
    require(policy.get('claim') in ('present','absent','undetermined'),'Explicit diagnostic claim required')
    for key in ('source_kind','method_ref','coverage_scope_ref'):text(journal.get(key),key)
    for key in ('history_complete','source_latching_complete','initial_available'):
        require(key in journal,'Explicit '+key+' required');boolean(journal[key],key)
    if journal['history_complete'] is not True:gap('history_incomplete')
    uint(journal.get('initial_status'),'initial status',maximum,True);uint(journal.get('initial_epoch'),'initial epoch',nullable=True)
    epoch=journal['initial_epoch'];clean={epoch:journal['initial_status'] is not None and not journal['initial_status']&mask} if epoch is not None else {}
    available=journal['initial_available'];reads={};events=journal.get('events');require(isinstance(events,list),'Explicit diagnostic events required')
    record_state=None;last=-1;ids=set()
    def parse_record(value):
        require(isinstance(value,dict),'Record value required')
        for key in ('value','valid','epoch'):require(key in value,'Explicit record '+key+' required')
        uint(value['value'],'saved value',maximum,True);boolean(value['valid'],'saved validity');uint(value['epoch'],'saved epoch',nullable=True)
        return dict(value,origin=None)
    record_state=parse_record(journal.get('initial_record'))
    for event in events:
        require(isinstance(event,dict),'Event object required');text(event.get('id'),'event id');require(event['id'] not in ids,'Unique event id required');ids.add(event['id'])
        uint(event.get('seq'),'event sequence');require(event['seq']>last,'Strictly increasing sequence required');last=event['seq'];text(event.get('evidence_ref'),'event evidence')
        kind=event.get('kind');require(kind in ('availability','read','save','recovery','record_external'),'Supported diagnostic event kind required')
        if kind=='availability':
            require('value' in event,'Explicit availability required');boolean(event['value'],'availability');available=event['value'];continue
        if kind=='record_external':record_state=parse_record(event.get('record'));continue
        if kind=='recovery':
            require('observed' in event,'Explicit recovery observation required');boolean(event['observed'],'recovery observed')
            if event['observed'] is None:gap('recovery_assertion_unknown',event_ref=event['id']);epoch=None;record_state=dict(value=None,valid=None,epoch=None,origin=None)
            elif event['observed']:
                if status['reset_effect']=='clear':
                    result['erasures'].append({'event_ref':event['id'],'kind':'status-reset','epoch':epoch})
                    epoch=next_epoch(epoch,event['id'])
                    if epoch is not None:clean[epoch]=True
                elif status['reset_effect']=='unknown':gap('status_reset_effect_unknown',event_ref=event['id']);epoch=None
                if saved_spec['reset_effect']=='clear':record_state=dict(value=0,valid=False,epoch=0,origin=None)
                elif saved_spec['reset_effect']=='unknown':gap('record_reset_effect_unknown',event_ref=event['id']);record_state=dict(value=None,valid=None,epoch=None,origin=None)
            if 'epoch_after' in event:
                uint(event['epoch_after'],'recovery epoch',nullable=True)
                if epoch is not None and event['epoch_after'] is not None and epoch!=event['epoch_after']:finding('epoch_transition_disagreement',event_ref=event['id']);epoch=None
            continue
        text(event.get('actor_ref'),'event actor')
        if kind=='save':
            require('accepted' in event,'Explicit capture acceptance required');boolean(event['accepted'],'capture acceptance')
            value=parse_record(event.get('record'));source=event.get('source_read_ref')
            require(source is None or isinstance(source,str) and source.strip(),'Capture source read or null required')
            if event['accepted'] is None:gap('capture_acceptance_unknown',event_ref=event['id']);record_state=dict(value=None,valid=None,epoch=None,origin=None);continue
            if not event['accepted']:continue
            origin=reads.get(source)
            if origin is None:gap('capture_source_read_missing',event_ref=event['id'])
            elif not origin['usable']:gap('capture_source_read_unusable',event_ref=event['id'])
            elif event['actor_ref'] not in actors or origin['actor_ref'] not in actors:gap('capture_actor_not_authorized',event_ref=event['id'])
            elif value['valid'] is not True or value['value'] is None:gap('saved_capture_unknown_or_invalid',event_ref=event['id'])
            elif value['value']!=origin['data']:finding('saved_value_disagrees_with_source',event_ref=event['id'])
            elif value['epoch'] is not None and origin['epoch'] is not None and value['epoch']!=origin['epoch']:finding('saved_epoch_disagrees_with_source',event_ref=event['id'])
            else:value['origin']=dict(origin)
            record_state=value;continue
        require(event.get('source') in ('status','record'),'Explicit diagnostic source required')
        for key in ('accepted','error','available','hardware_quiet'):
            require(key in event,'Explicit read '+key+' required');boolean(event[key],'read '+key)
        require('data' in event and 'epoch' in event,'Explicit response data and epoch or null required')
        uint(event['data'],'read data',maximum,True);uint(event['epoch'],'read epoch',nullable=True)
        usable=event['accepted'] is True and event['error'] is False and event['available'] is True and event['hardware_quiet'] is True and event['data'] is not None
        if not usable:gap('read_not_qualified',event_ref=event['id'])
        if available is not None and event['available'] is not None and journal['history_complete'] is True and available!=event['available']:finding('read_availability_disagreement',event_ref=event['id']);usable=False
        info={'id':event['id'],'seq':event['seq'],'source':event['source'],'actor_ref':event['actor_ref'],'data':event['data'],'usable':usable,'response_qualified':usable,
              'epoch':epoch,'clean_start':clean.get(epoch,False),'origin_read_ref':event['id'],'origin_seq':event['seq'],'evidence_ref':event['evidence_ref']}
        if event['source']=='status':
            if usable and event['epoch'] is not None and epoch is not None and event['epoch']!=epoch:finding('read_epoch_disagreement',event_ref=event['id']);info['usable']=False
            if status['latch_kind']!='sticky-cause':gap('latch_semantics_unknown',event_ref=event['id']);info['usable']=False
            if event['accepted'] is True and event['error'] is False and event['available'] is True:
                if status['onread']=='clear' and event['hardware_quiet'] is True:
                    result['erasures'].append({'event_ref':event['id'],'kind':'read-clear','epoch':epoch});epoch=next_epoch(epoch,event['id'])
                    if epoch is not None:clean[epoch]=True
                elif status['onread']=='unknown' or status['onread']=='clear' and event['hardware_quiet'] is not True:gap('read_effect_unqualified',event_ref=event['id']);epoch=None
            elif event['accepted'] is None and status['onread']!='none':gap('possible_unobserved_read_effect',event_ref=event['id']);epoch=None
        else:
            require('record_valid' in event,'Explicit loaded-record validity required');boolean(event['record_valid'],'loaded record validity')
            origin=record_state['origin']
            if event['record_valid'] is not True:gap('loaded_record_unknown_or_invalid',event_ref=event['id']);info['usable']=False;info['response_qualified']=False
            if record_state['valid'] is not True or origin is None:gap('record_capture_provenance_unverified',event_ref=event['id']);info['usable']=False
            elif event['data']!=record_state['value']:finding('loaded_record_value_disagreement',event_ref=event['id']);info['usable']=False
            elif event['epoch'] is not None and (record_state['epoch'] if record_state['epoch'] is not None else origin['epoch']) is not None and event['epoch']!=(record_state['epoch'] if record_state['epoch'] is not None else origin['epoch']):finding('loaded_record_epoch_disagreement',event_ref=event['id']);info['usable']=False
            if origin is not None:
                for key in ('epoch','clean_start','origin_read_ref','origin_seq'):info[key]=origin[key]
                info['usable']=info['usable'] and origin['usable']
        reads[event['id']]=info
    selected=reads.get(policy['selected_read_ref'])
    if selected is None:gap('selected_diagnostic_read_absent')
    else:
        result['selected_observation']=selected
        if selected['response_qualified']:result['selected_cause_bit_set']=bool(selected['data']&mask)
        if selected['actor_ref']!=policy['consumer_ref']:gap('selected_consumer_mismatch')
        elif not selected['usable']:gap('selected_evidence_unusable')
        elif selected['epoch']!=policy['target_epoch']:gap('selected_epoch_mismatch',actual=selected['epoch'],required=policy['target_epoch'])
        elif not selected['clean_start']:gap('target_epoch_clean_start_unproven')
        elif journal['history_complete'] is not True:gap('epoch_history_unproven')
        elif spec['source_revision_ref']!=policy['source_revision_ref']:gap('selected_source_revision_unproven')
        elif result['selected_cause_bit_set']:result['evidence_answer']='present'
        elif selected['origin_seq']<policy['required_through_seq']:gap('observation_precedes_required_prefix')
        elif journal['source_latching_complete'] is not True:gap('negative_latching_coverage_unproven')
        else:result['evidence_answer']='absent_in_observed_prefix';result['negative_through_seq']=selected['origin_seq']
    answer=result['evidence_answer']
    if policy['claim']!='undetermined':
        if answer=='unknown':finding('claim_not_established_by_selected_evidence',claim=policy['claim'])
        elif (policy['claim']=='present')!=(answer=='present'):finding('claim_contradicted_by_selected_evidence',claim=policy['claim'],answer=answer)
    result['status']='review_required' if result['findings'] else 'incomplete' if result['gaps'] else 'within_observed_evidence'
    return result

def exit_code(report):return {'within_observed_evidence':0,'review_required':1,'incomplete':2}[report['status']]
