"""Pair frozen native identities with independently prepared recipe requirements."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from occ_common import read_json
from native_occ import IDENTITY,MAPPING,PROFILE,capture
from occ_core import markdown,review
def from_native(root):
    root=Path(root);manifest=read_json(root/'collection.json');results=[]
    for row in manifest['cases']:
        folder=root/row['case'];ctx=row['context'];expected={k:ctx[k] for k in IDENTITY};expected.update({'mapping':{k:ctx[k] for k in MAPPING},'behavior_sources':row['behavior_sources'],'sta_sources':row['sta_sources'],'run_command_sha256':row['run_command_sha256'],'sta_command_sha256':row['sta_command_sha256'],'native_profile':PROFILE});c={'format':'opentools.occ-contract.v1','expected':expected,'recipe':row['recipe']};e=capture(root,row['behavior_workdir'],row['sta_workdir'],ctx);r=review(c,e,root)
        for name,value in [('contract.json',c),('evidence.json',e),('review.json',r)]: (folder/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
        (folder/'review.md').write_text(markdown(r),encoding='utf-8');results.append({'case':row['case'],'status':r['status'],'exit_code':r['exit_code'],'native':r['native_behavior_status'],'counts':r['native_counts']})
    (root/'reviews.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8');return results
if __name__=='__main__':print(json.dumps(from_native(sys.argv[1]),indent=2))
