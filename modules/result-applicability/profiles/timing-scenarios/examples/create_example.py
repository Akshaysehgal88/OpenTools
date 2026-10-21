"""Review explicit scenario matrices without generating a corner/mode product."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scenario_common import read_json,save
from scenario_core import markdown,review
from fixture import FAMILIES
def from_native(root):
    root=Path(root);out=root/'reviews';out.mkdir();rows=[]
    for family in FAMILIES:
        for variant in ('complete','omitted','wrong-library','wrong-mode','unknown-mode','timing-failure'):
            plan=root/'requirements'/(family+('.timing-failure-plan.json' if variant=='timing-failure' else '.plan.json'));corpus=root/'requirements'/(family+'.'+variant+'.corpus.json');r=review(root,read_json(plan),read_json(corpus));ref=family+'-'+variant;save(out/(ref+'.json'),r);(out/(ref+'.md')).write_text(markdown(r),encoding='utf-8');rows.append({'case':ref,'plan':plan.relative_to(root).as_posix(),'corpus':corpus.relative_to(root).as_posix(),'status':r['status'],'exit_code':r['exit_code'],'counts':r['counts']})
    save(root/'review-collection.json',rows);return rows
if __name__=='__main__':print(from_native(sys.argv[1]))
