"""Review original native endpoint populations and independently frozen intent."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from endpoint_common import read_json,save
from endpoint_core import markdown,review
def from_native(root):
    root=Path(root);rows=[]
    for item in read_json(root/'collection.json')['cases']:
        p=root/item['run_ref'];r=review(read_json(p/'contract.json'),read_json(p/'evidence.json'),p);save(p/'review.json',r);(p/'review.md').write_text(markdown(r),encoding='utf-8');rows.append({'run_ref':item['run_ref'],'status':r['status'],'exit_code':r['exit_code'],'counts':r['counts']})
    save(root/'reviews.json',rows);return rows
if __name__=='__main__':print(from_native(sys.argv[1]))
