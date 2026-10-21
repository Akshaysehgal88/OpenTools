"""Collect owned combined-transition controls with an existing Linux Verilator runtime."""
import argparse,hashlib,json,os
from pathlib import Path
import shutil,subprocess,tempfile
HERE=Path(__file__).resolve().parent
ROLES={'interrupt':{'clock':'clk','reset':'por','hold':'core_reset','retain':'warm','event':'set_irq','ack':'irq_ack','pending':'pending','visible':'irq_out'},
       'maintenance':{'clock':'clock','reset':'init_n','hold':'asleep','retain':'retain','event':'flush_done','ack':'completion_ack','pending':'completion_pending','visible':'wake_out'}}
FIXTURE_CONTROLS={'interrupt':{'drop':'drop_on_hold','ack_priority':'ack_wins'},'maintenance':{'drop':'inject_drop','ack_priority':'inject_ack_priority'}}
CASES={**{s+'-'+v:(s,v,'warm','on') for s in ('separate','arrive','pending','ack-arrive','portfolio') for v in ('good','bug')},
       'cold-valid':('portfolio','good','cold','on'),'unchecked':('portfolio','bug','warm','off'),'short':('short','good','warm','on')}
SOURCES=('top.sv','ports.hpp','main.cpp')
BUILD=['--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','top','--Mdir','obj','top.sv','main.cpp']
XML=['--xml-only','-Wno-fatal','--top-module','top','--xml-output','model.xml','top.sv']
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2)+'\n')
def checksum(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('output',type=Path);ap.add_argument('--verilator',required=True);ap.add_argument('--verilator-root',required=True);ap.add_argument('--raw-only',action='store_true');a=ap.parse_args()
    if os.name!='posix':ap.error('Native generation is qualified on Linux; saved-data review is portable')
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);version=subprocess.run([a.verilator,'--version'],capture_output=True,text=True,check=True).stdout.strip()
    if not version.startswith('Verilator 5.020 '):raise ValueError('Qualified Verilator5.020 required')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='opentools-interactions-') as temp:
        temp=Path(temp);(temp/'runtime').symlink_to(Path(a.verilator_root).resolve(),target_is_directory=True);env=dict(os.environ,VERILATOR_ROOT=str(temp/'runtime'))
        for family,mapping in ROLES.items():
            work=temp/family;work.mkdir();retained=out/'builds'/family;retained.mkdir(parents=True);shutil.copy2(HERE/(family+'.sv'),work/'top.sv');shutil.copy2(HERE/'main.cpp',work/'main.cpp')
            m=dict(mapping,**FIXTURE_CONTROLS[family]);header=''.join('#define M_'+k.upper()+' '+v+'\n' for k,v in m.items())+'#define RESET_ACTIVE '+str(int(family=='interrupt'))+'\n';(work/'ports.hpp').write_text(header,encoding='utf-8')
            sources={p:checksum(work/p) for p in SOURCES}
            for label,command in [('build',BUILD),('xml',XML)]:
                cmd=[a.verilator]+command;r=subprocess.run(cmd,cwd=work,env=env,capture_output=True,text=True,timeout=180)
                save(retained/(label+'.command.json'),cmd);(retained/(label+'.stdout.txt')).write_text(r.stdout,encoding='utf-8');(retained/(label+'.stderr.txt')).write_text(r.stderr,encoding='utf-8')
                if r.returncode:raise ValueError(label+' failed: '+family)
            for p in SOURCES:
                assert checksum(work/p)==sources[p];shutil.copy2(work/p,retained/p)
            shutil.copy2(work/'model.xml',retained/'model.xml');shutil.copy2(work/'obj/Vtop',retained/'Vtop');(retained/'version.txt').write_text(version+'\n',encoding='utf-8')
            for name,args in CASES.items():
                folder=out/(family+'-'+name);run=folder/'run';shutil.copytree(retained,run);command=[str(retained/'Vtop'),*args];save(run/'run.command.json',command)
                command_sha=checksum(run/'run.command.json');r=subprocess.run(command,cwd=run,env=env,capture_output=True,text=True,timeout=30)
                (run/'run.stdout.txt').write_text(r.stdout,encoding='utf-8');(run/'run.stderr.txt').write_text(r.stderr,encoding='utf-8');save(run/'execution.json',{'build_exit':0,'xml_exit':0,'run_exit':r.returncode,'binary_sha256':checksum(run/'Vtop')})
                if r.returncode not in (0,1):raise ValueError('Native execution incomplete')
                rows.append({'case':family+'-'+name,'family':family,'selection':list(args),'run_exit':r.returncode,'source_sha256':sources,'command_sha256':command_sha});print(family+'-'+name+': native data retained',flush=True)
    save(out/'collection.json',{'version':version,'native_builds':2,'native_runs':len(rows),'cases':rows,'limits':'Owned bounded single-clock Boolean event/hold/ack transitions. Checker source and risk applicability require review; not exhaustive interaction generation or verification completeness.'})
    if not a.raw_only:
        from create_example import from_native
        from_native(out)
if __name__=='__main__':main()
