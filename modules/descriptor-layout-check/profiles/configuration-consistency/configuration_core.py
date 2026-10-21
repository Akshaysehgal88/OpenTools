"""Compare selected native configuration facts with independent units and intent."""
import hashlib
import json
from pathlib import Path
import sys

MODULE=Path(__file__).resolve().parents[2];sys.path.insert(0,str(MODULE))
from layout_core import fields as layout_fields
from layout_capture import fact_selection,source_ref

MIN=-(1<<63);MAX=(1<<63)-1
def require(condition,message):
    if not condition:raise ValueError(message)
def text(value,label):require(isinstance(value,str) and bool(value.strip()),label+' required')
def integer(value,label,nullable=False):require(nullable and value is None or type(value) is int and MIN<=value<=MAX,label+' must be signed64 or explicit null')
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def read_json(path):
    def unique(pairs):
        result={}
        for key,value in pairs:require(key not in result,'Duplicate JSON key: '+key);result[key]=value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique,
                      parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON value')))

def review(hardware,software,contract):
    require(isinstance(contract,dict) and contract.get('format')=='opentools.configuration.contract.v1','Supported configuration contract required')
    require(isinstance(contract.get('scope'),dict) and set(contract['scope'])=={'project','configuration_ref','family_ref','mode'},'Exact configuration scope required')
    for value in contract['scope'].values():text(value,'scope')
    for key in ('basis_ref','source_revision_ref','requirements_ref'):text(contract.get(key),key)
    require(type(contract.get('inputs_complete')) is bool,'Boolean contract completeness required')
    require(isinstance(contract.get('views'),dict) and set(contract['views'])=={'hardware','software'},'Independent hardware/software view bindings required')
    result={'format':'opentools.configuration.report.v1','scope':contract['scope'],
        'bindings':{key+'_sha256':digest(value) for key,value in (('hardware',hardware),('software',software),('contract',contract))},
        'views':{},'parameters':[],'findings':[],'gaps':[],
        'limits':['At most five selected signed64 roles with explicit exact unit rules and independent required values. Agreement is within supplied captures, not generator/dependency closure or signoff.',
                  'Native profile is selected Slang12/GCC13.3 Linux facts. Configuration agreement does not establish binary layout, wire encodings, formal/DFT/STA applicability or feature interaction correctness.']}
    def gap(kind,**details):result['gaps'].append(dict(kind=kind,**details))
    def finding(kind,**details):result['findings'].append(dict(kind=kind,**details))
    if not contract['inputs_complete']:gap('contract_inputs_incomplete')
    resolved={}
    for name,capture in (('hardware',hardware),('software',software)):
        require(isinstance(capture,dict),'Capture object required');layout_fields(capture)
        expected=contract['views'][name];require(isinstance(expected,dict),'View contract required')
        for key in ('export_sha256','source_ref','interface_ref','configuration_ref','frontend_ref','fact_phase','fact_kind'):text(expected.get(key),'required view '+key)
        require(expected['fact_kind'] in ('native','reference-fixture'),'Explicit capture kind required')
        matched=True
        if digest(capture)!=expected['export_sha256']:gap('export_binding_mismatch',view=name);matched=False
        for key in ('source_ref','interface_ref','configuration_ref','frontend_ref'):
            if capture.get(key)!=expected[key]:gap('view_basis_mismatch',view=name,field=key);matched=False
        if capture.get('kind')!=name:gap('view_kind_mismatch',view=name);matched=False
        provenance=capture.get('provenance');require(isinstance(provenance,dict),'Capture provenance required')
        for key in ('fact_phase','fact_kind'):
            if provenance.get(key)!=expected[key]:gap('view_fact_basis_mismatch',view=name,field=key);matched=False
        if provenance.get('fact_phase')!=('elaboration' if name=='hardware' else 'compile'):gap('fact_phase_unqualified',view=name);matched=False
        if provenance.get('fact_kind')=='native':
            if name=='hardware' and capture['frontend_ref']!='pyslang 12.0.0' or name=='software' and (capture['frontend_ref']!='GCC 13.3.0' or capture.get('target_abi')!='x86_64-linux-gnu LP64 -m64 -fno-short-enums'):
                gap('native_frontend_unqualified',view=name);matched=False
        elif provenance.get('fact_kind')!='reference-fixture':gap('capture_method_unqualified',view=name);matched=False
        sources=provenance.get('sources')
        if not isinstance(sources,dict) or not sources:gap('source_inventory_absent',view=name);matched=False
        else:
            for path,checksum in sources.items():
                text(path,'source path');require(isinstance(checksum,str) and len(checksum)==64 and all(c in '0123456789abcdef' for c in checksum),'Source SHA-256 required')
        selection=provenance.get('fact_selection')
        if selection is None:gap('resolved_fact_selection_absent',view=name);matched=False
        else:fact_selection(selection)
        values=provenance.get('selected_integral_parameters' if name=='hardware' else 'selected_constants')
        refs=provenance.get('parameter_fact_refs' if name=='hardware' else 'constant_fact_refs')
        if not isinstance(values,dict) or not isinstance(refs,dict):gap('resolved_facts_absent',view=name);matched=False;values={};refs={}
        else:
            for key,value in values.items():text(key,'fact name');integer(value,'resolved fact',True)
            if selection is not None and (set(values)!=set(selection) or set(refs)!=set(selection)):gap('fact_selection_disagreement',view=name);matched=False
            for ref in refs.values():text(ref,'fact evidence')
        if matched:
            if name=='hardware':
                context={'overrides':provenance.get('requested_parameters'),'observed_parameters':selection}
            else:context={'profile':provenance.get('profile'),'constants':selection}
            if source_ref(sources,context)!=capture['source_ref']:gap('source_context_binding_mismatch',view=name);matched=False
        if not capture['inputs_complete']:gap('capture_inputs_incomplete',view=name)
        result['views'][name]={'binding_matches':matched,'fact_kind':provenance.get('fact_kind'),'fact_phase':provenance.get('fact_phase'),
            'source_ref':capture['source_ref'],'frontend_ref':capture['frontend_ref'],'inputs_complete':capture['inputs_complete']}
        resolved[name]=(values,refs,matched)
    rules=contract.get('unit_rules');require(isinstance(rules,dict),'Explicit unit rule inventory required')
    for key,rule in rules.items():
        text(key,'rule id');require(isinstance(rule,dict),'Unit rule object required')
        require(set(rule)=={'kind','source_unit','target_unit','numerator','denominator','evidence_ref'},'Exact unit rule fields required')
        for field in ('source_unit','target_unit','evidence_ref'):text(rule[field],'rule '+field)
        require(rule['kind'] in ('identity','exact-scale','unknown'),'Supported or explicit unknown unit rule required')
        if rule['kind']=='unknown':require(rule['numerator'] is None and rule['denominator'] is None,'Unknown transform cannot contain a guessed scale')
        else:
            for field in ('numerator','denominator'):integer(rule[field],'scale '+field);require(rule[field]>0,'Positive exact scale required')
            if rule['kind']=='identity':require(rule['numerator']==rule['denominator']==1 and rule['source_unit']==rule['target_unit'],'Identity requires the same unit and scale1/1')
    parameters=contract.get('parameters');require(isinstance(parameters,list) and 1<=len(parameters)<=5,'Select one to five configuration roles')
    ids=set();used={'hardware':set(),'software':set()}
    for parameter in parameters:
        require(isinstance(parameter,dict),'Configuration role required')
        for key in ('id','evidence_ref'):text(parameter.get(key),'parameter '+key)
        require(parameter['id'] not in ids,'Unique parameter roles required');ids.add(parameter['id'])
        require('unit' in parameter and (parameter['unit'] is None or isinstance(parameter['unit'],str) and parameter['unit'].strip()),'Canonical unit or explicit null required')
        require('required_value' in parameter,'Independent required value or null required');integer(parameter['required_value'],'required value',True)
        if parameter['unit'] is None:gap('canonical_unit_unknown',parameter=parameter['id'])
        if parameter['required_value'] is None:gap('required_value_unknown',parameter=parameter['id'])
        row={'id':parameter['id'],'unit':parameter['unit'],'required_value':parameter['required_value'],'evidence_ref':parameter['evidence_ref'],'observations':{}}
        canonical={}
        for name in ('hardware','software'):
            binding=parameter.get(name);require(isinstance(binding,dict) and set(binding)=={'fact_ref','unit','rule_ref'},'Exact fact/unit/rule binding required')
            text(binding['fact_ref'],'fact reference');require(binding['fact_ref'] not in used[name],'A source fact cannot silently stand for two independent roles');used[name].add(binding['fact_ref'])
            for field in ('unit','rule_ref'):require(binding[field] is None or isinstance(binding[field],str) and binding[field].strip(),'Explicit '+field+' or null required')
            values,refs,matched=resolved[name];observed={'fact_ref':binding['fact_ref'],'unit':binding['unit'],'raw_value':None,'canonical_value':None,'evidence_ref':None};row['observations'][name]=observed
            if not matched:continue
            if binding['fact_ref'] not in values or values[binding['fact_ref']] is None:gap('selected_fact_unknown',view=name,parameter=parameter['id']);continue
            raw=values[binding['fact_ref']];observed.update(raw_value=raw,evidence_ref=refs[binding['fact_ref']])
            rule=rules.get(binding['rule_ref'])
            if rule is None:gap('unit_rule_absent',view=name,parameter=parameter['id']);continue
            if binding['unit'] is None or parameter['unit'] is None or binding['unit']!=rule['source_unit'] or parameter['unit']!=rule['target_unit']:
                gap('unit_rule_basis_mismatch',view=name,parameter=parameter['id']);continue
            if rule['kind']=='unknown':gap('unit_transform_unknown',view=name,parameter=parameter['id']);continue
            scaled=raw*rule['numerator'];denominator=rule['denominator']
            if scaled%denominator:finding('non_integral_unit_conversion',view=name,parameter=parameter['id'],raw_value=raw);continue
            value=scaled//denominator
            if not MIN<=value<=MAX:gap('canonical_range_unqualified',view=name,parameter=parameter['id']);continue
            canonical[name]=value;observed['canonical_value']=value
            if parameter['required_value'] is not None and value!=parameter['required_value']:
                finding('required_parameter_mismatch',view=name,parameter=parameter['id'],required=parameter['required_value'],observed=value)
        if len(canonical)==2 and canonical['hardware']!=canonical['software']:
            finding('peer_parameter_mismatch',parameter=parameter['id'],hardware=canonical['hardware'],software=canonical['software'])
        result['parameters'].append(row)
    result['status']='review_required' if result['findings'] else 'incomplete' if result['gaps'] else 'within_selected_contract'
    return result

def exit_code(report):return {'within_selected_contract':0,'review_required':1,'incomplete':2}[report['status']]
