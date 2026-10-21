"""Reconstruct a bound native endpoint-pair observation without executing archives."""
import math
from pathlib import Path
from reach_common import PROFILE,VERSION,config,digest,file,parse,read_json,require,sha,token
HERE=Path(__file__).resolve().parent
SOURCES=('design.v','cells.lef','cells.lib','config.tcl','loader.tcl','trace_exception.tcl','export_reach.tcl')
PRODUCERS=SOURCES[4:]
ARTIFACTS=('native.jsonl','native.odb','consumed.sdc')

def read_native(path):
    require(path.stat().st_size<16*1024*1024,'Native export too large')
    rows=[parse(s) for s in path.read_text(encoding='utf-8').splitlines()]
    require(rows and all(isinstance(r,list) and r and all(isinstance(x,str) for x in r) for r in rows),'Invalid native JSONL')
    require(len(rows[0])==3 and rows[0][:2]==['HEADER','opentools.sta-exception-native.v1'] and rows[-1]==['END'],'Incomplete native export')
    n={'run_ref':rows[0][2],'selectors':{},'applications':{},'phases':{p:{'cases':{},'clocks':{},'clock_pins':[],'data_pins':[],'output_pins':[],'pairs':{},'paths':[]} for p in ('before','after')},'record_count':len(rows)}
    for tag,*v in rows[1:-1]:
        if tag=='SELECTOR':
            require(len(v)>1 and v[0] in ('from','to') and v[0] not in n['selectors'] and len(v[1:])==len(set(v[1:])),'Malformed selector')
            for name in v[1:]:token(name)
            n['selectors'][v[0]]=sorted(v[1:])
        elif tag=='TRACE':
            require(len(v)==4 and 'trace' not in n and all(x.isdigit() for x in v),'Malformed trace');n['trace']=dict(zip(('active','ended','constructor_count','application_count'),map(int,v)))
        elif tag=='APPLICATION':
            require(len(v)==4 and v[0].isdigit() and v[0] not in n['applications'] and v[2].isdigit(),'Malformed/duplicate application')
            n['applications'][v[0]]={'min_max':v[1],'through_count':int(v[2]),'comment':v[3],'from':{},'to':{}}
        elif tag in ('EDGE','RESOLVED'):
            require(len(v)>=3 and v[0] in n['applications'] and v[1] in ('from','to'),'Unknown application selector');selector=n['applications'][v[0]][v[1]]
            if tag=='EDGE':
                require(len(v)==4 and 'rf' not in selector,'Duplicate edge');selector.update(rf=v[2],end_rf=v[3])
            else:
                require(v[2] in ('pins','clocks','instances') and v[2] not in selector and len(v[3:])==len(set(v[3:])),'Duplicate resolved selector');selector[v[2]]=sorted(v[3:])
        elif tag in ('CASE','CLOCK','MEMBERSHIP','REGISTER_PIN','DATA_PIN','OUTPUT_PIN','PAIR','PATH'):
            require(v and v[0] in n['phases'],'Unknown native phase');p=n['phases'][v[0]];x=v[1:]
            if tag=='CASE':require(len(x)==2 and x[0] not in p['cases'] and x[1] in ('0','1','X'),'Malformed case');p['cases'][x[0]]=x[1]
            elif tag=='CLOCK':
                require(len(x)==2 and x[0] not in p['clocks'] and math.isfinite(float(x[1])) and float(x[1])>0,'Malformed clock');p['clocks'][x[0]]={'period_ns':float(x[1]),'pins':[]}
            elif tag=='MEMBERSHIP':
                require(len(x)==2 and x[0] in p['clocks'] and x[1] not in p['clocks'][x[0]]['pins'],'Duplicate/unknown clock membership');p['clocks'][x[0]]['pins'].append(x[1])
            elif tag in ('REGISTER_PIN','DATA_PIN','OUTPUT_PIN'):
                key={'REGISTER_PIN':'clock_pins','DATA_PIN':'data_pins','OUTPUT_PIN':'output_pins'}[tag];require(len(x)==1 and x[0] not in p[key],'Duplicate/malformed register pin');p[key].append(x[0])
            elif tag=='PAIR':
                require(len(x)==3 and x[2].isdigit() and 0<=int(x[2])<=16,'Malformed selected pair');key=x[0]+'->'+x[1];require(key not in p['pairs'],'Duplicate pair');p['pairs'][key]=int(x[2])
            else:
                require(len(x)==5 and math.isfinite(float(x[4])),'Malformed native path');p['paths'].append({'from':x[0],'to':x[1],'startpoint':x[2],'endpoint':x[3],'slack_native_ns':x[4]})
        else:raise ValueError('Unknown native record: '+tag)
    require(set(n['selectors'])=={'from','to'} and 'trace' in n,'Missing selectors/trace')
    pairs={a+'->'+b for a in n['selectors']['from'] for b in n['selectors']['to']};require(1<=len(pairs)<=64,'Unsupported selected scope')
    for p in n['phases'].values():
        require(set(p['pairs'])==pairs and p['clocks'] and p['clock_pins'] and p['data_pins'] and p['output_pins'],'Incomplete selected native pair/register inventory')
        require(sum(p['pairs'].values())==len(p['paths']),'Native path count differs')
        for key,count in p['pairs'].items():require(sum(x['from']+'->'+x['to']==key for x in p['paths'])==count,'Per-pair native path count differs')
        for path in p['paths']:require(p['pairs'].get(path['from']+'->'+path['to'],0)>0 and path['startpoint'].split('/')[0]==path['from'] and path['endpoint'].split('/')[0]==path['to'],'Path outside selected pair')
        for k in ('clock_pins','data_pins','output_pins'):p[k].sort()
        for c in p['clocks'].values():c['pins'].sort();require(set(c['pins'])<=set(p['clock_pins']),'Clock membership outside register census')
    require(n['trace']['application_count']==len(n['applications']),'Trace application count differs')
    for a in n['applications'].values():
        for side in ('from','to'):require(set(a[side])=={'rf','end_rf','pins','clocks','instances'},'Incomplete resolved application')
    return n

def capture(run_dir,ctx):
    cfg=config(ctx);names=(*SOURCES,*ARTIFACTS,'execution.json','command.json','stdout.txt','stderr.txt','openroad-version.txt')
    paths={k:file(run_dir,k) for k in names};hashes={k:sha(p) for k,p in paths.items()};x=read_json(paths['execution.json']);command=read_json(paths['command.json'])
    require(x.get('format')=='opentools.sta-exception-execution.v1' and x['native_exit']==0,'Native execution incomplete')
    require(isinstance(command,list) and len(command)==4 and command[1:]==['-exit','-no_init','loader.tcl'] and hashes['command.json']==x['command_sha256'],'Native command binding differs')
    originals=x.get('original_documents')
    require(isinstance(originals,dict) and {'contract.json','context.json','command.json'}<=set(originals) and len(originals)<=32,'Original intent/context bindings required')
    for name,binding in originals.items():
        require(isinstance(name,str) and name.endswith('.json') and isinstance(binding,str) and len(binding)==64,'Invalid original-document binding')
        if name not in paths:paths[name]=file(run_dir,name);hashes[name]=sha(paths[name])
        require(hashes[name]==binding,'Original intent/context changed: '+name)
    require(read_json(paths['context.json'])==ctx and digest(read_json(paths['contract.json']))==x['contract_digest'],'Original context/intent digest differs')
    require(paths['openroad-version.txt'].read_text().strip()==VERSION,'Unqualified native version')
    for k in SOURCES:require(hashes[k]==x['source_sha256'][k],'Consumed source changed: '+k)
    for k in ARTIFACTS:require(hashes[k]==x['artifacts'][k],'Native artifact changed: '+k)
    for k in PRODUCERS:require(hashes[k]==sha(HERE/k),'Unqualified native producer')
    require(paths['config.tcl'].read_text()==cfg,'Original native setup differs')
    require('OPENTOOLS_STA_EXCEPTION_RUN_COMPLETE' in paths['stdout.txt'].read_text(),'Native completion marker absent')
    n=read_native(paths['native.jsonl']);require(n['run_ref']==ctx['run_ref'],'Native run differs')
    for phase in n['phases'].values():require(set(phase['cases'])==set(ctx['setup']['cases']),'Native case inventory differs')
    require(all(sha(p)==hashes[k] for k,p in paths.items()),'Original changed during capture')
    return {'format':'opentools.sta-exception-evidence.v1','profile':PROFILE,'context':ctx,'native':n,'source_sha256':{k:hashes[k] for k in SOURCES},'file_sha256':hashes,'execution':x,'command':command}

def revalidate(e,run_dir):
    require(e.get('format')=='opentools.sta-exception-evidence.v1' and e.get('profile')==PROFILE,'Unsupported evidence')
    require(digest(capture(run_dir,e['context']))==digest(e),'Evidence differs from original native artifacts')
