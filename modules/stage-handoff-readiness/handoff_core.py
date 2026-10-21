"""Review one execution handoff against independent successor requirements."""
import hashlib
import json
from pathlib import Path

MAX=(1<<64)-1

def require(condition,message):
    if not condition:raise ValueError(message)

def text(value,label):require(isinstance(value,str) and bool(value.strip()),label+' required')
def uint(value,label,positive=False):require(type(value) is int and (1 if positive else 0)<=value<=MAX,label+' must be an unsigned 64-bit integer')
def boolean(value,label):require(value is None or type(value) is bool,label+' must be boolean or null')
def sha(value,label):require(isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value),label+' must be lowercase SHA-256')
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def read_json(path):
    def unique(pairs):
        result={}
        for key,value in pairs:require(key not in result,'Duplicate JSON key: '+key);result[key]=value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique,
                      parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON value')))

def region(record,label):
    require(isinstance(record,dict),label+' range required');uint(record.get('start'),label+' start');uint(record.get('size'),label+' size',True)
    require(record['start']+record['size']<=MAX+1,label+' range overflows');return record['start'],record['start']+record['size']

def review(inventory,journal,policy):
    for record,name in ((inventory,'inventory'),(journal,'journal'),(policy,'policy')):
        require(isinstance(record,dict) and record.get('format')=='opentools.stage.'+name+'.v1','Unsupported '+name+' format')
        require(isinstance(record.get('scope'),dict) and set(record['scope'])=={'project','configuration','handoff_ref','mode'},'Exact handoff scope required')
        for v in record['scope'].values():text(v,'scope')
        text(record.get('basis_ref'),'basis_ref');require(type(record.get('inputs_complete')) is bool,'Boolean inputs_complete required')
    result={'format':'opentools.stage.report.v1','scope':inventory['scope'],
        'bindings':{k+'_sha256':digest(v) for k,v in (('inventory',inventory),('journal',journal),('policy',policy))},
        'obligations':[],'findings':[],'gaps':[],'first_stack_access':None,'observed_result':None,
        'limits':['Typed supplied facts for one selected execution handoff; no automatic company-native trace adapter or undocumented ROM inference.',
                  'Image hashes establish identity, not secure-boot authenticity. No universal ISA, ECC, clock/reset, cache/MMU or silicon qualification.']}
    def gap(kind,**details):result['gaps'].append(dict(kind=kind,**details))
    def finding(kind,**details):result['findings'].append(dict(kind=kind,**details))
    bound=True
    for record,name in ((journal,'journal'),(policy,'policy')):
        if record['scope']!=inventory['scope'] or record['basis_ref']!=inventory['basis_ref'] or record.get('inventory_sha256')!=digest(inventory):gap('scope_or_inventory_binding',record=name);bound=False
    if policy.get('journal_sha256')!=digest(journal):gap('journal_binding');bound=False
    if not bound:result['status']='incomplete';return result
    for record,name in ((inventory,'inventory'),(journal,'journal'),(policy,'policy')):
        if not record['inputs_complete']:gap('partial_inputs',record=name)
    image=inventory.get('image');require(isinstance(image,dict),'Image metadata required')
    sha(image.get('sha256'),'actual image identity');uint(image.get('entry'),'image entry');text(image.get('evidence_ref'),'image evidence')
    segments=image.get('segments');require(isinstance(segments,list) and segments,'Resolved loaded segments required')
    executable=[]
    for segment in segments:
        a,b=region(segment,'image segment');permissions=segment.get('permissions')
        require(isinstance(permissions,list) and len(set(permissions))==len(permissions) and set(permissions)<={'R','W','X'},'Explicit R/W/X permissions required')
        text(segment.get('evidence_ref'),'segment evidence')
        if 'X' in permissions:executable.append((a,b))
    text(inventory.get('source_kind'),'source kind');text(inventory.get('method_ref'),'method ref');text(inventory.get('source_revision_ref'),'source revision')
    text(policy.get('source_revision_ref'),'required source revision')
    if inventory['source_revision_ref']!=policy['source_revision_ref']:gap('source_revision_mismatch')
    for k in ('successor_ref','requirements_ref'):text(policy.get(k),k)
    sha(policy.get('image_sha256'),'required image identity')
    for k in ('entry','initial_sp'):uint(policy.get(k),'required '+k)
    stack_start,stack_end=region(policy.get('stack_region'),'required stack')
    alignment=policy.get('stack_alignment');uint(alignment,'stack alignment',True);require(alignment&(alignment-1)==0,'Power-of-two stack alignment required')
    expected=policy.get('requirements');require(isinstance(expected,dict) and expected,'Independent receiving requirements required')
    for key,value in expected.items():text(key,'requirement id');require(type(value) is bool,'Boolean required state')
    require('expected_result' in policy,'Explicit expected result or null required')
    if policy['expected_result'] is not None:uint(policy['expected_result'],'expected result')
    require('events_complete' in journal,'Explicit event coverage required');boolean(journal['events_complete'],'event coverage')
    if journal['events_complete'] is not True:gap('event_capture_incomplete')
    events=journal.get('events');require(isinstance(events,list),'Explicit event list required')
    last=-1;latest={};loaded=None;handoff=None;accesses=[];outputs=[]
    for event in events:
        require(isinstance(event,dict),'Event record required');uint(event.get('seq'),'event sequence');require(event['seq']>last,'Strictly increasing event sequence required');last=event['seq']
        text(event.get('evidence_ref'),'event evidence');kind=event.get('kind')
        require(kind in ('fact','image_load','handoff','access','result'),'Supported event kind required')
        if kind=='fact':
            text(event.get('id'),'fact id');require('value' in event,'Explicit fact value required');boolean(event['value'],'fact value');latest[event['id']]=event
        elif kind=='image_load':
            sha(event.get('image_sha256'),'loaded image');loaded=event
            if handoff is not None:gap('image_reload_after_handoff',seq=event['seq'])
        elif kind=='handoff':
            require(handoff is None,'One handoff per scoped journal');handoff=event
            for k in ('successor_ref',):text(event.get(k),k)
            for k in ('entry','initial_sp'):uint(event.get(k),'actual '+k)
            sha(event.get('image_sha256'),'handoff image')
            snapshot=event.get('state');require(isinstance(snapshot,dict),'Handoff state snapshot required')
            for key,value in snapshot.items():text(key,'snapshot id');boolean(value,'snapshot state')
            if loaded is None:gap('image_load_not_observed')
            elif loaded['image_sha256']!=event['image_sha256']:finding('handoff_loaded_image_disagreement')
            if event['image_sha256']!=image['sha256']:finding('actual_image_metadata_disagreement')
            if event['image_sha256']!=policy['image_sha256']:finding('required_image_mismatch')
            if event['successor_ref']!=policy['successor_ref']:finding('wrong_successor')
            if event['entry']!=policy['entry'] or event['entry']!=image['entry']:finding('entry_mismatch',actual=event['entry'],required=policy['entry'],image_entry=image['entry'])
            if not any(a<=event['entry']<b for a,b in executable):finding('entry_outside_executable_segment',entry=event['entry'])
            if event['initial_sp']!=policy['initial_sp']:finding('initial_stack_pointer_mismatch',actual=event['initial_sp'],required=policy['initial_sp'])
            if not stack_start<event['initial_sp']<=stack_end or event['initial_sp']%alignment:finding('initial_stack_outside_contract',initial_sp=event['initial_sp'])
            for key,required in expected.items():
                actual=snapshot.get(key);prior=latest.get(key)
                disposition='unknown' if actual is None else 'met' if actual==required else 'violated'
                result['obligations'].append({'id':key,'required':required,'at_handoff':actual,'status':disposition,'evidence_ref':event['evidence_ref'],
                    'prior_event_ref':prior['evidence_ref'] if prior else None})
                if actual is None:gap('handoff_prerequisite_unknown',id=key)
                elif actual!=required:finding('handoff_prerequisite_not_met',id=key,actual=actual,required=required,seq=event['seq'])
                if prior is not None and journal['events_complete'] is True and prior['value'] is not None and actual is not None and prior['value']!=actual:finding('snapshot_event_disagreement',id=key)
        elif kind=='access':
            text(event.get('actor_ref'),'access actor');require(event.get('purpose') in ('stack','data','fetch'),'Explicit access purpose required')
            uint(event.get('address'),'access address');uint(event.get('size'),'access size',True)
            require(event['address']+event['size']<=MAX+1,'Access range overflows')
            require(event.get('operation') in ('read','write','execute'),'Access operation required')
            require('successful' in event,'Explicit access result required');boolean(event['successful'],'access result')
            if event['actor_ref']!=policy['successor_ref']:gap('foreign_access_actor',seq=event['seq']);continue
            if handoff is None:finding('successor_access_before_handoff',seq=event['seq'])
            accesses.append(event)
            if event['successful'] is None:gap('access_result_unknown',seq=event['seq'])
            elif event['successful'] is False:finding('observed_successor_access_failure',seq=event['seq'],address=event['address'])
            if event['purpose']=='stack':
                if result['first_stack_access'] is None:result['first_stack_access']=dict(event)
                if not stack_start<=event['address'] or event['address']+event['size']>stack_end:finding('stack_access_outside_required_region',seq=event['seq'],address=event['address'],size=event['size'])
        elif kind=='result':
            text(event.get('actor_ref'),'result actor');require('value' in event,'Explicit result value required')
            if event['value'] is not None:uint(event['value'],'observed result')
            if event['actor_ref']!=policy['successor_ref']:gap('foreign_result_actor',seq=event['seq']);continue
            if handoff is None:finding('successor_result_before_handoff',seq=event['seq'])
            outputs.append(event)
    if handoff is None:gap('handoff_not_observed')
    if result['first_stack_access'] is None:gap('first_stack_access_not_observed')
    if not accesses:gap('successor_accesses_absent')
    if len(outputs)>1:gap('multiple_result_observations')
    if outputs:result['observed_result']=outputs[-1]['value']
    if policy['expected_result'] is not None:
        if not outputs or outputs[-1]['value'] is None:gap('successor_result_unknown')
        elif outputs[-1]['value']!=policy['expected_result']:finding('successor_result_mismatch',actual=outputs[-1]['value'],required=policy['expected_result'])
    result['status']='review_required' if result['findings'] else 'incomplete' if result['gaps'] else 'within_observed_contract'
    return result

def exit_code(report):return {'within_observed_contract':0,'review_required':1,'incomplete':2}[report['status']]
