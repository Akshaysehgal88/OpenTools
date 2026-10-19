"""Opt-in Linux Verilator 5.020 save/restore qualification for the supplied harness."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time

MODULE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(MODULE))
from replay_core import check, qualify, exit_code, fingerprint, require

OBSERVABLES=['time','rng','dut_memory','reference_memory','pending','checker_digest','checked','failures','valid','data_out']
CAPTURED=['dut_memory_pipeline','simulation_time','driver_rng','pending_transactions','reference_model','scoreboard']
NOT_USED=['scheduled_processes','dpi_native_objects','file_positions','external_interactions']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def execute(command,cwd,out,label,env):
    import resource
    before=resource.getrusage(resource.RUSAGE_CHILDREN)
    start=time.perf_counter_ns()
    result=subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True,timeout=180,
                          preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
    wall=time.perf_counter_ns()-start
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    info={'argv':[str(v) for v in command],'cwd':str(cwd),'exit_code':result.returncode,
          'wall_ns':wall,'child_user_s':after.ru_utime-before.ru_utime,
          'child_system_s':after.ru_stime-before.ru_stime,'stdout':result.stdout,'stderr':result.stderr}
    save(out/(label+'.invocation.json'),info)
    return info


def journal(info):
    rows=[json.loads(line) for line in info['stdout'].splitlines()]
    require(all(isinstance(row,dict) and row.get('type') in ('start','sample','end','summary') for row in rows),
            'Unsupported native example journal')
    for kind in ('start','end','summary'):
        require(sum(row['type']==kind for row in rows)==1,'Native journal must have one '+kind)
    require(rows[0]['type']=='start' and rows[-2]['type']=='end' and rows[-1]['type']=='summary'
            and all(row['type']=='sample' for row in rows[1:-2]),'Native journal ordering changed')
    return rows


def records(out,profile,control,seed,prefix,suffix,snapshot='model.bin',rng_present=True):
    rows=journal(control)
    context={'binary_sha256':sha(out/'sim.bin'),
             'configuration':{'top':'top','state_model':'single-thread clocked memory and C++ driver',
                              'timing':'explicit clock stepping, no HDL delay scheduler','checks':'read-before-write reference queue'},
             'prefix_inputs':[{'id':'firmware','sha256':sha(out/'prefix.bin'),'evidence_ref':'prefix.bin: exact 16 bytes loaded during first 16 transactions'}],
             'prefix_seed':seed,'capture_point':{'step':prefix,'unit':'driver-step','definition_ref':'one advance() read-before-write transaction; low clock after eval'}}
    checkpoint={'format':'opentools.checkpoint.v1','checkpoint_ref':'example:'+snapshot,
                'profile_sha256':fingerprint(profile),'mechanism':'serialized_model','context':context,
                'reference_continuation':{'stimulus':'continue captured LCG(1664525,1013904223) and pending transaction state'},
                'state_inventory':[{'id':name,'status':'captured','method':'generated native serialization' if name in ('dut_memory_pipeline','simulation_time') else 'explicit wrapper stream fields',
                                    'capture_ref':'sources/runner.cpp:save; generated root serialization',
                                    'restore_ref':'sources/runner.cpp:restore; generated root deserialization'} for name in CAPTURED]+
                                  [{'id':name,'status':'not_used','method':'absent from this inspected harness',
                                    'capture_ref':'sources/top.sv and runner.cpp: closed prefix file, no DPI/sockets/delays',
                                    'restore_ref':'no corresponding live resource to reconstruct'} for name in NOT_USED],
                'state_inventory_complete':{'complete':True,'evidence_ref':'sources/runner.cpp Driver, tick, image, save/restore; sources/top.sv'},
                'capture':{'complete':True,'exit_code':control['exit_code'],'evidence_ref':'control native invocation and stream close'},
                'artifacts':[{'path':snapshot,'sha256':sha(out/snapshot),'evidence_ref':'native VerilatedSave closed file'}],
                'boundary_observation':{k:copy.deepcopy(rows[0][k]) for k in ('step','values')},
                'provenance':{'native_profile':'Verilator-5.020-clocked-memory.v1','source_manifest':'source-manifest.json'}}
    checkpoint['boundary_observation']['evidence_ref']='control native start row immediately after quiescent capture'
    if not rng_present:
        state=next(item for item in checkpoint['state_inventory'] if item['id']=='driver_rng')
        state.update(status='missing',method='intentional capture omission',capture_ref='sources/runner.cpp: rng_present=0',
                     restore_ref='initial seed fallback cannot reconstruct advanced RNG')
    request={'format':'opentools.replay-request.v1','request_ref':'example:'+snapshot+':continuation',
             'checkpoint_ref':checkpoint['checkpoint_ref'],'profile_sha256':fingerprint(profile),'intent':'faithful',
             'context':copy.deepcopy(context),'continuation':copy.deepcopy(checkpoint['reference_continuation']),
             'horizon':{'start_step':prefix,'end_step':prefix+suffix,'unit':'driver-step',
                        'definition_ref':context['capture_point']['definition_ref'],'evidence_ref':'explicit requested suffix length'},
             'binary':{'path':'sim.bin','sha256':context['binary_sha256'],'evidence_ref':'actual requested executable bytes'},
             'prefix_files':[{'id':'firmware','path':'prefix.bin','sha256':context['prefix_inputs'][0]['sha256'],
                              'evidence_ref':'actual requested prefix image bytes'}],
             'evidence_ref':'explicit supplied native example arguments'}
    return checkpoint,request


def normalized(info,checkpoint,request,profile,role,label):
    rows=journal(info)
    return {'format':'opentools.replay-run.v1','run_ref':'example:'+label,'role':role,
            'request_sha256':fingerprint(request),'checkpoint_sha256':fingerprint(checkpoint),'profile_sha256':fingerprint(profile),
            'horizon':copy.deepcopy(request['horizon']),
            'completion':{'complete':True,'exit_code':info['exit_code'],'evidence_ref':label+'.invocation.json'},
            'start':{**{k:rows[0][k] for k in ('step','values')},'evidence_ref':label+'.invocation.json:start'},
            'samples':[{k:row[k] for k in ('step','values')} for row in rows if row['type']=='sample'],
            'end':{**{k:rows[-2][k] for k in ('step','values')},'evidence_ref':label+'.invocation.json:end'},
            'observations_ref':label+'.invocation.json: ordered stdout JSONL'}


def generate(args):
    require(platform.system()=='Linux','This native recipe is qualified on Linux; use the portable helper on other systems')
    require(16<=args.prefix_steps<=10000000 and 0<args.suffix_steps<=10000000
            and args.prefix_steps+args.suffix_steps<=10000000 and 0<=args.seed<=0xffffffff
            and 0<=args.overhead_pairs<=20,'Example bounds exceeded')
    out=Path(args.directory).absolute()
    require(out.parent.is_dir() and not out.exists(),'Choose a new output directory with an existing parent')
    binary=Path(args.verilator).resolve(strict=True)
    runtime=Path(args.verilator_root).resolve(strict=True)
    require(binary.is_file() and runtime.is_dir(),'Existing Verilator executable and runtime root required')
    out.mkdir()
    (out/'sources').mkdir()
    sources={}
    for name in ('top.sv','runner.cpp'):
        target=out/'sources'/name
        shutil.copyfile(Path(__file__).parent/name,target)
        sources[name]=sha(target)
    save(out/'source-manifest.json',sources)
    (out/'prefix.bin').write_bytes(bytes((i*7+11)&255 for i in range(16)))
    with tempfile.TemporaryDirectory(prefix='opentools-replay-example-') as folder:
        work=Path(folder).resolve()
        require(work.parent==Path(tempfile.gettempdir()).resolve() and work.name.startswith('opentools-replay-example-'),
                'Unexpected native temporary directory')
        # GNU Make is sensitive to spaces; only the build workspace uses these aliases.
        (work/'verilator').symlink_to(binary)
        (work/'lib').symlink_to(runtime,target_is_directory=True)
        for name in sources:
            shutil.copyfile(out/'sources'/name,work/name)
        env=dict(os.environ,VERILATOR_ROOT=str(work/'lib'))
        version=execute([str(work/'verilator'),'--version'],work,out,'version',env)
        require(version['exit_code']==0 and version['stdout'].startswith('Verilator 5.020 '),'Native recipe requires Verilator 5.020')
        compile_argv=[str(work/'verilator'),'--cc','--exe','--build','--savable','--top-module','top',
                      '-CFLAGS','-std=c++17','-j','2','top.sv','runner.cpp']
        build=execute(compile_argv,work,out,'build',env)
        require(build['exit_code']==0,'Native build failed; see build.invocation.json')
        shutil.copy2(work/'obj_dir/Vtop',out/'sim.bin')
        (out/'generated').mkdir()
        for path in (work/'obj_dir').glob('*__Slow.cpp'):
            if '__Vserialize' in path.read_text():
                shutil.copyfile(path,out/'generated'/path.name)
        profile={'format':'opentools.checkpoint-profile.v1','id':'Verilator-5.020-clocked-memory.v1:'+fingerprint(sources),
                 'mechanism':'serialized_model','boundary_ref':'quiescent low clock after prefix, before suffix; generated context serialization',
                 'evidence_ref':'source-manifest.json; inspected explicit Driver and generated serialization',
                 'state':[{'id':name,'requirement':'capture','evidence_ref':'sources/runner.cpp save/restore and sources/top.sv'} for name in CAPTURED]+
                         [{'id':name,'requirement':'not_used','evidence_ref':'sources: no delay scheduler, DPI, open input files or external transactions'} for name in NOT_USED],
                 'observables':OBSERVABLES}
        save(out/'profile.json',profile)
        calls={}
        def native(label,mode,snapshot='model.bin',save_rng=1,sample_every_step=1):
            info=execute([str(out/'sim.bin'),mode,snapshot,'prefix.bin',str(args.seed),str(args.prefix_steps),
                          str(args.suffix_steps),str(save_rng),str(sample_every_step)],out,out,label,env)
            calls[label]=info
            return info
        control=native('control','control')
        require(control['exit_code']==0,'Native control checks failed')
        checkpoint,request=records(out,profile,control,args.seed,args.prefix_steps,args.suffix_steps)
        save(out/'checkpoint.json',checkpoint); save(out/'request.json',request)
        check_start=time.perf_counter_ns()
        gate=check(checkpoint,request,profile,out)
        check_wall_ns=time.perf_counter_ns()-check_start
        save(out/'compatibility.json',gate)
        require(exit_code(gate)==0,'Restore blocked by captured-state compatibility check')
        restored=native('restored','restore')
        c=normalized(control,checkpoint,request,profile,'control','control')
        r=normalized(restored,checkpoint,request,profile,'restored','restored')
        save(out/'control.json',c); save(out/'restored.json',r)
        qualification_start=time.perf_counter_ns()
        qualification=qualify(checkpoint,request,profile,c,r,out)
        qualification_wall_ns=time.perf_counter_ns()-qualification_start
        save(out/'qualification.json',qualification)
        require(qualification['status']=='matched_selected_observables','Native replay failed qualification')
        restart=native('restart','restart','unused.bin')
        restart_rows=journal(restart)
        require(restart['exit_code']==0 and restart_rows[:-1]==journal(control)[:-1],
                'Restart-from-reset selected observations differ')
        save(out/'restart-observation-comparison.json',{'matches_selected_start_and_suffix':True,
             'limits':'Independent reset-based control, not a restored execution or process checkpoint'})
        sampling=[]
        for pair in range(args.overhead_pairs):
            observations={}
            for sampling_mode in ((0,1) if pair%2==0 else (1,0)):
                label='sampling-%02d-%s'%(pair,'every-step' if sampling_mode else 'boundaries')
                value=native(label,'restart','unused.bin',1,sampling_mode)
                rows=journal(value)
                require(value['exit_code']==0 and rows[0]['values']==c['start']['values']
                        and rows[-2]['values']==c['end']['values'],'Sampling-cost control changed checked final/boundary state')
                observations[sampling_mode]={'whole_process_wall_ns':value['wall_ns'],
                                            'suffix_observed_wall_ns':rows[-1]['suffix_ns'],
                                            'stdout_bytes':len(value['stdout'].encode('utf-8'))}
            sampling.append({'pair':pair,'boundary_only':observations[0],'every_step':observations[1],
                  'whole_process_delta_ns':observations[1]['whole_process_wall_ns']-observations[0]['whole_process_wall_ns'],
                  'suffix_delta_ns':observations[1]['suffix_observed_wall_ns']-observations[0]['suffix_observed_wall_ns']})
        save(out/'sampling-cost.json',{'pairs':sampling,
             'scope':'Alternating same-binary reset runs with all reference checks and matching selected boundary/final state. Boundary-only journals do not qualify full trajectory replay.',
             'limits':'Measured output/probe overhead at this tiny horizon, plus process/filesystem noise; no production instrumentation or speedup estimate.'})
        negatives={}
        if args.negative_controls:
            missing=native('missing-rng-control','control','missing-rng.bin',0)
            require(missing['exit_code']==0,'Missing-RNG capture control unexpectedly failed hardware checks')
            mc,mq=records(out,profile,missing,args.seed,args.prefix_steps,args.suffix_steps,'missing-rng.bin',False)
            mg=check(mc,mq,profile,out)
            require(mg['status']=='incompatible','Missing external RNG must block normal restoration')
            save(out/'missing-rng-checkpoint.json',mc); save(out/'missing-rng-request.json',mq); save(out/'missing-rng-compatibility.json',mg)
            # Controlled counterexample using our own deliberately incomplete file;
            # this call intentionally bypasses the rejected operational gate.
            bad=native('missing-rng-restored','restore','missing-rng.bin',0)
            require(bad['exit_code']==0,'Omitted RNG should still pass this hardware reference checker')
            bc=normalized(missing,mc,mq,profile,'control','missing-rng-control')
            br=normalized(bad,mc,mq,profile,'restored','missing-rng-restored')
            bq=qualify(mc,mq,profile,bc,br,out)
            require(bq['status']=='incompatible' and bq['differences'],'Missing RNG must retain observed continuation differences')
            save(out/'missing-rng-control.json',bc); save(out/'missing-rng-restored.json',br); save(out/'missing-rng-qualification.json',bq)
            negatives['missing_rng']={'native_checker_exit':bad['exit_code'],'gate':mg['status'],'observed_difference_count':len(bq['differences']),
                                      'limits':'Own-file controlled bypass demonstrates why the normal gate rejects incomplete state'}
            dropped=native('dropped-queue','restore-drop-queue')
            require(dropped['exit_code']==1,'Dropped pending transaction should fail the checker')
            dq=qualify(checkpoint,request,profile,c,normalized(dropped,checkpoint,request,profile,'restored','dropped-queue'),out)
            require(dq['status']=='diverged','Dropped queue must diverge')
            save(out/'dropped-queue-qualification.json',dq)
            negatives['dropped_queue']={'native_checker_exit':1,'status':dq['status']}
            changed=bytearray((out/'prefix.bin').read_bytes()); changed[0]^=1
            (out/'changed-prefix.bin').write_bytes(changed)
            changed_request=copy.deepcopy(request)
            changed_request['context']['prefix_inputs'][0]['sha256']=sha(out/'changed-prefix.bin')
            changed_request['prefix_files'][0].update(path='changed-prefix.bin',sha256=sha(out/'changed-prefix.bin'))
            cg=check(checkpoint,changed_request,profile,out)
            require(cg['status']=='incompatible','Changed consumed prefix image must be rejected')
            save(out/'changed-prefix-request.json',changed_request); save(out/'changed-prefix-compatibility.json',cg)
            negatives['changed_prefix']={'status':cg['status'],'native_restore_executed':False}
            seed_request=copy.deepcopy(request); seed_request['context']['prefix_seed']=(args.seed+1)&0xffffffff
            sg=check(checkpoint,seed_request,profile,out)
            require(sg['status']=='incompatible','Changed prefix seed must be rejected')
            save(out/'changed-seed-request.json',seed_request); save(out/'changed-seed-compatibility.json',sg)
            negatives['changed_seed']={'status':sg['status'],'native_restore_executed':False}
            alternate=compile_argv.copy()
            alternate[alternate.index('-std=c++17')]='-std=c++17 -DPROFILE_BUILD_REV=2'
            alternate += ['--Mdir','alternate']
            changed_build=execute(alternate,work,out,'changed-binary-build',env)
            require(changed_build['exit_code']==0,'Alternate native build failed')
            shutil.copy2(work/'alternate/Vtop',out/'alternate.bin')
            binary_request=copy.deepcopy(request)
            binary_request['context']['binary_sha256']=sha(out/'alternate.bin')
            binary_request['binary'].update(path='alternate.bin',sha256=sha(out/'alternate.bin'))
            bg=check(checkpoint,binary_request,profile,out)
            require(bg['status']=='incompatible','Changed native binary must be rejected')
            save(out/'changed-binary-request.json',binary_request); save(out/'changed-binary-compatibility.json',bg)
            negatives['changed_binary']={'status':bg['status'],'native_restore_executed':False}
            (out/'truncated.bin').write_bytes((out/'model.bin').read_bytes()[:32])
            corrupt=copy.deepcopy(checkpoint); corrupt['artifacts'][0]['path']='truncated.bin'
            corrupt_gate=check(corrupt,request,profile,out)
            require(corrupt_gate['status']=='unavailable_checkpoint','Truncation must fail the current-file check')
            save(out/'truncated-compatibility.json',corrupt_gate)
            failed=native('deliberate-failed-restore','restore','truncated.bin')
            require(failed['exit_code']!=0,'Truncated native restoration must fail')
            negatives['failed_restore']={'gate':corrupt_gate['status'],'native_exit':failed['exit_code'],
                 'actual_snapshot_sha256':sha(out/'truncated.bin'),'expected_snapshot_sha256':sha(out/'model.bin'),
                 'limits':'Own-file controlled native failure; normal operation is blocked by the hash gate first'}
        summary={'profile':profile['id'],'status':qualification['status'],
                 'horizon':request['horizon'],'negative_controls':negatives,
                 'checkpoint_bytes':(out/'model.bin').stat().st_size,'binary_bytes':(out/'sim.bin').stat().st_size,
                 'build_wall_ns':build['wall_ns'],
                 'check_wall_ns':check_wall_ns,'qualification_wall_ns':qualification_wall_ns,
                 'execution_wall_ns':{label:info['wall_ns'] for label,info in calls.items()},
                 'native_phase_observations':{label:journal(info)[-1] for label,info in calls.items()
                     if label!='deliberate-failed-restore'},
                 'limits':'Single synchronous harness and selected observations, not UVM/cocotb/DPI/process capture or universal equivalence. Costs include journal work within process; no SoC speedup or amortized production benefit inferred.'}
        save(out/'summary.json',summary)
        return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verilator',required=True,help='Existing 5.020 executable, qualified with verilator_bin')
    parser.add_argument('--verilator-root',required=True,help='Existing share/verilator runtime directory')
    parser.add_argument('--directory',required=True,help='New local output directory')
    parser.add_argument('--prefix-steps',type=int,default=64)
    parser.add_argument('--suffix-steps',type=int,default=128)
    parser.add_argument('--seed',type=int,default=17)
    parser.add_argument('--negative-controls',action='store_true')
    parser.add_argument('--overhead-pairs',type=int,default=0,help='0-20 alternating full versus boundary-only observation pairs')
    args=parser.parse_args(argv)
    try:
        start=time.perf_counter_ns()
        summary=generate(args)
        save(Path(args.directory).absolute()/'recipe-timing.json',{'whole_recipe_wall_ns':time.perf_counter_ns()-start,
             'includes':'build, native control/capture/restore/reset, records, checks, requested negative/sampling controls and owned temporary build cleanup',
             'excludes':'Python startup, native tool installation and human review'})
        print(json.dumps({'status':summary['status'],'output':str(Path(args.directory).absolute()),
                          'negative_controls':summary['negative_controls']},indent=2))
        return 0
    except (ValueError,OSError,TypeError,KeyError,subprocess.SubprocessError) as error:
        print('example error: '+str(error),file=sys.stderr)
        return 3


if __name__=='__main__':
    sys.exit(main())
