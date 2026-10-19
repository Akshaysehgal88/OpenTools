"""Opt-in native timeout investigation with capture-time selection and expansion."""
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
from capture_core import PROFILE, assess, fingerprint, render, require
from native_vcd import inspect_header, import_inventory, reader, write_viewer


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def execute(command,cwd,out,label,env):
    import resource
    before=resource.getrusage(resource.RUSAGE_CHILDREN)
    start=time.perf_counter_ns()
    result=subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True,timeout=180)
    wall=time.perf_counter_ns()-start
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    info={'argv':[str(v) for v in command],'cwd':str(cwd),'exit_code':result.returncode,'wall_ns':wall,
          'child_user_s':after.ru_utime-before.ru_utime,'child_system_s':after.ru_stime-before.ru_stime,
          'stdout':result.stdout,'stderr':result.stderr}
    save(out/(label+'.invocation.json'),info)
    require(result.returncode==0,'Native command failed; inspect '+label+'.invocation.json')
    return info


def waveform(path):
    tokenize,Kind=reader()
    header=inspect_header(path)
    current=None;changes={};times=[]
    start=time.perf_counter_ns()
    with path.open('rb') as stream:
        for token in tokenize(stream):
            if token.kind is Kind.CHANGE_TIME:
                current=token.data;times.append(current)
            elif token.kind in (Kind.CHANGE_SCALAR,Kind.CHANGE_VECTOR):
                require(current is not None,'Native VCD data has no timestamp')
                value=token.data.value
                if isinstance(value,str) and value in ('0','1'):
                    value=int(value)
                changes.setdefault(token.data.id_code,[]).append([current,value])
    return {'header':header,'changes':changes,'times':times,'parse_wall_ns':time.perf_counter_ns()-start}


def signal(data,path):
    item=next(v for v in data['header']['objects'] if v['path']==path)
    return data['changes'].get(item['id_code'],[])


def plan(inventory,start,end,objects):
    return {'format':'opentools.capture-plan.v1','plan_ref':'example:'+str(start)+'-'+str(end),
            'question':'Was the request accepted, and what upstream control prevented its response?',
            'original_run_ref':'original-uninstrumented.invocation.json','inventory_sha256':fingerprint(inventory),
            'operation':'capture_time','waveform_format':'vcd','window':{'start':{'value':str(start),'unit':'ns'},
                'end':{'value':str(end),'unit':'ns'},'evidence_ref':'failure/transaction observations and explicit expansion hypothesis'},
            'failure':{'time':{'value':'240','unit':'ns'},'evidence_ref':'original native timeout transition'},
            'clock':{'kind':'affine_edge_index','clock_ref':'TOP.top.clk','period':{'value':'2','unit':'ns'},
                     'origin':{'value':'0','unit':'ns'},'evidence_ref':'runner.cpp: rising edge n occurs at tick 2*n'},
            'objects':[{'name':name,'role':'clock/reset' if name.endswith(('clk','reset_n')) else 'transaction/control',
                        'rationale':'Retain observable state or context for the current investigation question',
                        'evidence_ref':'native inventory and sources/top.sv connectivity'} for name in objects],
            'history':{'method':'replay_from_reset','available_from':{'value':'0','unit':'ns'},
                       'evidence_ref':'scheduled new native invocation from reset before selected window'},
            'correspondence':{'status':'unknown','evidence_ref':None},'intent':'reproduce',
            'run':{'stop':{'value':'260','unit':'ns'},'argv':['--request-cycle','90','--config-cycle','60','--config-value','1'],
                   'evidence_ref':'original native workload arguments'},
            'expansion':[{'trigger':'State is already inconsistent at the first dump or acceptance is absent',
                          'action':'Extend to the request and then the earlier upstream configuration event; add fabric control objects',
                          'evidence_ref':'observed late timeout and hypothesized request/grant dependency'}]}


def generate(args):
    require(platform.system()=='Linux','The native recipe is qualified on Linux')
    require(0<=args.timing_repeats<=10,'timing-repeats must be 0-10')
    reader()
    out=Path(args.directory).absolute()
    require(out.parent.is_dir() and not out.exists(),'Choose a new output directory with an existing parent')
    binary=Path(args.verilator).resolve(strict=True);runtime=Path(args.verilator_root).resolve(strict=True)
    require(binary.is_file() and runtime.is_dir(),'Existing Verilator executable/runtime required')
    out.mkdir();(out/'sources').mkdir()
    sources={}
    for name in ('top.sv','runner.cpp'):
        shutil.copyfile(Path(__file__).parent/name,out/'sources'/name)
        sources[name]=sha(out/'sources'/name)
    save(out/'source-manifest.json',sources)
    with tempfile.TemporaryDirectory(prefix='opentools-waveform-example-') as folder:
        work=Path(folder).resolve()
        require(work.parent==Path(tempfile.gettempdir()).resolve() and work.name.startswith('opentools-waveform-example-'),'Unexpected native build directory')
        (work/'verilator').symlink_to(binary);(work/'lib').symlink_to(runtime,target_is_directory=True)
        env=dict(os.environ,VERILATOR_ROOT=str(work/'lib'))
        for name in sources:
            shutil.copyfile(out/'sources'/name,work/name)
        version=execute([str(work/'verilator'),'--version'],work,out,'version',env)
        require(version['stdout'].startswith('Verilator 5.020 '),'Qualified Verilator 5.020 executable required')
        builds={}
        for label,tracing in [('traced',True),('plain',False)]:
            command=[str(work/'verilator'),'--cc','--exe','--build','--top-module','top','-CFLAGS','-std=c++17',
                     '--Mdir',label,'-j','2']+(['--trace'] if tracing else [])+['top.sv','runner.cpp']
            builds[label]=execute(command,work,out,'build-'+label,env)
            shutil.copy2(work/label/'Vtop',out/(label+'.bin'))
        traced=out/'traced.bin';plain=out/'plain.bin'
        caps=execute([str(traced),'--capabilities'],out,out,'capabilities',env)
        capability=json.loads(caps['stdout'])
        require(capability['profile']==PROFILE and capability['producer_version'] in ('5.020','5.020 2024-01-01') and capability['trace_compiled'],
                'Compiled trace wrapper capability mismatch')
        no_caps=json.loads(execute([str(plain),'--capabilities'],out,out,'plain-capabilities',env)['stdout'])
        require(no_caps['trace_compiled'] is False,'Plain binary must advertise absent instrumentation')
        execute([str(traced),'--inventory-vcd',str(out/'inventory.vcd')],out,out,'inventory',env)
        header=inspect_header(out/'inventory.vcd');save(out/'header.json',header)
        require(header['tick']==capability['tick'],'Native tick declaration disagrees with actual VCD')
        context={'format':'opentools.trace-context.v1','profile':PROFILE,'producer_version':capability['producer_version'],
                 'binary_sha256':sha(traced),'header_sha256':header['header_sha256'],'max_tick':capability['max_tick'],'trace_compiled':True,
                 'evidence_ref':'actual --capabilities, byte-hashed binary, unfiltered --inventory-vcd and source-manifest.json',
                 'aliases':[{'name':'accepted_transaction','target':'TOP.top.dma.accepted','evidence_ref':'native declared DMA acceptance net'}]}
        save(out/'context.json',context)
        inventory=import_inventory(out/'inventory.vcd',context);save(out/'inventory.json',inventory)
        workload=['--request-cycle','90','--config-cycle','60','--config-value','1']
        no_capture=['--no-capture','--stop-tick','260','--',*workload]
        original=execute([str(plain),*no_capture],out,out,'original-uninstrumented',env)
        expected=[json.loads(line) for line in original['stdout'].splitlines()]
        require(len(expected)==261 and next(v['tick'] for v in expected if v['accepted'])==180
                and next(v['tick'] for v in expected if v['timeout'])==240,'Original timeout scenario changed')
        disabled=execute([str(traced),*no_capture],out,out,'instrumented-no-dump',env)
        require(disabled['stdout']==original['stdout'],'Instrumentation changed selected behavior')
        narrow=['TOP.top.clk','TOP.top.reset_n','accepted_transaction','TOP.top.dma.outstanding',
                'TOP.top.dma.response','TOP.top.dma.timeout','TOP.top.dma.age']
        extended=narrow+['TOP.top.dma.request_valid','TOP.top.dma.request_ready','TOP.top.dma.grant','TOP.top.fabric.quiesce_active']
        expanded=extended+['TOP.top.fabric.config_write','TOP.top.fabric.config_value']
        selections={
            'full':plan(inventory,0,260,[v['path'] for v in inventory['objects'] if v['selectable']]),
            'initial':plan(inventory,220,250,narrow),
            'request-window':plan(inventory,170,250,extended),
            'expanded':plan(inventory,110,250,expanded)}
        captures={};reports={}
        for name,value in selections.items():
            save(out/(name+'-plan.json'),value)
            start=time.perf_counter_ns()
            recipe=render(value,inventory,traced,out/(name+'.vcd'))
            preparation_ns=time.perf_counter_ns()-start
            save(out/(name+'-recipe.json'),recipe);write_viewer(recipe,out/(name+'.gtkw'))
            run=execute(recipe['argv'],out,out,name,env)
            require(run['stdout']==original['stdout'],'Capture replay diverged in selected original observations: '+name)
            data=waveform(out/(name+'.vcd'))
            actual={v['path'] for v in data['header']['objects']}
            require(actual==set(recipe['assessment']['expected_declarations']),'Native selector declarations differ from preview')
            require(min(data['times'])==recipe['assessment']['native_ticks']['start']
                    and max(data['times'])==recipe['assessment']['native_ticks']['end'],'Native capture boundary differs from preview')
            captures[name]=data
            reports[name]={'bytes':(out/(name+'.vcd')).stat().st_size,'process_wall_ns':run['wall_ns'],
                'prepare_wall_ns':preparation_ns,'vcd_tokenize_wall_ns':data['parse_wall_ns'],'declarations':len(actual),
                'first_tick':min(data['times']),'last_tick':max(data['times']),
                'correspondence':'matched selected original behavior at all 261 ticks; different original/trace binaries retained'}
        require(not any(v==1 for t,v in signal(captures['initial'],'TOP.top.dma.accepted')),
                'Initial window unexpectedly contains acceptance')
        require([180,1] in signal(captures['request-window'],'TOP.top.dma.accepted'),'Request expansion lost acceptance')
        require(signal(captures['request-window'],'TOP.top.fabric.quiesce_active')[0]==[170,1],
                'Intermediate window should begin after upstream quiesce is active')
        require([120,1] in signal(captures['expanded'],'TOP.top.fabric.config_write')
                and [120,1] in signal(captures['expanded'],'TOP.top.fabric.quiesce_active')
                and [120,0] in signal(captures['expanded'],'TOP.top.dma.grant')
                and [240,1] in signal(captures['expanded'],'TOP.top.dma.timeout'),
                'Controlled scope/history expansion lost required upstream/timeout observations')
        # A changed workload is an exploratory counterfactual, not reproduction.
        branch=execute([str(traced),'--no-capture','--stop-tick','260','--','--request-cycle','90',
                        '--config-cycle','60','--config-value','0'],out,out,'counterfactual-branch',env)
        branch_rows=[json.loads(line) for line in branch['stdout'].splitlines()]
        require(branch['stdout']!=original['stdout'] and any(v['response'] for v in branch_rows)
                and not any(v['timeout'] for v in branch_rows),'Counterfactual should change the original failure')
        trials=[]
        for i in range(args.timing_repeats):
            order=('full','expanded','instrumented-no-dump','plain-no-dump') if i%2==0 else ('plain-no-dump','instrumented-no-dump','expanded','full')
            row={}
            for name in order:
                label='timing-%02d-%s'%(i,name)
                if name in ('full','expanded'):
                    command=render(selections[name],inventory,traced,out/(label+'.vcd'))['argv']
                else:
                    command=[str(plain if name=='plain-no-dump' else traced),*no_capture]
                result=execute(command,out,out,label,env)
                require(result['stdout']==original['stdout'],'Cost trial changed required selected behavior')
                row[name]={'wall_ns':result['wall_ns'],'child_user_s':result['child_user_s'],'child_system_s':result['child_system_s']}
            trials.append(row)
        summary={'profile':PROFILE,'build_wall_ns':{k:v['wall_ns'] for k,v in builds.items()},'captures':reports,
                 'cost_trials':trials,'causal_observations':{'upstream_control_tick':120,'accepted_tick':180,'timeout_tick':240,
                 'initial_insufficient':True,'upstream_cause_outside_initial_scope':True},
                 'counterfactual':'config_value=0 changes response/timeout; exploratory branch with separate invocation',
                 'unmeasured':['actual GUI load time','engineer review cost','production workflow benefit'],
                 'limits':'Owned synchronous toy. Per-capture simulation runs from reset, selection/window apply during dumping, and trace instrumentation remains compiled in. Selected reproduction/counterfactual evidence is not universal causality proof or a SoC speedup.'}
        save(out/'summary.json',summary)
        return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verilator',required=True);parser.add_argument('--verilator-root',required=True)
    parser.add_argument('--directory',required=True);parser.add_argument('--timing-repeats',type=int,default=0)
    args=parser.parse_args(argv)
    try:
        start=time.perf_counter_ns();summary=generate(args)
        save(Path(args.directory).absolute()/'recipe-timing.json',{'whole_recipe_wall_ns':time.perf_counter_ns()-start,
             'includes':'builds, actual inventory, plan/render, replay/dumps, VCD parsing, viewer files, counterfactual, requested timing trials and temporary cleanup',
             'excludes':'Python startup, tool installation, GUI viewing and human review'})
        print(json.dumps({'output':str(Path(args.directory).absolute()),'captures':summary['captures']},indent=2))
        return 0
    except (ValueError,OSError,TypeError,KeyError,subprocess.SubprocessError) as error:
        print('waveform example error: '+str(error),file=sys.stderr)
        return 3


if __name__=='__main__':
    sys.exit(main())
