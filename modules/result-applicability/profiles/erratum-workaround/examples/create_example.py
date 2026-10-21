"""Review original notices plus current-approval/maintenance query controls."""
import copy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from erratum_common import read_json,save
from erratum_core import markdown,review
from fixture import FAMILIES
from reference_model import applicability,disposition
def from_native(root):
    root=Path(root);out=root/'reviews';out.mkdir();requests=root/'requests';requests.mkdir();rows=[]
    def emit(name,n,q,expected,code,nref,qref):
        r=review(root,n,q)
        if (r['status'],r['exit_code'])!=(expected,code):raise ValueError('Unexpected review '+name+':'+r['status']+' '+str(r['findings'])+' '+str(r['gaps']))
        save(out/(name+'.json'),r);(out/(name+'.md')).write_text(markdown(r),encoding='utf-8');rows.append({'case':name,'notice':nref,'request':qref,'status':r['status'],'exit_code':r['exit_code']});return r
    for item in read_json(root/'collection.json')['cases']:
        ref=item['run_ref'];nref=ref+'/capture-notice.json';qref=ref+'/capture-request.json';n=read_json(root/nref);q=read_json(root/qref);expected,code=disposition(item['family'],item['case']);r=emit(ref,n,q,expected,code,nref,qref)
        if r['applicability']['truth'] is not applicability(item['case']):raise ValueError('Wrong original predicate state')
    for family in FAMILIES:
        ref=family+'-affected-mitigated';nref=ref+'/capture-notice.json';n=read_json(root/nref);original=read_json(root/ref/'capture-request.json')
        for variant in ('approval-missing','approval-pending','approval-withdrawn','approval-stale','remove-affected','stronger-claim'):
            q=copy.deepcopy(original);q['claim_ref']=family+'/'+variant
            if variant=='approval-missing':q['approval']=None
            elif variant=='approval-pending':q['approval']['status']='pending'
            elif variant=='approval-withdrawn':q['approval']['status']='withdrawn'
            elif variant=='approval-stale':q['review_cut_ref']='owned-review-cut-r2'
            elif variant=='remove-affected':q['intent']='remove';q['approval']['intent']='remove'
            else:q['required_fields']['physical.all_modes.verified']={'value':True,'evidence_ref':'owned/original-stronger-maintenance-question'}
            code=2 if variant in ('approval-missing','approval-pending','stronger-claim') else 1;name=family+'-'+variant;qref='requests/'+name+'.json';save(root/qref,q);emit(name,n,q,'INCOMPLETE' if code==2 else 'REVIEW_REQUIRED',code,nref,qref)
    save(root/'review-collection.json',rows);return rows
if __name__=='__main__':print(from_native(sys.argv[1]))
