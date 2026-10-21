"""Review original native runs and compare population/premise changes."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reach_common import read_json,save
from reach_core import drift,inspect,markdown
from fixture import FAMILIES,rename_map

def from_native(root):
    root=Path(root);manifest=read_json(root/'collection.json');rows=[]
    for item in manifest['cases']:
        folder=root/item['run_ref'];r=inspect(read_json(folder/'contract.json'),read_json(folder/'evidence.json'),folder);save(folder/'review.json',r);(folder/'review.md').write_text(markdown(r),encoding='utf-8');rows.append({'run_ref':item['run_ref'],'status':r['status'],'exit_code':r['exit_code'],'counts':r['counts']})
    for family in FAMILIES:
        before=root/(family+'-baseline')
        for case in ('baseline','expanded','renamed','wrong-mode','untraced','unknown-mode','retarget'):
            after=root/(family+'-'+case);mapping=rename_map(family,case) if case in ('renamed','retarget') else None
            if mapping is not None:save(after/'identity-map.json',mapping)
            r=drift(read_json(before/'contract.json'),read_json(before/'evidence.json'),before,read_json(after/'contract.json'),read_json(after/'evidence.json'),after,mapping);save(after/'drift.json',r);(after/'drift.md').write_text(markdown(r),encoding='utf-8')
    save(root/'reviews.json',rows);return rows
if __name__=='__main__':print(from_native(sys.argv[1]))
