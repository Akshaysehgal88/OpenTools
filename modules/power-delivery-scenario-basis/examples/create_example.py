"""Select original results against requests saved before their native analyses."""
import argparse,copy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from supply_common import read_json,save
from supply_core import binding
from supply_review import evaluate,load
SCENARIOS={'base':('base','base'),'old-loads':('base','loads'),'old-source':('base','source-change'),
 'old-corner':('base','corner-change'),'old-cut':('base','connectivity-cut'),
 'exact-loads':('loads','loads'),'exact-source':('source-change','source-change'),
 'exact-corner':('corner-change','corner-change'),'exact-cut':('connectivity-cut','connectivity-cut'),'dynamic':('loads','loads')}
def policy(root,family,scenario):
    root=Path(root);selected,target=SCENARIOS[scenario];ref=family+'-'+selected;target_ref=family+'-'+target
    p={'format':'opentools.supply-policy.v1','selected_ref':ref,'selected_binding':binding(load(root,ref)),
       'request':read_json(root/target_ref/'request.json'),'cached_ref':None,'cached_binding':None}
    if selected!=target:p.update(cached_ref=target_ref,cached_binding=binding(load(root,target_ref)))
    if scenario=='dynamic':
        p['request']['claim']='Establish dynamic IR during simultaneous wake; preserve the missing transient basis.'
        p['request']['required_claims'].update(dynamic_IR=True,wake_sequence=True)
    return p
def from_native(root):
    root=Path(root);dest=root/'reviews';dest.mkdir(exist_ok=False);rows=[]
    for family in ('series','branch'):
        for scenario in SCENARIOS:
            name=family+'-'+scenario;p=policy(root,family,scenario);r=evaluate(root,p);save(dest/(name+'.policy.json'),p);save(dest/(name+'.report.json'),r)
            rows.append({'family':family,'scenario':scenario,'name':name,'exit_code':r['exit_code'],'status':r['status'],'findings':len(r['findings']),'gaps':len(r['gaps'])})
    save(root/'review-collection.json',rows);return rows
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root');a=p.parse_args()
    for row in from_native(a.root):print(row)
