"""Collect original native memory geometry and test/repair/first-access transactions."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
from fixture import CASES,FAMILIES,context,header,plan,policy,top
HERE=Path(__file__).resolve().parent;PARENT=HERE.parents[2]
SOURCES=('ecc_profile.sv','memory_bank.sv','top.sv','main.cpp','plans.hpp')
BUILD=['--cc','--exe','--build','-j','2','--timescale','1ns/1ns','-Wno-fatal','--top-module','top','--Mdir','obj','ecc_profile.sv','memory_bank.sv','top.sv','main.cpp']
XML=['--xml-only','--timescale','1ns/1ns','-Wno-fatal','--top-module','top','--xml-output','model.xml','ecc_profile.sv','memory_bank.sv','top.sv']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2)+'\n')
def collect(output,verilator,verilator_root):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);exe=Path(verilator).resolve();version=subprocess.run([str(exe),'--version'],capture_output=True,text=True,check=True).stdout.strip()
    if not version.startswith('Verilator 5.020 '):raise ValueError('Qualified Verilator5.020 required')
    rows=[];designs=[]
    with tempfile.TemporaryDirectory(prefix='opentools-test-repair-') as temporary:
        temporary=Path(temporary);(temporary/'runtime').symlink_to(Path(verilator_root).resolve(),target_is_directory=True);env=dict(os.environ,VERILATOR_ROOT=str(temporary/'runtime'))
        for family,c in FAMILIES.items():
            work=temporary/family;work.mkdir();design=out/'designs'/family;design.mkdir(parents=True)
            shutil.copy2(PARENT/'examples/ecc_profile.sv',work/'ecc_profile.sv')
            for name in ('memory_bank.sv','main.cpp'):shutil.copy2(HERE/name,work/name)
            (work/'top.sv').write_text(top(family,c));(work/'plans.hpp').write_text(header(family,c));before={n:sha(work/n) for n in SOURCES}
            for label,args in [('build',BUILD),('xml',XML)]:
                cmd=[str(exe),*args];r=subprocess.run(cmd,cwd=work,env=env,capture_output=True,text=True,timeout=180);save(design/(label+'.command.json'),cmd);(design/(label+'.stdout.txt')).write_text(r.stdout);(design/(label+'.stderr.txt')).write_text(r.stderr)
                if r.returncode:raise ValueError(label+' failed: '+r.stderr[-1800:])
            for n in SOURCES+('model.xml',):shutil.copy2(work/n,design/n)
            shutil.copy2(work/'obj/Vtop',design/'Vtop');(design/'version.txt').write_text(version+'\n');designs.append({'family':family,'sources':before,'binary_sha256':sha(design/'Vtop')})
            for case in CASES:
                folder=out/(family+'-'+case);folder.mkdir();run=folder/'run';shutil.copytree(design,run);p=plan(family,c,case);ctx=context(family,c,case);pol=policy(family,c,case);save(run/'plan.json',p);cmd=[str(design/'Vtop'),str(p['case_index'])];save(run/'run.command.json',cmd);command_sha=sha(run/'run.command.json');r=subprocess.run(cmd,cwd=run,env=env,capture_output=True,text=True,timeout=30)
                (run/'run.stdout.txt').write_text(r.stdout);(run/'run.stderr.txt').write_text(r.stderr);save(run/'execution.json',{'build_exit':0,'xml_exit':0,'run_exit':r.returncode,'binary_sha256':sha(run/'Vtop')})
                if r.returncode not in (0,1) or 'NATIVE_RESULT ' not in r.stdout:raise ValueError('Native transaction run incomplete')
                for n,h in before.items():
                    if sha(work/n)!=h or sha(run/n)!=h:raise ValueError('Original native source changed')
                save(folder/'context.json',ctx);save(folder/'policy.json',pol);rows.append({'case':family+'-'+case,'family':family,'selection':case,'context':ctx,'policy':pol,'plan':p,'sources':before,'plan_sha256':sha(run/'plan.json'),'command_sha256':command_sha,'native_exit':r.returncode});print(family+' '+case+': native handoff retained',flush=True)
    record={'verilator_version':version,'native_builds':2,'native_xml_exports':2,'native_runs':len(rows),'designs':designs,'cases':rows,'limits':'Owned one-command-port32/39SECDED memory, one optional repair entry and one test-to-functional transition. Native XML geometry and actual words/owners/maps are evidence; no foundry repair format, MBIST algorithm/fault coverage or physical initialization certification.'};save(out/'collection.json',record);return record
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--verilator',required=True);p.add_argument('--verilator-root',required=True);p.add_argument('--raw-only',action='store_true');a=p.parse_args()
    if os.name!='posix':p.error('Native generation is qualified on Linux; saved-data review is portable')
    collect(a.output,a.verilator,a.verilator_root)
    if not a.raw_only:
        from create_example import from_native
        from_native(a.output)
if __name__=='__main__':main()
