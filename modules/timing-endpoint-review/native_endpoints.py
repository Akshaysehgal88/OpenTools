"""Original native census, unconstrained report and PathEnd classifications."""
from pathlib import Path
import re
from endpoint_common import PROFILE,VERSION,config,digest,file,number,parse,read_json,require,sha
HERE=Path(__file__).resolve().parent
SOURCES=('design.v','cells.lef','cells.lib','config.tcl','loader.tcl','export_endpoints.tcl')
ARTIFACTS=('native.jsonl','unconstrained.txt','native.odb','consumed.sdc')

def read_report(path):
    lines=path.read_text(encoding='utf-8').splitlines()
    if not lines:return []
    m=re.fullmatch(r'Warning: There (?:is|are) (\d+) unconstrained endpoints?\.',lines[0]);require(m is not None,'Unsupported unconstrained report')
    names=[]
    for line in lines[1:]:
        require(line.startswith('  ') and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_/]*',line[2:]),'Malformed native endpoint name');names.append(line[2:])
    require(len(names)==int(m[1]) and len(names)==len(set(names)),'Native unconstrained population count differs');return sorted(names)

def native(path,reported):
    require(path.stat().st_size<16*1024*1024,'Native export too large');rows=[parse(line) for line in path.read_text(encoding='utf-8').splitlines()]
    require(rows and all(isinstance(r,list) and r and all(isinstance(v,str) for v in r) for r in rows),'Invalid native JSONL')
    require(len(rows[0])==3 and rows[0][:2]==['HEADER','opentools.sta-endpoint-native.v1'] and rows[-1]==['END'],'Incomplete native endpoint export')
    n={'run_ref':rows[0][2],'clocks':{},'clock_pins':[],'cases':{},'endpoints':{},'reported_unconstrained':reported,'record_count':len(rows)}
    for tag,*v in rows[1:-1]:
        if tag=='CLOCK':
            require(len(v)==3 and v[0] not in n['clocks'] and v[2] in ('0','1'),'Malformed clock');n['clocks'][v[0]]={'period_ns':number(float(v[1])),'propagated':int(v[2]),'sources':[],'pins':[]}
        elif tag in ('SOURCE','COVERAGE'):
            require(len(v)==2 and v[0] in n['clocks'],'Unknown clock association');key='sources' if tag=='SOURCE' else 'pins';require(v[1] not in n['clocks'][v[0]][key],'Duplicate clock association');n['clocks'][v[0]][key].append(v[1])
        elif tag=='CLOCK_PIN':require(len(v)==1 and v[0] not in n['clock_pins'],'Duplicate clock pin');n['clock_pins'].append(v[0])
        elif tag=='CASE':require(len(v)==2 and v[0] not in n['cases'] and v[1] in ('0','1','X'),'Malformed case');n['cases'][v[0]]=int(v[1]) if v[1] in ('0','1') else None
        elif tag=='ENDPOINT':
            require(len(v)==6 and v[0] not in n['endpoints'] and v[1] in ('output','data') and all(x in ('0','1','X','Z') for x in v[2:5]) and v[5].isdigit(),'Malformed/duplicate endpoint census')
            n['endpoints'][v[0]]={'kind':v[1],'logic':v[2],'case':v[3],'simulated':v[4],'path_count':int(v[5]),'paths':[],'reported_unconstrained':v[0] in reported}
        elif tag=='PATH':
            require(len(v)==10 and v[0] in n['endpoints'] and all(x in ('0','1') for x in v[3:6]),'Malformed native path');require(v[2]==v[0],'Path outside selected endpoint')
            if v[6] not in ('INF','-INF'):number(float(v[6]))
            number(float(v[7]));n['endpoints'][v[0]]['paths'].append(dict(zip(('startpoint','endpoint','unconstrained','output_delay','check','slack_native_ns','margin_ns','source_clock','target_clock'),[v[1],v[2],*map(int,v[3:6]),v[6],float(v[7]),v[8] or None,v[9] or None])))
        else:raise ValueError('Unsupported native record: '+tag)
    require(len(n['clocks'])==1 and n['clock_pins'] and n['endpoints'] and set(reported)<=set(n['endpoints']),'Incomplete/foreign native endpoint inventory')
    n['clock_pins'].sort()
    for c in n['clocks'].values():c['sources'].sort();c['pins'].sort();require(set(c['pins'])<=set(n['clock_pins']),'Clock association outside census')
    for name,e in n['endpoints'].items():
        require(e['path_count']==len(e['paths']),'Native path count differs')
        require(not any(p['unconstrained'] for p in e['paths']) or e['reported_unconstrained'],'Path classification contradicts native reported population')
    return n

def capture(run_dir,ctx):
    cfg=config(ctx);names=(*SOURCES,*ARTIFACTS,'context.json','contract.json','execution.json','command.json','stdout.txt','stderr.txt','openroad-version.txt')
    paths={name:file(run_dir,name) for name in names};hashes={name:sha(p) for name,p in paths.items()};x=read_json(paths['execution.json']);command=read_json(paths['command.json'])
    require(x.get('format')=='opentools.sta-endpoint-execution.v1' and x['native_exit']==0,'Native execution incomplete')
    require(isinstance(command,list) and len(command)==4 and command[1:]==['-exit','-no_init','loader.tcl'] and hashes['command.json']==x['command_sha256'],'Native invocation differs')
    require(paths['openroad-version.txt'].read_text().strip()==VERSION,'Unqualified native version')
    for name in SOURCES:require(hashes[name]==x['source_sha256'][name],'Consumed source changed: '+name)
    for name in ARTIFACTS:require(hashes[name]==x['artifacts'][name],'Native artifact changed: '+name)
    for name in ('loader.tcl','export_endpoints.tcl'):require(hashes[name]==sha(HERE/name),'Unqualified native producer')
    require(hashes['context.json']==x['context_sha256'] and read_json(paths['context.json'])==ctx and paths['config.tcl'].read_text()==cfg,'Original context/setup differs')
    require(digest(read_json(paths['contract.json']))==x['contract_digest'],'Original independent contract changed')
    require('OPENTOOLS_STA_ENDPOINT_RUN_COMPLETE' in paths['stdout.txt'].read_text(),'Native export incomplete')
    n=native(paths['native.jsonl'],read_report(paths['unconstrained.txt']));require(n['run_ref']==ctx['run_ref'] and set(n['cases'])==set(ctx['setup']['cases']),'Native run/case inventory differs')
    require(all(sha(p)==hashes[name] for name,p in paths.items()),'Original changed during capture')
    return {'format':'opentools.sta-endpoint-evidence.v1','profile':PROFILE,'context':ctx,'native':n,'source_sha256':{name:hashes[name] for name in SOURCES},'file_sha256':hashes,'execution':x,'command':command}

def revalidate(e,run_dir):require(e.get('format')=='opentools.sta-endpoint-evidence.v1' and e.get('profile')==PROFILE and digest(capture(run_dir,e['context']))==digest(e),'Saved evidence differs from original native artifacts')
