"""Collect original native graphs, selected STA coverage and clock-delivery reports."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
from fixture import CASES,FAMILIES,cells_lef,cells_lib,config,context,design,header
HERE=Path(__file__).resolve().parent;PROFILE=HERE.parent
SOURCES=('design.v','cells.lef','cells.lib','models.sv','main.cpp','bindings.hpp','export_eco.tcl','config.tcl')
BUILD=['--cc','--exe','--build','-j','1','-Wno-fatal','--top-module','top','--Mdir','obj','design.v','models.sv','main.cpp']
XML=['--xml-only','-Wno-fatal','--top-module','top','--xml-output','logical.xml','design.v','models.sv']
def sha(p):
    result=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):result.update(block)
    return result.hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2)+'\n')

def collect(output,openroad,verilator,verilator_root):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);orexe=Path(openroad).resolve();vexe=Path(verilator).resolve();env=dict(os.environ)
    version=subprocess.run([str(orexe),'-version'],env=env,capture_output=True,text=True,check=True).stdout.strip();vv=subprocess.run([str(vexe),'--version'],capture_output=True,text=True,check=True).stdout.strip()
    if version!='v2.0-17598-ga008522d8' or not vv.startswith('Verilator 5.020 '):raise ValueError('Qualified native versions required')
    tools={'openroad_sha256':sha(orexe),'verilator_sha256':sha(vexe)};rows=[]
    with tempfile.TemporaryDirectory(prefix='opentools-eco-evidence-') as tmp:
        tmp=Path(tmp);(tmp/'runtime').symlink_to(Path(verilator_root).resolve(),target_is_directory=True);venv=dict(env,VERILATOR_ROOT=str(tmp/'runtime'))
        for family,c in FAMILIES.items():
            for case in CASES:
                key=family+'-'+case;work=tmp/key;work.mkdir();folder=out/key;folder.mkdir();ctx=context(family,c,case)
                for name in ('models.sv','main.cpp'):shutil.copy2(HERE/name,work/name)
                shutil.copy2(PROFILE/'export_eco.tcl',work/'export_eco.tcl');(work/'design.v').write_text(design(c,case));(work/'cells.lef').write_text(cells_lef());(work/'cells.lib').write_text(cells_lib());(work/'bindings.hpp').write_text(header(c,case));(work/'config.tcl').write_text(config(ctx));sources={n:sha(work/n) for n in SOURCES}
                for n in SOURCES:shutil.copy2(work/n,folder/n)
                cmd=[str(orexe),'-exit','-no_init','export_eco.tcl'];save(folder/'native.command.json',cmd);command_sha=sha(folder/'native.command.json');r=subprocess.run(cmd,cwd=work,env=env,capture_output=True,text=True,timeout=90)
                (folder/'native.stdout.txt').write_text(r.stdout);(folder/'native.stderr.txt').write_text(r.stderr)
                if r.returncode or 'OPENTOOLS_ECO_NATIVE_COMPLETE' not in r.stdout or '[ERROR' in r.stdout+r.stderr:raise ValueError('Native ECO export incomplete: '+key+'\n'+r.stdout[-1400:]+r.stderr[-1000:])
                for name in ('graph.txt','sta.txt','consumed.sdc','design.odb','exported.v'):shutil.copy2(work/name,folder/name)
                for label,args in [('build',BUILD),('xml',XML)]:
                    cmd=[str(vexe),*args];save(folder/(label+'.command.json'),cmd);r=subprocess.run(cmd,cwd=work,env=venv,capture_output=True,text=True,timeout=180);(folder/(label+'.stdout.txt')).write_text(r.stdout);(folder/(label+'.stderr.txt')).write_text(r.stderr)
                    if r.returncode:raise ValueError('Native '+label+' failed: '+key+'\n'+r.stderr[-1800:])
                shutil.copy2(work/'logical.xml',folder/'logical.xml');shutil.copy2(work/'obj/Vtop',folder/'Vtop');binary_sha=sha(folder/'Vtop');cmd=[str(work/'obj/Vtop')];save(folder/'run.command.json',cmd);run_command_sha=sha(folder/'run.command.json');r=subprocess.run(cmd,cwd=work,env=venv,capture_output=True,text=True,timeout=30)
                (folder/'clock.stdout.txt').write_text(r.stdout);(folder/'clock.stderr.txt').write_text(r.stderr)
                if r.returncode not in (0,1) or 'CLOCK_RESULT ' not in r.stdout:raise ValueError('Native clock report incomplete')
                if sha(work/'obj/Vtop')!=binary_sha or any(sha(work/n)!=h or sha(folder/n)!=h for n,h in sources.items()):raise ValueError('Consumed source/binary changed')
                if sha(orexe)!=tools['openroad_sha256'] or sha(vexe)!=tools['verilator_sha256']:raise ValueError('Native executable changed during collection')
                artifacts={n:sha(folder/n) for n in ('graph.txt','sta.txt','consumed.sdc','design.odb','exported.v','logical.xml','clock.stdout.txt')}
                save(folder/'execution.json',{'native_exit':0,'build_exit':0,'xml_exit':0,'clock_exit':r.returncode,'binary_sha256':binary_sha,'sources':sources,'tools':tools,'artifacts':artifacts,'native_command_sha256':command_sha,'run_command_sha256':run_command_sha})
                save(folder/'context.json',ctx);(folder/'openroad-version.txt').write_text(version+'\n');(folder/'verilator-version.txt').write_text(vv+'\n');rows.append({'case':key,'family':family,'selection':case,'sources':sources,'binary_sha256':binary_sha,'clock_exit':r.returncode,'artifacts':artifacts});print(key+': original ECO evidence retained',flush=True)
    record={'native_OpenROAD_runs':len(rows),'native_Verilator_builds':len(rows),'native_Verilator_exports':len(rows),'native_clock_runs':len(rows),'OpenROAD_version':version,'Verilator_version':vv,'tools':tools,'cases':rows,'limits':'Owned flat single-pin endpoint rewires and two scoped report types: native selected-path presence and finite Boolean clock delivery. Not complete ECO equivalence, parasitic/route or timing signoff.'};save(out/'collection.json',record);return record

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--openroad',required=True);p.add_argument('--verilator',required=True);p.add_argument('--verilator-root',required=True);p.add_argument('--raw-only',action='store_true');a=p.parse_args()
    if os.name!='posix':p.error('Native collection is qualified on Linux; saved-data review is portable')
    collect(a.output,a.openroad,a.verilator,a.verilator_root)
    if not a.raw_only:
        from create_example import from_native
        from_native(a.output)
if __name__=='__main__':main()
