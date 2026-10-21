"""Read original native clock objects and resolved constructor records only."""
from pathlib import Path
from lineage_common import config,file,number,parse,read_json,require,sha
HERE=Path(__file__).resolve().parent
SOURCES=('design.v','cells.lef','cells.lib','config.tcl','loader.tcl','trace_clocks.tcl','export_clocks.tcl')
ARTIFACTS=('native.jsonl','native.odb','consumed.sdc')
def read_native(path):
    require(path.stat().st_size<64*1024*1024,'Native export exceeds profile')
    rows=[parse(s) for s in path.read_text(encoding='utf-8').splitlines()]
    require(rows and all(isinstance(r,list) and r and all(isinstance(v,str) for v in r) for r in rows),'Invalid JSON lines')
    require(len(rows[0])==4 and rows[0][:2]==['HEADER','opentools.sta-lineage-native.v1'] and rows[-1]==['END'],'Incomplete native export')
    out={'run_ref':rows[0][2],'endpoint':rows[0][3],'clocks':{},'generated_events':[],'register_clock_pins':[],'cases':{},'paths':[],'record_count':len(rows)}
    event_ids=set()
    for tag,*v in rows[1:-1]:
        if tag=='TRACE':require(len(v)==4 and 'trace' not in out,'Malformed/duplicate trace header');out['trace']={k:int(x) for k,x in zip(('initialized','active','ended','initial_clocks'),v)}
        elif tag=='GENERATED':
            require(len(v)>=14 and v[0] not in event_ids and all(v[i] in ('0','1') for i in (7,8,9,10)),'Malformed native generated record');event_ids.add(v[0])
            out['generated_events'].append({'index':int(v[0]),'name':v[1],'master':v[2] or None,'reference_source':v[3],
              'divide_by':int(v[4]),'multiply_by':int(v[5]),'duty_cycle':number(float(v[6]),'native duty'),
              'invert':int(v[7]),'combinational':int(v[8]),'add':int(v[9]),'current_object_matches':int(v[10]),
              'native_edges':v[11],'native_shifts':v[12],'targets':sorted(v[13:])})
        elif tag=='CLOCK':
            require(len(v)==5 and v[0] not in out['clocks'] and all(x in ('0','1') for x in v[2:]),'Malformed/duplicate native clock')
            out['clocks'][v[0]]={'period_ns':number(float(v[1]),'native period'),'is_generated':int(v[2]),'is_propagated':int(v[3]),'waveform_valid':int(v[4]),'targets':[],'clock_pins':[]}
        elif tag=='WAVEFORM':
            require(len(v)>=2 and v[0] in out['clocks'] and 'waveform_ns' not in out['clocks'][v[0]],'Malformed native waveform');out['clocks'][v[0]]['waveform_ns']=[number(float(x),'native edge') for x in v[1:]]
        elif tag in ('TARGET','COVERAGE'):
            require(len(v)==2 and v[0] in out['clocks'],'Native clock collection references unknown object');key='targets' if tag=='TARGET' else 'clock_pins';require(v[1] not in out['clocks'][v[0]][key],'Duplicate native clock association');out['clocks'][v[0]][key].append(v[1])
        elif tag=='REGISTER_PIN':require(len(v)==1 and v[0] not in out['register_clock_pins'],'Duplicate/malformed clock-pin census');out['register_clock_pins'].append(v[0])
        elif tag=='CASE':require(len(v)==2 and v[0] not in out['cases'],'Malformed/duplicate case');out['cases'][v[0]]=v[1]
        elif tag=='PATH_COUNT':require(len(v)==1 and 'path_count' not in out,'Malformed/duplicate path count');out['path_count']=int(v[0])
        elif tag=='PATH':require(len(v)==3,'Malformed path');number(float(v[0]),'native slack');out['paths'].append({'slack_native_ns':v[0],'startpoint':v[1],'endpoint':v[2]})
        else:raise ValueError('Unknown native record: '+tag)
    require('trace' in out and out['clocks'] and out['register_clock_pins'] and out.get('path_count')==len(out['paths']),'Incomplete clock/census/path record')
    require(all('waveform_ns' in c for c in out['clocks'].values()),'Native waveform metadata incomplete')
    for c in out['clocks'].values():
        c['targets'].sort();c['clock_pins'].sort();require(set(c['clock_pins'])<=set(out['register_clock_pins']),'Clock association outside native register census')
    out['register_clock_pins'].sort();return out
def capture(run_dir,ctx):
    cfg=config(ctx);names=(*SOURCES,*ARTIFACTS,'execution.json','command.json','stdout.txt','stderr.txt','openroad-version.txt')
    paths={k:file(run_dir,k) for k in names};hashes={k:sha(p) for k,p in paths.items()};execution=read_json(paths['execution.json']);command=read_json(paths['command.json'])
    require(execution.get('format')=='opentools.sta-lineage-execution.v1' and execution['native_exit']==0,'Native execution incomplete')
    require(isinstance(command,list) and len(command)==4 and command[1:]==['-exit','-no_init','loader.tcl'] and hashes['command.json']==execution['command_sha256'],'Native invocation/binding differs')
    require(paths['openroad-version.txt'].read_text().strip()=='v2.0-17598-ga008522d8','Unqualified native version')
    for k in SOURCES:require(hashes[k]==execution['source_sha256'][k],'Consumed source changed: '+k)
    for k in ARTIFACTS:require(hashes[k]==execution['artifacts'][k],'Native artifact changed: '+k)
    for k in ('loader.tcl','trace_clocks.tcl','export_clocks.tcl'):require(hashes[k]==sha(HERE/k),'Unqualified native producer')
    require(paths['config.tcl'].read_text()==cfg,'Native setup differs from original context')
    log=paths['stdout.txt'].read_text()+paths['stderr.txt'].read_text();require('OPENTOOLS_STA_LINEAGE_RUN_COMPLETE' in log and 'OPENTOOLS_STA_LINEAGE_EXPORT_COMPLETE' in log,'Native clock export incomplete')
    n=read_native(paths['native.jsonl']);require(n['run_ref']==ctx['run_ref'] and n['endpoint']==ctx['setup']['endpoint'],'Native selected scope differs')
    require(set(n['cases'])==set(ctx['setup']['cases']),'Native mode-port inventory differs')
    require(all(p['endpoint']==n['endpoint'] for p in n['paths']),'Native selected path differs')
    require(all(sha(p)==hashes[k] for k,p in paths.items()),'Original evidence changed during capture')
    return {'format':'opentools.sta-lineage-evidence.v1','context':ctx,'native':n,'source_sha256':{k:hashes[k] for k in SOURCES},
            'file_sha256':hashes,'execution':execution,'command':command,
            'limits':'Original native clock objects, resolved explicit constructor inputs and endpoint collections. Defined clocks and native constraint waveforms are not functional availability, pulse/glitch, CDC/RDC or timing signoff. References/bytes do not authenticate intent or authority.'}
