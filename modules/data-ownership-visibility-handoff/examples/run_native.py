#!/usr/bin/env python3
"""Observe actual owned cache/backing/consumer paths against a separate image ledger."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from cache_model import CASES,FIELDS,coherent,trace
MODULE=Path(__file__).resolve().parents[1]


def require(condition,message):
    if not condition:raise ValueError(message)


def save(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def observe(output,verilator,verilator_root):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    source=output/'cache_handoff.sv';shutil.copyfile(MODULE/'examples/cache_handoff.sv',source)
    checksum=hashlib.sha256(source.read_bytes()).hexdigest()
    version=subprocess.run([verilator,'--version'],check=True,capture_output=True,text=True).stdout.strip()
    require(version.startswith('Verilator 5.020'),'This recipe is qualified with Verilator 5.020')
    with tempfile.TemporaryDirectory(prefix='opentools-handoff-') as temporary:
        scratch=Path(temporary);runtime=scratch/'runtime';runtime.symlink_to(Path(verilator_root).resolve(),target_is_directory=True)
        env=os.environ.copy();env['VERILATOR_ROOT']=str(runtime);shutil.copyfile(source,scratch/source.name)
        command=[verilator,'--binary','--timing','-Wno-fatal','--top-module','handoff_top','--Mdir',str(scratch/'obj'),str(scratch/source.name)]
        save(output/'build.command.json',command)
        build=subprocess.run(command,cwd=scratch,env=env,capture_output=True,text=True,timeout=180)
        (output/'build.stdout.txt').write_text(build.stdout,encoding='utf-8');(output/'build.stderr.txt').write_text(build.stderr,encoding='utf-8')
        require(build.returncode==0,'Native build failed; inspect diagnostics')
        binary=scratch/'obj/Vhandoff_top';shutil.copy2(binary,output/'Vhandoff_top')
        result=subprocess.run([str(binary)],cwd=scratch,env=env,capture_output=True,text=True,timeout=30)
        (output/'native.stdout.txt').write_text(result.stdout,encoding='utf-8');(output/'native.stderr.txt').write_text(result.stderr,encoding='utf-8')
        require(result.returncode==0,'Native simulation failed')
    configs={};rows={i:[] for i in range(len(CASES))}
    for number,line in enumerate(result.stdout.splitlines(),1):
        if line.startswith('CONFIG '):
            values=[int(v) for v in line.split()[1:]];require(len(values)==2 and values[0] not in configs,'Invalid native configuration');configs[values[0]]=values[1]
        elif line.startswith('HANDOFF '):
            values=[int(v) for v in line.split()[1:]];require(len(values)==30 and values[0] in rows,'Invalid native columns')
            index,seq,time,op,line_index,data,*state=values
            rows[index].append(dict(seq=seq,time_tick=time,op=op,line=line_index,data=data,evidence_ref='native.stdout.txt:'+str(number),**dict(zip(FIELDS,state))))
    cases=[]
    for index,case in enumerate(CASES):
        require(configs.get(index)==int(coherent(case)),'Native coherence configuration differs')
        expected=trace(case);require(len(rows[index])==len(expected),'Native event coverage differs')
        for reference,row in zip(expected,rows[index]):
            require(all(row[k]==v for k,v in reference.items() if k!='event_ref'),'Native image/action mismatch: '+case+' seq '+str(row['seq']))
            row['event_ref']=reference['event_ref']
        reads=[r for r in rows[index] if r['op']==6]
        require(len(reads)==1 and reads[0]['read_valid']==1 and reads[0]['read_control']==1,'Missing actual consumer/control read')
        expected_data=17 if index in (0,3,4,8) else 34 if index==10 else 165
        require(reads[0]['read_data']==expected_data,'Unexpected native read data')
        folder=output/case;folder.mkdir();save(folder/'raw.json',rows[index])
        cases.append({'case':case,'native_rows':len(expected),'payload_coherent':bool(configs[index]),
                      'read_data':reads[0]['read_data'],'read_epoch':reads[0]['read_epoch'],'read_control':bool(reads[0]['read_control'])})
    require(hashlib.sha256(source.read_bytes()).hexdigest()==checksum,'Retained source changed')
    result={'verilator':version,'source_sha256':checksum,'cases':cases,
            'reference':'Independent versioned private/backing images and captured writeback ledger; all native state/action fields and actual consumer reads compared. No production cache/DMA or ISA ordering qualification.'}
    save(output/'observation.json',result);return result


def run(output,verilator,verilator_root):
    result=observe(output,verilator,verilator_root)
    from create_example import from_native
    result['reviews']=from_native(Path(output));save(Path(output)/'summary.json',result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--verilator',required=True);parser.add_argument('--verilator-root',required=True);args=parser.parse_args()
    print(json.dumps(run(args.directory,args.verilator,args.verilator_root),indent=2))


if __name__=='__main__':main()
