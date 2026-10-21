"""Collect original static analyses and requests; tools are configured separately."""
import argparse,os,shutil,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;MODULE=HERE.parent;sys.path.insert(0,str(MODULE))
from supply_common import BASIS,CLAIMS,config,save,sha,source_csv
from native_supply import FIXED,OPTIONAL,SOURCES
from fixture import CASES,FAMILIES,context,design,library,point
def original_request(ctx,sources,tool_sha,p):
    run=ctx['run_ref'];return {'format':'opentools.supply-request.v1','claim_id':run+'/static-basis',
      'claim':'Review applicability of this selected static supply scenario. No dynamic wake, lifetime, load-model or signoff claim.',
      'scope_ref':ctx['scope_ref'],'source_ref':run+'/request.json','owner_ref':ctx['owner_ref'],'inputs_complete':True,
      'basis':{k:ctx[k] for k in BASIS},'required_claims':{k:False for k in CLAIMS},
      'fields':{**{'source/'+k:sources[k] for k in ('cells.lef','cells.lib','design.def')},
         'setup':ctx['setup'],'scenario':ctx['scenario'],'tool_sha256':tool_sha,
         'configuration':{k:ctx[k] for k in ('design_ref','configuration_ref')},'point':p}}
def collect(output,openroad):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);exe=Path(openroad).resolve();version=subprocess.run([str(exe),'-version'],capture_output=True,text=True,check=True).stdout.strip()
    if version!='v2.0-17598-ga008522d8':raise ValueError('Qualified native version required')
    tool_sha=sha(exe);rows=[]
    with tempfile.TemporaryDirectory(prefix='opentools-static-supply-') as tmp:
        tmp=Path(tmp)
        for family in FAMILIES:
            for case in CASES:
                ctx=context(family,case);ref=ctx['run_ref'];folder=out/ref;folder.mkdir();work=tmp/ref;work.mkdir()
                shutil.copy2(HERE/'cells.lef',work/'cells.lef');(work/'cells.lib').write_text(library(family,case));(work/'design.def').write_text(design(family,case));(work/'config.tcl').write_text(config(ctx));(work/'sources.csv').write_text(source_csv(ctx))
                for n in ('loader.tcl','export_supply.tcl'):shutil.copy2(MODULE/n,work/n)
                sources={n:sha(work/n) for n in SOURCES}
                for n in SOURCES:shutil.copy2(work/n,folder/n)
                save(folder/'context.json',ctx);request=original_request(ctx,sources,tool_sha,point(family,case));save(folder/'request.json',request);request_sha=sha(folder/'request.json')
                command=[str(exe),'-exit','-no_init','loader.tcl'];save(folder/'command.json',command);command_sha=sha(folder/'command.json');p=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=90);(folder/'stdout.txt').write_text(p.stdout);(folder/'stderr.txt').write_text(p.stderr)
                if p.returncode or 'OPENTOOLS_SUPPLY_RUN_COMPLETE' not in p.stdout or 'OPENTOOLS_SUPPLY_EXPORT_COMPLETE' not in p.stdout:raise ValueError('Native run incomplete: '+ref+'\n'+p.stdout[-1600:]+p.stderr[-1200:])
                artifacts={}
                for n in (*FIXED,*OPTIONAL):
                    if (work/n).exists():shutil.copy2(work/n,folder/n);artifacts[n]=sha(folder/n)
                    elif n in FIXED:raise ValueError('Native output missing: '+n)
                if any(sha(work/n)!=v or sha(folder/n)!=v for n,v in sources.items()) or sha(exe)!=tool_sha or sha(folder/'request.json')!=request_sha:raise ValueError('Original tool/source/request changed')
                execution={'format':'opentools.supply-execution.v1','native_exit':p.returncode,'source_sha256':sources,'tool_sha256':tool_sha,'command_sha256':command_sha,'request_sha256':request_sha,'artifacts':artifacts}
                save(folder/'execution.json',execution);(folder/'openroad-version.txt').write_text(version+'\n');rows.append({'family':family,'case':case,'run_ref':ref,**execution});print(ref+': original static evidence retained',flush=True)
    save(out/'collection.json',{'native_OpenROAD_runs':len(rows),'OpenROAD_version':version,'tool_sha256':tool_sha,'cases':rows,'limits':'Owned static supply loading and native physical continuity. No dynamic IR, wake transient, electromigration lifetime, load-model validity or full-chip signoff.'})
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');p.add_argument('--openroad',required=True);p.add_argument('--raw-only',action='store_true');a=p.parse_args()
    if os.name!='posix':p.error('Native collection qualified on Linux; saved review is portable')
    collect(a.output,a.openroad)
    if not a.raw_only:
        from create_example import from_native
        from_native(a.output)
if __name__=='__main__':main()
