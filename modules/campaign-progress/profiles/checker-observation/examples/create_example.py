"""Normalize retained owned native data without running a simulator or imported command."""
import argparse,json
from pathlib import Path
import sys
PROFILE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROFILE))
from native_capture import capture
from observation_core import EXPECTED,exit_code,markdown,review
from run_native import ROLES
from reference_model import expected
EXPECTED_EXITS={'good-clean':0,'good-fault':0,'gated-clean':1,'gated-fault':1,'disabled':1,'stimulus':1,'wrong-id':1,'stalled':2,'reset':0,'short-window':2,'no-mode1':2}
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2)+'\n')
def capture_context(name,family):
    m={k:v for k,v in ROLES[family].items() if k!='fault'}
    return {'format':'opentools.checker-observation-context.v1','run_ref':'owned:'+name,'campaign_ref':'owned:handshake-checker-observation','scope_ref':'owned:'+family+':top-stream',
            'configuration_ref':'owned:'+family+':8bit-ID-16bit-data','model_ref':'owned:'+family+':native-model','clock_ref':'top.'+m['clock'],'edge':'positive','sampling':'stable_preedge','reset_ref':'top.'+m['reset'],'reset_active':int(family=='stream'),
            'checker_ref':'owned:ObservationChecker','checker_source_ref':'run/checker.hpp','scope_basis_ref':'owned:one-flat-single-clock-ready-valid-pair-reset-cancels-pending',
            'instrumentation_review_ref':'owned:source-reviewed-independent-raw-port-preedge-journal-and-checker-enable-getter','oracle_ref':'owned:source-reviewed-fixture-XOR-expected-data-model',
            'dependencies_complete':True,'dependency_basis_ref':'owned:four-original-inputs-and-existing-pinned-runtime','port_map':m,'window_ref':'owned:'+name+':contiguous-complete-native-window'}
def intent_for(name,family,source_sha):
    ctx=capture_context(name,family);fields={k:ctx[k] for k in EXPECTED if k!='source_sha256'};fields['source_sha256']=source_sha
    return {'format':'opentools.checker-observation-intent.v1','claim_id':'owned:'+name+':observation','claim':'Every completed transaction in the required modes is checked at the declared completion event with the correct original identity and observed payload.',
            'owner_ref':'owned:checker-integration-review-owner','basis_ref':'owned:independent-event-contract-ready-valid-preedge-reset-cancel','expected':fields,'required_modes':[0,1],
            'mode_basis_ref':'owned:normal-and-retained-interval-completion-obligations','policy_ref':'owned:offline-review-only-no-campaign-stop-authority'}
def from_native(root):
    root=Path(root);collection=json.loads((root/'collection.json').read_text(encoding='utf-8'));rows=[]
    for row in collection['cases']:
        name=row['case'];family=row['family'];folder=root/name;ctx=capture_context(name,family);e=capture(folder,'run',ctx)
        ref=expected(family,row['policy'],row['scenario'],row['fault'])
        assert e['edges']==ref['edges'],name+' independent edge model differs'
        assert e['checks']==ref['checks'] and e['native']['counts']==ref['counts'],name+' independent checker model differs'
        i=intent_for(name,family,row['source_sha256']);r=review(i,e,folder);key=name.removeprefix(family+'-');assert exit_code(r)==EXPECTED_EXITS[key],(name,r['findings'],r['gaps'])
        for filename,value in [('capture-context.json',ctx),('intent.json',i),('evidence.json',e),('independent-reference.json',ref),('report.json',r)]:save(folder/filename,value)
        (folder/'report.md').write_text(markdown(r),encoding='utf-8',newline='\n');rows.append({'case':name,'status':r['status'],'exit':exit_code(r),'native_status':e['native']['status'],'counts':e['native']['counts'],'cancelled':len(r['events']['cancelled']),'outstanding':len(r['events']['outstanding'])})
        print(name+': '+r['status'],flush=True)
    save(root/'summary.json',{'version':collection['version'],'native_builds':collection['native_builds'],'native_runs':collection['native_runs'],'cases':rows,
         'limits':'Native single-clock finite-window observation correspondence; expected-source/oracle review remains required. Correctly caught native failure can have valid observation. No verification completeness.'})
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('native_output',type=Path);from_native(p.parse_args().native_output)
