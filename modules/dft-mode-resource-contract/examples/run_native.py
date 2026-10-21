"""Collect owned OpenROAD scan resources and actual stitched-netlist behavior on Linux."""
import argparse,hashlib,json,os
from pathlib import Path
import shutil,subprocess,tempfile
from fixture import CASES,FAMILIES,dft_script,export_script,header,mode_sdc,roles,seed,topology,wrapper
HERE=Path(__file__).resolve().parent
OPENROAD_VERSION='v2.0-17598-ga008522d8'
BUILD=['--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','top','--Mdir','obj','top.sv','scanned.v','cells_model.sv','main.cpp']
XML=['--xml-only','-Wno-fatal','--top-module','top','--xml-output','model.xml','top.sv','scanned.v','cells_model.sv']
SOURCES=('seed.v','scanned.v','cells.lib','cells.lef','cells_model.sv','top.sv','ports.hpp','main.cpp')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2)+'\n')
def checked_native(work,executable,script,marker,env):
    command=[str(executable),'-exit','-no_init',script];r=subprocess.run(command,cwd=work,env=env,capture_output=True,text=True,timeout=90)
    text=r.stdout+r.stderr
    if r.returncode or marker not in r.stdout or any(s in text for s in ('[ERROR','Error:','Signal 11','initialization failed')):raise ValueError('Native OpenROAD task incomplete: '+script+'\n'+text[-1800:])
    return command,r
def collect(output,openroad,verilator,verilator_root):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);openroad=Path(openroad).resolve();verilator=Path(verilator).resolve();env=dict(os.environ)
    version=subprocess.run([str(openroad),'-version'],env=env,capture_output=True,text=True,check=True).stdout.strip()
    if version!=OPENROAD_VERSION:raise ValueError('Qualified OpenROAD '+OPENROAD_VERSION+' required')
    vv=subprocess.run([str(verilator),'--version'],capture_output=True,text=True,check=True).stdout.strip()
    if not vv.startswith('Verilator 5.020 '):raise ValueError('Qualified Verilator5.020 required')
    rows=[];designs=[]
    with tempfile.TemporaryDirectory(prefix='opentools-dft-resources-') as temp:
        temp=Path(temp);(temp/'runtime').symlink_to(Path(verilator_root).resolve(),target_is_directory=True);build_env=dict(env,VERILATOR_ROOT=str(temp/'runtime'))
        for family,c in FAMILIES.items():
            work=temp/family;work.mkdir();retained=out/'designs'/family;retained.mkdir(parents=True)
            for name in ('cells.lib','cells.lef','cells_model.sv','main.cpp'):shutil.copy2(HERE/name,work/name)
            (work/'seed.v').write_text(seed(c));(work/'dft.tcl').write_text(dft_script(c));(work/'export.tcl').write_text(export_script(c));(work/'mode.sdc').write_text(mode_sdc(c,CASES['supported-mask'][0],'match'))
            command,r=checked_native(work,openroad,'dft.tcl','OPENTOOLS_NATIVE_DFT_COMPLETE',env)
            save(retained/'dft.command.json',command);(retained/'dft.stdout.txt').write_text(r.stdout);(retained/'dft.stderr.txt').write_text(r.stderr)
            command,r=checked_native(work,openroad,'export.tcl','OPENTOOLS_NATIVE_RESOURCE_EXPORT_COMPLETE',env)
            (retained/'discovery.stdout.txt').write_text(r.stdout);(retained/'discovery.stderr.txt').write_text(r.stderr);save(retained/'discovery.command.json',command)
            order,positions,stop=topology((work/'resources.txt').read_text(),c)
            (work/'top.sv').write_text(wrapper(family,c,stop));(work/'ports.hpp').write_text(header(family,c,positions))
            before={p:sha(work/p) for p in SOURCES}
            for label,args in [('build',BUILD),('xml',XML)]:
                command=[str(verilator)]+args;r=subprocess.run(command,cwd=work,env=build_env,capture_output=True,text=True,timeout=180)
                save(retained/(label+'.command.json'),command);(retained/(label+'.stdout.txt')).write_text(r.stdout);(retained/(label+'.stderr.txt')).write_text(r.stderr)
                if r.returncode:raise ValueError('Native '+label+' failed: '+r.stderr[-1800:])
            for name in SOURCES+('dft.tcl','export.tcl','replaced.v','scanned.odb','scanned.def','model.xml'):
                if name in before and sha(work/name)!=before[name]:raise ValueError('Original build source changed')
                shutil.copy2(work/name,retained/name)
            shutil.copy2(work/'obj/Vtop',retained/'Vtop');(retained/'openroad-version.txt').write_text(version+'\n');(retained/'verilator-version.txt').write_text(vv+'\n')
            designs.append({'family':family,'width':c['width'],'order':order,'scan_bits':positions,'stop':stop,'source_sha256':before,'role_map':roles(family)})
            for case,(flags,kind) in CASES.items():
                folder=out/(family+'-'+case);run=folder/'run';shutil.copytree(retained,run)
                (work/'mode.sdc').write_text(mode_sdc(c,flags,kind));command,r=checked_native(work,openroad,'export.tcl','OPENTOOLS_NATIVE_RESOURCE_EXPORT_COMPLETE',env)
                for name in ('mode.sdc','resources.txt'):shutil.copy2(work/name,run/name)
                save(run/'mode.command.json',command);(run/'mode.stdout.txt').write_text(r.stdout);(run/'mode.stderr.txt').write_text(r.stderr)
                command=[str(retained/'Vtop'),*map(str,flags)];save(run/'run.command.json',command);command_sha=sha(run/'run.command.json')
                result=subprocess.run(command,cwd=run,env=build_env,capture_output=True,text=True,timeout=30)
                (run/'run.stdout.txt').write_text(result.stdout);(run/'run.stderr.txt').write_text(result.stderr)
                save(run/'execution.json',{'dft_exit':0,'mode_exit':0,'build_exit':0,'xml_exit':0,'run_exit':result.returncode,'binary_sha256':sha(run/'Vtop')})
                if result.returncode not in (0,1) or 'NATIVE_RESULT ' not in result.stdout:raise ValueError('Behavior task incomplete')
                rows.append({'case':family+'-'+case,'family':family,'flags':flags,'mode_kind':kind,'width':c['width'],'source_sha256':before,'command_sha256':command_sha,
                             'mode_sdc_sha256':sha(run/'mode.sdc'),'run_exit':result.returncode,'scan_bits':positions,'stop':stop,'role_map':roles(family)})
                print(family+'-'+case+': native resources/behavior retained',flush=True)
    record={'openroad_version':version,'verilator_version':vv,'native_dft_runs':2,'native_mode_exports':26,'native_builds':2,'native_xml_exports':2,'native_behavior_runs':len(rows),
            'designs':designs,'cases':rows,'limits':'One reset-capable chain/domain, owned ideal functional library and Boolean supply/isolation/access proxy. Explicit native root cases, same-net consequences and finite observed levels remain separate from unknown propagated values. No characterized timing, analog supply, ATPG or security-policy proof.'}
    save(out/'collection.json',record);return record
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--openroad',required=True);p.add_argument('--verilator',required=True);p.add_argument('--verilator-root',required=True);p.add_argument('--raw-only',action='store_true');a=p.parse_args()
    if os.name!='posix':p.error('Native generation is qualified on Linux; saved-data review is portable')
    collect(a.output,a.openroad,a.verilator,a.verilator_root)
    if not a.raw_only:
        from create_example import from_native
        from_native(a.output)
if __name__=='__main__':main()
