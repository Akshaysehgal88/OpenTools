#!/usr/bin/env python3
"""Run owned ownership transfers and compare actual messages/rights with a set ledger."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from reference_model import CASES,FIELDS,guard,trace
PROFILE=Path(__file__).resolve().parents[1]


def require(condition,message):
    if not condition:raise ValueError(message)


def save(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def observe(output,verilator,verilator_root):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    source=output/'ownership_transfer.sv';shutil.copyfile(PROFILE/'examples/ownership_transfer.sv',source)
    checksum=hashlib.sha256(source.read_bytes()).hexdigest()
    version=subprocess.run([verilator,'--version'],check=True,capture_output=True,text=True).stdout.strip()
    require(version.startswith('Verilator 5.020'),'This recipe is qualified with Verilator 5.020')
    with tempfile.TemporaryDirectory(prefix='opentools-transition-') as temporary:
        scratch=Path(temporary);runtime=scratch/'runtime';runtime.symlink_to(Path(verilator_root).resolve(),target_is_directory=True)
        env=os.environ.copy();env['VERILATOR_ROOT']=str(runtime);shutil.copyfile(source,scratch/source.name)
        command=[verilator,'--binary','--timing','-Wno-fatal','--top-module','transition_top','--Mdir',str(scratch/'obj'),str(scratch/source.name)]
        save(output/'build.command.json',command)
        build=subprocess.run(command,cwd=scratch,env=env,capture_output=True,text=True,timeout=180)
        (output/'build.stdout.txt').write_text(build.stdout,encoding='utf-8');(output/'build.stderr.txt').write_text(build.stderr,encoding='utf-8')
        require(build.returncode==0,'Native build failed; inspect diagnostics')
        binary=scratch/'obj/Vtransition_top';shutil.copy2(binary,output/'Vtransition_top')
        result=subprocess.run([str(binary)],cwd=scratch,env=env,capture_output=True,text=True,timeout=30)
        (output/'native.stdout.txt').write_text(result.stdout,encoding='utf-8');(output/'native.stderr.txt').write_text(result.stderr,encoding='utf-8')
        require(result.returncode==0,'Native simulation failed')
    rows={i:[] for i in range(len(CASES))};configs={}
    for number,line in enumerate(result.stdout.splitlines(),1):
        if line.startswith('CONFIG '):
            values=[int(v) for v in line.split()[1:]];require(len(values)==2 and values[0] not in configs,'Invalid native config');configs[values[0]]=values[1]
        elif line.startswith('TRANSFER '):
            values=[int(v) for v in line.split()[1:]];require(len(values)==28 and values[0] in rows,'Invalid native columns')
            index,seq,time,op,source_id,msg_id,msg_epoch,ready,*state=values
            rows[index].append(dict(seq=seq,time_tick=time,op=op,source=source_id,message_id=msg_id,message_epoch=msg_epoch,ready=ready,
                                    evidence_ref='native.stdout.txt:'+str(number),**dict(zip(FIELDS,state))))
    cases=[]
    for index,case in enumerate(CASES):
        require(configs.get(index)==guard(case),'Native guard differs')
        expected=trace(case);require(len(rows[index])==len(expected),'Native event population differs')
        for reference,row in zip(expected,rows[index]):
            require(all(row[k]==v for k,v in reference.items() if k!='event_ref'),'Native state/action ledger mismatch: '+case+' seq '+str(row['seq']))
            row['event_ref']=reference['event_ref']
        folder=output/case;folder.mkdir();save(folder/'raw.json',rows[index])
        grant=next(r for r in rows[index] if r['event_ref']=='grant');old=next(r for r in rows[index] if r['event_ref']=='old-read')
        new=next(r for r in rows[index] if r['event_ref']=='new-read')
        require(grant['grant_accepted']==1 and new['read_valid']==1,'Required grant/read not observed')
        require(bool(old['read_valid'])==(index in (0,3,5)),'Unexpected old-holder access')
        require(new['read_data']==(0 if index==2 else 17),'Unexpected transferred-data read')
        cases.append({'case':case,'native_rows':len(expected),'grant_pending_mask':grant['pending_mask'],'grant_pending_count':grant['pending_count'],
                      'new_read':new['read_data'],'old_read_valid':bool(old['read_valid']),'old_read':old['read_data']})
    require(hashlib.sha256(source.read_bytes()).hexdigest()==checksum,'Retained source changed')
    result={'verilator':version,'source_sha256':checksum,'cases':cases,
        'reference':'Independent set-based holders/obligations and full per-action state comparison. Owned single-resource transfer and two-worker reclaim subset; no full coherence/ring protocol or general liveness proof.'}
    save(output/'observation.json',result);return result


def run(output,verilator,verilator_root):
    result=observe(output,verilator,verilator_root)
    from create_example import from_native
    result['reviews']=from_native(Path(output));save(Path(output)/'summary.json',result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--verilator',required=True);parser.add_argument('--verilator-root',required=True);args=parser.parse_args()
    print(json.dumps(run(args.directory,args.verilator,args.verilator_root),indent=2))


if __name__=='__main__':main()
