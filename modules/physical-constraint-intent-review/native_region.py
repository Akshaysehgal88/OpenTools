"""Read retained native facts without loading OpenROAD or executing source files."""
from pathlib import Path
from physical_common import IDENTITY,box,config,file,integer,number,parse,read_json,require,sha,text
HERE=Path(__file__).resolve().parent
SOURCES=('design.v','cells.lef','cells.lib','loader.tcl','export_region.tcl','config.tcl')
ARTIFACTS=('native.jsonl','native.odb','consumed.sdc')

def read_native(path):
    require(path.stat().st_size<64*1024*1024,'Native export exceeds bounded profile');rows=[parse(s) for s in path.read_text(encoding='utf-8').splitlines()]
    require(len(rows)>=10 and all(isinstance(r,list) and r and all(isinstance(v,str) for v in r) for r in rows),'Invalid native JSON lines')
    require(len(rows[0])==5 and rows[0][:2]==['HEADER','opentools.physical-native.v1'] and rows[-1]==['END'],'Incomplete native export')
    result={'run_ref':rows[0][2],'selected_net':rows[0][3],'endpoint':rows[0][4], 'instances':{},'pins':{},'ports':{},'blockages':[],
            'cases':{},'clock_sources':[],'net_terms':[],'net_bterms':[],'paths':[],'record_count':len(rows)}
    def once(k,value):require(k not in result,'Duplicate native '+k);result[k]=value
    def ints(values):return [integer(int(v),'native coordinate') for v in values]
    for row in rows[1:-1]:
        key,*v=row
        if key=='UNITS':require(len(v)==1 and int(v[0])>0,'Invalid native units');once('units',int(v[0]))
        elif key in ('DIE','CORE','NET_BBOX'):
            require(len(v)==4,'Malformed native box');once(key.lower(),box(ints(v),key,degenerate=key=='NET_BBOX'))
        elif key=='CLOCK':require(len(v)==3,'Malformed native clock');once('clock',{'name':v[0],'period_ns':number(float(v[1]),'native period'),'is_generated':v[2]})
        elif key=='CLOCK_SOURCE':require(len(v)==1 and v[0] not in result['clock_sources'],'Malformed/duplicate clock source');result['clock_sources'].append(v[0])
        elif key=='CASE':require(len(v)==2 and v[0] not in result['cases'],'Malformed/duplicate native case');result['cases'][v[0]]=v[1]
        elif key=='INSTANCE':
            require(len(v)==8 and v[0] not in result['instances'],'Malformed/duplicate native instance')
            result['instances'][v[0]]={'master':v[1],'orientation':v[2],'status':v[3],'box':box(ints(v[4:]),'native instance',degenerate=True)}
        elif key=='PIN':
            require(len(v)==8 and v[0]+'/'+v[1] not in result['pins'] and v[5] in ('0','1'),'Malformed/duplicate native pin')
            result['pins'][v[0]+'/'+v[1]]={'instance':v[0],'pin':v[1],'direction':v[2],'signal_type':v[3],'net':v[4],
                                                'position_known':v[5]=='1','xy':ints(v[6:])}
        elif key=='PORT':require(len(v)==3 and v[0] not in result['ports'],'Malformed/duplicate boundary port');result['ports'][v[0]]={'direction':v[1],'net':v[2]}
        elif key=='BLOCKAGE':require(len(v)==5 and v[4] in ('0','1'),'Malformed native blockage');result['blockages'].append({'box':box(ints(v[:4]),'blockage'),'soft':v[4]=='1'})
        elif key=='NET_TERM':
            require(len(v)==2 and v[0]+'/'+v[1] not in result['net_terms'],'Malformed/duplicate selected endpoint');result['net_terms'].append(v[0]+'/'+v[1])
        elif key=='NET_BTERM':require(len(v)==1 and v[0] not in result['net_bterms'],'Malformed/duplicate selected boundary endpoint');result['net_bterms'].append(v[0])
        elif key=='PATH_COUNT':require(len(v)==1 and int(v[0])>=0,'Malformed native path count');once('path_count',int(v[0]))
        elif key=='PATH':require(len(v)==3,'Malformed native timing path');number(float(v[0]),'native slack');result['paths'].append({'slack_native_ns':v[0],'startpoint':v[1],'endpoint':v[2]})
        elif key=='PLACEMENT_CHECK':require(len(v)==2 and v[0] in ('0','1'),'Malformed native placement result');once('placement_check',{'return_code':int(v[0]),'native_message':v[1]})
        else:raise ValueError('Unsupported native record: '+key)
    require(all(k in result for k in ('units','die','core','net_bbox','clock','path_count','placement_check')) and result['instances'],'Native inventory incomplete')
    require(result['path_count']==len(result['paths']) and all(p['instance'] in result['instances'] for p in result['pins'].values()),'Native path/instance correspondence incomplete')
    require(set(result['net_terms'])=={k for k,p in result['pins'].items() if p['net']==result['selected_net']},'Native selected-net pin population differs')
    require(set(result['net_bterms'])=={k for k,p in result['ports'].items() if p['net']==result['selected_net']},'Native selected-net boundary population differs')
    for k in ('net_terms','net_bterms','clock_sources'):result[k].sort()
    result['blockages'].sort(key=lambda b:(b['box'],b['soft']))
    return result

def capture(run_dir,ctx):
    expected_config=config(ctx);names=(*SOURCES,*ARTIFACTS,'execution.json','native.command.json','native.stdout.txt','native.stderr.txt','openroad-version.txt')
    paths={n:file(run_dir,n) for n in names};hashes={n:sha(p) for n,p in paths.items()};execution=read_json(paths['execution.json']);command=read_json(paths['native.command.json'])
    require(execution.get('format')=='opentools.physical-execution.v1' and execution['native_exit']==0,'Native execution incomplete')
    require(isinstance(command,list) and len(command)==4 and command[1:]==['-exit','-no_init','loader.tcl'],'Unqualified native command')
    require(hashes['native.command.json']==execution['command_sha256'],'Native command binding changed')
    require(paths['openroad-version.txt'].read_text().strip()=='v2.0-17598-ga008522d8','Unqualified native version')
    require(isinstance(execution['tool_sha256'],str) and len(execution['tool_sha256'])==64,'Original tool identity unavailable')
    for n in SOURCES:require(hashes[n]==execution['source_sha256'][n],'Consumed source changed: '+n)
    for n in ARTIFACTS:require(hashes[n]==execution['artifacts'][n],'Native artifact changed: '+n)
    for n in ('loader.tcl','export_region.tcl'):require(hashes[n]==sha(HERE/n),'Unqualified native producer: '+n)
    require(paths['config.tcl'].read_text()==expected_config,'Native setup/selection differs from context')
    log=paths['native.stdout.txt'].read_text()+paths['native.stderr.txt'].read_text();require('OPENTOOLS_PHYSICAL_EXPORT_COMPLETE' in log,'Native export did not complete')
    n=read_native(paths['native.jsonl']);s=ctx['setup']
    require((n['run_ref'],n['selected_net'],n['endpoint'])==(ctx['run_ref'],s['selected_net'],s['endpoint']),'Native selected scope differs')
    require(set(n['instances'])==set(s['placements']),'Native instance population differs from original setup')
    for name,p in s['placements'].items():
        observed=n['instances'][name];require(observed['orientation']==p['orientation'] and observed['status']=='PLACED' and observed['box'][:2]==p['xy_dbu'],'Actual native placement differs from consumed setup')
    for key in ('die','core'):require(n[key]==[v*n['units'] for v in s[key+'_um']],'Native floorplan/units differ from setup')
    require(n['blockages']==sorted([{'box':b,'soft':False} for b in s['blockages']],key=lambda b:(b['box'],b['soft'])),'Native constraints differ from consumed setup')
    require(n['clock']=={'name':s['clock']['name'],'period_ns':float(s['clock']['period_ns']),'is_generated':'0'} and n['clock_sources']==[s['clock']['port']],'Native clock differs from setup')
    require(n['cases']=={k:str(v) for k,v in s['case_values'].items()},'Native operating phase differs from setup')
    require(all(p['endpoint']==s['endpoint'] for p in n['paths']),'Native path selection differs')
    require(all(sha(p)==hashes[k] for k,p in paths.items()),'Native evidence changed during capture')
    return {'format':'opentools.physical-evidence.v1','context':ctx,'native':n,'source_sha256':{k:hashes[k] for k in SOURCES},
            'file_sha256':hashes,'execution':execution,'command':command,'qualified_batch_loader':True,
            'limits':'Original placed database and selected native observations. No interconnect RC model in this batch loader. Byte/label binding does not authenticate execution, source authority, freshness, intent approval or signoff.'}
