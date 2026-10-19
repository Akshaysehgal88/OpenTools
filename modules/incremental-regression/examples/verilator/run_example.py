#!/usr/bin/env python3
"""Compile owned RTL variants; compare actual targeted and independent full runs."""
import argparse
import copy
import hashlib
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
from selection_core import fingerprint,plan,feedback,exit_code

IDS=['soc_smoke','dma_directed','fabric_integration','soc_stress','reset_sequence','fabric_long']


def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output');parser.add_argument('--verilator',default='verilator')
    parser.add_argument('--verilator-root',help='Runtime directory when invoking verilator_bin directly')
    args=parser.parse_args();out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter_ns();env=dict(os.environ);compiler=shutil.which(args.verilator) or args.verilator
    compiler=Path(compiler).resolve()
    if not compiler.is_file():raise ValueError('Supply an installed Verilator executable')
    if sys.platform!='linux':raise ValueError('This native recipe is qualified only on Linux; the selector is portable')
    work=Path(tempfile.mkdtemp(prefix='opentools-regression-',dir='/tmp')).resolve()
    if not str(work).startswith('/tmp/opentools-regression-'):raise ValueError('Unexpected native scratch root')
    commands=[]
    try:
        if args.verilator_root:
            runtime=Path(args.verilator_root).resolve()
            if not runtime.is_dir():raise ValueError('Verilator runtime directory is absent')
            (work/'runtime').symlink_to(runtime,target_is_directory=True);env['VERILATOR_ROOT']=str(work/'runtime')
        (work/'verilator').symlink_to(compiler)
        def execute(argv,label,cwd,expected=(0,)):
            begin=time.perf_counter_ns()
            run=subprocess.run(list(map(str,argv)),cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',timeout=180)
            duration=time.perf_counter_ns()-begin
            record={'argv':list(map(str,argv)),'cwd':str(cwd),'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr,'wall_ns':duration}
            save(out/(label+'.invocation.json'),record);commands.append(label)
            if run.returncode not in expected:raise RuntimeError(label+' failed; inspect archived invocation')
            return record
        version=execute([compiler,'--version'],'version',work)['stdout'].strip()
        binaries={};source_hashes={}
        for variant in ('baseline','local','shared','unknown'):
            folder=work/variant;folder.mkdir();archive=out/(variant+'-sources');archive.mkdir()
            for name in ('top.sv','shared_pkg.sv','glue_pkg.sv','runner.cpp'):
                content=(HERE/name).read_text(encoding='utf-8')
                if variant=='local' and name=='top.sv':content=content.replace("DMA_BIAS = 8'd0","DMA_BIAS = 8'd1")
                if variant=='shared' and name=='shared_pkg.sv':content=content.replace("STEP = 8'd1","STEP = 8'd2")
                if variant=='unknown' and name=='glue_pkg.sv':content=content.replace('return value;','return value + 1\'b1;')
                (folder/name).write_text(content,encoding='utf-8',newline='\n');shutil.copy2(folder/name,archive/name)
            command=[work/'verilator','--cc','--exe','--build','-j','2','--top-module','top','-Wno-fatal','--Mdir','obj','-o','simulation',
                     'shared_pkg.sv','glue_pkg.sv','top.sv','runner.cpp']
            execute(command,'build-'+variant,folder)
            binary=out/(variant+'.bin');shutil.copy2(folder/'obj/simulation',binary);binaries[variant]=binary
            source_hashes[variant]={name:sha(archive/name) for name in ('top.sv','shared_pkg.sv','glue_pkg.sv','runner.cpp')}
        # This universe comes from the fixture's maintained full manifest, not selection.
        # Preserve all variants and checker populations even when a stage omits some.
        summary=[]
        scenarios=[('baseline','baseline','rtl',0),('local','local','rtl',0),('shared','shared','shared',0),
                   ('configuration','baseline','configuration',1),('unknown','unknown','rtl',0),
                   ('renamed','baseline','test',0),('misleading-map','shared','rtl',0)]
        for label,variant,category,config in scenarios:
            folder=out/label;folder.mkdir();ids=list(IDS)
            if label=='renamed':ids[1]='dma_directed_v2'
            universe={'format':'opentools.test-universe.v1','universe_ref':'fixture:full-native-manifest','revision_ref':'fixture:'+label,
                'scope_ref':'fixture:configuration-'+str(config),'source_ref':'maintained independent IDS plus runner.cpp supported tests; sources archived',
                'complete':True,'tests':[{'id':key,'name':IDS[i],'configuration_ref':'fixture:config-'+str(config)+'/deterministic-stimulus',
                    'execution_ref':str(binaries[variant])+' '+IDS[i]+' '+str(config),'available':True,'evidence_ref':'actual binary sha256:'+sha(binaries[variant])} for i,key in enumerate(ids)]}
            path='shared_pkg.sv' if variant=='shared' else 'glue_pkg.sv' if variant=='unknown' else 'campaign configuration' if label=='configuration' else 'full test manifest' if label=='renamed' else 'top.sv'
            changes={'format':'opentools.regression-change.v1','change_ref':'fixture:'+label,'base_revision_ref':'fixture:baseline','revision_ref':universe['revision_ref'],
                'scope_ref':universe['scope_ref'],'diff_ref':'archived baseline/current sources and invocation configuration','complete':True,
                'items':[{'id':'change','path':path,'category':category,'evidence_ref':'actual retained sources/config; baseline '+json.dumps(source_hashes['baseline'])+' current '+json.dumps(source_hashes[variant])}]}
            if label=='baseline':changes['items']=[]
            mapping={'format':'opentools.test-mapping.v1','mapping_ref':'fixture:explicit-manual-map','scope_ref':universe['scope_ref'],'source_ref':'source-reviewed illustrative map; not an extracted dependency graph',
                'universe_sha256':fingerprint(universe),'change_sha256':fingerprint(changes),
                'entries':[] if label in ('baseline','unknown') else [{'change_id':'change','test_ids':['dma_directed'] if label in ('renamed','misleading-map') else ['dma_directed','soc_stress'],
                    'complete':True,'evidence_ref':'fixture:claimed complete map, intentionally false in misleading-map case'}]}
            policy={'format':'opentools.regression-policy.v1','policy_ref':'fixture:fast-feedback-policy','scope_ref':universe['scope_ref'],'source_ref':'fixture:mandatory smoke and integration policy',
                'universe_sha256':fingerprint(universe),'stage':'fast-feedback','mandatory_ids':['soc_smoke','fabric_integration'],'required_ids':ids,
                'defer_ids':['fabric_long'],'later_stage_ref':'fixture:later full qualification','broaden_categories':['shared','configuration','toolchain','generator'],'unknown_impact':'broaden_all'}
            selection=plan(universe,changes,mapping,policy)
            for name,value in [('universe',universe),('changes',changes),('mapping',mapping),('policy',policy),('selection',selection)]:save(folder/(name+'.json'),value)
            def campaign(kind,names):
                attempts=[]
                for key in names:
                    native_name=next(v['name'] for v in universe['tests'] if v['id']==key)
                    invocation=execute([binaries[variant],native_name,str(config)],label+'-'+kind+'-'+key,work,expected=(0,1))
                    observed=json.loads(invocation['stdout']);assert observed['test']==native_name and observed['config']==config and observed['checks']>0
                    assert observed['passed']==(observed['failures']==0)==(invocation['exit_code']==0)
                    attempts.append({'attempt_ref':label+':'+kind+':'+key,'test_id':key,'state':'pass' if observed['passed'] else 'fail',
                        'run_ref':label+'-'+kind+'-'+key,'evidence_ref':label+'-'+kind+'-'+key+'.invocation.json','wall_ns':invocation['wall_ns']})
                return {'format':'opentools.regression-results.v1','campaign_ref':'fixture:'+label+':'+kind,'kind':kind,'scope_ref':universe['scope_ref'],'source_ref':'actual native invocations and checker counters',
                    'universe_sha256':fingerprint(universe),'change_sha256':fingerprint(changes),'selection_sha256':fingerprint(selection) if kind=='targeted' else None,'complete':True,'attempts':attempts}
            targeted=campaign('targeted',selection['selected_ids']);full=campaign('full',ids)
            save(folder/'targeted-results.json',targeted);save(folder/'full-results.json',full)
            review=feedback(universe,changes,mapping,policy,targeted,full);save(folder/'feedback.json',review)
            summary.append({'case':label,'selected':len(selection['selected_ids']),'universe':len(ids),'selection_status':selection['status'],
                'feedback_status':review['status'],'actual_full_failed':[v['test_id'] for v in full['attempts'] if v['state']=='fail'],
                'failures_outside_selection':review['failures_outside_selection'],'targeted_attempt_wall_ns':[v['wall_ns'] for v in targeted['attempts']],
                'full_attempt_wall_ns':[v['wall_ns'] for v in full['attempts']]})
        assert summary[0]['actual_full_failed']==[]
        assert summary[1]['actual_full_failed']==['dma_directed','fabric_integration','soc_stress'] and not summary[1]['failures_outside_selection']
        assert summary[2]['selected']==6 and summary[3]['selected']==6 and summary[4]['selected']==6
        assert summary[5]['selection_status']=='review_required'
        assert summary[6]['failures_outside_selection']==['soc_stress','fabric_long']
        save(out/'native-observations.json',{'producer_version':version,'scenarios':summary,'commands':commands,'source_hashes':source_hashes,
            'recipe_sha256':sha(Path(__file__)),'selection_core_sha256':sha(MODULE/'selection_core.py'),
            'builds':4,'targeted_and_full_runs_are_separate':True,'limits':'Owned tiny fixture, illustrative manual maps and deliberate defects; no production selectivity, general dependency completeness or total effort benefit established.'})
    finally:
        # Only the exact owned /tmp directory returned above is removed.
        if work.parent==Path('/tmp') and work.name.startswith('opentools-regression-'):shutil.rmtree(work)
    save(out/'recipe-cost.json',{'wall_ns':time.perf_counter_ns()-start,'scope':'whole recipe including four builds, preparation, native runs, reports and scratch cleanup',
        'excluded':['tool installation','Python startup','AI/engineer review','farm wait/licensing'],'additivity':'Per-attempt process wall observations are not CPU or an independent workflow-savings claim.'})
    print('Native campaigns retained in',out)


if __name__=='__main__':main()
