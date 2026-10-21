"""Read original owned emulated-device observations without executing them."""
import re
from pathlib import Path
from bringup_common import HERE,MODEL,SELECTION,context,diagnostic_review,digest,file,folder,qualified_compiler,read_json,require,sha
SOURCES=('device.cpp','device.cfg','firmware.txt')
ARTIFACTS=('device','native.stdout.txt','native.stderr.txt')
ROW_FIELDS=('tick','host_ns','op','status','epoch','saved','saved_epoch','saved_valid','rd','rd_epoch','rd_valid','accepted','error','available')
META={'revision','fuse','clock_id','clock_ns','warm_clears','read_clears','board_power'}

def program(p):
    rows=[]
    for line in p.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):continue
        v=line.split();require(len(v)==2 and v[0].isdigit() and v[1] in ('POR','WARM','FAULT','READ','MONITOR','SAVE','RECORD'),'Unsupported command image')
        tick=int(v[0]);require((not rows or tick>rows[-1][0]) and 1<=tick<=8,'Monotonic bounded image required');rows.append((tick,v[1]))
    require(rows and rows[0][1] in ('POR','WARM'),'Explicit entry reset required');return rows

def native(p):
    require(p.stat().st_size<1024*1024,'Native observation export too large');lines=p.read_text(encoding='utf-8').splitlines()
    require(lines and lines[0]=='HEADER '+MODEL and lines[-1]=='OPENTOOLS_BRINGUP_RUN_COMPLETE','Incomplete/unsupported observation export');meta={};anchors=[];rows=[]
    for line in lines[1:-1]:
        v=line.split();require(v,'Empty native record');tag=v[0];v=v[1:]
        if tag=='META':
            require(len(v)==2 and v[0] in META and v[0] not in meta,'Unexpected native property');meta[v[0]]=v[1] if v[0] in ('revision','clock_id') else int(v[1])
        elif tag=='ANCHOR':require(len(v)==2,'Invalid clock anchor');anchors.append(list(map(int,v)))
        elif tag=='ROW':
            require(len(v)==len(ROW_FIELDS),'Invalid native response');row={k:(x if k=='op' else int(x)) for k,x in zip(ROW_FIELDS,v)};require(not rows or row['tick']>rows[-1]['tick'],'Unordered native observations');rows.append(row)
        else:raise ValueError('Unknown native record')
    require(set(meta)==META and len(anchors)==2 and anchors[0][0]<anchors[1][0] and anchors[0][1]<anchors[1][1] and rows and rows[0]['op']=='INIT' and rows[0]['tick']==0,'Incomplete model/clock/initial observation')
    require(all(meta[k] in (0,1) for k in ('warm_clears','read_clears','board_power')) and 1<=meta['clock_ns']<=1000000 and 0<=meta['fuse']<=255,'Invalid native model properties')
    for row in rows:
        require(all(row[k] in (0,1) for k in ('status','saved','saved_valid','rd','rd_valid','accepted','error','available')) and 0<=row['epoch']<=32 and 0<=row['rd_epoch']<=32 and 0<=row['saved_epoch']<=32 and 0<=row['tick']<=8,'Native state outside first scope')
        require(row['host_ns']==anchors[0][1]+(row['tick']-anchors[0][0])*meta['clock_ns'],'Native time/counter observations disagree')
    require(anchors[1][1]-anchors[0][1]==(anchors[1][0]-anchors[0][0])*meta['clock_ns'],'Native clock anchors disagree')
    return {'meta':meta,'anchors':anchors,'rows':rows,'record_count':len(lines)}

def diagnostic(c,n,source_revision):
    raw=n['rows'];m=n['meta'];initial=raw[1];resets=[r for r in raw[2:] if r['op'] in ('POR','WARM')]
    require(resets and all(r['op']==c['recovery_kind'] for r in resets),'One explicit post-entry recovery class required')
    clear=c['recovery_kind']=='POR' or bool(m['warm_clears']);scope={'project':c['project_ref'],'configuration':c['configuration_ref'],'recovery_ref':c['recovery_kind'],'mode':c['mode_ref']}
    base={'scope':scope,'basis_ref':MODEL,'inputs_complete':True};ref=c['run_ref']+'/native.stdout.txt'
    spec=dict(base,format='opentools.diagnostic.spec.v1',source_revision_ref=source_revision,
       status={'id':'fault','width':1,'latch_kind':'sticky-cause','onread':'clear' if m['read_clears'] else 'none','reset_effect':'clear' if clear else 'retain','evidence_ref':ref+'#native-model'},
       record={'id':'host-retained-receipt','reset_effect':'retain','evidence_ref':ref+'#host-capture'})
    events=[];last_read=None
    for row in raw[2:]:
        op=row['op'];tick=row['tick'];e={'id':'event-'+str(tick),'seq':tick,'evidence_ref':ref+'#tick='+str(tick)}
        if op in ('READ','MONITOR','RECORD'):
            e.update(kind='read',source='record' if op=='RECORD' else 'status',actor_ref='monitor' if op=='MONITOR' else 'firmware',data=row['rd'],epoch=row['rd_epoch'],accepted=bool(row['accepted']),error=bool(row['error']),available=bool(row['available']),hardware_quiet=True)
            if op=='RECORD':e['record_valid']=bool(row['saved_valid'])
            last_read=e['id'] if row['rd_valid'] else None
        elif op=='SAVE':e.update(kind='save',actor_ref='firmware',accepted=bool(row['accepted']),source_read_ref=last_read,record={'value':row['saved'],'valid':bool(row['saved_valid']),'epoch':row['saved_epoch']})
        elif op in ('POR','WARM'):e.update(kind='recovery',observed=True,epoch_after=row['epoch'])
        else:continue
        events.append(e)
    journal=dict(base,format='opentools.diagnostic.journal.v1',spec_sha256=digest(spec),source_kind='owned-native-cpp-emulation',method_ref=MODEL,coverage_scope_ref='bounded-monotonic-model-program',history_complete=c['history_complete'],source_latching_complete=c['latching_complete'],initial_status=initial['status'],initial_epoch=initial['epoch'],initial_available=bool(initial['available']),initial_record={'value':initial['saved'],'valid':bool(initial['saved_valid']),'epoch':initial['saved_epoch']},events=events)
    s=c['selection'];policy=dict(base,format='opentools.diagnostic.policy.v1',spec_sha256=digest(spec),journal_sha256=digest(journal),source_revision_ref=source_revision,requirements_ref='original-captured-selection',fault_mask=s['fault_mask'],target_epoch=s['target_epoch'],required_through_seq=s['required_through_tick'],consumer_ref='firmware',allowed_capture_actors=['firmware'],selected_read_ref='event-'+str(s['selected_read_tick']),claim='undetermined')
    return {'spec':spec,'journal':journal,'policy':policy,'report':diagnostic_review(spec,journal,policy)}

def capture(root,c):
    context(c);names=(*SOURCES,*ARTIFACTS,'context.json','command.json','execution.json','capture-question.json','compiler-version.txt')
    paths={name:file(root,name) for name in names};hashes={name:sha(p) for name,p in paths.items()};x=read_json(paths['execution.json']);command=read_json(paths['command.json'])
    require(x.get('format')=='opentools.bringup-execution.v1' and x['native_exit']==0,'Native observation execution incomplete')
    require(command==['./device','device.cfg','firmware.txt'] and hashes['command.json']==x['command_sha256'],'Original observation invocation differs')
    require(qualified_compiler(paths['compiler-version.txt'].read_text()),'Native example qualified with GCC13.3.0')
    for name in SOURCES:require(hashes[name]==x['source_sha256'][name],'Consumed source changed: '+name)
    for name in ARTIFACTS:require(hashes[name]==x['artifacts'][name],'Original native artifact changed: '+name)
    require(hashes['device']==x['binary_sha256'],'Native binary identity disagrees with execution')
    require(hashes['device.cpp']==sha(HERE/'examples/device.cpp') and sha(HERE.parent/'diagnostic-validity/diagnostic_core.py')==x['diagnostic_core_sha256'],'Unqualified producer/diagnostic engine')
    require(hashes['context.json']==x['context_sha256'] and read_json(paths['context.json'])==c and hashes['capture-question.json']==x['question_sha256'],'Original scope/selection/question changed')
    n=native(paths['native.stdout.txt']);require([(r['tick'],r['op']) for r in n['rows'][1:]]==program(paths['firmware.txt']),'Native responses do not match the consumed command image')
    config_values={};parts=paths['device.cfg'].read_text().split();require(len(parts)==14,'Invalid consumed device configuration')
    for k,v in zip(parts[::2],parts[1::2]):require(k in META and k not in config_values,'Invalid consumed property');config_values[k]=v if k in ('revision','clock_id') else int(v)
    require(config_values==n['meta'],'Native model readout differs from consumed configuration')
    d=diagnostic(c,n,'sha256:'+digest(x['source_sha256']));require(all(sha(p)==hashes[name] for name,p in paths.items()),'Original observation evidence changed during read')
    return {'format':'opentools.bringup-evidence.v1','context':c,'native':n,'diagnostic':d,'source_sha256':x['source_sha256'],'file_sha256':hashes,'execution':x,'command':command,'capture_question':read_json(paths['capture-question.json'])}

def load(root,ref):
    p=folder(root,ref);c=read_json(file(p,'context.json'));context(c);require(c['run_ref']==ref,'Run/producer identity differs');return capture(p,c)

def conditions(e):
    n=e['native'];m=n['meta'];c=e['context'];ref=c['run_ref']+'/native.stdout.txt';fact=lambda v,source=ref:{'value':v,'evidence_ref':source}
    return {'source.kind':fact(MODEL),'source.model_sha256':fact(e['source_sha256']['device.cpp'],c['run_ref']+'/device.cpp'),
       'silicon.revision':fact(m['revision']),'silicon.fuses':fact(m['fuse']),'firmware.image_sha256':fact(e['source_sha256']['firmware.txt'],c['run_ref']+'/firmware.txt'),
       'board.power_on':fact(bool(m['board_power'])),'clock.identity':fact(m['clock_id']),'clock.period_ns':fact(m['clock_ns']),
       'reset.entry':fact(n['rows'][1]['op']),'reset.recovery':fact(c['recovery_kind']),
       'diagnostic.effects':fact({'read_clear':bool(m['read_clears']),'recovery_status_clear':e['diagnostic']['spec']['status']['reset_effect']=='clear','capture_retention':'host'})}
