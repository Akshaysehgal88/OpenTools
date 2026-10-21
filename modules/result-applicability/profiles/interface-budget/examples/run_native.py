"""Analyze actual block A, block B and integrated paths with frozen budgets."""
import argparse,os,shutil,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROFILE=HERE.parent;sys.path.insert(0,str(PROFILE))
from budget_common import VERSION,VIEWS,config,digest,save,sha
from native_budget import SOURCES,ARTIFACTS,capture,snapshot
from fixture import CASES,FAMILIES,context,design,original_contract
from reference_model import expected

def collect(output,openroad,selections=None):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);exe=Path(openroad).resolve();version=subprocess.run([str(exe),'-version'],capture_output=True,text=True,check=True).stdout.strip()
    if version!=VERSION:raise ValueError('Qualified native version required')
    tool_sha=sha(exe);packets=out/'packets';packets.mkdir();rows=[];packet_rows=[]
    selected=selections if selections is not None else [(family,case) for family in FAMILIES for case in CASES]
    with tempfile.TemporaryDirectory(prefix='opentools-interface-budget-') as tmp:
        tmp=Path(tmp)
        for family,case in selected:
            descriptors={}
            for view in VIEWS:
                ctx=context(family,case,view);ref=ctx['run_ref'];work=tmp/ref;work.mkdir();folder=out/ref;folder.mkdir()
                shutil.copy2(HERE/'cells.lef',work/'cells.lef');lib=(HERE/'cells.lib').read_text()
                if case=='wrong-model' and view=='upstream':lib=lib.replace('values ("0.11")','values ("0.06")')
                (work/'cells.lib').write_text(lib);(work/'design.v').write_text(design(family,case,view));(work/'config.tcl').write_text(config(ctx))
                for name in SOURCES[4:]:shutil.copy2(PROFILE/name,work/name)
                sources={name:sha(work/name) for name in SOURCES}
                for name in SOURCES:shutil.copy2(work/name,folder/name)
                command=[str(exe),'-exit','-no_init','loader.tcl'];save(folder/'command.json',command);save(folder/'context.json',ctx);save(folder/'independent-reference.json',expected(family,case,view))
                descriptors[view]={'context':ctx,'sources':sources,'command_sha256':sha(folder/'command.json'),'folder':folder,'work':work,'command':command}
            contract=original_contract(family,case,descriptors);packet_ref=family+'-'+case;save(packets/(packet_ref+'.json'),contract);contract_sha=sha(packets/(packet_ref+'.json'))
            for view,d in descriptors.items():
                folder,work,ctx=d['folder'],d['work'],d['context'];ref=ctx['run_ref'];frozen={name:sha(folder/name) for name in ('context.json','command.json','independent-reference.json')}
                p=subprocess.run(d['command'],cwd=work,capture_output=True,text=True,timeout=90);(folder/'stdout.txt').write_text(p.stdout);(folder/'stderr.txt').write_text(p.stderr)
                for name in ARTIFACTS:
                    if (work/name).is_file():shutil.copy2(work/name,folder/name)
                if p.returncode or 'OPENTOOLS_INTERFACE_BUDGET_RUN_COMPLETE' not in p.stdout:raise ValueError('Native run incomplete: '+ref+'\n'+p.stdout[-2300:]+p.stderr[-1000:])
                if sha(exe)!=tool_sha or sha(packets/(packet_ref+'.json'))!=contract_sha or any(sha(work/name)!=value or sha(folder/name)!=value for name,value in d['sources'].items()) or any(sha(folder/name)!=value for name,value in frozen.items()):raise ValueError('Original tool/source/contract changed')
                x={'format':'opentools.interface-budget-execution.v1','native_exit':p.returncode,'source_sha256':d['sources'],'tool_sha256':tool_sha,'command_sha256':d['command_sha256'],'context_sha256':frozen['context.json'],'reference_sha256':frozen['independent-reference.json'],'contract_digest':digest(contract),'artifacts':{name:sha(folder/name) for name in ARTIFACTS}};save(folder/'execution.json',x);(folder/'openroad-version.txt').write_text(version+'\n');e=capture(folder,ctx);save(folder/'evidence.json',e);save(folder/'snapshot.json',snapshot(e));n=e['native'];r=expected(family,case,view);p=n['paths'][0]
                for key in ('slack_ns','arrival_ns','required_ns','margin_ns','target_time_ns'):assert abs(p[key]-r[key])<.00002,(ref,key,p,r)
                assert n['report']['source_edge']['time_ns']==r['source_time_ns'] and n['report']['source_edge']['transition']==r['source_transition'] and n['report']['target_edge']['transition']==r['target_transition'] and n['cases']==r['cases']
                assert p['output_delay']==r['output_delay'] and p['check']==r['check'] and sum(m=='ECO_BUF' for m in n['cells'].values())==r['buffer_cells']
                if view!='top':assert n['report']['input_delay_ns']==r['input_delay_ns'] and all(v=={'pin_pF':r['load_pF'],'wire_pF':0.0} for v in n['port_cap'].values())
                else:assert n['bridge_net']['pin_cap_pF']==.05 and n['sink_net']['pin_cap_pF']==.05
                rows.append({'family':family,'case':case,'view':view,'run_ref':ref,'source_sha256':d['sources'],'reference_sha256':frozen['independent-reference.json'],'native_outcome':snapshot(e)['result']['outcome'],'independent_reference_checked':True});print(ref+': native block/top path checked',flush=True)
            packet_rows.append({'family':family,'case':case,'packet_ref':packet_ref,'contract':'packets/'+packet_ref+'.json','contract_sha256':contract_sha})
    save(out/'collection.json',{'native_OpenROAD_runs':len(rows),'interface_packets':len(packet_rows),'OpenROAD_version':version,'tool_sha256':tool_sha,'cases':rows,'packets':packet_rows,'limits':'Actual selected native block/top paths and mapped scalar buffer cones under explicit ns/pF/reference edges. Owned scalar models/unannotated interconnect;no physical,all-path,frequency or signoff claim.'})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');p.add_argument('--openroad',required=True);p.add_argument('--raw-only',action='store_true');a=p.parse_args()
    if os.name!='posix':p.error('Native collection qualified on Linux;saved review is portable')
    collect(a.output,a.openroad)
    if not a.raw_only:
        from create_example import from_native
        from_native(a.output)
if __name__=='__main__':main()
