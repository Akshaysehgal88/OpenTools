#!/usr/bin/env python3
"""Observe finite resource episodes and compare with exhaustive independent states."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from episode_model import CASES,FIELDS,INITIAL,config,explore,trace,transition
MODULE=Path(__file__).resolve().parents[1]


def require(condition,message):
    if not condition:raise ValueError(message)


def save(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def observe(output,verilator,verilator_root):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    source=output/'resource_episode.sv';shutil.copyfile(MODULE/'examples/resource_episode.sv',source)
    checksum=hashlib.sha256(source.read_bytes()).hexdigest()
    version=subprocess.run([verilator,'--version'],check=True,capture_output=True,text=True).stdout.strip()
    require(version.startswith('Verilator 5.020'),'This recipe is qualified with Verilator 5.020')
    with tempfile.TemporaryDirectory(prefix='opentools-progress-') as temporary:
        scratch=Path(temporary);runtime=scratch/'runtime';runtime.symlink_to(Path(verilator_root).resolve(),target_is_directory=True)
        env=os.environ.copy();env['VERILATOR_ROOT']=str(runtime);shutil.copyfile(source,scratch/source.name)
        command=[verilator,'--binary','--timing','-Wno-fatal','--top-module','episode_top','--Mdir',str(scratch/'obj'),str(scratch/source.name)]
        save(output/'build.command.json',command)
        build=subprocess.run(command,cwd=scratch,env=env,capture_output=True,text=True,timeout=180)
        (output/'build.stdout.txt').write_text(build.stdout,encoding='utf-8');(output/'build.stderr.txt').write_text(build.stderr,encoding='utf-8')
        require(build.returncode==0,'Native build failed; inspect retained diagnostics')
        binary=scratch/'obj/Vepisode_top';shutil.copy2(binary,output/'Vepisode_top')
        result=subprocess.run([str(binary)],cwd=scratch,env=env,capture_output=True,text=True,timeout=30)
        (output/'native.stdout.txt').write_text(result.stdout,encoding='utf-8');(output/'native.stderr.txt').write_text(result.stderr,encoding='utf-8')
        require(result.returncode==0,'Native simulation failed')
    configs={};rows={i:[] for i in range(9)}
    for number,line in enumerate(result.stdout.splitlines(),1):
        if line.startswith('CONFIG '):
            values=[int(v) for v in line.split()[1:]];require(len(values)==3 and values[0] not in configs,'Invalid native configuration');configs[values[0]]=values[1:]
        elif line.startswith('STATE '):
            values=[int(v) for v in line.split()[1:]];require(len(values)==17 and values[0] in rows,'Invalid native state columns')
            index,seq,time,selected,*data=values
            rows[index].append(dict(seq=seq,time_tick=time,selected=selected,evidence_ref='native.stdout.txt:'+str(number),**dict(zip(FIELDS,data))))
    summary=[]
    for index,case in enumerate(CASES):
        cfg=config(case);require(configs.get(index)==list(cfg),'Native configuration differs')
        require(len(rows[index])==13,'Native samples incomplete')
        analysis=explore(cfg);state=INITIAL
        require(bool(analysis['blocked'])==(cfg==(0,False)),'Unexpected exhaustive finite-model result')
        for expected,row in zip(trace(case),rows[index]):
            require(all(row[key]==value for key,value in expected.items()),'Native/oracle state mismatch: '+case+' seq '+str(row['seq']))
            if row['seq']:state=transition(state,cfg,row['selected'])
            require(list(state) in analysis['reachable_states'],'Native state not in independent reachable set')
        folder=output/case;folder.mkdir()
        save(folder/'raw.json',rows[index]);save(folder/'state-search.json',analysis)
        summary.append({'case':case,'native_rows':len(rows[index]),'reachable_states':analysis['states'],
                        'reachable_model_blocking_states':len(analysis['blocked']),
                        'observed_done':[rows[index][-1]['done_a'],rows[index][-1]['done_b']]})
    require(hashlib.sha256(source.read_bytes()).hexdigest()==checksum,'Retained source changed')
    result={'verilator':version,'source_sha256':checksum,'cases':summary,
        'reference':'Independent exhaustive explicit-state search of owned finite model and per-action/flag comparison of 117 native observations. No arbitrary RTL/formal-equivalence or liveness claim.'}
    save(output/'observation.json',result);return result


def run(output,verilator,verilator_root):
    result=observe(output,verilator,verilator_root)
    from create_example import from_native
    result['reviews']=from_native(Path(output))
    save(Path(output)/'summary.json',result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--verilator',required=True);parser.add_argument('--verilator-root',required=True);args=parser.parse_args()
    print(json.dumps(run(args.directory,args.verilator,args.verilator_root),indent=2))


if __name__=='__main__':main()
