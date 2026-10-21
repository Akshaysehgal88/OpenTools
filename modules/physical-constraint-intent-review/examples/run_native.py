"""Collect original native placed experiments; no downloads or tool installation."""
import argparse,os,shutil,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;MODULE=HERE.parent;sys.path.insert(0,str(MODULE))
from physical_common import config,save,sha
from fixture import CASES,FAMILIES,context,original_intent

def collect(output,openroad):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);exe=Path(openroad).resolve()
    version=subprocess.run([str(exe),'-version'],capture_output=True,text=True,check=True).stdout.strip()
    if version!='v2.0-17598-ga008522d8':raise ValueError('Qualified native version required')
    tool_sha=sha(exe);rows=[]
    with tempfile.TemporaryDirectory(prefix='opentools-physical-review-') as tmp:
        tmp=Path(tmp)
        for family,c in FAMILIES.items():
            save(out/(family+'-intent.json'),original_intent(family))
            for case in CASES:
                key=family+'-'+case;work=tmp/key;work.mkdir();folder=out/key;folder.mkdir();ctx=context(family,case)
                for name in ('cells.lib','cells.lef'):shutil.copy2(HERE/name,work/name)
                shutil.copy2(HERE/c['design'],work/'design.v')
                for name in ('loader.tcl','export_region.tcl'):shutil.copy2(MODULE/name,work/name)
                (work/'config.tcl').write_text(config(ctx));names=('design.v','cells.lef','cells.lib','loader.tcl','export_region.tcl','config.tcl');sources={n:sha(work/n) for n in names}
                for name in names:shutil.copy2(work/name,folder/name)
                command=[str(exe),'-exit','-no_init','loader.tcl'];save(folder/'native.command.json',command);command_sha=sha(folder/'native.command.json')
                p=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=90);(folder/'native.stdout.txt').write_text(p.stdout);(folder/'native.stderr.txt').write_text(p.stderr)
                if p.returncode or 'OPENTOOLS_PHYSICAL_EXPORT_COMPLETE' not in p.stdout:raise ValueError('Native export incomplete: '+key+'\n'+p.stdout[-1800:]+p.stderr[-1200:])
                for name in ('native.jsonl','native.odb','consumed.sdc'):shutil.copy2(work/name,folder/name)
                if sha(exe)!=tool_sha or any(sha(work/n)!=v or sha(folder/n)!=v for n,v in sources.items()):raise ValueError('Native consumed source/tool changed')
                artifacts={n:sha(folder/n) for n in ('native.jsonl','native.odb','consumed.sdc')}
                e={'format':'opentools.physical-execution.v1','native_exit':p.returncode,'tool_sha256':tool_sha,'source_sha256':sources,'command_sha256':command_sha,'artifacts':artifacts}
                save(folder/'execution.json',e);save(folder/'context.json',ctx);(folder/'openroad-version.txt').write_text(version+'\n')
                rows.append({'family':family,'case':case,'run_ref':key,**e});print(key+': retained native placement experiment',flush=True)
    save(out/'collection.json',{'native_OpenROAD_runs':len(rows),'OpenROAD_version':version,'tool_sha256':tool_sha,'cases':rows,
        'limits':'Original native placement/blockage/path observations. Terminal-bbox half perimeter is derived geometry, not routed wirelength/congestion/timing improvement; no interconnect RC model.'})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');p.add_argument('--openroad',required=True);p.add_argument('--raw-only',action='store_true');a=p.parse_args()
    if os.name!='posix':p.error('Native collection is qualified on Linux; saved review is portable')
    collect(a.output,a.openroad)
    if not a.raw_only:
        from create_example import from_native
        from_native(a.output)
if __name__=='__main__':main()
