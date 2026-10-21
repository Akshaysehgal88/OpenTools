"""Retain actual OpenROAD runs, original intent and independently checked populations."""
import argparse,os,shutil,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROFILE=HERE.parent;sys.path.insert(0,str(PROFILE))
from reach_common import VERSION,config,digest,save,sha
from native_reach import ARTIFACTS,SOURCES,capture
from fixture import CASES,FAMILIES,context,design,original_contract,requirements
from reference_model import expected

def collect(output,openroad):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);exe=Path(openroad).resolve();version=subprocess.run([str(exe),'-version'],capture_output=True,text=True,check=True).stdout.strip()
    if version!=VERSION:raise ValueError('Qualified native version required')
    tool_sha=sha(exe);rows=[]
    with tempfile.TemporaryDirectory(prefix='opentools-sta-exception-') as tmp:
        tmp=Path(tmp)
        for family in FAMILIES:
            for case in CASES:
                ctx=context(family,case);ref=ctx['run_ref'];work=tmp/ref;work.mkdir();folder=out/ref;folder.mkdir()
                for name in ('cells.lef','cells.lib'):shutil.copy2(HERE/name,work/name)
                (work/'design.v').write_text(design(family,case));(work/'config.tcl').write_text(config(ctx))
                for name in SOURCES[4:]:shutil.copy2(PROFILE/name,work/name)
                sources={name:sha(work/name) for name in SOURCES}
                for name in SOURCES:shutil.copy2(work/name,folder/name)
                command=[str(exe),'-exit','-no_init','loader.tcl'];save(folder/'command.json',command);command_sha=sha(folder/'command.json')
                contract=original_contract(ctx,sources,command_sha);save(folder/'context.json',ctx);save(folder/'requirements.json',requirements(family,case));save(folder/'contract.json',contract);save(folder/'independent-reference.json',expected(family,case))
                frozen={name:sha(folder/name) for name in ('contract.json','requirements.json','independent-reference.json','context.json','command.json')}
                p=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=90);(folder/'stdout.txt').write_text(p.stdout);(folder/'stderr.txt').write_text(p.stderr)
                if p.returncode or 'OPENTOOLS_STA_EXCEPTION_RUN_COMPLETE' not in p.stdout:raise ValueError('Native run incomplete: '+ref+'\n'+p.stdout[-2200:]+p.stderr[-1200:])
                for name in ARTIFACTS:shutil.copy2(work/name,folder/name)
                if sha(exe)!=tool_sha or any(sha(work/name)!=value or sha(folder/name)!=value for name,value in sources.items()) or any(sha(folder/name)!=value for name,value in frozen.items()):raise ValueError('Consumed tool/source/original intent changed')
                execution={'format':'opentools.sta-exception-execution.v1','native_exit':p.returncode,'source_sha256':sources,'tool_sha256':tool_sha,'command_sha256':command_sha,'contract_digest':digest(contract),'original_documents':frozen,'artifacts':{name:sha(folder/name) for name in ARTIFACTS}}
                save(folder/'execution.json',execution);(folder/'openroad-version.txt').write_text(version+'\n');e=capture(folder,ctx);save(folder/'evidence.json',e)
                n=e['native'];reference=expected(family,case)
                assert n['selectors']=={'from':reference['from'],'to':reference['to']}
                for phase in ('before','after'):
                    actual=n['phases'][phase];assert sorted({x['startpoint']+'->'+x['endpoint'] for x in actual['paths']})==reference[phase];assert actual['cases']==reference['cases']
                    assert {pin:sorted(k for k,c in actual['clocks'].items() if pin in c['pins']) for pin in actual['clock_pins']}==reference['membership']
                    assert actual['data_pins']==reference['data_pins'] and actual['output_pins']==reference['output_pins']
                assert len(n['applications'])==reference['application_count']
                rows.append({'family':family,'case':case,'run_ref':ref,'source_sha256':sources,'independent_reference_checked':True});print(ref+': native populations checked',flush=True)
    save(out/'collection.json',{'native_OpenROAD_runs':len(rows),'OpenROAD_version':version,'tool_sha256':tool_sha,'cases':rows,'limits':'Native setup endpoint-pair reach only; original fixture rationale is not a production approval.'})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');p.add_argument('--openroad',required=True);p.add_argument('--raw-only',action='store_true');a=p.parse_args()
    if os.name!='posix':p.error('Native run qualified on Linux; saved-data review is portable')
    collect(a.output,a.openroad)
    if not a.raw_only:
        from create_example import from_native
        from_native(a.output)
if __name__=='__main__':main()
