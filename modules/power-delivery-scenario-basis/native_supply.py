"""Data-only native supply, status, voltage and linear-network readers."""
import csv,io,re
from pathlib import Path
from supply_common import BASIS,config,file,known,number,parse,read_json,require,sha,source_csv
HERE=Path(__file__).resolve().parent
SOURCES=('cells.lef','cells.lib','design.def','sources.csv','config.tcl','loader.tcl','export_supply.tcl')
FIXED=('native.jsonl','native.odb','status.jsonl')
OPTIONAL=('voltage.csv','network.sp','connectivity.rpt','errors.rpt')
def lines(path):
    require(path.stat().st_size<64*1024*1024,'Native file exceeds bounded profile');rows=[parse(s) for s in path.read_text(encoding='utf-8').splitlines()]
    require(rows and all(isinstance(r,list) and r and all(isinstance(v,str) for v in r) for r in rows),'Invalid native JSON lines');return rows
def read_native(path):
    rows=lines(path);require(len(rows[0])==4 and rows[0][:2]==['HEADER','opentools.supply-native.v1'] and rows[-1]==['END'],'Incomplete native supply export')
    out={'run_ref':rows[0][2],'net_name':rows[0][3],'iterms':{},'bterms':{},'shapes':[],'vias':[],'point':None,'record_count':len(rows)};seen=set()
    for key,*v in rows[1:-1]:
        if key in ('UNITS','NET','LIBRARY','OPERATING_POINT','NO_OPERATING_POINT'):
            require(key not in seen,'Duplicate native '+key);seen.add(key)
        if key=='UNITS':require(len(v)==1 and int(v[0])>0,'Invalid units');out['units']=int(v[0])
        elif key=='NET':require(len(v)==2,'Invalid native net');out['net']={'name':v[0],'signal_type':v[1]}
        elif key=='ITERM':
            require(len(v)==8 and v[0]+'/'+v[1] not in out['iterms'] and v[5] in ('0','1'),'Invalid/duplicate native terminal')
            out['iterms'][v[0]+'/'+v[1]]={'instance':v[0],'pin':v[1],'signal_type':v[2],'master':v[3],'status':v[4],'position_known':v[5]=='1','xy_dbu':[int(x) for x in v[6:]]}
        elif key=='BTERM':require(len(v)==2 and v[0] not in out['bterms'],'Invalid/duplicate supply port');out['bterms'][v[0]]=v[1]
        elif key=='SHAPE':require(len(v)==5,'Invalid native shape');out['shapes'].append({'layer':v[0],'box_dbu':[int(x) for x in v[1:]]})
        elif key=='VIA':require(len(v)==4,'Invalid native via');out['vias'].append([int(x) for x in v])
        elif key=='LIBRARY':require(len(v)==2,'Invalid selected library');out['library_cell']='/'.join(v)
        elif key=='OPERATING_POINT':require(len(v)==3,'Invalid operating point');out['point']={k:number(float(x),'native point') for k,x in zip(('process','voltage','temperature'),v)}
        elif key=='NO_OPERATING_POINT':require(not v,'Invalid missing-point record')
        else:raise ValueError('Unknown native record')
    require({'UNITS','NET','LIBRARY'}<=seen and (('OPERATING_POINT' in seen)^('NO_OPERATING_POINT' in seen)),'Native supply inventory incomplete')
    require(out['net']['name']==out['net_name'] and out['iterms'] and out['shapes'],'Native net population empty/different')
    out['shapes'].sort(key=lambda s:(s['layer'],s['box_dbu']));out['vias'].sort();return out
def read_status(path,run_ref):
    rows=lines(path);require(rows[0]==['HEADER','opentools.supply-status.v1',run_ref] and rows[-1]==['END'],'Native stage record incomplete');out={}
    for r in rows[1:-1]:require(len(r)==4 and r[0]=='STATUS' and r[1] not in out and r[2] in ('0','1'),'Duplicate/malformed stage');out[r[1]]={'tcl_catch':int(r[2]),'native_result':r[3]}
    require(set(out)=={'connectivity','analysis','spice'},'Native stages incomplete');return out
def read_voltages(path):
    rows=list(csv.DictReader(io.StringIO(path.read_text(encoding='utf-8'))));expected={'Instance','Terminal','Layer','X location','Y location','Voltage'};out={}
    require(rows and set(rows[0])==expected,'Unknown native voltage CSV schema')
    for r in rows:
        key=r['Instance']+'/'+r['Terminal'];require(key not in out,'Duplicate native voltage point')
        out[key]={'layer':r['Layer'],'xy_um':[number(float(r[k]),'native location') for k in ('X location','Y location')],'voltage_V':number(float(r['Voltage']),'native voltage')}
    return out
def read_spice(path):
    require(path.stat().st_size<64*1024*1024,'Network exceeds profile');out={'resistors':{},'sinks':{},'sources':{}};sink_ref=None
    for line in path.read_text(encoding='utf-8').splitlines():
        v=line.split()
        if not v:continue
        if line.startswith('* Sink for '):sink_ref=line[len('* Sink for '):].strip();continue
        if v[0][0] in ('*','.'):continue
        name=v[0];kind=name[0];require(kind in 'RIV','Unknown native circuit element')
        group={'R':'resistors','I':'sinks','V':'sources'}[kind];require(name not in out[group],'Duplicate native circuit element')
        if kind=='R':require(len(v)==4 and v[3].startswith('R='),'Unknown resistor syntax');value=number(float(v[3][2:]),'native resistance');require(value>0,'Nonpositive resistance');out[group][name]={'a':v[1],'b':v[2],'ohm':value}
        else:
            require(len(v)==5 and v[2]=='0' and v[3]=='DC','Only grounded independent DC sources qualified');value=number(float(v[4]),'native source');require(value>=0,'Negative source/current outside profile')
            out[group][name]={'node':v[1],'value':value}
            if kind=='I':require(sink_ref is not None,'Native current-to-terminal correspondence missing');out[group][name]['terminal']=sink_ref;sink_ref=None
    require(all(out[k] for k in out),'Incomplete native linear network');return out
def capture(run_dir,ctx):
    cfg=config(ctx);paths={k:file(run_dir,k) for k in (*SOURCES,*FIXED,'execution.json','command.json','stdout.txt','stderr.txt','openroad-version.txt')};hashes={k:sha(p) for k,p in paths.items()};execution=read_json(paths['execution.json']);gaps=[]
    require(execution.get('format')=='opentools.supply-execution.v1' and execution['native_exit']==0,'Native process incomplete')
    command=read_json(paths['command.json']);require(isinstance(command,list) and len(command)==4 and command[1:]==['-exit','-no_init','loader.tcl'] and hashes['command.json']==execution['command_sha256'],'Native invocation/binding differs')
    require(paths['openroad-version.txt'].read_text().strip()=='v2.0-17598-ga008522d8','Unqualified native version')
    for k in SOURCES:require(hashes[k]==execution['source_sha256'][k],'Consumed source changed: '+k)
    for k in FIXED:require(hashes[k]==execution['artifacts'][k],'Native artifact changed: '+k)
    for k in ('loader.tcl','export_supply.tcl'):require(hashes[k]==sha(HERE/k),'Unqualified native producer')
    require(paths['config.tcl'].read_text()==cfg and paths['sources.csv'].read_text()==source_csv(ctx),'Original source/load setup differs')
    log=paths['stdout.txt'].read_text()+paths['stderr.txt'].read_text();require('OPENTOOLS_SUPPLY_RUN_COMPLETE' in log and 'OPENTOOLS_SUPPLY_EXPORT_COMPLETE' in log,'Native capture incomplete')
    native=read_native(paths['native.jsonl']);statuses=read_status(paths['status.jsonl'],ctx['run_ref']);require(native['run_ref']==ctx['run_ref'] and native['net_name']==ctx['setup']['net'] and native['library_cell']==ctx['setup']['library_cell'],'Native selected scope differs')
    require(native['net']['signal_type']=='POWER','First profile qualifies a selected power supply')
    require({p['instance'] for p in native['iterms'].values()}==set(ctx['setup']['powers_W']) and len(native['iterms'])==len(ctx['setup']['powers_W']),'Explicit one-PG-terminal-per-instance power population required')
    reports={};optional_paths={}
    for k in OPTIONAL:
        p=file(run_dir,k,optional=True);optional_paths[k]=p;actual=sha(p) if p else None;hashes[k]=actual;expected=execution['artifacts'].get(k)
        if expected is not None and actual!=expected:gaps.append({'kind':'original_native_report_missing_or_changed','file':k});reports[k]=None
        elif expected is None:reports[k]=None
        elif k=='voltage.csv' and statuses['analysis']['tcl_catch']==0:reports[k]=read_voltages(p)
        elif k=='network.sp' and statuses['spice']['tcl_catch']==0:reports[k]=read_spice(p)
        else:reports[k]=None
    if statuses['analysis']['tcl_catch']==0:
        match=re.findall(r'^Corner\s*:\s*(\S+)\s*$',log,re.M);require(len(match)==1,'Actual native analysis corner unavailable/ambiguous');actual_corner=match[0]
    else:actual_corner=None
    require(all(sha(p)==hashes[k] for k,p in paths.items()),'Native files changed during capture')
    require(all((sha(p) if p is not None else None)==hashes[k] for k,p in optional_paths.items()),'Native reports changed during capture')
    return {'format':'opentools.supply-evidence.v1','context':ctx,'native':native,'native_status':statuses,'native_corner':actual_corner,
            'reports':reports,'report_gaps':gaps,'source_sha256':{k:hashes[k] for k in SOURCES},'file_sha256':hashes,'execution':execution,'command':command,
            'limits':'Original static network, sources and quantitative report, not electrical acceptance. Byte/scope binding does not authenticate source authority, consumption, freshness, load-model validity or signoff.'}
