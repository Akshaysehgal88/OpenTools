"""Retain original finite stuck-at campaign exports from two owned logic contexts."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
from fixture import CASES,FAMILIES,context,header,plan,top
HERE=Path(__file__).resolve().parent
SOURCES=('fault_network.sv','top.sv','main.cpp','plans.hpp')
BUILD=['--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','top','--Mdir','obj','fault_network.sv','top.sv','main.cpp']
XML=['--xml-only','-Wno-fatal','--top-module','top','--xml-output','model.xml','fault_network.sv','top.sv']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2)+'\n')

def collect(output,verilator,verilator_root):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False);exe=Path(verilator).resolve();version=subprocess.run([str(exe),'--version'],capture_output=True,text=True,check=True).stdout.strip()
    if not version.startswith('Verilator 5.020 '):raise ValueError('Qualified Verilator5.020 required')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='opentools-fault-campaign-') as tmp:
        tmp=Path(tmp);(tmp/'runtime').symlink_to(Path(verilator_root).resolve(),target_is_directory=True);env=dict(os.environ,VERILATOR_ROOT=str(tmp/'runtime'))
        for family,c in FAMILIES.items():
            work=tmp/family;work.mkdir();design=output/'designs'/family;design.mkdir(parents=True)
            for name in ('fault_network.sv','main.cpp'):shutil.copy2(HERE/name,work/name)
            (work/'top.sv').write_text(top(family,c));(work/'plans.hpp').write_text(header(family,c));sources={name:sha(work/name) for name in SOURCES}
            for label,args in [('build',BUILD),('xml',XML)]:
                command=[str(exe),*args];r=subprocess.run(command,cwd=work,env=env,capture_output=True,text=True,timeout=180);save(design/(label+'.command.json'),command);(design/(label+'.stdout.txt')).write_text(r.stdout);(design/(label+'.stderr.txt')).write_text(r.stderr)
                if r.returncode:raise ValueError(label+' failed: '+r.stderr[-1500:])
            for name in SOURCES+('model.xml',):shutil.copy2(work/name,design/name)
            shutil.copy2(work/'obj/Vtop',design/'Vtop');(design/'version.txt').write_text(version+'\n')
            for case in CASES:
                folder=output/(family+'-'+case);folder.mkdir();run=folder/'run';shutil.copytree(design,run);p=plan(c,case);ctx=context(family,c,case);save(run/'plan.json',p);command=[str(design/'Vtop'),str(p['index'])];save(run/'run.command.json',command);plan_sha=sha(run/'plan.json');command_sha=sha(run/'run.command.json')
                r=subprocess.run(command,cwd=run,env=env,capture_output=True,text=True,timeout=30);(run/'run.stdout.txt').write_text(r.stdout);(run/'run.stderr.txt').write_text(r.stderr);save(run/'execution.json',{'build_exit':0,'xml_exit':0,'run_exit':r.returncode,'binary_sha256':sha(run/'Vtop')});save(folder/'context.json',ctx)
                if r.returncode or 'NATIVE_CHECKS ' not in r.stdout:raise ValueError('Native campaign incomplete')
                if any(sha(work/n)!=h or sha(run/n)!=h for n,h in sources.items()):raise ValueError('Frozen source changed')
                rows.append({'case':family+'-'+case,'family':family,'selection':case,'context':ctx,'plan':p,'sources':sources,'plan_sha256':plan_sha,'command_sha256':command_sha,'binary_sha256':sha(run/'Vtop')});print(family+' '+case+': native campaign retained',flush=True)
    record={'native_builds':2,'native_xml_exports':2,'native_runs':len(rows),'verilator_version':version,'cases':rows,'limits':'Finite combinational selected-site single stuck-at injection only; no commercial ATPG, transition/delay faults, full netlist pin census, scan protocol or production coverage qualification.'};save(output/'collection.json',record);return record

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--verilator',required=True);p.add_argument('--verilator-root',required=True);p.add_argument('--raw-only',action='store_true');a=p.parse_args()
    if os.name!='posix':p.error('Native generation is qualified on Linux; saved-data review is portable')
    collect(a.output,a.verilator,a.verilator_root)
    if not a.raw_only:
        from create_example import from_native
        from_native(a.output)
if __name__=='__main__':main()
