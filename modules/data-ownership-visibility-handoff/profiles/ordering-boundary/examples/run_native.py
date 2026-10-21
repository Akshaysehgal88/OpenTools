#!/usr/bin/env python3
"""Observe the owned buffered publication path across RAM and MMIO schedules."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from reference_model import CASES,FIELDS,config,covers,enumerate_outcomes,prefix,trace
PROFILE=Path(__file__).resolve().parents[1]


def require(condition,message):
    if not condition:raise ValueError(message)


def save(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def observe(output,verilator,verilator_root):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    source=output/'buffered_publication.sv';shutil.copyfile(PROFILE/'examples/buffered_publication.sv',source)
    checksum=hashlib.sha256(source.read_bytes()).hexdigest()
    version=subprocess.run([verilator,'--version'],check=True,capture_output=True,text=True).stdout.strip()
    require(version.startswith('Verilator 5.020'),'This recipe is qualified with Verilator 5.020')
    with tempfile.TemporaryDirectory(prefix='opentools-ordering-') as temporary:
        scratch=Path(temporary);runtime=scratch/'runtime';runtime.symlink_to(Path(verilator_root).resolve(),target_is_directory=True)
        env=os.environ.copy();env['VERILATOR_ROOT']=str(runtime);shutil.copyfile(source,scratch/source.name)
        command=[verilator,'--binary','--timing','-Wno-fatal','--top-module','ordering_top','--Mdir',str(scratch/'obj'),str(scratch/source.name)]
        save(output/'build.command.json',command)
        build=subprocess.run(command,cwd=scratch,env=env,capture_output=True,text=True,timeout=180)
        (output/'build.stdout.txt').write_text(build.stdout,encoding='utf-8');(output/'build.stderr.txt').write_text(build.stderr,encoding='utf-8')
        require(build.returncode==0,'Native build failed; inspect diagnostics')
        binary=scratch/'obj/Vordering_top';shutil.copy2(binary,output/'Vordering_top')
        result=subprocess.run([str(binary)],cwd=scratch,env=env,capture_output=True,text=True,timeout=30)
        (output/'native.stdout.txt').write_text(result.stdout,encoding='utf-8');(output/'native.stderr.txt').write_text(result.stderr,encoding='utf-8')
        require(result.returncode==0,'Native simulation failed')
    rows={i:{} for i in range(10)};configs={}
    for number,line in enumerate(result.stdout.splitlines(),1):
        if line.startswith('CONFIG '):
            values=[int(v) for v in line.split()[1:]];require(len(values)==5 and values[0] not in configs,'Invalid native config');configs[values[0]]=values[1:]
        elif line.startswith('ORDER '):
            values=[int(v) for v in line.split()[1:]];require(len(values)==18 and values[0] in rows,'Invalid native sample columns')
            case,run,seq,time,command,*state=values
            rows[case].setdefault(run,[]).append(dict(seq=seq,time_tick=time,command=command,evidence_ref='native.stdout.txt:'+str(number),**dict(zip(FIELDS,state))))
    cases=[]
    for index,case in enumerate(CASES):
        cfg=config(case);require(configs.get(index)==[int(cfg[k]) for k in ('flag_io','pred','succ','placement')],'Native config differs')
        expected_runs=1 if index==9 else 6;require(set(rows[index])==set(range(expected_runs)),'Native schedule coverage differs')
        folder=output/case;folder.mkdir();outcomes=set();complete=0;sample_count=0
        for run,samples in rows[index].items():
            expected=trace(case,run);require(len(samples)==len(expected),'Native program prefix/sample population differs')
            require(all(all(sample[k]==v for k,v in reference.items()) for sample,reference in zip(samples,expected)),'Native state/action oracle mismatch: '+case+' run '+str(run))
            final=samples[-1];observed=(final['rflag'],final['rpayload'] if final['rpayload_valid'] else -1);outcomes.add(observed)
            require(final['consumed']==1 and bool(final['flag_guarded'])==covers(case),'Native observation or captured domain guard differs')
            complete+=all(s['step_enabled'] for s in samples[-3:]);sample_count+=len(samples)
            save(folder/('run-'+str(run)+'.json'),samples)
        enumeration=enumerate_outcomes(case);allowed={(o['flag'],-1 if o['payload'] is None else o['payload']) for o in enumeration['outcomes']}
        require(outcomes<=allowed,'Actual owned outcome outside reference enumeration')
        if index!=9:
            require(outcomes==allowed and complete==len(enumeration['linearizations']),'Exhaustive native/reference outcomes or successful schedule population differ')
        else:require(config(case)==config('ram-no-control') and prefix(case)==prefix('ram-no-control') and outcomes=={(1,1)},'Selected favorable control differs')
        save(folder/'enumeration.json',enumeration)
        cases.append({'case':case,'runs':expected_runs,'native_rows':sample_count,'complete_linearizations_observed':complete,'domain_control_covers':covers(case),
            'observed_outcomes':[{'flag':f,'payload':None if p==-1 else p} for f,p in sorted(outcomes)],
            'model_allows_stale':enumeration['bad_witness'] is not None,'observed_stale':(1,0) in outcomes})
    require(hashlib.sha256(source.read_bytes()).hexdigest()==checksum,'Retained source changed')
    result={'verilator':version,'source_sha256':checksum,'cases':cases,
        'reference':'Independent topological enumeration of fixed owned queue/observer events plus complete native state/action ledger; not a new ISA model, hardware observation or RVWMO/atomicity proof.'}
    save(output/'observation.json',result);return result


def run(output,verilator,verilator_root):
    result=observe(output,verilator,verilator_root)
    from create_example import from_native
    result['reviews']=from_native(Path(output));save(Path(output)/'summary.json',result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--verilator',required=True);parser.add_argument('--verilator-root',required=True);args=parser.parse_args()
    print(json.dumps(run(args.directory,args.verilator,args.verilator_root),indent=2))


if __name__=='__main__':main()
