"""Collect cached native STA scenarios and measured OCC/shift observations on Linux."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
from fixture import CASES,FAMILIES,STA,header,selections,sta_script,unit,wrapper
HERE=Path(__file__).resolve().parent;VERSION='v2.0-17598-ga008522d8'
BEHAVIOR_SOURCES=('unit.v','top.sv','models.sv','ports.hpp','main.cpp');STA_SOURCES=('unit.v','cells.lib','cells.lef','sta.tcl')
BUILD=['--cc','--exe','--build','-j','2','--timescale','1ns/1ns','-Wno-fatal','--top-module','top','--Mdir','obj',*BEHAVIOR_SOURCES[:3],'main.cpp']
XML=['--xml-only','--timescale','1ns/1ns','-Wno-fatal','--top-module','top','--xml-output','model.xml',*BEHAVIOR_SOURCES[:3]]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2)+'\n')
def collect(output,openroad,verilator,verilator_root):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);openroad=Path(openroad).resolve();verilator=Path(verilator).resolve();version=subprocess.run([str(openroad),'-version'],capture_output=True,text=True,check=True).stdout.strip();vv=subprocess.run([str(verilator),'--version'],capture_output=True,text=True,check=True).stdout.strip()
    if version!=VERSION or not vv.startswith('Verilator 5.020 '):raise ValueError('Qualified OpenROAD/Verilator versions required')
    cases=[];jobs=[];designs=[]
    with tempfile.TemporaryDirectory(prefix='opentools-occ-handoff-') as temporary:
        temporary=Path(temporary);(temporary/'runtime').symlink_to(Path(verilator_root).resolve(),target_is_directory=True);env=dict(os.environ,VERILATOR_ROOT=str(temporary/'runtime'))
        for family,c in FAMILIES.items():
            work=temporary/family;work.mkdir();design=out/'designs'/family;design.mkdir(parents=True)
            for name in ('models.sv','main.cpp','cells.lib','cells.lef'):shutil.copy2(HERE/name,work/name)
            (work/'unit.v').write_text(unit(family,c));(work/'top.sv').write_text(wrapper(family,c));(work/'ports.hpp').write_text(header(family,c));before={n:sha(work/n) for n in BEHAVIOR_SOURCES}
            for label,args in [('build',BUILD),('xml',XML)]:
                cmd=[str(verilator),*args];result=subprocess.run(cmd,cwd=work,env=env,capture_output=True,text=True,timeout=180);save(design/(label+'.command.json'),cmd);(design/(label+'.stdout.txt')).write_text(result.stdout);(design/(label+'.stderr.txt')).write_text(result.stderr)
                if result.returncode:raise ValueError(label+' failed: '+result.stderr[-1500:])
            for name in BEHAVIOR_SOURCES+('model.xml',):shutil.copy2(work/name,design/name)
            shutil.copy2(work/'obj/Vtop',design/'Vtop');(design/'version.txt').write_text(vv+'\n');designs.append({'family':family,'sources':before,'binary_sha256':sha(design/'Vtop')})
            for key in STA:
                target=out/'sta'/(family+'-'+key);target.mkdir(parents=True);sw=temporary/(family+'-sta-'+key);sw.mkdir()
                for name in ('unit.v','cells.lib','cells.lef'):shutil.copy2(work/name,sw/name)
                (sw/'sta.tcl').write_text(sta_script(family,c,key));source_hashes={n:sha(sw/n) for n in STA_SOURCES};cmd=[str(openroad),'-exit','-no_init','sta.tcl'];save(sw/'command.json',cmd);command_sha=sha(sw/'command.json');result=subprocess.run(cmd,cwd=sw,capture_output=True,text=True,timeout=90)
                (sw/'stdout.txt').write_text(result.stdout);(sw/'stderr.txt').write_text(result.stderr)
                if result.returncode or result.stdout.count('OPENTOOLS_NATIVE_OCC_STA_COMPLETE')!=1 or any(s in result.stdout+result.stderr for s in ('[ERROR','Error:','Signal 11')):raise ValueError('STA incomplete: '+key+'\n'+result.stdout+result.stderr)
                (sw/'version.txt').write_text(version+'\n');save(sw/'execution.json',{'exit_code':result.returncode})
                for n,h in source_hashes.items():
                    if sha(sw/n)!=h:raise ValueError('Original STA input changed')
                shutil.copytree(sw,target/'run');jobs.append({'family':family,'key':key,'workdir':'sta/'+family+'-'+key+'/run','sources':source_hashes,'command_sha256':command_sha});print(family+' STA '+key+': complete',flush=True)
            for case in CASES:
                context,recipe,flags,key=selections(family,c,case);folder=out/(family+'-'+case);folder.mkdir();run=folder/'run';shutil.copytree(design,run);cmd=[str(design/'Vtop'),*map(str,flags)];save(run/'run.command.json',cmd);cmd_sha=sha(run/'run.command.json');result=subprocess.run(cmd,cwd=run,env=env,capture_output=True,text=True,timeout=30)
                (run/'run.stdout.txt').write_text(result.stdout);(run/'run.stderr.txt').write_text(result.stderr);save(run/'execution.json',{'build_exit':0,'xml_exit':0,'run_exit':result.returncode,'binary_sha256':sha(run/'Vtop')})
                if result.returncode not in (0,1) or 'NATIVE_RESULT ' not in result.stdout:raise ValueError('Behavior incomplete')
                for n,h in before.items():
                    if sha(work/n)!=h or sha(run/n)!=h:raise ValueError('Original behavior input changed')
                job=next(v for v in jobs if v['family']==family and v['key']==key);save(folder/'context.json',context);save(folder/'recipe.json',recipe)
                cases.append({'case':family+'-'+case,'family':family,'selection':case,'flags':flags,'context':context,'recipe':recipe,'behavior_workdir':family+'-'+case+'/run','sta_workdir':job['workdir'],'behavior_sources':before,'sta_sources':job['sources'],'run_command_sha256':cmd_sha,'sta_command_sha256':job['command_sha256'],'native_exit':result.returncode});print(family+' '+case+': behavior retained',flush=True)
    record={'openroad_version':version,'verilator_version':vv,'native_builds':2,'native_xml_exports':2,'native_sta_runs':len(jobs),'native_behavior_runs':len(cases),'designs':designs,'sta_jobs':jobs,'cases':cases,'limits':'Owned LOC/shift controller and ideal cell/timing model. Separate cached STA scenarios are explicitly joined to measured behavior by shared source and context. No native ATPG, characterized timing, physical pulse-quality or fault coverage qualification.'};save(out/'collection.json',record);return record
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--openroad',required=True);p.add_argument('--verilator',required=True);p.add_argument('--verilator-root',required=True);p.add_argument('--raw-only',action='store_true');a=p.parse_args()
    if os.name!='posix':p.error('Native generation is qualified on Linux; saved-data review is portable')
    collect(a.output,a.openroad,a.verilator,a.verilator_root)
    if not a.raw_only:
        from create_example import from_native
        from_native(a.output)
if __name__=='__main__':main()
