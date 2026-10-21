"""Collect native endpoint reports after freezing independent timing contracts."""
import argparse,os,shutil,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;MODULE=HERE.parent;sys.path.insert(0,str(MODULE))
from endpoint_common import VERSION,config,digest,save,sha
from native_endpoints import ARTIFACTS,SOURCES,capture
from fixture import CASES,FAMILIES,context,design,original_contract
from reference_model import expected

def collect(output,openroad):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);exe=Path(openroad).resolve();version=subprocess.run([str(exe),'-version'],capture_output=True,text=True,check=True).stdout.strip()
    if version!=VERSION:raise ValueError('Qualified native version required')
    tool_sha=sha(exe);rows=[]
    with tempfile.TemporaryDirectory(prefix='opentools-sta-endpoints-') as tmp:
        tmp=Path(tmp)
        for family in FAMILIES:
            for case in CASES:
                ctx=context(family,case);ref=ctx['run_ref'];work=tmp/ref;work.mkdir();folder=out/ref;folder.mkdir()
                for name in ('cells.lef','cells.lib'):shutil.copy2(HERE/name,work/name)
                (work/'design.v').write_text(design(family,case));(work/'config.tcl').write_text(config(ctx))
                for name in SOURCES[4:]:shutil.copy2(MODULE/name,work/name)
                sources={name:sha(work/name) for name in SOURCES}
                for name in SOURCES:shutil.copy2(work/name,folder/name)
                command=[str(exe),'-exit','-no_init','loader.tcl'];save(folder/'command.json',command);command_sha=sha(folder/'command.json');c=original_contract(ctx,sources,command_sha,case);save(folder/'context.json',ctx);save(folder/'contract.json',c);save(folder/'independent-reference.json',expected(family,case));frozen={name:sha(folder/name) for name in ('command.json','context.json','contract.json','independent-reference.json')}
                p=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=90);(folder/'stdout.txt').write_text(p.stdout);(folder/'stderr.txt').write_text(p.stderr)
                if p.returncode or 'OPENTOOLS_STA_ENDPOINT_RUN_COMPLETE' not in p.stdout:raise ValueError('Native run incomplete: '+ref+'\n'+p.stdout[-2200:]+p.stderr[-1000:])
                for name in ARTIFACTS:shutil.copy2(work/name,folder/name)
                if sha(exe)!=tool_sha or any(sha(work/name)!=value or sha(folder/name)!=value for name,value in sources.items()) or any(sha(folder/name)!=value for name,value in frozen.items()):raise ValueError('Consumed tool/source/intent changed')
                x={'format':'opentools.sta-endpoint-execution.v1','native_exit':p.returncode,'source_sha256':sources,'tool_sha256':tool_sha,'context_sha256':frozen['context.json'],'reference_sha256':frozen['independent-reference.json'],'contract_digest':digest(c),'command_sha256':command_sha,'artifacts':{name:sha(folder/name) for name in ARTIFACTS}};save(folder/'execution.json',x);(folder/'openroad-version.txt').write_text(version+'\n');e=capture(folder,ctx);save(folder/'evidence.json',e);n=e['native'];reference=expected(family,case);clock=n['clocks']['root']
                assert n['reported_unconstrained']==reference['unconstrained'] and n['clock_pins']==reference['clock_pins'] and clock['sources']==reference['clock_sources'] and clock['period_ns']==reference['period_ns'] and clock['pins']==reference['clock_members'] and n['cases']==reference['cases'],(ref,n,reference)
                assert set(n['endpoints'])==set(reference['endpoints'])
                for name,r in reference['endpoints'].items():
                    a=n['endpoints'][name];assert (a['kind'],a['reported_unconstrained'],a['path_count'],a['simulated'])==(r['kind'],r['unconstrained'],r['path_count'],r['simulated']),(ref,name,a,r)
                    if a['paths']:assert bool(a['paths'][0]['unconstrained'])==r['unconstrained']
                    if r.get('output_margin') is not None:assert a['paths'][0]['output_delay']==1 and a['paths'][0]['margin_ns']==r['output_margin']
                rows.append({'family':family,'case':case,'run_ref':ref,'source_sha256':sources,'reference_sha256':frozen['independent-reference.json'],'independent_reference_checked':True});print(ref+': native denominator/classes checked',flush=True)
    save(out/'collection.json',{'native_OpenROAD_runs':len(rows),'OpenROAD_version':version,'tool_sha256':tool_sha,'cases':rows,'limits':'Native selected-mode flat endpoint census/report and scalar path/constant observations; no full timing,physical power or signoff claim.'})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');p.add_argument('--openroad',required=True);p.add_argument('--raw-only',action='store_true');a=p.parse_args()
    if os.name!='posix':p.error('Native collection qualified on Linux; saved-data review is portable')
    collect(a.output,a.openroad)
    if not a.raw_only:
        from create_example import from_native
        from_native(a.output)
if __name__=='__main__':main()
