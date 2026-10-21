"""Read bound native block/top paths, clock edges, loads and mapped graph."""
import json,re
from pathlib import Path
from budget_common import IDENTITY,PROFILE,VERSION,config,digest,file,folder,number,read_json,require,sha
HERE=Path(__file__).resolve().parent
SOURCES=('design.v','cells.lef','cells.lib','config.tcl','loader.tcl','export_budget.tcl')
ARTIFACTS=('native.jsonl','path.txt','bridge-net.txt','sink-net.txt','native.odb','consumed.sdc')
FLOAT=r'[-+]?(?:\d+\.\d+|\d+)'

def report(path):
    s=path.read_text(encoding='utf-8');edges=[];points={}
    for line in s.splitlines():
        m=re.fullmatch(r'\s*('+FLOAT+r')\s+('+FLOAT+r')\s+clock ([A-Za-z_][A-Za-z0-9_]*) \((rise|fall) edge\)',line)
        if m:edges.append({'clock':m[3],'transition':m[4],'time_ns':float(m[2])})
        m=re.fullmatch(r'\s*('+FLOAT+r')\s+('+FLOAT+r')\s+[\^v]\s+(\S+)\s+\([^)]+\)',line)
        if m:points.setdefault(m[3],[]).append(float(m[2]))
    require(len(edges)==2,'Expected one full-clock native path with source/target edge records')
    inputs=re.findall(r'^\s*('+FLOAT+r')\s+('+FLOAT+r')\s+(?:[\^v]\s+)?input external delay\s*$',s,re.M)
    outputs=re.findall(r'^\s*('+FLOAT+r')\s+('+FLOAT+r')\s+output external delay\s*$',s,re.M)
    require(len(inputs)<=1 and len(outputs)<=1,'Multiple external-delay rows outside profile')
    return {'source_edge':edges[0],'target_edge':edges[1],'point_times_ns':points,'input_delay_ns':float(inputs[0][0]) if inputs else None,'output_delay_ns':-float(outputs[0][0]) if outputs else None}

def net_report(path):
    s=path.read_text(encoding='utf-8')
    if not s:return None
    header=re.search(r'^Net (\S+)\s*$',s,re.M);require(header is not None,'Missing native net report')
    out={'name':header[1]}
    for name,label in (('pin_cap_pF','Pin'),('wire_cap_pF','Wire'),('total_cap_pF','Total')):
        matches=re.findall(r'^ '+label+r' capacitance: ('+FLOAT+r')\s*$',s,re.M);require(len(matches)==1,'Unsupported native capacitance range/report');out[name]=float(matches[0])
    for name,label in (('drivers','drivers'),('loads','loads'),('pins','pins')):
        matches=re.findall(r'^ Number of '+label+r': (\d+)\s*$',s,re.M);require(len(matches)==1,'Missing native connectivity count');out[name]=int(matches[0])
    return out

def native(path):
    require(path.stat().st_size<32*1024*1024,'Native export too large');rows=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    require(rows and all(isinstance(r,list) and r and all(isinstance(v,str) for v in r) for r in rows),'Invalid native JSONL')
    require(len(rows[0])==4 and rows[0][:2]==['HEADER','opentools.interface-budget-native.v1'] and rows[-1]==['END'],'Incomplete native budget export')
    n={'run_ref':rows[0][2],'view':rows[0][3],'libraries':[],'pvt':{},'clocks':{},'cases':{},'port_cap':{},'paths':[],'cells':{},'pins':{},'ports':{},'record_count':len(rows)}
    for tag,*v in rows[1:-1]:
        if tag=='LIBRARY':require(len(v)==1 and v[0] not in n['libraries'],'Malformed library');n['libraries'].append(v[0])
        elif tag=='PVT':require(len(v)==4 and v[0] in ('min','max') and v[0] not in n['pvt'],'Malformed PVT');n['pvt'][v[0]]=dict(zip(('process','voltage_V','temperature_C'),[round(number(float(x)),6) for x in v[1:]]))
        elif tag=='CLOCK':require(len(v)==2 and v[0] not in n['clocks'],'Malformed clock');n['clocks'][v[0]]={'period_ns':number(float(v[1])),'sources':[]}
        elif tag=='WAVE':require(len(v)==3 and v[0] in n['clocks'] and 'waveform_ns' not in n['clocks'][v[0]],'Malformed waveform');n['clocks'][v[0]]['waveform_ns']=[number(float(x)) for x in v[1:]]
        elif tag=='SOURCE':require(len(v)==2 and v[0] in n['clocks'] and v[1] not in n['clocks'][v[0]]['sources'],'Malformed clock source');n['clocks'][v[0]]['sources'].append(v[1])
        elif tag=='CASE':require(len(v)==2 and v[0] not in n['cases'] and v[1] in ('0','1','X'),'Malformed case');n['cases'][v[0]]=int(v[1]) if v[1] in ('0','1') else None
        elif tag=='PORT_CAP':require(len(v)==3 and v[0] in ('min','max') and v[0] not in n['port_cap'],'Malformed native port cap');n['port_cap'][v[0]]={'pin_pF':number(float(v[1])),'wire_pF':number(float(v[2]))}
        elif tag=='PATH_COUNT':require(len(v)==1 and v[0].isdigit() and 'path_count' not in n,'Malformed path count');n['path_count']=int(v[0])
        elif tag=='PATH':
            require(len(v)==11 and all(v[k] in ('0','1') for k in (9,10)) and v[8] in ('^','v'),'Malformed native path')
            p=dict(zip(('startpoint','endpoint'),v[:2]));p.update(zip(('slack_ns','arrival_ns','required_ns','margin_ns','target_time_ns','target_phase_ns'),[number(float(x)) for x in v[2:8]]));p.update(target_transition=v[8],output_delay=int(v[9]),check=int(v[10]));n['paths'].append(p)
        elif tag=='CELL':require(len(v)==2 and v[0] not in n['cells'],'Duplicate/malformed cell');n['cells'][v[0]]=v[1]
        elif tag in ('PIN','PORT'):
            require(len(v)==3 and v[1] in ('INPUT','OUTPUT','INOUT') and v[0] not in n['pins' if tag=='PIN' else 'ports'],'Malformed native graph term');n['pins' if tag=='PIN' else 'ports'][v[0]]={'direction':v[1],'net':v[2] or None}
        else:raise ValueError('Unknown native record: '+tag)
    require(len(n['libraries'])==len(n['clocks'])==1 and set(n['pvt'])=={'min','max'} and n.get('path_count')==len(n['paths']) and n['cells'] and n['ports'],'Incomplete native model/path/graph')
    for clock in n['clocks'].values():require('waveform_ns' in clock,'Missing native waveform');clock['sources'].sort()
    return n

def capture(run_dir,ctx):
    cfg=config(ctx);names=(*SOURCES,*ARTIFACTS,'context.json','execution.json','command.json','stdout.txt','stderr.txt','openroad-version.txt')
    paths={name:file(run_dir,name) for name in names};hashes={name:sha(p) for name,p in paths.items()};x=read_json(paths['execution.json']);command=read_json(paths['command.json'])
    require(x.get('format')=='opentools.interface-budget-execution.v1' and x['native_exit']==0,'Native execution incomplete')
    require(isinstance(command,list) and len(command)==4 and command[1:]==['-exit','-no_init','loader.tcl'] and hashes['command.json']==x['command_sha256'],'Native invocation differs')
    require(paths['openroad-version.txt'].read_text().strip()==VERSION,'Unqualified native version')
    for name in SOURCES:require(hashes[name]==x['source_sha256'][name],'Consumed source changed: '+name)
    for name in ARTIFACTS:require(hashes[name]==x['artifacts'][name],'Native artifact changed: '+name)
    for name in ('loader.tcl','export_budget.tcl'):require(hashes[name]==sha(HERE/name),'Unqualified native producer')
    require(hashes['context.json']==x['context_sha256'] and read_json(paths['context.json'])==ctx and paths['config.tcl'].read_text()==cfg,'Original native setup/context differs')
    log=paths['stdout.txt'].read_text();require('OPENTOOLS_INTERFACE_BUDGET_RUN_COMPLETE' in log,'Native completion marker absent')
    require(log.count('OPENTOOLS_BUDGET_UNITS_BEGIN')==log.count('OPENTOOLS_BUDGET_UNITS_END')==1,'Native unit report absent/ambiguous')
    units=log.split('OPENTOOLS_BUDGET_UNITS_BEGIN',1)[1].split('OPENTOOLS_BUDGET_UNITS_END',1)[0];require(re.search(r'^ time 1ns\s*$',units,re.M) and re.search(r'^ capacitance 1pF\s*$',units,re.M),'Qualify explicit ns/pF native units')
    n=native(paths['native.jsonl']);require(n['run_ref']==ctx['run_ref'] and n['view']==ctx['view'] and set(n['cases'])==set(ctx['setup']['cases']),'Native view/case identity differs')
    n['report']=report(paths['path.txt']);n['bridge_net']=net_report(paths['bridge-net.txt']);n['sink_net']=net_report(paths['sink-net.txt'])
    require(len(n['paths'])==1,'Select exactly one scalar native path')
    p=n['paths'][0];require(abs(p['target_time_ns']-n['report']['target_edge']['time_ns'])<.000002,'Native target edge observations disagree')
    require(all(sha(p)==hashes[name] for name,p in paths.items()),'Original evidence changed during capture')
    return {'format':'opentools.interface-budget-evidence.v1','profile':PROFILE,'context':ctx,'native':n,'source_sha256':{name:hashes[name] for name in SOURCES},'file_sha256':hashes,'execution':x,'command':command}

def load(root,ref):
    p=folder(root,ref);ctx=read_json(file(p,'context.json'));config(ctx);require(ctx['run_ref']==ref,'Run/producer identity differs');return capture(p,ctx)

def fields(e):
    c=e['context'];n=e['native'];ref=c['run_ref']+'/native.jsonl';fact=lambda v,source=ref:{'value':v,'evidence_ref':source};clock_name=next(iter(n['clocks']));p=n['paths'][0]
    return {'scope.identity':fact({k:c[k] for k in IDENTITY[1:]}),'implementation.source_sha256':fact(e['source_sha256']['design.v']),
      'library.source_sha256':fact(e['source_sha256']['cells.lib']),'physical_library.source_sha256':fact(e['source_sha256']['cells.lef']),'library.pvt':fact(n['pvt']),
      'clock.definition':fact({'name':clock_name,**n['clocks'][clock_name]}),'native.cases':fact(n['cases']),
      'reference.source':fact(n['report']['source_edge'],c['run_ref']+'/path.txt'),'reference.target':fact(n['report']['target_edge'],c['run_ref']+'/path.txt'),
      'native.input_delay_ns':fact(n['report']['input_delay_ns'],c['run_ref']+'/path.txt'),'native.output_delay_ns':fact(n['report']['output_delay_ns'],c['run_ref']+'/path.txt'),
      'native.output_load':fact(n['port_cap']),'selected.points':fact({'startpoint':p['startpoint'],'endpoint':p['endpoint']}),'profile':fact(PROFILE)}

def snapshot(e):
    c=e['context'];ref=c['run_ref'];p=e['native']['paths'][0];outcome='fail' if p['slack_ns']<0 else 'pass';artifact=ref+'/native.jsonl'
    return {'format':'opentools.result-snapshot.v1','run_ref':ref,'manifest_ref':ref+'/execution.json','execution':{'state':'completed','evidence_ref':ref+'/execution.json','command':e['command'],'executable_ref':e['execution']['tool_sha256'],'dependency_capture_complete':True,'dependency_evidence_ref':ref+'/execution.json#closed-mapped-view'},
      'result':{'outcome':outcome,'native_status':'SELECTED_MAX_SETUP '+outcome.upper()+'; not complete timing/signoff','complete':True,'producer_run_ref':ref,'evidence_ref':artifact,'artifact':{'path':artifact,'sha256':e['file_sha256']['native.jsonl']}},'fields':fields(e),'provenance':{'profile':PROFILE,'limits':'Native selected path, explicit ns/pF, model, clock references and load observations only; no functional equivalence, extracted RC or signoff inference.'}}
