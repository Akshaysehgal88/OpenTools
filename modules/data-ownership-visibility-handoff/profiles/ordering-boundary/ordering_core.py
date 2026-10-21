"""Review scoped outcomes for the owned three-event buffered-publication profile."""
import hashlib
from itertools import permutations
import json
from pathlib import Path

MODEL='opentools.owned-buffered-publication.v1'
METHOD='owned-three-event-enumeration.v1'
EVENTS=('payload-commit','publication-commit','observe')
DOMAINS={'I','O','R','W'}


def require(condition,message):
    if not condition:raise ValueError(message)


def text(value,label):require(isinstance(value,str) and bool(value.strip()),label+' required')


def boolean(value,label):require(type(value) is bool or value is None,label+' must be boolean or null')


def uint(value,maximum,label,nullable=False):
    require(nullable and value is None or type(value) is int and 0<=value<=maximum,label+' outside unsigned range')


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()


def read_json(path):
    def unique(pairs):
        result={}
        for key,value in pairs:require(key not in result,'Duplicate JSON key: '+key);result[key]=value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique,
                      parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON value')))


def program_digest(contract):
    return digest({key:contract[key] for key in ('program','attributes','producer_ref','observer_ref','producer_contract_ref','observer_contract_ref')})


def outcome(record):
    require('flag' in record and 'payload' in record,'Explicit outcome values required')
    uint(record['flag'],1,'observed flag',True);uint(record['payload'],1,'observed payload',True)
    return record['flag'],record['payload']


def review(contract,evidence,claim):
    for record,kind in ((contract,'contract'),(evidence,'evidence'),(claim,'claim')):
        require(isinstance(record,dict) and record.get('format')=='opentools.ordering.'+kind+'.v1','Unsupported '+kind+' format')
        require(isinstance(record.get('scope'),dict) and set(record['scope'])=={'project','configuration','boundary_ref','mode'},'Exact ordering scope required')
        for value in record['scope'].values():text(value,'scope')
        text(record.get('basis_ref'),'basis_ref');require(type(record.get('inputs_complete')) is bool,'Boolean inputs_complete required')
    report={'format':'opentools.ordering.report.v1','scope':contract['scope'],
        'bindings':{key+'_sha256':digest(value) for key,value in (('contract',contract),('evidence',evidence),('claim',claim))},
        'findings':[],'gaps':[],'control_covers_boundary':None,'model_permits_stale':None,'model_witness':None,
        'observations':[],'observed_stale_runs':[],
        'limits':['One owned buffered-publication family with ordered observer and single-bit sentinels. Not a new ISA memory model or proof of architectural access width/atomicity.',
                  'Model-allowed outcomes and owned RTL observations remain separate. An unobserved outcome is not thereby forbidden; no hardware, compiler, RVWMO, MMIO platform or universal fence qualification.']}
    def gap(kind,**details):report['gaps'].append(dict(kind=kind,**details))
    def finding(kind,**details):report['findings'].append(dict(kind=kind,**details))
    bound=True
    for record,name in ((evidence,'evidence'),(claim,'claim')):
        if record['scope']!=contract['scope'] or record['basis_ref']!=contract['basis_ref'] or record.get('contract_sha256')!=digest(contract):gap('scope_or_contract_binding',record=name);bound=False
    if claim.get('evidence_sha256')!=digest(evidence):gap('evidence_binding');bound=False
    if not bound:report['status']='incomplete';return report
    for record,name in ((contract,'contract'),(evidence,'evidence'),(claim,'claim')):
        if not record['inputs_complete']:gap('partial_inputs',record=name)
    for key in ('model_ref','model_revision_ref','model_kind','producer_ref','observer_ref','producer_contract_ref','observer_contract_ref','attribute_basis_ref','visibility_basis_ref','instruction_scope_ref'):
        text(contract.get(key),key)
    claim_basis_qualified=True
    for key in ('model_ref','model_revision_ref','producer_ref','observer_ref','producer_contract_ref','observer_contract_ref'):
        text(claim.get(key),'claimed '+key)
        if claim[key]!=contract[key]:gap('claimed_contract_basis_mismatch',field=key);claim_basis_qualified=False
    require(claim.get('property') in ('publication_implies_payload','atomicity'),'Explicit supported claim category required')
    require(claim.get('strength') in ('selected_model','isa','hardware'),'Explicit claim strength required')
    supported=contract['model_ref']==MODEL and contract['model_kind']=='owned-implementation'
    if not supported:gap('model_profile_unqualified')
    property_qualified=supported and claim_basis_qualified and claim['property']=='publication_implies_payload' and claim['strength']=='selected_model'
    if claim['property']!='publication_implies_payload':gap('atomicity_not_qualified')
    if claim['strength']!='selected_model':gap('claim_strength_not_qualified',strength=claim['strength'])
    require(contract.get('sentinel_bits')==1 and type(contract['sentinel_bits']) is int,'Owned profile uses one-bit sentinels; no architectural width claim')
    require('observer_ordered' in contract,'Explicit observer-order premise required');boolean(contract['observer_ordered'],'observer order')
    if contract['observer_ordered'] is not True:gap('observer_order_unqualified')
    attributes=contract.get('attributes');require(isinstance(attributes,dict) and set(attributes)=={'payload','publication'},'Exact path attributes required')
    for role,entry in attributes.items():
        require(isinstance(entry,dict),'Path attribute record required')
        for key in ('path_ref','cacheability_ref','shareability_ref','mapping_revision_ref','evidence_ref'):
            if entry.get(key) is None:gap('path_attribute_unknown',role=role,field=key)
            else:text(entry[key],role+' '+key)
    require(isinstance(claim.get('required_attributes'),dict) and set(claim['required_attributes'])=={'payload','publication'},'Independent required paths required')
    for role,entry in claim['required_attributes'].items():
        require(isinstance(entry,dict),'Required path record required')
        for key in ('path_ref','cacheability_ref','shareability_ref','mapping_revision_ref'):
            text(entry.get(key),'required path '+key)
            if entry[key]!=attributes[role].get(key):gap('required_path_mismatch',role=role,field=key);property_qualified=False
    program=contract.get('program');require(isinstance(program,list) and program,'Explicit producer program required')
    steps={};positions={}
    for position,step in enumerate(program):
        for key in ('id','actor_ref','evidence_ref'):text(step.get(key),'program '+key)
        require(step['id'] not in steps and step.get('kind') in ('store','ordering_control'),'Unique supported program steps required')
        if step['actor_ref']!=contract['producer_ref']:gap('producer_program_actor_mismatch',event_ref=step['id'])
        if step['kind']=='store':
            require('domain' in step and (step['domain'] in DOMAINS or step['domain'] is None),'Explicit access domain required')
            if step['domain'] is None:gap('access_domain_unknown',event_ref=step['id'])
            text(step.get('object_ref'),'store object');uint(step.get('value'),1,'sentinel store value')
        else:
            for key in ('predecessors','successors'):
                require(key in step and (step[key] is None or isinstance(step[key],list) and len(set(step[key]))==len(step[key]) and set(step[key])<=DOMAINS),'Unique known domain mask or null required')
                if step[key] is None:gap('ordering_domain_mask_unknown',event_ref=step['id'],field=key)
        steps[step['id']]=step;positions[step['id']]=position
    for key in ('payload_event_ref','publication_event_ref'):text(claim.get(key),key)
    require('control_event_ref' in claim,'Explicit selected control ref required')
    if claim['control_event_ref'] is not None:text(claim['control_event_ref'],'control event')
    require(isinstance(claim.get('required_domains'),dict) and set(claim['required_domains'])=={'payload','publication'},'Independent required access domains required')
    payload=steps.get(claim['payload_event_ref']);publication=steps.get(claim['publication_event_ref']);control=steps.get(claim['control_event_ref'])
    family_qualified=payload is not None and publication is not None and payload['kind']=='store' and publication['kind']=='store'
    if not family_qualified:gap('required_producer_access_absent')
    for role,step in (('payload',payload),('publication',publication)):
        require(claim['required_domains'][role] in DOMAINS,'Expected access domain required')
        if step is not None and step.get('domain')!=claim['required_domains'][role]:gap('required_access_domain_mismatch',role=role);property_qualified=False
    if family_qualified:
        if payload['domain']!='W' or publication['domain'] not in ('W','O') or payload['object_ref']!='payload' or publication['object_ref']!='publication' or payload['value']!=1 or publication['value']!=1 or positions[payload['id']]>=positions[publication['id']]:gap('program_family_unqualified');family_qualified=False
        expected_ids={payload['id'],publication['id']}|({claim['control_event_ref']} if claim['control_event_ref'] is not None else set())
        if set(steps)!=expected_ids:gap('unreviewed_producer_program_steps');family_qualified=False
    if claim['control_event_ref'] is None:coverage=False
    elif control is None or control['kind']!='ordering_control':gap('selected_ordering_control_absent');coverage=None
    elif family_qualified:
        placement=positions[payload['id']]<positions[control['id']]<positions[publication['id']]
        coverage=False if not placement else None if control['predecessors'] is None or control['successors'] is None else payload['domain'] in control['predecessors'] and publication['domain'] in control['successors']
    else:coverage=None
    report['control_covers_boundary']=coverage
    program_hash=program_digest(contract)
    analysis=evidence.get('model_result');valid_witnesses={};analysis_qualified=False;analysis_exhaustive=False
    if analysis is None:gap('model_result_absent')
    else:
        require(isinstance(analysis,dict),'Model result must be object or null')
        for key in ('kind','model_ref','model_revision_ref','program_sha256','evidence_ref'):text(analysis.get(key),'model result '+key)
        require('complete' in analysis,'Explicit model coverage required');boolean(analysis['complete'],'model coverage')
        analysis_bound=analysis['model_ref']==contract['model_ref'] and analysis['model_revision_ref']==contract['model_revision_ref'] and analysis['program_sha256']==program_hash
        if not analysis_bound:gap('model_result_basis_mismatch')
        if analysis['kind']!=METHOD:gap('model_result_method_unqualified')
        if analysis['complete'] is not True:gap('model_enumeration_not_complete')
        require(isinstance(analysis.get('witnesses'),list) and isinstance(analysis.get('outcomes'),list),'Explicit model outcomes and witnesses required')
        declared=set()
        for entry in analysis['outcomes']:
            result=outcome(entry);require(result not in declared,'Duplicate model outcome');declared.add(result)
            if result[0] is None or result[0]==1 and result[1] is None:gap('model_outcome_unknown')
        witness_orders=set()
        expected_orders={order for order in permutations(EVENTS) if not coverage or order.index('payload-commit')<order.index('publication-commit')} if coverage is not None else None
        for witness in analysis['witnesses']:
            text(witness.get('evidence_ref'),'witness evidence');require(isinstance(witness.get('order'),list) and len(witness['order'])==3 and set(witness['order'])==set(EVENTS),'Owned witness must order all three events once')
            order=tuple(witness['order']);require(order not in witness_orders,'Duplicate model witness');witness_orders.add(order)
            result=outcome(witness)
            if analysis_bound and analysis['kind']==METHOD and supported and family_qualified and expected_orders is not None:
                if order not in expected_orders:finding('model_witness_conflicts_with_control',order=list(order))
                else:
                    flag=int(order.index('publication-commit')<order.index('observe'))
                    expected=(flag,int(order.index('payload-commit')<order.index('observe')) if flag else None)
                    if result[0] is None or result[0]==1 and result[1] is None:gap('model_witness_outcome_unknown',order=list(order))
                    elif result!=expected:finding('model_witness_outcome_mismatch',order=list(order),expected=list(expected),observed=list(result))
                    else:valid_witnesses[order]=result
        observed_results=set(valid_witnesses.values())
        if analysis_bound and supported and analysis['kind']==METHOD:
            if declared!=observed_results:gap('model_outcome_witness_disagreement')
            if analysis['complete'] is True and (expected_orders is None or set(valid_witnesses)!=expected_orders):gap('model_enumeration_coverage_incomplete')
            analysis_qualified=family_qualified and contract['observer_ordered'] is True and expected_orders is not None
            analysis_exhaustive=analysis_qualified and analysis['complete'] is True and set(valid_witnesses)==expected_orders and declared==observed_results
            if analysis_qualified and (1,0) in observed_results:
                report['model_permits_stale']=True;order=next(order for order,value in valid_witnesses.items() if value==(1,0));report['model_witness']=list(order)
                if property_qualified:finding('selected_model_permits_stale',order=list(order))
            elif analysis_qualified and analysis['complete'] is True and set(valid_witnesses)==expected_orders and declared==observed_results:report['model_permits_stale']=False
    observations=evidence.get('observations');require(isinstance(observations,list),'Explicit observation list required');seen=set()
    for observation in observations:
        for key in ('run_ref','kind','model_revision_ref','program_sha256','evidence_ref'):text(observation.get(key),'observation '+key)
        require(observation['run_ref'] not in seen,'Duplicate observation identity');seen.add(observation['run_ref'])
        for key in ('payload_read_valid','all_steps_enabled'):
            require(key in observation,'Explicit observation flags required');boolean(observation[key],key)
        if observation['all_steps_enabled'] is None:gap('schedule_completion_unknown',run_ref=observation['run_ref'])
        result=outcome(observation);observation_bound=observation['model_revision_ref']==contract['model_revision_ref'] and observation['program_sha256']==program_hash
        known_method=observation['kind'] in ('owned-rtl-simulation','owned-reference-fixture')
        qualified=observation_bound and known_method and supported
        if not observation_bound:gap('observation_basis_mismatch',run_ref=observation['run_ref'])
        if not known_method:gap('observation_method_unqualified',run_ref=observation['run_ref'])
        if result[0] is None or result[0]==1 and (observation['payload_read_valid'] is not True or result[1] is None):gap('consumer_observation_unknown',run_ref=observation['run_ref'])
        elif result[0]==0 and (result[1] is not None or observation['payload_read_valid'] is not False):gap('observer_shape_unqualified',run_ref=observation['run_ref'])
        if qualified and result==(1,0) and observation['payload_read_valid'] is True:
            report['observed_stale_runs'].append(observation['run_ref'])
            if property_qualified:finding('observed_stale_owned_implementation',run_ref=observation['run_ref'])
        if qualified and analysis_exhaustive and result[0] is not None and (result[0]==0 and result[1] is None or result[0]==1 and result[1] is not None) and result not in set(valid_witnesses.values()):finding('observation_outside_supplied_model',run_ref=observation['run_ref'])
        report['observations'].append({'run_ref':observation['run_ref'],'kind':observation['kind'],'flag':result[0],'payload':result[1],
            'payload_read_valid':observation['payload_read_valid'],'complete_linearization':observation['all_steps_enabled']})
    if property_qualified and report['model_permits_stale'] is None:gap('no_qualified_model_exclusion')
    report['status']='review_required' if report['findings'] else 'incomplete' if report['gaps'] else 'within_selected_owned_model'
    return report


def exit_code(report):return {'within_selected_owned_model':0,'review_required':1,'incomplete':2}[report['status']]
