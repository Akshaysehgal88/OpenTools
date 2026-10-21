"""Compare original native runs with independent pre-run population/exclusion sources."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scan_common import read_json
from native_inventory import IDENTITY,PROFILE,capture
from population_core import drift,markdown,review
def from_native(root):
    root=Path(root);manifest=read_json(root/'collection.json');rows=[]
    for row in manifest['cases']:
        folder=root/row['case'];ctx=row['context'];contract={'format':'opentools.scan-contract.v1','expected':{**{k:ctx[k] for k in IDENTITY},'sources':row['sources'],'command_sha256':row['command_sha256'],'native_profile':PROFILE},'requirements_basis_ref':'owned/'+row['family']+'/independent-state-intent','owner_ref':'owned/'+row['family']+'/fixture-review-owner'}
        e=capture(root,row['case']+'/run',ctx);r=review(contract,e,root)
        for name,value in [('contract.json',contract),('evidence.json',e),('review.json',r)]: (folder/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
        (folder/'review.md').write_text(markdown(r),encoding='utf-8');rows.append({'case':row['case'],'status':r['status'],'exit_code':r['exit_code'],'counts':r['counts']})
    for family in sorted({row['family'] for row in manifest['cases']}):
        before=read_json(root/(family+'-allowed-exclusion')/'evidence.json');after=read_json(root/(family+'-obsolete-role')/'evidence.json');r=drift(before,after,root)
        (root/(family+'-exclusion-drift.json')).write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    (root/'reviews.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8');return rows
if __name__=='__main__':print(json.dumps(from_native(sys.argv[1]),indent=2))
