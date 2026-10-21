"""Create source-backed interaction review records from retained owned native runs."""
import argparse,copy,json
from pathlib import Path
import shutil,sys
PROFILE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROFILE))
from interaction_core import EXPECT,exit_code,markdown,review
from saved_native import capture,file_hash
from run_native import ROLES
from reference_model import expected
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2)+'\n')
def context_for(row):
    family=row['family'];name=row['case'];_,variant,mode,_=row['selection'];m=ROLES[family]
    return {'format':'opentools.interaction-capture-context.v1','run_ref':'owned:'+name,'scope_ref':'owned:'+family+':shared-pending-transition','configuration_ref':'owned:'+family+':'+variant+':'+mode,
            'model_ref':'owned:'+family+':pending-bit-model','scenario_ref':'owned:'+name+':original-execution','scenario_basis_ref':'owned:source-reviewed-owned-scenario-input-schedule',
            'clock_ref':'top.'+m['clock'],'reset_ref':'top.'+m['reset'],'reset_active':int(family=='interrupt'),'port_map':m,'window_ref':'owned:'+name+':complete-contiguous-window',
            'instrumentation_review_ref':'owned:source-reviewed-pre-post-top-port-journal-independent-of-checker-enable','oracle_ref':'owned:independent-retained-event-contract-and-expected-state-model',
            'scope_basis_ref':'owned:one-Boolean-event-store-single-positive-clock','dependencies_complete':True,'dependency_basis_ref':'owned:three-retained-inputs-and-existing-pinned-runtime'}
def run_expectation(row):
    ctx=context_for(row);return {k:row['source_sha256'] if k=='sources' else row['command_sha256'] if k=='command_sha256' else ctx[k] for k in EXPECT}
def obligation(name,title,trigger,source_sha,configuration_ref,cold=False):
    conditional=name!='ack-new-arrival';facts={'retain':0 if cold else 1} if conditional else {}
    return {'id':name,'title':title,'definition_ref':'owned:CONTRACT.md#'+name,'owner_ref':'owned:receiving-scenario-review-owner',
            'relationship':{'resource_ref':'owned:single-pending-store','producer_ref':'owned:source-event','consumer_ref':'owned:consumer-hold-and-ack',
                            'risk_ref':'owned:pending-retention-and-clear-set-priority','source_ref':'examples/CONTRACT.md','revision_ref':'owned:CONTRACT.md-sha256:'+file_hash(Path(__file__).parent/'CONTRACT.md'),
                            'design_source_sha256':source_sha,'configuration_ref':configuration_ref},
            'applicability':{'status':'not_applicable' if cold and conditional else 'applicable','facts':facts,'basis_ref':'owned:explicit-retain-or-cold-discard-policy',
                             'reviewer_ref':'owned:known-fixture-reviewer-not-production-approval','reason':'Cold hold explicitly permits discard; ACK/new arrival remains required.' if cold and conditional else 'The shared pending bit participates in both selected operations.'},
            'trigger':trigger,'after':5,'checkers':[{'id':'state_model','observed':'post_pending','basis_ref':'owned:expected-state-checker-source'},
                                                   {'id':'delivery_model','observed':'post_visible','basis_ref':'owned:expected-visible-checker-source'}]}
def term(field,equals,offset=0):return {'field':field,'offset':offset,'equals':equals}
def plan_for(name,rows):
    ctx=context_for(rows[0]);cold=rows[0]['selection'][2]=='cold'
    return {'format':'opentools.interaction-obligations.v1','review_ref':'owned:'+name+':review','claim':'The three explicitly selected shared-state interaction obligations have applicable retained scenario and native checker evidence.',
            'scope_ref':ctx['scope_ref'],'configuration_ref':ctx['configuration_ref'],'model_ref':ctx['model_ref'],'owner_ref':'owned:scenario-closure-owner','population_ref':'owned:three-CONTRACT.md-shared-state-interactions',
            'population_complete':True,'basis_ref':'owned:CONTRACT.md-independent-three-interaction-roster','scope_facts':{'retain':{'value':int(not cold),'basis_ref':'owned:explicit-warm-or-cold-configuration-contract'}},
            'runs':[run_expectation(row) for row in rows],
            'obligations':[obligation('arrival-under-hold','Event arrives while consumer is held',[term('hold',1),term('event',1)],rows[0]['source_sha256']['top.sv'],ctx['configuration_ref'],cold),
                           obligation('pending-enters-hold','Pending work enters consumer hold',[term('hold',1),term('hold',0,-1),term('post_pending',1,-1)],rows[0]['source_sha256']['top.sv'],ctx['configuration_ref'],cold),
                           obligation('ack-new-arrival','New arrival coincides with old-work acknowledgement',[term('hold',0),term('ack',1),term('event',1),term('pre_pending',1)],rows[0]['source_sha256']['top.sv'],ctx['configuration_ref'],cold)]}
def report_packet(folder,name,rows,paths):
    plan=plan_for(name,rows);corpus={'format':'opentools.interaction-evidence-corpus.v1','complete':True,'evidence_ref':'owned:'+name+':original-selected-scenario-manifest',
                                  'runs':[{'path':p,'sha256':file_hash(folder/p)} for p in paths]};r=review(plan,corpus,folder)
    save(folder/'plan.json',plan);save(folder/'corpus.json',corpus);save(folder/'report.json',r);(folder/'report.md').write_text(markdown(r),encoding='utf-8',newline='\n');return r
def from_native(root):
    root=Path(root);collection=json.loads((root/'collection.json').read_text(encoding='utf-8'));rows=[];by_name={r['case']:r for r in collection['cases']}
    for row in collection['cases']:
        name=row['case'];folder=root/name;ctx=context_for(row);e=capture(folder,'run',ctx);ref=expected(row['family'],row['selection'])
        assert e['frames']==ref['frames'] and e['checks']==ref['checks'] and e['native']['counts']==ref['counts'],name+' independent reference differs'
        save(folder/'capture-context.json',ctx);save(folder/'native.json',e);save(folder/'independent-reference.json',ref);r=report_packet(folder,name,[row],['native.json'])
        scenario,variant,mode,checkers=row['selection'];wanted=0 if scenario=='portfolio' and variant=='good' else 1 if variant=='bug' and scenario!='separate' else 2
        assert exit_code(r)==wanted,(name,r['findings'],r['gaps']);rows.append({'case':name,'native_status':e['native']['status'],'status':r['status'],'exit':exit_code(r),'obligations':{o['id']:o['status'] for o in r['obligations']}});print(name+': '+r['status'],flush=True)
    for family in ROLES:
        for variant in ('good','bug'):
            name=family+'-joined-'+variant;folder=root/name;folder.mkdir();selected=[by_name[family+'-'+s+'-'+variant] for s in ('arrive','pending','ack-arrive')];paths=[]
            for row in selected:
                source=root/row['case'];target=folder/'evidence'/row['case'];shutil.copytree(source/'run',target/'run');shutil.copy2(source/'native.json',target/'native.json');paths.append('evidence/'+row['case']+'/native.json')
            r=report_packet(folder,name,selected,paths);assert exit_code(r)==(0 if variant=='good' else 1)
            rows.append({'case':name,'native_status':'mixed-retained-original-runs','status':r['status'],'exit':exit_code(r),'obligations':{o['id']:o['status'] for o in r['obligations']}})
    save(root/'summary.json',{'version':collection['version'],'native_builds':collection['native_builds'],'native_runs':collection['native_runs'],'review_packets':len(rows),'cases':rows,
         'limits':'Three source-selected named interactions in two contexts; finite native observations and declared independent applicability, not automatic exhaustive planning or signoff. Joined packets reuse existing original runs, not new executions.'})
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('native_output',type=Path);from_native(ap.parse_args().native_output)
