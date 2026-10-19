#!/usr/bin/env python3
"""Generate actual campaign exports and review them offline; no external service."""
import argparse
import copy
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

HERE=Path(__file__).resolve().parent;MODULE=HERE.parents[1]
sys.path.insert(0,str(MODULE))
from progress_core import review,markdown,exit_code
spec=importlib.util.spec_from_file_location('campaign_example',MODULE/'examples/create_example.py')
example=importlib.util.module_from_spec(spec);spec.loader.exec_module(example)

def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output')
    parser.add_argument('--verilator',default='verilator');parser.add_argument('--verilator-root');args=parser.parse_args()
    if sys.platform!='linux':raise ValueError('Native recipe qualified on Linux only; offline helper is portable')
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
    compiler=Path(shutil.which(args.verilator) or args.verilator).resolve()
    if not compiler.is_file():raise ValueError('Supply an installed Verilator executable')
    begin=time.perf_counter_ns();env=dict(os.environ);commands=[]
    work=Path(tempfile.mkdtemp(prefix='opentools-campaign-',dir='/tmp')).resolve()
    if work.parent!=Path('/tmp') or not work.name.startswith('opentools-campaign-'):raise ValueError('Unexpected scratch root')
    try:
        if args.verilator_root:
            runtime=Path(args.verilator_root).resolve()
            if not runtime.is_dir():raise ValueError('Verilator runtime is absent')
            (work/'runtime').symlink_to(runtime,target_is_directory=True);env['VERILATOR_ROOT']=str(work/'runtime')
        (work/'verilator').symlink_to(compiler)
        source=out/'sources';source.mkdir()
        for name in ('top.sv','runner.cpp'):
            shutil.copy2(HERE/name,work/name);shutil.copy2(HERE/name,source/name)
        def execute(argv,label,expected=(0,)):
            start=time.perf_counter_ns();run=subprocess.run(list(map(str,argv)),cwd=work,env=env,capture_output=True,text=True,encoding='utf-8',timeout=180)
            packet={'argv':list(map(str,argv)),'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr,'wall_ns':time.perf_counter_ns()-start}
            save(out/(label+'.invocation.json'),packet);commands.append(label)
            if run.returncode not in expected:raise RuntimeError(label+' failed; inspect retained native invocation')
            return packet
        version=execute([compiler,'--version'],'version')['stdout'].strip()
        execute([work/'verilator','--cc','--exe','--build','-j','2','--top-module','top','--Mdir','obj','-o','simulation','top.sv','runner.cpp'],'build')
        binary=out/'simulation.bin';shutil.copy2(work/'obj/simulation',binary)
        model='sha256:'+sha(binary)
        def contract(label,ids):
            value=example.example()[0]
            value.update(campaign_ref='fixture:'+label,scope_ref='fixture:campaign-scope',configuration_ref='fixture:cfg0',model_ref=model,
                population_ref='fixture:independent required native manifest '+','.join(ids),required_run_refs=ids,evidence_ref='fixture:declared objective/policy record before scenario review')
            value['objectives'][0]['target']['run_refs']=ids
            value['objectives'][0].update(basis_ref='fixture:native explicit checker verdict',policy_ref='fixture:all required passes')
            value['objectives'][1].update(basis_ref='fixture:accepted-payload-mod-4-boolean-hit.v1',policy_ref='fixture:four required named goals')
            value['objectives'][2].update(basis_ref='fixture:checked-native-handshake-events.v1',policy_ref='fixture:192 effective checked events, repeats count without independent-trial claim')
            value['policy'].update(ref='fixture:review-only policy',evidence_ref='fixture:owned campaign criteria, no scheduler authority')
            return value
        def planned(ref):return {'run_ref':ref,'configuration_ref':'fixture:cfg0','model_ref':model,'native_state':'NOT_EXECUTED_BY_RECIPE_YET',
            'state':'not_run','evidence_ref':'independent declared required manifest; no farm queue claimed','measurements':[],'resources':[]}
        def native(ref,active=1,config=0,values=3,bins=4,force=0):
            invocation=execute([binary,ref,'64',str(active),str(config),str(values),str(bins),str(force)],ref,expected=(0,1))
            data=json.loads(invocation['stdout'])
            assert data['run_ref']==ref and data['accepted']==(64 if active else 0) and data['checks']>0
            assert data['passed']==(data['failures']==0)==(invocation['exit_code']==0)
            evidence=ref+'.invocation.json'
            return {'run_ref':ref,'configuration_ref':'fixture:cfg'+str(config),'model_ref':model,'native_state':'CHECKER_PASS' if data['passed'] else 'CHECKER_FAIL',
                'state':'passed' if data['passed'] else 'failed','evidence_ref':evidence,
                'measurements':[
                    {'objective_id':'coverage','basis_ref':'fixture:accepted-payload-mod-'+str(bins)+'-boolean-hit.v1','qualified':True,'complete':True,'evidence_ref':evidence,
                     'data':{'population_ids':['bin'+str(i) for i in range(bins)],'hit_ids':['bin'+str(i) for i in range(bins) if data['hit_mask']&(1<<i)]}},
                    {'objective_id':'stress','basis_ref':'fixture:checked-native-handshake-events.v1','qualified':True,'complete':True,'evidence_ref':evidence,
                     'data':{'unit':'checked_handshake','ranges':[{'space_ref':'fixture:native-events:'+ref,'start':0,'stop':data['accepted'],'evidence_ref':evidence}] if data['accepted'] else []}}],
                'resources':[{'metric':'process_wall','value':str(invocation['wall_ns']),'unit':'ns','definition_ref':'subprocess wall incl native startup','basis':'measured','evidence_ref':evidence},
                    {'metric':'stimulus_cycles','value':str(data['stimulus_cycles']),'unit':'cycle','definition_ref':'64 stimulus cycles excludes initial reset cycle','basis':'measured','evidence_ref':evidence},
                    {'metric':'simulated_ticks','value':str(data['simulated_ticks']),'unit':'tick','definition_ref':'native context.time increments including reset; not effective exposure','basis':'measured','evidence_ref':evidence}]}
        def snapshot(c,label,runs,complete=True):return {'format':'opentools.campaign-snapshot.v1','campaign_ref':c['campaign_ref'],'snapshot_ref':'fixture:'+label,
            'scope_ref':c['scope_ref'],'captured_at':now(),'mode':'cumulative','complete':complete,'evidence_ref':'retained native invocations plus explicit planned manifest','runs':copy.deepcopy(runs)}
        summaries=[]
        def case(label,c,a,b,expected):
            folder=out/label;folder.mkdir()
            for name,value in [('contract',c),('before',a),('after',b)]:save(folder/(name+'.json'),value)
            report=review(c,a,b);save(folder/'report.json',report);(folder/'report.md').write_text(markdown(report),encoding='utf-8',newline='\n')
            assert exit_code(report)==expected,(label,report['conflicts'],report['missing_context'])
            summaries.append({'case':label,'status':report['status'],'current':[{k:v[k] for k in ('id','known_value','target','remaining','recorded_target_attained')} for v in report['after']['objectives']],
                'changes':report['objective_changes'],'remaining_required_runs':report['after']['remaining_required_run_refs']})
        c=contract('productive',['a','b','c']);save(out/'declared-contract.json',c)
        a=native('a');before=snapshot(c,'productive-before',[a,planned('b'),planned('c')])
        b=native('b');plateau=snapshot(c,'productive-plateau',[a,b,planned('c')]);case('plateau',c,before,plateau,0)
        third=native('c',values=4);complete=snapshot(c,'productive-targets',[a,b,third]);case('recorded-targets',c,plateau,complete,0)
        assert review(c,plateau,complete)['all_recorded_targets_attained']
        idle_contract=contract('ineffective',['idle-a','idle-b','idle-c']);save(out/'idle-declared-contract.json',idle_contract)
        idle_a=native('idle-a',active=0);idle_before=snapshot(idle_contract,'idle-before',[idle_a,planned('idle-b'),planned('idle-c')])
        idle_b=native('idle-b',active=0);idle_c=native('idle-c',active=0)
        idle_after=snapshot(idle_contract,'idle-after',[idle_a,idle_b,idle_c]);case('ineffective',idle_contract,idle_before,idle_after,0)
        for label,kwargs,expected in [('changed-config',{'config':1},1),('changed-denominator',{'bins':3},2),('failed-prefix',{'force':1},1)]:
            ref=label+'-b';scoped=contract(label,['a',ref,'c']);save(out/(label+'-declared-contract.json'),scoped)
            start=snapshot(scoped,label+'-before',[a,planned(ref),planned('c')]);observed=native(ref,**kwargs)
            end=snapshot(scoped,label+'-after',[a,observed,planned('c')]);case(label,scoped,start,end,expected)
        missing=copy.deepcopy(plateau);missing.update(snapshot_ref='fixture:deliberately-partial-export',complete=False,
            provenance={'negative_case':'Deliberately omit actual completed b from historical plateau export; original cutoff, journal and full snapshot retained.',
                        'derived_export_created_at':now()})
        missing['runs']=[row for row in missing['runs'] if row['run_ref']!='b'];case('missing-data',c,before,missing,2)
        save(out/'native-observations.json',{'producer_version':version,'commands':commands,'scenarios':summaries,'model_sha256':sha(binary),
            'recipe_sha256':sha(Path(__file__)),'core_sha256':sha(MODULE/'progress_core.py'),'sources':{name:sha(source/name) for name in ('top.sv','runner.cpp')},
            'limits':'Synthetic deterministic stimulus and local checker. Event counts are not independent trials or reliability/confidence estimates.'})
    finally:
        if work.parent==Path('/tmp') and work.name.startswith('opentools-campaign-'):shutil.rmtree(work)
    save(out/'recipe-cost.json',{'wall_ns':time.perf_counter_ns()-begin,'scope':'whole recipe including build, export preparation, nine native runs, reports and owned scratch cleanup',
        'excluded':['tool installation','Python startup','AI/engineer review','farm/license wait'],'cpu':'unmeasured','savings':'not established'})
    print('Actual offline campaign evidence retained in',out)


if __name__=='__main__':main()
