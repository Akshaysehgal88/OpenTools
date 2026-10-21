"""Review each original interface contract against its three native views."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from budget_common import read_json,save
from budget_core import markdown,review

def from_native(root):
    root=Path(root);out=root/'reviews';out.mkdir();rows=[]
    for item in read_json(root/'collection.json')['packets']:
        c=read_json(root/item['contract']);r=review(root,c);ref=item['packet_ref'];save(out/(ref+'.json'),r);(out/(ref+'.md')).write_text(markdown(r),encoding='utf-8');rows.append({'case':ref,'contract':item['contract'],'status':r['status'],'exit_code':r['exit_code']})
    save(root/'review-collection.json',rows);return rows
if __name__=='__main__':print(from_native(sys.argv[1]))
