"""Scope-bound checkpoint compatibility and selected-observable qualification."""
import hashlib
import json
from pathlib import Path
import re

MECHANISMS=('serialized_model','native_simulator','process_checkpoint','manual_initialization')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def shape(value, keys, optional=()):
    require(isinstance(value,dict) and set(keys)<=set(value) and set(value)<=set(keys)|set(optional),
            'Invalid fields; expected '+', '.join(keys))


def text(value):
    return isinstance(value,str) and bool(value.strip())


def nullable(value):
    return value is None or text(value)


def digest(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def read_json(path):
    def unique(pairs):
        result={}
        for key,value in pairs:
            require(key not in result,'Duplicate JSON key: '+key)
            result[key]=value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Nonfinite JSON: '+v)))


def unknown(value):
    if value is None:
        return True
    if isinstance(value,dict):
        return any(unknown(v) for v in value.values())
    return isinstance(value,list) and any(unknown(v) for v in value)


def differences(a,b,path):
    if a is None or b is None:
        return []
    if type(a) is not type(b):
        return [{'path':path,'control':a,'requested_or_restored':b}]
    if isinstance(a,dict):
        if set(a)!=set(b):
            return [{'path':path+'/keys','control':sorted(a),'requested_or_restored':sorted(b)}]
        return [d for k in sorted(a) for d in differences(a[k],b[k],path+'/'+k)]
    if isinstance(a,list):
        if len(a)!=len(b):
            return [{'path':path+'/length','control':len(a),'requested_or_restored':len(b)}]
        return [d for i,(x,y) in enumerate(zip(a,b)) for d in differences(x,y,path+'/'+str(i))]
    return [] if a==b else [{'path':path,'control':a,'requested_or_restored':b}]


def fact(value):
    shape(value,('complete','evidence_ref'))
    require(value['complete'] is None or type(value['complete']) is bool,'Completeness must be boolean/null')
    require(nullable(value['evidence_ref']),'Invalid evidence reference')


def completion(value):
    shape(value,('complete','exit_code','evidence_ref'))
    require(value['complete'] is None or type(value['complete']) is bool,'Invalid completion flag')
    require(value['exit_code'] is None or type(value['exit_code']) is int,'Invalid invocation exit code')
    require(nullable(value['evidence_ref']),'Invalid completion evidence')


def step(value):
    return value is None or type(value) is int and value>=0


def observation(value):
    shape(value,('step','values','evidence_ref'))
    require(step(value['step']) and isinstance(value['values'],dict) and nullable(value['evidence_ref']),
            'Invalid boundary observation')


def relative(value):
    require(text(value) and ':' not in value and '\\' not in value,'Use relative POSIX file paths')
    parts=value.split('/')
    require(all(p not in ('','.','..') for p in parts),'File paths must stay within the explicit root')
    return parts


def file_record(value, with_id=False):
    shape(value,('id','path','sha256','evidence_ref') if with_id else ('path','sha256','evidence_ref'))
    relative(value['path'])
    require((not with_id or text(value['id'])) and (value['sha256'] is None or digest(value['sha256']))
            and nullable(value['evidence_ref']),'Invalid file identity/evidence')


def context(value):
    shape(value,('binary_sha256','configuration','prefix_inputs','prefix_seed','capture_point'))
    require(value['binary_sha256'] is None or digest(value['binary_sha256']),'Invalid binary digest')
    require(value['configuration'] is None or isinstance(value['configuration'],dict),'Invalid configuration')
    require(isinstance(value['prefix_inputs'],list),'Prefix inputs must be a list')
    names=set()
    for item in value['prefix_inputs']:
        shape(item,('id','sha256','evidence_ref'))
        require(text(item['id']) and item['id'] not in names and (item['sha256'] is None or digest(item['sha256']))
                and nullable(item['evidence_ref']),'Invalid/duplicate prefix input')
        names.add(item['id'])
    point=value['capture_point']
    shape(point,('step','unit','definition_ref'))
    require(step(point['step']) and nullable(point['unit']) and nullable(point['definition_ref']),'Invalid capture point')


def context_key(value):
    return {**value,'prefix_inputs':[{k:v for k,v in item.items() if k!='evidence_ref'} for item in value['prefix_inputs']]}


def horizon(value):
    shape(value,('start_step','end_step','unit','definition_ref','evidence_ref'))
    require(step(value['start_step']) and step(value['end_step']) and all(nullable(value[k]) for k in ('unit','definition_ref','evidence_ref')),
            'Invalid observation horizon')
    require(value['start_step'] is None or value['end_step'] is None or value['end_step']>value['start_step'],
            'Horizon must have a positive extent')


def horizon_key(value):
    return {k:v for k,v in value.items() if k!='evidence_ref'}


def validate_profile(value):
    shape(value,('format','id','mechanism','state','observables','boundary_ref','evidence_ref'))
    canonical(value)
    require(value['format']=='opentools.checkpoint-profile.v1' and text(value['id']) and value['mechanism'] in MECHANISMS,
            'Unsupported checkpoint profile/mechanism')
    require(nullable(value['boundary_ref']) and nullable(value['evidence_ref']),'Invalid profile evidence')
    require(isinstance(value['state'],list) and value['state'],'Nonempty state obligations required')
    names=set()
    for item in value['state']:
        shape(item,('id','requirement','evidence_ref'))
        require(text(item['id']) and item['id'] not in names and item['requirement'] in ('capture','not_used')
                and nullable(item['evidence_ref']),'Invalid state obligation')
        names.add(item['id'])
    require(isinstance(value['observables'],list) and value['observables'] and all(text(v) for v in value['observables'])
            and len(set(value['observables']))==len(value['observables']),'Unique selected observables required')


def validate_checkpoint(value):
    shape(value,('format','checkpoint_ref','profile_sha256','mechanism','context','reference_continuation',
                 'state_inventory','state_inventory_complete','capture','artifacts','boundary_observation'),('provenance',))
    canonical(value)
    require(value['format']=='opentools.checkpoint.v1' and text(value['checkpoint_ref']) and value['mechanism'] in MECHANISMS,
            'Unsupported checkpoint record')
    require(value['profile_sha256'] is None or digest(value['profile_sha256']),'Invalid profile digest')
    context(value['context'])
    require(value['reference_continuation'] is None or isinstance(value['reference_continuation'],dict),'Invalid continuation')
    fact(value['state_inventory_complete'])
    completion(value['capture'])
    observation(value['boundary_observation'])
    require(isinstance(value['state_inventory'],list) and isinstance(value['artifacts'],list),'Invalid inventory/artifact list')
    names=set()
    for item in value['state_inventory']:
        shape(item,('id','status','method','capture_ref','restore_ref'))
        require(text(item['id']) and item['id'] not in names and item['status'] in ('captured','not_used','missing','unknown')
                and all(nullable(item[k]) for k in ('method','capture_ref','restore_ref')),'Invalid state inventory entry')
        names.add(item['id'])
    names=set()
    for item in value['artifacts']:
        file_record(item)
        require(item['path'] not in names,'Duplicate checkpoint artifact path')
        names.add(item['path'])


def validate_request(value):
    shape(value,('format','request_ref','checkpoint_ref','profile_sha256','intent','context','continuation','horizon',
                 'binary','prefix_files','evidence_ref'),('provenance',))
    canonical(value)
    require(value['format']=='opentools.replay-request.v1' and all(text(value[k]) for k in ('request_ref','checkpoint_ref')),
            'Unsupported replay request')
    require(value['profile_sha256'] is None or digest(value['profile_sha256']),'Invalid profile digest')
    require(value['intent'] in ('faithful','exploratory') and nullable(value['evidence_ref']),'Invalid intent/evidence')
    context(value['context'])
    require(value['continuation'] is None or isinstance(value['continuation'],dict),'Invalid continuation')
    horizon(value['horizon'])
    file_record(value['binary'])
    require(isinstance(value['prefix_files'],list),'Invalid prefix file list')
    names=set()
    for item in value['prefix_files']:
        file_record(item,True)
        require(item['id'] not in names,'Duplicate prefix file ID')
        names.add(item['id'])


def verify_file(item, root, label):
    result={'label':label,'path':item['path'],'expected_sha256':item['sha256'],'observed_sha256':None,'status':'unverified'}
    gaps=[]
    if item['sha256'] is None or not text(item['evidence_ref']):
        gaps.append('Original file identity/evidence unknown: '+label)
    if root is None:
        gaps.append('Explicit artifact root required: '+label)
        return result,gaps
    directory=Path(root).resolve(strict=True)
    require(directory.is_dir(),'Artifact root must be an existing directory')
    path=directory
    safe=True
    for part in relative(item['path']):
        path=path/part
        safe=safe and not path.is_symlink()
    if not safe or not path.resolve().is_relative_to(directory) or not path.is_file():
        result['status']='missing_or_unsafe'
    else:
        result['observed_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        result['status']='original_hash_unknown' if item['sha256'] is None else 'verified' if result['observed_sha256']==item['sha256'] else 'mismatch'
    return result,gaps


def check(checkpoint,request,profile,artifact_root=None):
    validate_profile(profile)
    validate_checkpoint(checkpoint)
    validate_request(request)
    gaps=[]
    reasons=[]
    if any(v['profile_sha256']!=fingerprint(profile) for v in (checkpoint,request)):
        gaps.append('Checkpoint/request are not bound to this exact profile')
    if checkpoint['mechanism']!=profile['mechanism']:
        reasons.append({'path':'mechanism','control':checkpoint['mechanism'],'requested_or_restored':profile['mechanism']})
    if checkpoint['checkpoint_ref']!=request['checkpoint_ref']:
        reasons.append({'path':'checkpoint_ref','control':checkpoint['checkpoint_ref'],'requested_or_restored':request['checkpoint_ref']})
    if not text(profile['evidence_ref']) or not text(profile['boundary_ref']) or not text(request['evidence_ref']):
        gaps.append('Profile boundary/request evidence missing')
    a,b=context_key(checkpoint['context']),context_key(request['context'])
    reasons+=differences(a,b,'context')
    if unknown(a) or unknown(b):
        gaps.append('Unknown captured/requested context')
    for value in (checkpoint['context'],request['context']):
        if any(not text(item['evidence_ref']) for item in value['prefix_inputs']):
            gaps.append('Unsourced prefix input identity')
    if request['intent']=='faithful':
        reasons+=differences(checkpoint['reference_continuation'],request['continuation'],'continuation')
    if unknown(checkpoint['reference_continuation']) or unknown(request['continuation']):
        gaps.append('Unknown continuation conditions')
    if request['intent']=='exploratory':
        gaps.append('Exploratory continuation is a branch, not faithful replay qualification')
    point=request['context']['capture_point']
    h=request['horizon']
    for name,left,right in [('start_step',point['step'],h['start_step']),('unit',point['unit'],h['unit']),('definition_ref',point['definition_ref'],h['definition_ref'])]:
        reasons+=differences(left,right,'horizon/'+name)
    if unknown(h):
        gaps.append('Unknown horizon extent/definition/evidence')
    inventory={v['id']:v for v in checkpoint['state_inventory']}
    obligations={v['id']:v for v in profile['state']}
    if set(inventory)!=set(obligations):
        gaps.append('State inventory differs from the declared obligation population')
    for name,requirement in obligations.items():
        item=inventory.get(name)
        if not text(requirement['evidence_ref']):
            gaps.append('Unsourced state obligation: '+name)
        if item is None or item['status']=='unknown':
            gaps.append('Unknown state capture: '+name)
            continue
        expected='captured' if requirement['requirement']=='capture' else 'not_used'
        if item['status']!=expected:
            reasons.append({'path':'state/'+name,'control':expected,'requested_or_restored':item['status']})
        if any(not text(item[k]) for k in ('method','capture_ref','restore_ref')):
            gaps.append('Missing capture/restore basis: '+name)
    population=checkpoint['state_inventory_complete']
    if population['complete'] is not True or not text(population['evidence_ref']):
        gaps.append('State population completeness not established')
    capture=checkpoint['capture']
    if capture['complete'] is False or capture['exit_code'] is not None and capture['exit_code']!=0:
        reasons.append({'path':'capture','control':'completed successful capture','requested_or_restored':capture})
    if capture['complete'] is not True or capture['exit_code']!=0 or not text(capture['evidence_ref']):
        gaps.append('Completed capture evidence not established')
    boundary=checkpoint['boundary_observation']
    if boundary['step']!=checkpoint['context']['capture_point']['step']:
        gaps.append('Boundary observation does not bind the capture step')
    if set(boundary['values'])!=set(profile['observables']) or unknown(boundary['values']) or not text(boundary['evidence_ref']):
        gaps.append('Capture-boundary selected observations are incomplete')
    if not checkpoint['artifacts']:
        gaps.append('No checkpoint artifact declared')
    files=[]
    for item in checkpoint['artifacts']:
        result,missing=verify_file(item,artifact_root,'checkpoint:'+item['path'])
        files.append(result); gaps+=missing
    result,missing=verify_file(request['binary'],artifact_root,'requested binary')
    files.append(result); gaps+=missing
    reasons+=differences(request['context']['binary_sha256'],request['binary']['sha256'],'requested_binary_identity')
    inputs={item['id']:item for item in request['context']['prefix_inputs']}
    if set(inputs)!={item['id'] for item in request['prefix_files']}:
        gaps.append('Live prefix file inventory does not cover requested prefix identities')
    for item in request['prefix_files']:
        if item['id'] in inputs:
            reasons+=differences(inputs[item['id']]['sha256'],item['sha256'],'prefix_file/'+item['id'])
        result,missing=verify_file(item,artifact_root,'prefix:'+item['id'])
        files.append(result); gaps+=missing
    unavailable=any(item['status'] in ('missing_or_unsafe','mismatch') for item in files)
    status='incompatible' if reasons else 'unavailable_checkpoint' if unavailable else 'unknown_compatibility' if gaps else 'compatible_within_declared_scope'
    return {'format':'opentools.checkpoint-check.v1','status':status,'checkpoint_ref':checkpoint['checkpoint_ref'],
            'request_ref':request['request_ref'],'mechanism':checkpoint['mechanism'],
            'input_sha256':{'checkpoint':fingerprint(checkpoint),'request':fingerprint(request),'profile':fingerprint(profile)},
            'incompatibilities':reasons,'unknowns':list(dict.fromkeys(gaps)),'files':files,
            'limits':'Declared state/prefix correspondence and current file hashes only; no native execution, authentication, universal equivalence, operational lease or future compatibility proof.'}


def validate_run(value):
    shape(value,('format','run_ref','role','request_sha256','checkpoint_sha256','profile_sha256','horizon',
                 'completion','start','samples','end','observations_ref'),('provenance',))
    canonical(value)
    require(value['format']=='opentools.replay-run.v1' and text(value['run_ref']) and value['role'] in ('control','restored','exploratory'),
            'Unsupported replay run')
    require(all(value[k] is None or digest(value[k]) for k in ('request_sha256','checkpoint_sha256','profile_sha256')),'Invalid run binding')
    horizon(value['horizon'])
    completion(value['completion'])
    observation(value['start']); observation(value['end'])
    require(nullable(value['observations_ref']) and isinstance(value['samples'],list),'Invalid observations')
    for sample in value['samples']:
        shape(sample,('step','values'))
        require(step(sample['step']) and isinstance(sample['values'],dict),'Invalid sample')


def observed_differences(a,b,fields,path):
    # An absent channel is missing evidence, not an observed semantic mismatch.
    return [d for name in sorted(fields) if name in a and name in b for d in differences(a[name],b[name],path+'/'+name)]


def qualify(checkpoint,request,profile,control,restored,artifact_root=None):
    base=check(checkpoint,request,profile,artifact_root)
    for run in (control,restored):
        validate_run(run)
    gaps=[]
    mismatch=[]
    pair_bound=request['intent']=='faithful'
    observations=set(profile['observables'])
    h=request['horizon']
    for label,run in [('control',control),('restored',restored)]:
        for key,expected in [('request_sha256',fingerprint(request)),('checkpoint_sha256',fingerprint(checkpoint)),('profile_sha256',fingerprint(profile))]:
            if run[key]!=expected:
                gaps.append(label+': foreign/unknown '+key)
                pair_bound=False
        if run['role']!=label:
            gaps.append(label+': expected role differs or execution is exploratory')
            pair_bound=False
        if horizon_key(run['horizon'])!=horizon_key(h) or not text(run['horizon']['evidence_ref']):
            gaps.append(label+': horizon does not bind the requested extent/definition')
            pair_bound=False
        c=run['completion']
        if c['complete'] is not True or c['exit_code']!=0 or not text(c['evidence_ref']):
            gaps.append(label+': successful complete invocation not established')
        if not text(run['observations_ref']):
            gaps.append(label+': observations lack source evidence')
        for point,boundary in [('start',h['start_step']),('end',h['end_step'])]:
            if run[point]['step']!=boundary or not text(run[point]['evidence_ref']):
                gaps.append(label+': unestablished '+point+' boundary')
                pair_bound=False
        count=h['end_step']-h['start_step'] if h['end_step'] is not None and h['start_step'] is not None else None
        if count is None or len(run['samples'])!=count or any(sample['step']!=h['start_step']+i+1 for i,sample in enumerate(run['samples'])):
            gaps.append(label+': incomplete, duplicated or reordered step population')
        for item in [run['start'],*run['samples'],run['end']]:
            if set(item['values'])!=observations or unknown(item['values']):
                gaps.append(label+': selected observable values are incomplete/unexpected')
        if run['samples'] and run['end']['values']!=run['samples'][-1]['values']:
            gaps.append(label+': final boundary contradicts last sample')
            pair_bound=False
        mismatch+=observed_differences(checkpoint['boundary_observation']['values'],run['start']['values'],observations,label+'/capture_boundary')
    if control['run_ref']==restored['run_ref']:
        gaps.append('Control/restored execution identities must be distinct')
        pair_bound=False
    mismatch+=observed_differences(control['start']['values'],restored['start']['values'],observations,'start')
    # Compare only uniquely observed common steps. Missing, repeated or reordered
    # rows remain population gaps; they cannot create a behavioral difference.
    maps=[]
    for run in (control,restored):
        rows={}
        repeated=set()
        for sample in run['samples']:
            key=sample['step']
            if key in rows:
                repeated.add(key)
            rows[key]=sample['values']
        maps.append({k:v for k,v in rows.items() if k is not None and k not in repeated})
    for key in sorted(set(maps[0])&set(maps[1])):
        mismatch+=observed_differences(maps[0][key],maps[1][key],observations,'step/'+str(key))
    mismatch+=observed_differences(control['end']['values'],restored['end']['values'],observations,'end')
    # Keep all incompatibilities/gaps and known divergence; never promote a failed gate.
    status=base['status'] if base['status'] in ('incompatible','unavailable_checkpoint') else 'not_qualified' if not pair_bound else 'diverged' if mismatch else 'not_qualified' if gaps or base['status']!='compatible_within_declared_scope' else 'matched_selected_observables'
    return {'format':'opentools.replay-qualification.v1','status':status,'compatibility':base,
            'input_sha256':{**base['input_sha256'],'control':fingerprint(control),'restored':fingerprint(restored)},
            'horizon':h,'selected_observables':profile['observables'],
            'runs':{'control':control['run_ref'],'restored':restored['run_ref']},
            'differences':mismatch,'unknowns':list(dict.fromkeys(base['unknowns']+gaps)),
            'limits':'Selected captured-boundary and every declared step/observable only; matching is not universal state equivalence, verification acceptance or qualification for other inputs/horizons.'}


def exit_code(report):
    return {'compatible_within_declared_scope':0,'matched_selected_observables':0,'incompatible':1,
            'unavailable_checkpoint':1,'diverged':1,'unknown_compatibility':2,'not_qualified':2}[report['status']]


def markdown(report):
    return '# Checkpoint replay review\n\nStatus: '+report['status']+'\n\n```json\n'+json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n```\n'
