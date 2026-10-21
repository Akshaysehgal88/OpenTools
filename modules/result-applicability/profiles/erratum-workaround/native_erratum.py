"""Read bound original model commands,traces and the executed delivery checker."""
from erratum_common import HERE,IDENTITY,MODEL,compiler_ok,context,digest,file,folder,read_json,require,sha
SOURCES=('device.cpp','device.cfg','firmware.txt')
ARTIFACTS=('device','native.stdout.txt','native.stderr.txt')
TRACE=('seq','op','arg','visible','pending','base_ordered','wa_ordered','guard','force_clock','active_ticks','ack','data','check')
META={'revision','feature','fast_mode','guard_need','exception_enabled','power_on','fuse'}
CFG={'revision','feature','fast_mode','guard_need','exception_enabled','power_on','actual_fuse','fuse_readable'}
def image(p):
    rows=[]
    for line in p.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):continue
        v=line.split();require(len(v)==2 and v[0] in ('WRITE','BASE_FENCE','WA_FENCE','WA_GUARD','ISSUE') and v[1].isdigit(),'Unsupported command image');rows.append((v[0],int(v[1])))
    require(2<=len(rows)<=8 and rows[0]==('WRITE',42) and rows[-1]==('ISSUE',0),'One bounded payload/issue sequence required')
    require(sum(op=='ISSUE' for op,_ in rows)==sum(op=='WRITE' for op,_ in rows)==1,'One native delivery required')
    wa_phase=False
    for op,_ in rows:
        if op.startswith('WA_'):wa_phase=True
        if op=='BASE_FENCE':require(not wa_phase,'Baseline fence must precede the workaround phase')
    return rows
def native(p):
    require(p.stat().st_size<1024*1024,'Native export too large');lines=p.read_text(encoding='utf-8').splitlines();require(lines and lines[0]=='HEADER '+MODEL and lines[-1]=='OPENTOOLS_ERRATUM_RUN_COMPLETE','Unsupported/incomplete native execution')
    m={};rows=[];ticks=[];result=None
    for line in lines[1:-1]:
        v=line.split();require(v,'Empty native record');tag=v[0];v=v[1:]
        if tag=='META':require(len(v)==2 and v[0] in META and v[0] not in m,'Invalid model property');m[v[0]]=None if v[0]=='fuse' and v[1]=='X' else int(v[1])
        elif tag=='TRACE':
            require(len(v)==len(TRACE),'Malformed native trace');r={k:(x if k=='op' else int(x)) for k,x in zip(TRACE,v)};require(r['seq']==len(rows)+1,'Truncated/unordered native trace');rows.append(r)
        elif tag=='TICK':require(len(v)==5,'Malformed native clock tick');ticks.append(list(map(int,v)))
        elif tag=='RESULT':
            require(len(v)==5 and result is None,'Malformed/duplicate native result');result=dict(zip(('ack','data','check','interaction_violation','active_ticks'),map(int,v)))
        else:raise ValueError('Unsupported native record')
    require(set(m)==META and rows and result is not None and rows[-1]['op']=='ISSUE','Incomplete model/trace/checker')
    require(m['revision'] in (1,2) and m['fuse'] in (None,0,1) and 1<=m['guard_need']<=4 and all(m[k] in (0,1) for k in ('feature','fast_mode','exception_enabled','power_on')),'Native model outside first scope')
    for r in rows:require(all(r[k] in (0,1) for k in ('base_ordered','wa_ordered','force_clock','ack','check')) and 0<=r['guard']<=4 and 0<=r['active_ticks']<=4 and r['visible'] in (0,42) and r['pending'] in (0,42) and r['data'] in (-1,0,42),'Native trace outside first scope')
    require(all(result[k]==rows[-1][k] for k in ('ack','data','check','active_ticks')) and result['check']==int(bool(result['ack']) and result['data']==42) and result['interaction_violation']==int(bool(m['exception_enabled'] and rows[-1]['force_clock'])),'Native checker/result observations disagree')
    require(len(ticks)==max(rows[-1]['guard'],1),'Incomplete held-launch clock trace');active=0
    for index,(tick,clock,count,ack,visible) in enumerate(ticks):
        require(tick==index and clock==int(bool(rows[-1]['force_clock'] or index==0)) and ack in (0,1) and visible==rows[-1]['visible'],'Native tick/clock observations disagree');active+=clock;require(active==count,'Native active-clock count disagrees')
    require(active==result['active_ticks'] and ticks[-1][3]==result['ack'],'Native pulse/checker observations disagree')
    return {'meta':m,'trace':rows,'ticks':ticks,'result':result,'record_count':len(lines)}
def capture(root,c):
    context(c);names=(*SOURCES,*ARTIFACTS,'context.json','command.json','execution.json','capture-notice.json','capture-request.json','compiler-version.txt');paths={name:file(root,name) for name in names};hashes={name:sha(p) for name,p in paths.items()};x=read_json(paths['execution.json']);command=read_json(paths['command.json'])
    require(x.get('format')=='opentools.erratum-execution.v1' and x['native_exit']==0,'Incomplete native execution')
    require(command==['./device','device.cfg','firmware.txt'] and hashes['command.json']==x['command_sha256'],'Original invocation differs')
    require(compiler_ok(paths['compiler-version.txt'].read_text()),'Qualified compiler version required')
    for name in SOURCES:require(hashes[name]==x['source_sha256'][name],'Consumed source changed: '+name)
    for name in ARTIFACTS:require(hashes[name]==x['artifacts'][name],'Native artifact changed: '+name)
    require(hashes['device']==x['binary_sha256'] and hashes['device.cpp']==sha(HERE/'examples/device.cpp'),'Unqualified producer/binary')
    for name,key in [('context.json','context_sha256'),('capture-notice.json','notice_sha256'),('capture-request.json','request_sha256')]:require(hashes[name]==x[key],'Original captured source changed: '+name)
    require(read_json(paths['context.json'])==c,'Native scope differs');n=native(paths['native.stdout.txt']);require([(v['op'],v['arg']) for v in n['trace']]==image(paths['firmware.txt']),'Trace differs from executed image')
    parts=paths['device.cfg'].read_text().split();require(len(parts)==16,'Invalid original config');cfg={}
    for k,v in zip(parts[::2],parts[1::2]):require(k in CFG and k not in cfg,'Unexpected model property');cfg[k]=int(v)
    observed={k:cfg[k] for k in META-{'fuse'}};observed['fuse']=cfg['actual_fuse'] if cfg['fuse_readable'] else None
    require(observed==n['meta'],'Native property readout differs from model configuration')
    require(all(sha(p)==hashes[name] for name,p in paths.items()),'Original evidence changed during read')
    return {'format':'opentools.erratum-evidence.v1','context':c,'native':n,'source_sha256':x['source_sha256'],'file_sha256':hashes,'execution':x,'command':command,'capture_notice':read_json(paths['capture-notice.json']),'capture_request':read_json(paths['capture-request.json'])}
def load(root,ref):
    p=folder(root,ref);c=read_json(file(p,'context.json'));context(c);require(c['run_ref']==ref,'Run/producer identity differs');return capture(p,c)
def fields(e):
    c=e['context'];n=e['native'];m=n['meta'];last=n['trace'][-1];ref=c['run_ref']+'/native.stdout.txt';fact=lambda v,source=ref:{'value':v,'evidence_ref':source}
    return {'scope.identity':fact({k:c[k] for k in IDENTITY[1:]}),'source.kind':fact(MODEL),'source.model_sha256':fact(e['source_sha256']['device.cpp'],c['run_ref']+'/device.cpp'),'firmware.image_sha256':fact(e['source_sha256']['firmware.txt'],c['run_ref']+'/firmware.txt'),'native.guard_need':fact(m['guard_need']),
      'silicon.revision':fact(m['revision']),'silicon.repair_fuse':fact(None if m['fuse'] is None else bool(m['fuse'])),'path.feature_enabled':fact(bool(m['feature'])),'clock.fast_mode':fact(bool(m['fast_mode'])),'power.on':fact(bool(m['power_on'])),'power.exception_enabled':fact(bool(m['exception_enabled'])),
      'firmware.base_ordered':fact(bool(last['base_ordered'])),'firmware.wa_ordered':fact(bool(last['wa_ordered'])),'workaround.guard_ticks':fact(n['result']['active_ticks']),'workaround.requested_guard_ticks':fact(last['guard']),'workaround.force_clock':fact(bool(last['force_clock']))}
def snapshot(e):
    c=e['context'];ref=c['run_ref'];artifact=ref+'/native.stdout.txt';outcome='pass' if e['native']['result']['check'] else 'fail'
    return {'format':'opentools.result-snapshot.v1','run_ref':ref,'manifest_ref':ref+'/execution.json','execution':{'state':'completed','evidence_ref':ref+'/execution.json','command':e['command'],'executable_ref':e['execution']['binary_sha256'],'dependency_capture_complete':True,'dependency_evidence_ref':ref+'/execution.json#owned-closed-model'},
     'result':{'outcome':outcome,'native_status':'OWNED_SELECTED_DELIVERY_CHECK '+outcome.upper(),'complete':True,'producer_run_ref':ref,'evidence_ref':artifact,'artifact':{'path':artifact,'sha256':e['file_sha256']['native.stdout.txt']}},'fields':fields(e),'provenance':{'profile':MODEL,'limits':'One selected owned model delivery/data check;not erratum discovery,real silicon,firmware ISA,power verification or signoff.'}}
