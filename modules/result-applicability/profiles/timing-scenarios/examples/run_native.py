"""Run owned native scenarios after freezing their independent obligation roster."""
import argparse,os,shutil,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROFILE=HERE.parent;sys.path.insert(0,str(PROFILE))
from scenario_common import VERSION,config,save,sha
from native_scenario import SOURCES,ARTIFACTS,capture,snapshot
from fixture import FAMILIES,cases,context,corpus,design,plan
from reference_model import expected

def collect(output,openroad):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);exe=Path(openroad).resolve();version=subprocess.run([str(exe),'-version'],capture_output=True,text=True,check=True).stdout.strip()
    if version!=VERSION:raise ValueError('Qualified OpenROAD version required')
    tool_sha=sha(exe);requirements=out/'requirements';requirements.mkdir();rows=[]
    for family in FAMILIES:
        save(requirements/(family+'.plan.json'),plan(family));save(requirements/(family+'.timing-failure-plan.json'),plan(family,True))
        for variant in ('complete','omitted','wrong-library','wrong-mode','unknown-mode','timing-failure'):save(requirements/(family+'.'+variant+'.corpus.json'),corpus(family,variant))
    original_requirements={p.name:sha(p) for p in requirements.iterdir()}
    with tempfile.TemporaryDirectory(prefix='opentools-sta-scenarios-') as tmp:
        tmp=Path(tmp)
        for family,mode,corner,control in cases():
            ctx=context(family,mode,corner,control);ref=ctx['run_ref'];work=tmp/ref;work.mkdir();folder=out/ref;folder.mkdir();actual_corner=('nominal' if corner=='low_voltage' else 'low_voltage') if control=='wrong-library' else corner
            shutil.copy2(HERE/'cells.lef',work/'cells.lef');shutil.copy2(HERE/('cells.'+actual_corner+'.lib'),work/'cells.lib');(work/'design.v').write_text(design(family));(work/'config.tcl').write_text(config(ctx))
            for name in SOURCES[4:]:shutil.copy2(PROFILE/name,work/name)
            sources={name:sha(work/name) for name in SOURCES}
            for name in SOURCES:shutil.copy2(work/name,folder/name)
            save(folder/'context.json',ctx);save(folder/'independent-reference.json',expected(family,mode,corner,control));context_sha=sha(folder/'context.json');reference_sha=sha(folder/'independent-reference.json')
            command=[str(exe),'-exit','-no_init','loader.tcl'];save(folder/'command.json',command);command_sha=sha(folder/'command.json');p=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=90);(folder/'stdout.txt').write_text(p.stdout);(folder/'stderr.txt').write_text(p.stderr)
            if p.returncode or 'OPENTOOLS_STA_SCENARIO_RUN_COMPLETE' not in p.stdout:raise ValueError('Native run incomplete: '+ref+'\n'+p.stdout[-2000:]+p.stderr[-1000:])
            for name in ARTIFACTS:shutil.copy2(work/name,folder/name)
            if sha(exe)!=tool_sha or any(sha(work/name)!=value or sha(folder/name)!=value for name,value in sources.items()) or sha(folder/'context.json')!=context_sha or sha(folder/'independent-reference.json')!=reference_sha or any(sha(requirements/name)!=value for name,value in original_requirements.items()):raise ValueError('Original tool/source/intent changed')
            x={'format':'opentools.sta-scenario-execution.v1','native_exit':p.returncode,'source_sha256':sources,'tool_sha256':tool_sha,'context_sha256':context_sha,'reference_sha256':reference_sha,'command_sha256':command_sha,'artifacts':{name:sha(folder/name) for name in ARTIFACTS}}
            save(folder/'execution.json',x);(folder/'openroad-version.txt').write_text(version+'\n');e=capture(folder,ctx);save(folder/'evidence.json',e);save(folder/'snapshot.json',snapshot(e));n=e['native'];reference=expected(family,mode,corner,control)
            assert n['library']['name']==reference['library'] and all(c['normalized']==reference['pvt'] and c['matches_library_default']==1 for c in n['operating'].values());assert n['cases']==reference['cases']
            assert n['clock_pins']==reference['register_clock_pins'] and n['data_pins']==reference['data_pins'] and n['output_pins']==reference['output_pins'];clock=n['clocks']['root'];assert clock['period_ns']==reference['period_ns'] and clock['pins']==reference['register_clock_pins'] and clock['sources']==['clk']
            assert len(n['paths'])==1 and n['paths'][0]['startpoint']==reference['startpoint'] and n['paths'][0]['endpoint']==reference['endpoint'] and abs(n['paths'][0]['slack_native_ns']-reference['slack_ns'])<0.00002,(ref,n['paths'],reference)
            rows.append({'family':family,'mode':mode,'corner':corner,'control':control,'run_ref':ref,'source_sha256':sources,'reference_sha256':reference_sha,'native_result':snapshot(e)['result'],'independent_reference_checked':True});print(ref+': native scenario checked',flush=True)
    save(out/'collection.json',{'native_OpenROAD_runs':len(rows),'OpenROAD_version':version,'tool_sha256':tool_sha,'original_requirements_sha256':original_requirements,'cases':rows,'limits':'Illustrative owned Liberty scalar tables and unannotated logical interconnect; actual native model/condition observations,not characterized silicon PVT or complete STA/physical-power signoff.'})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');p.add_argument('--openroad',required=True);p.add_argument('--raw-only',action='store_true');a=p.parse_args()
    if os.name!='posix':p.error('Native collection qualified on Linux; saved-data review is portable')
    collect(a.output,a.openroad)
    if not a.raw_only:
        from create_example import from_native
        from_native(a.output)
if __name__=='__main__':main()
