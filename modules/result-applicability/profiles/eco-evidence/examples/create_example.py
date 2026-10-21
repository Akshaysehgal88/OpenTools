"""Create example report selections from existing, retained native runs."""
import argparse,copy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eco_common import CLAIMS,IDENTITY,REPORTS,digest,read_json,save
from eco_core import load,review
from eco_records import request,snapshot
from native_eco import capture
from fixture import FAMILIES,CASES,context,mode

SCENARIOS=('unchanged-old','data-old','control-old','phase-old','data-cached',
           'control-cached','unchanged-cached','data-no-approval','missing-correspondence','foreign-binding')

def expected_phase(c,case):
    a,b=mode(c,case);p=c['ports']
    return {'sta':{'cases':{p['reset']:str(1-c['reset_asserted']),p['a']:str(a),p['b']:str(b)},
                   'clock':{'name':'root','period':float(c['period']),'is_generated':'0'},'clock_sources':[p['clock']]},
            'clock':{'reset':1-c['reset_asserted'],'a':a,'b':b,'cycles':c['cycles'],
                     'clock_pattern':[i%2 for i in range(2*c['cycles'])],'measurement':'logical-half-cycle-counter'}}

def binding(e,records):
    c=e['context']
    return {'identity':{k:c[k] for k in IDENTITY},
            'selection':{k:c[k] for k in ('ports','cells','wake','clock_name','period','reset_asserted','mode_a','mode_b','cycles')},
            'source_sha256':e['source_sha256'],'graph_sha256':e['file_sha256']['graph.txt'],
            'binary_sha256':e['execution']['binary_sha256'],'tools':e['execution']['tools'],
            'report_record_fingerprints':{k:digest(v) for k,v in records.items() if v is not None}}

def policy(root,family,scenario):
    c=FAMILIES[family]
    case={'unchanged-old':'unchanged','data-old':'data-eco','control-old':'control-eco',
          'phase-old':'phase-change','data-cached':'data-eco','control-cached':'control-eco',
          'unchanged-cached':'unchanged','data-no-approval':'data-eco',
          'missing-correspondence':'data-eco','foreign-binding':'data-eco'}[scenario]
    before,old=load(root,family+'-before');after,new=load(root,family+'-'+case)
    p={'format':'opentools.eco-policy.v1','before':before['context']['run_ref'],'after':after['context']['run_ref'],
       'before_binding':binding(before,old),'after_binding':binding(after,new),
       'claim_id':family+'/'+scenario,'claim':'Check selected report evidence for the endpoint-rewire proposal and required operating phase.',
       'scope_ref':'owned/'+family,'source_ref':'owned-example-intent/'+family,'owner_ref':'owned-example-reviewer',
       'inputs_complete':True,'correspondence_ref':'owned-example-stable-native-instance-and-pin-map',
       'required_claims':{k:False for k in CLAIMS},'required_phase':expected_phase(c,case),
       'required_outcome':{k:'pass' for k in REPORTS},'reports':{k:{'selected':'before','reviewed_reuse':None} for k in REPORTS}}
    if scenario in ('data-cached','unchanged-cached','control-cached'):
        p['reports']['sta']['selected']='after'
        if scenario!='data-cached':p['reports']['clock']['selected']='after'
    if scenario not in ('data-no-approval','missing-correspondence','foreign-binding'):
        for kind in REPORTS:
            if p['reports'][kind]['selected']!='before':continue
            req=request(after,kind,p)
            pairs={k:{'observed':old[kind]['fields'][k]['value'],'requested':req['required_fields'][k]['value']}
                   for k in ('implementation.netlist_sha','build.report_producer')
                   if old[kind]['fields'][k]['value']!=req['required_fields'][k]['value']}
            if pairs:
                p['reports'][kind]['reviewed_reuse']={'run_ref':old[kind]['run_ref'],'after_run_ref':after['context']['run_ref'],
                    'report_type':kind,'pairs':pairs,'rule_ref':'owned-example-conditional-rule/'+family+'/'+scenario+'/'+kind,
                    'approved_by':'owned-example-reviewer','basis_ref':'owned-example-primitive-and-phase-review',
                    'reason':'Example supplied approval for these exact global identities, conditional on identical report projection, models and phase. Not production authority.'}
    if scenario=='missing-correspondence':p['correspondence_ref']=None
    if scenario=='foreign-binding':p['after_binding']['identity']['configuration_ref']='foreign/configuration'
    return p

def from_native(root):
    root=Path(root)
    for family in FAMILIES:
        for case in CASES:
            run=root/(family+'-'+case);e=capture(run,read_json(run/'context.json'))
            for kind in REPORTS:save(run/(kind+'.snapshot.json'),snapshot(e,kind))
    dest=root/'reviews';dest.mkdir(exist_ok=False);rows=[]
    for family in FAMILIES:
        for scenario in SCENARIOS:
            name=family+'-'+scenario;p=policy(root,family,scenario);r=review(root,p)
            save(dest/(name+'.policy.json'),p);save(dest/(name+'.report.json'),r)
            rows.append({'family':family,'scenario':scenario,'status':r['status'],'exit_code':r['exit_code'],
                         'changed_pins':len(r['changed_objects']),'findings':len(r['findings']),'gaps':len(r['gaps'])})
    save(root/'review-collection.json',rows);return rows

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root');a=p.parse_args()
    for row in from_native(a.root):print(row)
