"""Collect native timing objects and original mode contracts with pinned tools."""
import argparse,os,shutil,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROFILE=HERE.parent;sys.path.insert(0,str(PROFILE))
from lineage_common import config,save,sha
from native_lineage import ARTIFACTS,SOURCES
from fixture import CASES,FAMILIES,context,design,original_contract
def collect(output,openroad):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);exe=Path(openroad).resolve();version=subprocess.run([str(exe),'-version'],capture_output=True,text=True,check=True).stdout.strip()
    if version!='v2.0-17598-ga008522d8':raise ValueError('Qualified native version required')
    tool_sha=sha(exe);rows=[]
    with tempfile.TemporaryDirectory(prefix='opentools-sta-lineage-') as tmp:
        tmp=Path(tmp)
        for family,c in FAMILIES.items():
            for case in CASES:
                ctx=context(family,case);ref=ctx['run_ref'];work=tmp/ref;work.mkdir();folder=out/ref;folder.mkdir()
                for n in ('cells.lef','cells.lib'):shutil.copy2(HERE/n,work/n)
                (work/'design.v').write_text(design(c));(work/'config.tcl').write_text(config(ctx))
                for n in ('loader.tcl','trace_clocks.tcl','export_clocks.tcl'):shutil.copy2(PROFILE/n,work/n)
                sources={n:sha(work/n) for n in SOURCES}
                for n in SOURCES:shutil.copy2(work/n,folder/n)
                save(folder/'context.json',ctx);save(folder/'contract.json',original_contract(ctx,sources));contract_sha=sha(folder/'contract.json')
                command=[str(exe),'-exit','-no_init','loader.tcl'];save(folder/'command.json',command);command_sha=sha(folder/'command.json');p=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=90);(folder/'stdout.txt').write_text(p.stdout);(folder/'stderr.txt').write_text(p.stderr)
                if p.returncode or 'OPENTOOLS_STA_LINEAGE_RUN_COMPLETE' not in p.stdout or 'OPENTOOLS_STA_LINEAGE_EXPORT_COMPLETE' not in p.stdout:raise ValueError('Native run incomplete: '+ref+'\n'+p.stdout[-1800:]+p.stderr[-1200:])
                for n in ARTIFACTS:shutil.copy2(work/n,folder/n)
                if sha(exe)!=tool_sha or any(sha(work/n)!=v or sha(folder/n)!=v for n,v in sources.items()) or sha(folder/'contract.json')!=contract_sha:raise ValueError('Consumed tool/source/contract changed')
                e={'format':'opentools.sta-lineage-execution.v1','native_exit':p.returncode,'source_sha256':sources,'tool_sha256':tool_sha,
                   'command_sha256':command_sha,'contract_sha256':contract_sha,'artifacts':{n:sha(folder/n) for n in ARTIFACTS}}
                save(folder/'execution.json',e);(folder/'openroad-version.txt').write_text(version+'\n');rows.append({'family':family,'case':case,'run_ref':ref,**e});print(ref+': native clock objects retained',flush=True)
    save(out/'collection.json',{'native_OpenROAD_runs':len(rows),'OpenROAD_version':version,'tool_sha256':tool_sha,'cases':rows,
       'limits':'Native timing definitions, resolved explicit constructor inputs and clock-pin coverage only; no physical waveform, actual power/reset readiness, CDC/RDC or timing signoff.'})
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');p.add_argument('--openroad',required=True);p.add_argument('--raw-only',action='store_true');a=p.parse_args()
    if os.name!='posix':p.error('Native collection qualified on Linux; saved-data review is portable')
    collect(a.output,a.openroad)
    if not a.raw_only:
        from create_example import from_native
        from_native(a.output)
if __name__=='__main__':main()
