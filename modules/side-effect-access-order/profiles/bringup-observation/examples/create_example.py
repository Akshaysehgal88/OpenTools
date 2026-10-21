"""Compare each original captured question without treating raw bits as a test pass."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bringup_common import read_json,save
from bringup_core import markdown,review
from reference_model import disposition
def from_native(root):
    root=Path(root);out=root/'reviews';out.mkdir();rows=[]
    for item in read_json(root/'collection.json')['cases']:
        ref=item['run_ref'];q=ref+'/capture-question.json';r=review(root,read_json(root/q));expected,code=disposition(item['family'],item['case'])
        if (r['status'],r['exit_code'])!=(expected,code):raise ValueError('Unexpected comparison: '+ref+' '+r['status']+' '+str(r['gaps']))
        save(out/(ref+'.json'),r);(out/(ref+'.md')).write_text(markdown(r),encoding='utf-8');rows.append({'case':ref,'request':q,'status':r['status'],'exit_code':r['exit_code']})
    save(root/'review-collection.json',rows);return rows
if __name__=='__main__':print(from_native(sys.argv[1]))
