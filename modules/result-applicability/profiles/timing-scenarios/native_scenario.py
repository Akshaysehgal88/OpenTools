"""Pinned saved native scenario intake; no archived scripts are executed."""
import json,re
from pathlib import Path
from scenario_common import PROFILE,VERSION,config,digest,file,folder,number,read_json,require,sha
HERE=Path(__file__).resolve().parent
SOURCES=('design.v','cells.lef','cells.lib','config.tcl','loader.tcl','export_scenario.tcl')
ARTIFACTS=('native.jsonl','native.odb','consumed.sdc')

def pvt(values):
    require(len(values)==3,'Native PVT tuple incomplete');raw=[number(float(v)) for v in values]
    return {'raw':raw,'normalized':dict(zip(('process','voltage_V','temperature_C'),(round(v,6) for v in raw)))}

def read_native(path,log):
    require(path.stat().st_size<16*1024*1024,'Native export too large')
    rows=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    require(rows and all(isinstance(r,list) and r and all(isinstance(x,str) for x in r) for r in rows),'Invalid native JSONL')
    require(len(rows[0])==3 and rows[0][:2]==['HEADER','opentools.sta-scenario-native.v1'] and rows[-1]==['END'],'Incomplete native export')
    n={'run_ref':rows[0][2],'operating':{},'cases':{},'clocks':{},'clock_pins':[],'data_pins':[],'output_pins':[],'paths':[],'record_count':len(rows)}
    for tag,*v in rows[1:-1]:
        if tag=='LIBRARY':require(len(v)==4 and 'library' not in n,'Duplicate/malformed library');n['library']={'name':v[0],**pvt(v[1:])}
        elif tag=='OPERATING':
            require(len(v)==5 and v[0] in ('min','max') and v[0] not in n['operating'] and v[-1] in ('0','1'),'Malformed effective operating condition');n['operating'][v[0]]={**pvt(v[1:4]),'matches_library_default':int(v[-1])}
        elif tag=='CASE':require(len(v)==2 and v[0] not in n['cases'] and v[1] in ('0','1','X'),'Malformed/duplicate case');n['cases'][v[0]]=int(v[1]) if v[1] in ('0','1') else None
        elif tag=='CLOCK':
            require(len(v)==3 and v[0] not in n['clocks'] and v[2] in ('0','1'),'Malformed clock');n['clocks'][v[0]]={'period_ns':number(float(v[1])),'propagated':int(v[2]),'sources':[],'pins':[]}
        elif tag in ('SOURCE','COVERAGE'):
            require(len(v)==2 and v[0] in n['clocks'],'Unknown clock association');key='sources' if tag=='SOURCE' else 'pins';require(v[1] not in n['clocks'][v[0]][key],'Duplicate clock association');n['clocks'][v[0]][key].append(v[1])
        elif tag in ('CLOCK_PIN','DATA_PIN','OUTPUT_PIN'):
            key={'CLOCK_PIN':'clock_pins','DATA_PIN':'data_pins','OUTPUT_PIN':'output_pins'}[tag];require(len(v)==1 and v[0] not in n[key],'Duplicate native register pin');n[key].append(v[0])
        elif tag=='PATH_COUNT':require(len(v)==1 and v[0].isdigit() and 'path_count' not in n,'Malformed path count');n['path_count']=int(v[0])
        elif tag=='PATH':require(len(v)==3,'Malformed native path');n['paths'].append({'startpoint':v[0],'endpoint':v[1],'slack_native_ns':number(float(v[2]))})
        else:raise ValueError('Unsupported native record: '+tag)
    require('library' in n and set(n['operating'])=={'min','max'} and n.get('path_count')==len(n['paths']) and len(n['clocks'])==1,'Incomplete native scenario inventory')
    for key in ('clock_pins','data_pins','output_pins'):n[key].sort();require(n[key],'Missing register pin census')
    for clock in n['clocks'].values():clock['sources'].sort();clock['pins'].sort();require(set(clock['pins'])<=set(n['clock_pins']),'Clock association outside census')
    require(log.count('OPENTOOLS_SCENARIO_RC_BEGIN')==log.count('OPENTOOLS_SCENARIO_RC_END')==1,'Parasitic report boundary absent/ambiguous')
    rc=log.split('OPENTOOLS_SCENARIO_RC_BEGIN',1)[1].split('OPENTOOLS_SCENARIO_RC_END',1)[0]
    counts=re.findall(r'^Found (\d+) (unannotated|partially unannotated) drivers\.$',rc,re.M)
    require(len(counts)==2 and {kind for _,kind in counts}=={'unannotated','partially unannotated'},'Unsupported native parasitic report')
    n['parasitics']={kind:int(value) for value,kind in counts};return n

def capture(run_dir,ctx):
    cfg=config(ctx);names=(*SOURCES,*ARTIFACTS,'execution.json','command.json','stdout.txt','stderr.txt','openroad-version.txt','context.json')
    paths={k:file(run_dir,k) for k in names};hashes={k:sha(p) for k,p in paths.items()};x=read_json(paths['execution.json']);command=read_json(paths['command.json'])
    require(x.get('format')=='opentools.sta-scenario-execution.v1' and x['native_exit']==0,'Native execution incomplete')
    require(isinstance(command,list) and len(command)==4 and command[1:]==['-exit','-no_init','loader.tcl'] and hashes['command.json']==x['command_sha256'],'Native invocation binding differs')
    require(paths['openroad-version.txt'].read_text().strip()==VERSION,'Unqualified native version')
    for k in SOURCES:require(hashes[k]==x['source_sha256'][k],'Consumed source changed: '+k)
    for k in ARTIFACTS:require(hashes[k]==x['artifacts'][k],'Native artifact changed: '+k)
    for k in ('loader.tcl','export_scenario.tcl'):require(hashes[k]==sha(HERE/k),'Unqualified native producer')
    require(hashes['context.json']==x['context_sha256'] and read_json(paths['context.json'])==ctx and paths['config.tcl'].read_text()==cfg,'Original context/setup changed')
    log=paths['stdout.txt'].read_text();require('OPENTOOLS_STA_SCENARIO_RUN_COMPLETE' in log,'Native completion marker absent');n=read_native(paths['native.jsonl'],log)
    require(n['run_ref']==ctx['run_ref'] and set(n['cases'])==set(ctx['setup']['cases']),'Native scenario run/case inventory differs')
    require(all(sha(p)==hashes[k] for k,p in paths.items()),'Original changed during capture')
    return {'format':'opentools.sta-scenario-evidence.v1','profile':PROFILE,'context':ctx,'native':n,'source_sha256':{k:hashes[k] for k in SOURCES},'file_sha256':hashes,'execution':x,'command':command}

def load(root,ref):
    p=folder(root,ref);ctx=read_json(file(p,'context.json'));require(ctx['run_ref']==ref,'Run/producer identity differs');return capture(p,ctx)

def fields(e):
    ctx=e['context'];n=e['native'];ref=ctx['run_ref']+'/native.jsonl';s=ctx['scenario'];f=lambda value,source=ref:{'value':value,'evidence_ref':source}
    clock=next(iter(n['clocks'].values()));name=next(iter(n['clocks']));rc=n['parasitics'];view='unannotated' if rc['unannotated']>0 and rc['partially unannotated']==0 else None
    return {'scope.identity':f({k:ctx[k] for k in ('scope_ref','design_ref','configuration_ref')}),
      'implementation.source_sha256':f(e['source_sha256']['design.v'],ctx['run_ref']+'/design.v'),
      'library.source_sha256':f(e['source_sha256']['cells.lib'],ctx['run_ref']+'/cells.lib'),'physical_library.source_sha256':f(e['source_sha256']['cells.lef'],ctx['run_ref']+'/cells.lef'),
      'library.pvt':f({'library':n['library']['name'],'min':n['operating']['min']['normalized'],'max':n['operating']['max']['normalized']}),
      'scenario.mode':f(s['mode'],s['mode_basis_ref']),'scenario.corner':f(s['corner'],s['corner_basis_ref']),'power.state':f(s['power_state'],s['power_basis_ref']),
      'native.cases':f(n['cases']),'clock.definition':f({'name':name,'period_ns':clock['period_ns'],'propagated':clock['propagated'],'sources':clock['sources'],'register_clock_pins':clock['pins']}),
      'rc.view':f(view,ctx['run_ref']+'/stdout.txt#OPENTOOLS_SCENARIO_RC_BEGIN'),'profile':f(PROFILE)}

def snapshot(e):
    ctx=e['context'];ref=ctx['run_ref'];n=e['native'];clock=next(iter(n['clocks'].values()));selected=(ctx['setup']['from_cell'],ctx['setup']['to_cell']);supported=len(n['paths'])==1
    for instance in selected:
        supported=supported and all(len([p for p in n[k] if p.split('/')[0]==instance])==1 for k in ('clock_pins','data_pins','output_pins'))
        supported=supported and len([p for p in clock['pins'] if p.split('/')[0]==instance])==1
    supported=supported and all(c['matches_library_default']==1 for c in n['operating'].values())
    for p in n['paths']:supported=supported and p['startpoint'] in n['output_pins'] and p['endpoint'] in n['data_pins'] and p['startpoint'].split('/')[0]==selected[0] and p['endpoint'].split('/')[0]==selected[1]
    outcome=('fail' if min(p['slack_native_ns'] for p in n['paths'])<0 else 'pass') if supported else 'unknown'
    artifact=ref+'/native.jsonl'
    return {'format':'opentools.result-snapshot.v1','run_ref':ref,'manifest_ref':ref+'/execution.json',
      'execution':{'state':'completed','evidence_ref':ref+'/execution.json','command':e['command'],'executable_ref':e['execution']['tool_sha256'],'dependency_capture_complete':True,'dependency_evidence_ref':ref+'/execution.json#closed-single-library-producer'},
      'result':{'outcome':outcome,'native_status':'SELECTED_MAX_SETUP_REPRESENTATIVE '+outcome.upper()+'; not complete STA signoff','complete':bool(supported),'producer_run_ref':ref,'evidence_ref':artifact,'artifact':{'path':artifact,'sha256':e['file_sha256']['native.jsonl']}},
      'fields':fields(e),'provenance':{'profile':PROFILE,'limits':'Actual selected maximum-setup representative and effective min/max operating-condition model values. No hold, all-path or physical-power/RC/signoff inference. Supplied mode,corner and power-state roles require original source review.'}}
