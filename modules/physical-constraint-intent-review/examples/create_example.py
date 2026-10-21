"""Prepare review sidecars from original native artifacts and separate intent."""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from physical_common import CLAIMS,read_json,save
from physical_review import load
from physical_core import binding,review
from fixture import FAMILIES,CASES

def policy(root,family,case):
    root=Path(root);intent=read_json(root/(family+'-intent.json'));before=load(root,family+'-baseline');after=load(root,family+'-'+case)
    return {'format':'opentools.physical-policy.v1','before':before['context']['run_ref'],'after':after['context']['run_ref'],
       'before_binding':binding(before),'after_binding':binding(after),'claim_id':family+'/'+case,'claim':intent['required_claim'],
       'scope_ref':intent['scope_ref'],'source_ref':intent['source_ref'],'owner_ref':intent['owner_ref'],'inputs_complete':True,
       'correspondence_ref':'owned/'+family+'/stable-native-map','allowed_moved_instances':[intent['moving_instance']],
       'selection':{'net':intent['selected_net'],'endpoint_names':sorted(intent['endpoint_names'])},
       'region':{'box_dbu':intent['region_dbu'],'require_hard_blockage':intent['required_hard_blockage'],
           'require_clear_instances':intent['required_clear_region'],'source_ref':intent['source_ref'],
           'rationale_ref':'owned/'+family+'/access-or-boundary-rationale','anchor_ref':'owned/'+family+'/selected-endpoints'},
       'required_claims':{k:False for k in CLAIMS}}

def from_native(root):
    root=Path(root);dest=root/'reviews';dest.mkdir(exist_ok=False);rows=[]
    for family in FAMILIES:
        for case in CASES[1:]:
            p=policy(root,family,case);r=review(load(root,p['before']),load(root,p['after']),p);name=family+'-'+case
            save(dest/(name+'.policy.json'),p);save(dest/(name+'.report.json'),r)
            rows.append({'family':family,'case':case,'name':name,'exit_code':r['exit_code'],'status':r['status'],
                         'findings':len(r['findings']),'gaps':len(r['gaps']),'delta_dbu':r['metric']['reported_delta_dbu']})
    save(root/'review-collection.json',rows);return rows

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root');a=p.parse_args()
    for row in from_native(a.root):print(row)
