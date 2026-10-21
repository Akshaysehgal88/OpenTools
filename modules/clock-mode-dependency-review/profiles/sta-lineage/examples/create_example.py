"""Bind retained native objects to the original independent mode contract."""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lineage_common import read_json,save
from lineage_core import binding
from sta_review import evaluate,load
def policy(root,ref):
    root=Path(root);return {'format':'opentools.sta-lineage-policy.v1','run_ref':ref,'binding':binding(load(root,ref)),'contract':read_json(root/ref/'contract.json')}
def from_native(root):
    root=Path(root);dest=root/'reviews';dest.mkdir(exist_ok=False);rows=[]
    for row in read_json(root/'collection.json')['cases']:
        ref=row['run_ref'];p=policy(root,ref);r=evaluate(root,p);save(dest/(ref+'.policy.json'),p);save(dest/(ref+'.report.json'),r)
        rows.append({'family':row['family'],'case':row['case'],'run_ref':ref,'exit_code':r['exit_code'],'status':r['status'],'findings':len(r['findings']),'gaps':len(r['gaps'])})
    save(root/'review-collection.json',rows);return rows
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root');a=p.parse_args()
    for row in from_native(a.root):print(row)
