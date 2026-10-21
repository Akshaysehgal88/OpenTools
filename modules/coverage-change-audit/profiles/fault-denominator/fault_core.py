"""Compare original fault obligations, native classes and measurement definitions."""
from fault_common import BASIS,CLASSES,IDENTITY,digest,require,text,uint

def compare(baseline,current,policy):
    require(policy.get('format')=='opentools.fault-policy.v1','Unsupported objective record')
    require(all(e.get('format')=='opentools.fault-evidence.v1' for e in (baseline,current)),'Unsupported fault evidence')
    report={'format':'opentools.fault-comparison.v1','status':'incomplete','findings':[],'gaps':[],
            'baseline':{'context':baseline['context'],'native_result':baseline['native_result'],'measurement':baseline['measurement']},
            'current':{'context':current['context'],'native_result':current['native_result'],'measurement':current['measurement']},
            'original_faults':[],'class_changes':[],'exclusion_changes':[],
            'newly_detected_faults':[],'resolved_classifications':[],
            'same_detection_scope':False,'same_measurement_definition':False,'reported_delta_percent':None,
            'policy_sha256':digest(policy),'baseline_sha256':digest(baseline),'current_sha256':digest(current),
            'owner_ref':policy.get('owner_ref'),
            'recheck_when':['fault model or source population changes','collapse mapping or legal mode changes',
                            'constraints/patterns/budget change','exclusions or classification rules change','reported metric or population basis changes'],
            'limits':'Selected owned injection sites and finite combinational response equivalence only. Original/native classes remain distinct from exclusions and reported measurement. This does not qualify commercial ATPG, complete netlist faults, transition/delay models or production acceptance.'}
    def finding(kind,**data):report['findings'].append(dict(kind=kind,**data))
    def gap(kind,**data):report['gaps'].append(dict(kind=kind,**data))
    def finish():
        report['status']='review_required' if report['findings'] else 'incomplete' if report['gaps'] else 'aligned'
        return report
    admitted=True
    for label,e in [('baseline',baseline),('current',current)]:
        binding=policy.get(label,{})
        for k in IDENTITY:
            if binding.get('identity',{}).get(k)!=e['context'][k]:gap('scope_not_admitted',run=label,field=k);admitted=False
        for k,actual in [('source_sha256',e['source_sha256']),('plan_sha256',e['file_sha256']['plan.json']),
                         ('run_command_sha256',e['file_sha256']['run.command.json']),('binary_sha256',e['file_sha256']['Vtop'])]:
            if binding.get(k)!=actual:gap('artifact_not_admitted',run=label,field=k);admitted=False
        for k in BASIS:
            if not e['context'].get(k):gap('missing_native_basis',run=label,field=k)
    if not admitted:return finish()
    for k in ('source_ref','owner_ref'):
        if not policy.get(k):gap('missing_objective_basis',field=k)
        else:text(policy[k],k)
    if policy.get('inputs_complete') is not True:gap('incomplete_objective_record')
    roster=policy.get('required_original_faults');require(isinstance(roster,list) and roster,'Independent original fault roster required')
    required={}
    for f in roster:
        fid=uint(f['id'],100000,'original fault ID');require(fid not in required,'Duplicate required fault')
        uint(f['site'],100000,'fault site');uint(f['stuck'],1,'stuck value');required[fid]=f
        if not f.get('source_ref'):gap('missing_fault_definition',fault_id=fid)
    populations=[]
    for label,e in [('baseline',baseline),('current',current)]:
        faults={}
        for f in e['faults']:
            require(f['id'] not in faults and f['classification'] in CLASSES,'Invalid native fault inventory');faults[f['id']]=f
        populations.append(faults)
        missing=sorted(set(required)-set(faults));extra=sorted(set(faults)-set(required))
        if missing:gap('required_faults_missing',run=label,fault_ids=missing)
        if extra:finding('faults_outside_original_roster',run=label,fault_ids=extra)
        for fid in set(required)&set(faults):
            f=faults[fid];r=required[fid]
            if (f['site'],f['stuck'])!=(r['site'],r['stuck']):finding('fault_definition_mismatch',run=label,fault_id=fid)
            if f['classification'] in ('AB','UNKNOWN'):gap('classification_unresolved',run=label,fault_id=fid,native_class=f['classification'])
        report[label]['original_population']=len(faults);report[label]['collapsed_population']=len(e['groups'])
        report[label]['native_classes']={c:sum(f['classification']==c for f in faults.values()) for c in CLASSES}
        report[label]['excluded_faults']=[f['id'] for f in faults.values() if f['excluded']]
    a,b=populations
    # Exclusion approval is a separate supplied decision, never a native class.
    reviewed={}
    for x in policy.get('reviewed_exclusions',[]):
        fid=uint(x['fault_id'],100000,'reviewed exclusion');require(fid not in reviewed,'Duplicate reviewed exclusion');reviewed[fid]=x
    for fid,f in b.items():
        if not f['excluded']:continue
        x=reviewed.get(fid)
        if not x or not all(x.get(k) for k in ('reason_ref','source_ref','owner_ref')):gap('exclusion_basis_unestablished',fault_id=fid)
    same_scope=all(baseline['context'][k]==current['context'][k] for k in IDENTITY if k!='run_ref') and baseline['source_sha256']==current['source_sha256'] and all(baseline['plan'][k]==current['plan'][k] for k in ('mode','legal_mask','legal_value'))
    report['same_detection_scope']=same_scope
    if not same_scope:gap('detection_scope_changed',reason='Mode, legal-input constraint, source or objective differs')
    # The original integer populations are retained even when the reporting unit changes.
    for fid in sorted(set(a)|set(b)):
        old=a.get(fid);new=b.get(fid)
        report['original_faults'].append({'id':fid,'required':fid in required,'baseline':old,'current':new})
        if old is None or new is None:continue
        if old['classification']!=new['classification']:
            report['class_changes'].append({'id':fid,'from':old['classification'],'to':new['classification']})
        if old['excluded']!=new['excluded']:report['exclusion_changes'].append({'id':fid,'from':old['excluded'],'to':new['excluded'],'reviewed_basis_supplied':fid in reviewed})
        if same_scope and old['classification']=='UD' and new['classification']=='DT':report['newly_detected_faults'].append(fid)
        if old['classification'] in ('AB','UNKNOWN') and new['classification'] not in ('AB','UNKNOWN'):report['resolved_classifications'].append(fid)
    if report['class_changes']:finding('native_classifications_changed',count=len(report['class_changes']))
    if report['exclusion_changes']:finding('native_exclusions_changed',fault_ids=[x['id'] for x in report['exclusion_changes']])
    oldmap={f['id']:f['representative'] for f in baseline['faults']};newmap={f['id']:f['representative'] for f in current['faults']}
    if oldmap!=newmap:finding('native_collapse_map_changed')
    am,bm=baseline['measurement'],current['measurement'];same_definition=all(am[k]==bm[k] for k in ('metric','population_basis'));report['same_measurement_definition']=same_definition
    if not same_definition:finding('native_measurement_definition_changed',baseline={'metric':am['metric'],'basis':am['population_basis']},current={'metric':bm['metric'],'basis':bm['population_basis']})
    for label,m in [('baseline',am),('current',bm)]:report[label]['reported_percent']=100*m['numerator']/m['denominator'] if m['denominator'] else None
    if same_definition and same_scope:
        if am['denominator']!=bm['denominator']:finding('reported_denominator_changed',baseline=am['denominator'],current=bm['denominator'])
        if am['denominator'] and bm['denominator']:
            report['reported_delta_percent']=report['current']['reported_percent']-report['baseline']['reported_percent']
            unresolved=any(f['classification'] in ('AB','UNKNOWN') for f in [*a.values(),*b.values()])
            if not unresolved and bm['numerator']*am['denominator']>am['numerator']*bm['denominator'] and not report['newly_detected_faults']:
                finding('reported_ratio_increased_without_new_detection',native_detected_before=sum(f['classification']=='DT' for f in a.values()),native_detected_after=sum(f['classification']=='DT' for f in b.values()))
    return finish()
