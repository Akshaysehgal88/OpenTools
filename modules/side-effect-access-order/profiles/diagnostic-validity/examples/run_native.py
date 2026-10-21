#!/usr/bin/env python3
"""Execute owned recovery/capture controls and compare each state/action field."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PROFILE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROFILE))
from diagnostic_core import exit_code,require,review
from create_example import normalize,save
from reference_model import CASES,FIELDS,config,trace

def run(output,verilator,verilator_root):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False);source=PROFILE/'examples/diagnostic_path.sv'
    shutil.copyfile(source,output/'diagnostic_path.sv')
    version=subprocess.run([verilator,'--version'],capture_output=True,text=True,check=True).stdout.strip()
    require(version.startswith('Verilator 5.020'),'Native recipe qualified with Verilator5.020')
    with tempfile.TemporaryDirectory(prefix='opentools-diagnostic-') as temporary:
        scratch=Path(temporary);runtime=scratch/'runtime';runtime.symlink_to(Path(verilator_root).resolve(),target_is_directory=True)
        env=dict(os.environ,VERILATOR_ROOT=str(runtime));shutil.copyfile(source,scratch/source.name)
        command=[verilator,'--binary','--timing','-Wno-fatal','--top-module','diagnostic_top','--Mdir',str(scratch/'obj'),str(scratch/source.name)]
        save(output/'build.command.json',command);built=subprocess.run(command,cwd=scratch,env=env,capture_output=True,text=True,timeout=180)
        (output/'build.stdout.txt').write_text(built.stdout,encoding='utf-8');(output/'build.stderr.txt').write_text(built.stderr,encoding='utf-8')
        require(built.returncode==0,'Native build failed; inspect retained diagnostics')
        executable=scratch/'obj/Vdiagnostic_top';shutil.copy2(executable,output/executable.name)
        executed=subprocess.run([str(executable)],cwd=scratch,env=env,capture_output=True,text=True,timeout=20)
        (output/'native.stdout.txt').write_text(executed.stdout,encoding='utf-8');(output/'native.stderr.txt').write_text(executed.stderr,encoding='utf-8')
        require(executed.returncode==0,'Native simulation failed')
    groups={case:[] for case in CASES};configs={}
    for line_number,line in enumerate(executed.stdout.splitlines(),1):
        if line.startswith('CONFIG '):
            case,*values=map(int,line.split()[1:]);configs[case]=values
        if not line.startswith('DIAG '):continue
        values=list(map(int,line.split()[1:]));require(len(values)==4+len(FIELDS),'Unexpected native columns')
        scenario,seq,tick,command,*fields=values;require(0<=scenario<len(CASES),'Unknown native case')
        groups[CASES[scenario]].append(dict(seq=seq,time_tick=tick,command=command,evidence_ref='native.stdout.txt:'+str(line_number),**dict(zip(FIELDS,fields))))
    summary=[]
    for index,case in enumerate(CASES):
        cfg=config(case);require(configs[index]==[int(cfg[k]) for k in ('cause_mask','read_clears','status_reset_clears','saved_reset_clears')],'Native configuration differs from reference')
        rows=groups[case];reference=trace(case)
        require(len(rows)==len(reference) and all(all(row[k]==v for k,v in expected.items()) for row,expected in zip(rows,reference)),'Native fields differ from independent cause-set/receipt ledger: '+case)
        values=normalize(case,rows,True);report=review(*values)
        code=2 if case=='post-reset-undetermined' else 0 if case in ('pre-reset-snapshot','no-fault-control','engine-retains-status','engine-fault-free') else 1
        require(exit_code(report)==code,'Unexpected diagnostic disposition: '+case)
        folder=output/case;folder.mkdir();save(folder/'raw.json',rows)
        for key,value in zip(('spec','journal','policy'),values):save(folder/(key+'.json'),value)
        save(folder/'report.json',report)
        summary.append({'case':case,'rows':len(rows),'status':report['status'],'selected_cause_bit_set':report['selected_cause_bit_set'],
            'evidence_answer':report['evidence_answer'],'negative_through_seq':report['negative_through_seq'],'findings':report['findings'],'gaps':report['gaps']})
    result={'Verilator':version,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'cases':summary,
        'reference':'Independent cause-ID sets, read-response receipts and saved-record history; every native action/state field compared.',
        'oracle_boundary':'Fault injection is test-oracle knowledge. It is not silently admitted as a selected consumer diagnostic observation.'}
    save(output/'summary.json',result);return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--verilator',required=True);parser.add_argument('--verilator-root',required=True);args=parser.parse_args()
    print(json.dumps(run(args.directory,args.verilator,args.verilator_root),indent=2))

if __name__=='__main__':main()
