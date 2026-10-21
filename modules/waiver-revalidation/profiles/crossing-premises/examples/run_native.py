#!/usr/bin/env python3
"""Exercise premise changes using a synthetic population and actual RTL journal."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PROFILE=Path(__file__).resolve().parents[1]
MODULE=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(PROFILE));sys.path.insert(0,str(MODULE))
from crossing_capture import capture
from waiver_core import compare,require
from create_example import CASES,journal_for,policy,population_for,save


def run(output,verilator,verilator_root):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    for name in ('crossing_path.sv','exception.txt'):shutil.copyfile(Path(__file__).parent/name,output/name)
    source=output/'crossing_path.sv';source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    native_version=subprocess.run([verilator,'--version'],check=True,capture_output=True,text=True).stdout.strip()
    require(native_version.startswith('Verilator 5.020'),'This recipe is qualified with Verilator 5.020')
    with tempfile.TemporaryDirectory(prefix='opentools-crossing-') as temporary:
        scratch=Path(temporary);runtime=scratch/'runtime';runtime.symlink_to(Path(verilator_root).resolve(),target_is_directory=True)
        env=os.environ.copy();env['VERILATOR_ROOT']=str(runtime);shutil.copyfile(source,scratch/source.name)
        command=[verilator,'--binary','--timing','-Wno-fatal','--top-module','crossing_top','--Mdir',str(scratch/'obj'),str(scratch/source.name)]
        save(output/'build.command.json',command)
        build=subprocess.run(command,cwd=scratch,env=env,capture_output=True,text=True,timeout=180)
        (output/'build.stdout.txt').write_text(build.stdout,encoding='utf-8');(output/'build.stderr.txt').write_text(build.stderr,encoding='utf-8')
        require(build.returncode==0,'Native build failed; inspect diagnostics')
        binary=scratch/'obj/Vcrossing_top';shutil.copy2(binary,output/'Vcrossing_top')
        observed=subprocess.run([str(binary)],cwd=scratch,env=env,capture_output=True,text=True,timeout=20)
        (output/'native.stdout.txt').write_text(observed.stdout,encoding='utf-8');(output/'native.stderr.txt').write_text(observed.stderr,encoding='utf-8')
        require(observed.returncode==0,'Native simulation failed')
    require(hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,'Retained source changed during native execution')
    rows={i:[] for i in range(4)};configurations={}
    for number,line in enumerate(observed.stdout.splitlines(),1):
        if line.startswith('CONFIG '):
            index,live,early=[int(v) for v in line.split()[1:]];require(index not in configurations,'Duplicate native configuration');configurations[index]=[live,early]
        elif line.startswith('CROSSING '):
            values=[int(v) for v in line.split()[1:]];require(len(values)==10 and values[0] in rows,'Invalid native columns');rows[values[0]].append((number,values[1:]))
    snapshots={};summary=[]
    for index,case in enumerate(CASES):
        require(configurations.get(index)==[int(index==1),int(index==3)],'Native profile identity differs')
        require(len(rows[index])==8,'Missing native events')
        population=population_for(case);population['native_journal_source_sha256']=source_hash
        require(population['waivers'][0]['definition_sha256']==hashlib.sha256((output/'exception.txt').read_bytes()).hexdigest(),'Retained exception definition differs from population')
        events=[];destination_value=0
        for expected_seq,(line_number,values) in enumerate(rows[index]):
            seq,time_tick,value,window,reset,active,ready,sampled,destination=values
            require(seq==expected_seq,'Native event sequence differs')
            expected_value=7 if index==1 and seq>=5 else 3
            expected_active=int(seq>=3 or index==3 and seq>=1)
            require([value,window,reset,active,ready,sampled]==[expected_value,int(3<=seq<=6),int(seq==0),expected_active,int(seq>=2),int(seq in (4,6))],'Native controls/state contradict independent event schedule')
            # Independent receiver schedule: destination state changes on its
            # actual sampled edges, not when a premise evaluator sees an update.
            if seq in (4,6):destination_value=expected_value
            require(destination==destination_value,'Native destination sample mismatch')
            events.append({'seq':seq,'time_tick':time_tick,'source_value':value,'window':bool(window),'source_reset':bool(reset),
                'destination_active':bool(active),'source_ready':bool(ready),'destination_sample':bool(sampled),'destination_value':destination,'evidence_ref':'native.stdout.txt:'+str(line_number)})
        journal=journal_for(population,events);snapshot=capture(population,journal);snapshots[case]=snapshot
        folder=output/case;folder.mkdir()
        for name,record in (('population',population),('journal',journal),('snapshot',snapshot)):save(folder/(name+'.json'),record)
    expected_status=['unchanged_within_scope','review_required','unchanged_within_scope','review_required']
    for index,case in enumerate(CASES):
        report=compare(snapshots['stable'],snapshots[case],policy())
        require(report['status']==expected_status[index],'Unexpected waiver revalidation disposition')
        save(output/case/'report.json',report)
        evidence=snapshots[case]['crossing_premise_capture']
        summary.append({'case':case,'status':report['status'],'stable_in_window':evidence['stable_in_window'],'source_ready_before_destination':evidence['source_ready_before_destination']})
    save(output/'policy.json',policy())
    result={'verilator':native_version,'structural_population':'Explicitly synthetic selected crossing; not native CDC/RDC analysis','source_sha256':source_hash,
        'cases':summary,'independent_reference':'Controlled source/destination clock/update/reset schedule and actual receiver samples; 32 native events.'}
    save(output/'summary.json',result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--verilator',required=True);parser.add_argument('--verilator-root',required=True);args=parser.parse_args()
    print(run(args.directory,args.verilator,args.verilator_root))


if __name__=='__main__':main()
