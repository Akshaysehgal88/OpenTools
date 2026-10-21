#!/usr/bin/env python3
"""Observe selective logical state loss and actual post-wake bundle reads."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

MODULE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(MODULE))
from restore_core import exit_code,require,review
from create_example import CASES,RAW_FIELDS,config,inventory_for,journal_for,normalize,policy_for,reference,save


def run(output,verilator,verilator_root):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    source=output/'restore_path.sv';shutil.copyfile(MODULE/'examples/restore_path.sv',source)
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    native_version=subprocess.run([verilator,'--version'],check=True,capture_output=True,text=True).stdout.strip()
    require(native_version.startswith('Verilator 5.020'),'This recipe is qualified with Verilator 5.020')
    with tempfile.TemporaryDirectory(prefix='opentools-restore-') as temporary:
        scratch=Path(temporary);runtime=scratch/'runtime';runtime.symlink_to(Path(verilator_root).resolve(),target_is_directory=True)
        env=os.environ.copy();env['VERILATOR_ROOT']=str(runtime);shutil.copyfile(source,scratch/source.name)
        command=[verilator,'--binary','--timing','-Wno-fatal','--top-module','restore_top','--Mdir',str(scratch/'obj'),str(scratch/source.name)]
        save(output/'build.command.json',command)
        build=subprocess.run(command,cwd=scratch,env=env,capture_output=True,text=True,timeout=180)
        (output/'build.stdout.txt').write_text(build.stdout,encoding='utf-8');(output/'build.stderr.txt').write_text(build.stderr,encoding='utf-8')
        require(build.returncode==0,'Native build failed; inspect retained diagnostics')
        binary=scratch/'obj/Vrestore_top';shutil.copy2(binary,output/'Vrestore_top')
        observed=subprocess.run([str(binary)],cwd=scratch,env=env,capture_output=True,text=True,timeout=20)
        (output/'native.stdout.txt').write_text(observed.stdout,encoding='utf-8');(output/'native.stderr.txt').write_text(observed.stderr,encoding='utf-8')
        require(observed.returncode==0,'Native simulation failed')
    require(hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,'Retained source changed during native run')
    rows,configurations={i:[] for i in range(9)},{}
    for number,line in enumerate(observed.stdout.splitlines(),1):
        if line.startswith('CONFIG '):
            values=[int(v) for v in line.split()[1:]];require(len(values)==6 and values[0] not in configurations,'Invalid native configuration');configurations[values[0]]=values[1:]
        elif line.startswith('RESTORE '):
            values=[int(v) for v in line.split()[1:]];require(len(values)==23 and values[0] in rows,'Invalid native sample columns');rows[values[0]].append((number,values[1:]))
    summary=[]
    expected_reads=[(0,0,0),(1,0,0),(1,0,165),(1,0,165),(1,1,165),(1,0,165),(1,0,60),(1,0,0),(1,0,109)]
    for index,case in enumerate(CASES):
        cfg=config(case);require(configurations.get(index)==[int(cfg[k]) for k in ('context','keep_mask','staged','cold','early')],'Native configuration differs')
        require(len(rows[index])==12,'Missing native samples')
        inventory=inventory_for(case);inventory['provenance']={'source_sha256':source_hash,'native_parameters':configurations[index],
            'role':'Owned logical-loss selection and state mapping; no retention-cell/UPF exporter.'}
        expected_rows=reference(case);samples=[];native_reads=[]
        for expected_step,(line_number,values) in enumerate(rows[index]):
            step,time_tick,*data=values;require(step==expected_step,'Native sample sequence differs')
            state=dict(zip(RAW_FIELDS,data[:10]));power,enabled,ready,loss,request,identity,initialize,reinitialize,publish,seed=data[10:]
            require(state==expected_rows[step]['state'],'Native state/read contradicts independent image ledger: '+case+' step '+str(step))
            require([power,enabled,ready,loss,request,identity,initialize,reinitialize,publish,seed]==[expected_rows[step][k] for k in ('power','enabled','ready','loss','request','requested_identity','initialize','reinitialize','publish','seed')],'Native action/control schedule differs')
            if state['response_valid']:native_reads.append(tuple(state[k] for k in ('read_hit','read_error','read_data')))
            samples.append(normalize({'step':step,'time_tick':time_tick,'state':state,'power':power,'enabled':enabled,'ready':ready,'loss':loss,'request':request,'requested_identity':identity},'native.stdout.txt:'+str(line_number)))
        require(native_reads==[expected_reads[index]] and samples[-1]['native_read_count']==1,'Unexpected actual post-wake read outcome')
        journal=journal_for(inventory,samples);policy=policy_for(inventory,journal,case);report=review(inventory,journal,policy)
        require(exit_code(report)==(0 if index in (2,5,6,8) else 1),'Unexpected restore review disposition')
        folder=output/case;folder.mkdir()
        for name,value in (('inventory',inventory),('journal',journal),('policy',policy),('report',report)):save(folder/(name+'.json'),value)
        summary.append({'case':case,'status':report['status'],'read':{'hit':expected_reads[index][0],'error':expected_reads[index][1],'data':expected_reads[index][2]},'findings':report['findings']})
    result={'verilator':native_version,'source_sha256':source_hash,'cases':summary,
        'independent_reference':'Separate saved-image/loss/rebuild ledger, action/state comparison and explicit post-wake read outcomes; 108 native rows.'}
    save(output/'summary.json',result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--verilator',required=True);parser.add_argument('--verilator-root',required=True);args=parser.parse_args()
    print(run(args.directory,args.verilator,args.verilator_root))


if __name__=='__main__':main()
