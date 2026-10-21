#!/usr/bin/env python3
"""Build real receiver ELFs and execute them under an owned readiness model."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

MODULE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(MODULE))
from handoff_core import exit_code,require,review
from image_capture import capture
from create_example import records,save
from reference_model import ALPHA,BETA,CODE,OUTPUT,PAGE,CASES,config,expected

def build(folder,assembler,linker,readelf):
    source=MODULE/'examples/receiver.S';shutil.copyfile(source,folder/'receiver.S');images={}
    commands=[]
    for stage,value in (('loader',90),('firmware',165)):
        commands.extend(([assembler,'--64','--defsym','VALUE='+str(value),'-o',stage+'.o','receiver.S'],
            [linker,'-m','elf_x86_64','--build-id=none','-Ttext',hex(CODE),'-e','_start','-o',stage+'.elf',stage+'.o']))
        for command in commands[-2:]:
            result=subprocess.run(command,cwd=folder,capture_output=True,text=True)
            (folder/(stage+('-assemble' if command[0]==assembler else '-link')+'.txt')).write_text(result.stdout+result.stderr,encoding='utf-8')
            require(result.returncode==0,'GNU image build failed: '+stage)
        image=capture(folder/(stage+'.elf'));result=subprocess.run([readelf,'--wide','--file-header','--program-headers',stage+'.elf'],cwd=folder,capture_output=True,text=True,env=dict(os.environ,LC_ALL='C'))
        require(result.returncode==0,'readelf failed');(folder/(stage+'-readelf.txt')).write_text(result.stdout,encoding='utf-8')
        entry=re.search(r'Entry point address:\s*(0x[0-9a-fA-F]+)',result.stdout);require(entry and int(entry[1],16)==image['entry'],'ELF entry differs from GNU readelf')
        loads=[]
        for line in result.stdout.splitlines():
            parts=line.split()
            if parts and parts[0]=='LOAD':
                loads.append((int(parts[2],16),int(parts[5],16),''.join(parts[6:-1])))
        require(loads==[(s['start'],s['size'],''.join('E' if p=='X' else p for p in s['permissions'])) for s in image['segments']],'ELF load metadata differs from GNU readelf')
        images[stage]=image;save(folder/(stage+'-image.json'),image)
    save(folder/'build-commands.json',commands)
    return images

def execute(case,images,folder):
    import unicorn as uc
    from unicorn.x86_const import UC_X86_REG_RAX,UC_X86_REG_RDI,UC_X86_REG_RIP,UC_X86_REG_RSP
    require(uc.__version__=='2.1.4','Native recipe qualified with Unicorn 2.1.4')
    cfg=config(case);engine=uc.Uc(uc.UC_ARCH_X86,uc.UC_MODE_64)
    selected=images[cfg['loaded_image']];data=(folder/(cfg['loaded_image']+'.elf')).read_bytes();pages={}
    for segment in selected['segments']:
        permissions=sum(bit for name,bit in (('R',uc.UC_PROT_READ),('W',uc.UC_PROT_WRITE),('X',uc.UC_PROT_EXEC)) if name in segment['permissions'])
        for page in range(segment['start']&~(PAGE-1),(segment['start']+segment['size']+PAGE-1)&~(PAGE-1),PAGE):pages[page]=pages.get(page,0)|permissions
    for page in pages:engine.mem_map(page,PAGE)
    for segment in selected['segments']:engine.mem_write(segment['start'],data[segment['file_offset']:segment['file_offset']+segment['file_size']])
    for page,permissions in pages.items():engine.mem_protect(page,PAGE,permissions)
    for base,ready in ((ALPHA,cfg['alpha_ready']),(BETA,cfg['beta_ready'])):engine.mem_map(base,PAGE,uc.UC_PROT_READ|uc.UC_PROT_WRITE if ready else uc.UC_PROT_NONE)
    engine.mem_map(OUTPUT,PAGE,uc.UC_PROT_READ|uc.UC_PROT_WRITE)
    engine.reg_write(UC_X86_REG_RSP,cfg['initial_sp']);engine.reg_write(UC_X86_REG_RDI,OUTPUT);engine.reg_write(UC_X86_REG_RIP,cfg['entry'])
    events=[]
    def emit(kind,**fields):events.append(dict(seq=len(events),kind=kind,evidence_ref=case+'/raw.json:journal_events:'+str(len(events)),**fields))
    state={'clock-ready':True,'reset-asserted':False,'stack-alpha-ready':cfg['alpha_ready'],'stack-beta-ready':cfg['beta_ready']}
    for key,ready in state.items():emit('fact',id=key,value=ready)
    emit('image_load',image_sha256=selected['sha256'])
    emit('handoff',successor_ref=cfg['successor_ref'],image_sha256=selected['sha256'],entry=engine.reg_read(UC_X86_REG_RIP),initial_sp=engine.reg_read(UC_X86_REG_RSP),state=state.copy())
    accesses=[];instructions=[];invalid=[];pending=[];halted=False
    def code_hook(machine,address,size,_):
        nonlocal halted
        for row in pending:
            if row['successful'] is None:row['successful']=True;row['confirmed_next_pc']=address
        pending.clear();instruction=bytes(machine.mem_read(address,size));instructions.append({'pc':address,'size':size,'bytes':instruction.hex(),'rsp':machine.reg_read(UC_X86_REG_RSP)})
        if instruction==b'\xf4':halted=True;machine.emu_stop()
    def memory_hook(machine,kind,address,size,value,_):
        operation='write' if kind==uc.UC_MEM_WRITE else 'read'
        row={'operation':operation,'address':address,'size':size,'value':value if operation=='write' else int.from_bytes(machine.mem_read(address,size),'little'),
            'successful':None,'purpose':'stack' if ALPHA<=address<ALPHA+PAGE or BETA<=address<BETA+PAGE else 'data'}
        accesses.append(row);pending.append(row)
    def invalid_hook(machine,kind,address,size,value,_):
        invalid.append({'kind':kind,'address':address,'size':size,'value':value})
        for row in pending:
            if row['address']==address and row['size']==size:row['successful']=False
        return False
    engine.hook_add(uc.UC_HOOK_CODE,code_hook)
    engine.hook_add(uc.UC_HOOK_MEM_READ|uc.UC_HOOK_MEM_WRITE,memory_hook)
    engine.hook_add(uc.UC_HOOK_MEM_INVALID,invalid_hook)
    error=None;fault=None
    try:engine.emu_start(cfg['entry'],CODE+PAGE,timeout=1000000,count=32)
    except uc.UcError as exception:
        error={'code':exception.errno,'message':str(exception)}
        fault='unready-stack-protection' if exception.errno==uc.UC_ERR_WRITE_PROT else 'unmapped-entry' if exception.errno==uc.UC_ERR_FETCH_UNMAPPED else 'other-emulator-error'
    completed=halted and error is None
    value=int.from_bytes(engine.mem_read(OUTPUT,8),'little') if any(a['address']==OUTPUT and a['operation']=='write' and a['successful'] is True for a in accesses) else None
    raw={'case':case,'configuration':cfg,'instructions':instructions,'accesses':accesses,'invalid':invalid,'error':error,
        'completed':completed,'fault':fault,'value':value,'final_rsp':engine.reg_read(UC_X86_REG_RSP),'final_rax':engine.reg_read(UC_X86_REG_RAX)}
    oracle=expected(case)
    require([{k:a[k] for k in ('operation','address','size','value','successful','purpose')} for a in accesses]==oracle['accesses'],'Actual instruction accesses differ from independent address/value reference: '+case)
    require(all(raw[k]==oracle[k] for k in ('completed','fault','value')),'Actual completion differs from independent reference: '+case)
    # Record applied controller facts before control transfers; later readiness
    # is a separate event and never edits the handoff snapshot or failed access.
    for index,access in enumerate(accesses):
        emit('access',actor_ref=cfg['successor_ref'],**{k:access[k] for k in ('purpose','operation','address','size','successful')})
        events[-1]['evidence_ref']=case+'/raw.json:accesses:'+str(index)
    emit('result',actor_ref=cfg['successor_ref'],value=value)
    if cfg['late_ready']:
        engine.mem_protect(ALPHA,PAGE,uc.UC_PROT_READ|uc.UC_PROT_WRITE);emit('fact',id='stack-alpha-ready',value=True)
    raw['journal_events']=events
    return raw

def run(output,assembler='as',linker='ld',readelf='readelf'):
    import unicorn
    output=Path(output);output.mkdir(parents=True,exist_ok=False);images=build(output,assembler,linker,readelf);summary=[]
    for case in CASES:
        raw=execute(case,images,output);folder=output/case;folder.mkdir();save(folder/'raw.json',raw)
        values=records(case,images,raw);report=review(*values)
        require(exit_code(report)==(0 if case in ('rom-ready','firmware-valid') else 1),'Unexpected handoff disposition: '+case)
        for key,value in zip(('inventory','journal','policy'),values):save(folder/(key+'.json'),value)
        save(folder/'report.json',report)
        summary.append({'case':case,'status':report['status'],'accesses':len(raw['accesses']),'completed':raw['completed'],
            'value':raw['value'],'fault':raw['fault'],'first_stack_access':report['first_stack_access'],'findings':report['findings'],'gaps':report['gaps']})
    result={'Unicorn':unicorn.__version__,'source_sha256':hashlib.sha256((MODULE/'examples/receiver.S').read_bytes()).hexdigest(),
        'cases':summary,'images':images,'reference':'Independent first push at SP-8, pop value and output store; explicit applied page-protection readiness contract.'}
    for name,tool in (('assembler',assembler),('linker',linker),('readelf',readelf)):
        result[name]=subprocess.run([tool,'--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    save(output/'summary.json',result);return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--assembler',default='as');parser.add_argument('--linker',default='ld');parser.add_argument('--readelf',default='readelf');args=parser.parse_args()
    result=run(args.directory,args.assembler,args.linker,args.readelf);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
