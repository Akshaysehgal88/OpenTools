"""Collect native macro-view exports and independent logical-wrapper elaboration."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
from fixture import CASES,FAMILIES,context,lef,liberty,model,selection,wrapper
HERE=Path(__file__).resolve().parent;MODULE=HERE.parent
OPENROAD_VERSION='v2.0-17598-ga008522d8'
SOURCES=('macro.lef','macro.lib','netlist.v','wrapper.sv','macro_model.sv','export_views.tcl','select.tcl')
XML=['--xml-only','-Wno-fatal','--top-module','top','--xml-output','logical.xml','wrapper.sv','macro_model.sv']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2)+'\n')

def collect(output,openroad,verilator,verilator_root):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);orexe=Path(openroad).resolve();vexe=Path(verilator).resolve();env=dict(os.environ)
    version=subprocess.run([str(orexe),'-version'],env=env,capture_output=True,text=True,check=True).stdout.strip();vv=subprocess.run([str(vexe),'--version'],capture_output=True,text=True,check=True).stdout.strip()
    if version!=OPENROAD_VERSION or not vv.startswith('Verilator 5.020 '):raise ValueError('Qualified native versions required')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='opentools-macro-views-') as temp:
        temp=Path(temp);(temp/'runtime').symlink_to(Path(verilator_root).resolve(),target_is_directory=True);venv=dict(env,VERILATOR_ROOT=str(temp/'runtime'))
        for family,c in FAMILIES.items():
            logical=temp/(family+'-logical');logical.mkdir();(logical/'wrapper.sv').write_text(wrapper(c));(logical/'macro_model.sv').write_text(model(c));command=[str(vexe),*XML];r=subprocess.run(command,cwd=logical,env=venv,capture_output=True,text=True,timeout=90)
            if r.returncode:raise ValueError('Logical elaboration failed: '+r.stderr[-1000:])
            design=out/'logical'/family;design.mkdir(parents=True);save(design/'logical.command.json',command);(design/'logical.stdout.txt').write_text(r.stdout);(design/'logical.stderr.txt').write_text(r.stderr)
            for name in ('wrapper.sv','macro_model.sv','logical.xml'):shutil.copy2(logical/name,design/name)
            for case in CASES:
                folder=out/(family+'-'+case);folder.mkdir();work=temp/(family+'-'+case);work.mkdir()
                for name in ('wrapper.sv','macro_model.sv','logical.xml','logical.command.json','logical.stdout.txt','logical.stderr.txt'):shutil.copy2(design/name,work/name)
                (work/'macro.lef').write_text(lef(c,case));(work/'macro.lib').write_text(liberty(c,case));(work/'netlist.v').write_text(wrapper(c,case));(work/'select.tcl').write_text(selection(c,case));shutil.copy2(MODULE/'export_views.tcl',work/'export_views.tcl');sources={n:sha(work/n) for n in SOURCES}
                command=[str(orexe),'-exit','-no_init','select.tcl'];save(folder/'native.command.json',command);command_sha=sha(folder/'native.command.json');r=subprocess.run(command,cwd=work,env=env,capture_output=True,text=True,timeout=90)
                (folder/'native.stdout.txt').write_text(r.stdout);(folder/'native.stderr.txt').write_text(r.stderr)
                if r.returncode or 'OPENTOOLS_MACRO_EXPORT_COMPLETE' not in r.stdout or any(t in r.stdout+r.stderr for t in ('[ERROR','Error:','Signal 11')):raise ValueError('Native view export incomplete: '+family+' '+case+'\n'+r.stdout[-2200:]+r.stderr[-1000:])
                for name in SOURCES+('logical.xml','logical.command.json','logical.stdout.txt','logical.stderr.txt','native.jsonl','native.odb'):
                    if name in sources and sha(work/name)!=sources[name]:raise ValueError('Frozen source changed')
                    shutil.copy2(work/name,folder/name)
                (folder/'openroad-version.txt').write_text(version+'\n');(folder/'verilator-version.txt').write_text(vv+'\n');save(folder/'execution.json',{'native_exit':r.returncode,'logical_exit':0,'database_sha256':sha(folder/'native.odb')});ctx=context(family,c,case);save(folder/'context.json',ctx)
                rows.append({'case':family+'-'+case,'family':family,'selection':case,'context':ctx,'sources':sources,'command_sha256':command_sha,'logical_xml_sha256':sha(folder/'logical.xml'),'database_sha256':sha(folder/'native.odb')});print(family+' '+case+': native views retained',flush=True)
    record={'native_OpenROAD_runs':len(rows),'native_Verilator_exports':2,'OpenROAD_version':version,'Verilator_version':vv,'cases':rows,'limits':'Two owned scalar-port macro classes; native physical/timing objects and logical elaboration, not characterized memory/clock behavior, DRC/LVS/routability or production approval.'};save(out/'collection.json',record);return record

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--openroad',required=True);p.add_argument('--verilator',required=True);p.add_argument('--verilator-root',required=True);p.add_argument('--raw-only',action='store_true');a=p.parse_args()
    if os.name!='posix':p.error('Native generation is qualified on Linux; saved-data review is portable')
    collect(a.output,a.openroad,a.verilator,a.verilator_root)
    if not a.raw_only:
        from create_example import from_native
        from_native(a.output)
if __name__=='__main__':main()
