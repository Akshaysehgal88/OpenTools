#!/usr/bin/env python3
"""Create explicit reference fixtures or an owned generated native source pair."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys

PROFILE=Path(__file__).resolve().parents[1];MODULE=PROFILE.parents[1];sys.path[:0]=[str(PROFILE),str(MODULE)]
from configuration_core import digest,review
from layout_capture import source_ref

CASES=('payload-matched','payload-stale-default','payload-same-number','payload-feature-stale',
       'storage-matched','storage-depth-stale','storage-agree-wrong-default','storage-wide-matched','payload-nonintegral','payload-mode-stale')
FACTS={'hardware':['WORD_BITS','DEPTH','FEATURE','MODE'],'software':['WORD_BYTES','DEPTH','FEATURE','MODE']}

def symbol_map(request,kind):
    if request['family']=='payload-word':return {name:name for name in FACTS[kind]}
    return dict(zip(FACTS[kind],['CELL_BITS' if kind=='hardware' else 'CELL_BYTES','ROW_TOTAL','BANK_ON','ACCESS_MODE']))

def native_values(request,kind,values):return {symbol_map(request,kind)[key]:value for key,value in values.items()}

def fact_names(request,kind):return list(symbol_map(request,kind).values())

def save(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def case_spec(case):
    if case not in CASES:raise ValueError('Unknown example')
    storage=case.startswith('storage');wanted={'WORD_BITS':32 if storage else 64,'DEPTH':64 if storage else 16,'FEATURE':0 if storage else 1,'MODE':0}
    if case=='payload-feature-stale':wanted['FEATURE']=0
    if case=='storage-agree-wrong-default':wanted['WORD_BITS']=64
    if case=='storage-wide-matched':wanted.update(WORD_BITS=64,DEPTH=128,FEATURE=1)
    if case=='payload-mode-stale':wanted['MODE']=1
    parameters=wanted.copy();defines={'WORD_BYTES':wanted['WORD_BITS']//8,'DEPTH':wanted['DEPTH'],'FEATURE':wanted['FEATURE'],'MODE':wanted['MODE']}
    if case=='payload-stale-default':del defines['WORD_BYTES']
    if case=='payload-same-number':defines['WORD_BYTES']=64
    if case=='payload-feature-stale':del defines['FEATURE']
    if case=='payload-mode-stale':del defines['MODE']
    if case=='storage-depth-stale':del defines['DEPTH']
    if case=='storage-agree-wrong-default':del parameters['WORD_BITS'];del defines['WORD_BYTES']
    if case=='payload-nonintegral':parameters['WORD_BITS']=66
    return {'case':case,'family':'storage-word' if storage else 'payload-word','wanted':wanted,'hardware_parameters':parameters,'software_defines':defines}

def effective(request):
    hardware={'WORD_BITS':32,'DEPTH':16,'FEATURE':1,'MODE':0}
    hardware.update(request['hardware_parameters']);software={'WORD_BYTES':4,'DEPTH':16,'FEATURE':1,'MODE':0};software.update(request['software_defines'])
    return hardware,software

def generate_pair(case,folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False);request=case_spec(case)
    for name in ('configuration.sv','configuration.h','defaults.h'):shutil.copyfile(PROFILE/'examples'/name,folder/name)
    if effective(request)[0]['WORD_BITS']>64:
        path=folder/'configuration.sv';source=path.read_text(encoding='utf-8')
        source=source.replace('logic [((WORD_BITS+7)/8)*8-1:0] payload;',
            'logic [((WORD_BITS+7)/8)*8-65:0] tail; logic [63:0] payload;')
        path.write_text(source,encoding='utf-8')
    if request['family']=='storage-word':
        for name,kind in (('configuration.sv','hardware'),('configuration.h','software'),('defaults.h','software')):
            path=folder/name;source=path.read_text(encoding='utf-8')
            for old,new in symbol_map(request,kind).items():source=re.sub(r'\b'+old+r'\b',new,source)
            path.write_text(source,encoding='utf-8')
    (folder/'selected_config.h').write_text(''.join('#define '+key+' '+str(value)+'\n' for key,value in native_values(request,'software',request['software_defines']).items()),encoding='utf-8')
    save(folder/'request.json',request);save(folder/'parameters.json',native_values(request,'hardware',request['hardware_parameters']))
    save(folder/'c-profile.json',{'fields':[{'name':'anchor'}],'defines':{}})
    return request

def contract_for(case,hardware,software,native=False):
    request=case_spec(case);wanted=request['wanted'];nonintegral=case=='payload-nonintegral'
    contract={'format':'opentools.configuration.contract.v1',
        'scope':{'project':'owned-generated-configuration','configuration_ref':case,'family_ref':request['family'],'mode':'owned-mode1' if wanted['MODE'] else 'functional'},
        'basis_ref':'owned-configuration-roles.v1','source_revision_ref':'sha256:'+digest(request),'requirements_ref':'owned-request:'+case,'inputs_complete':True,
        'views':{},'unit_rules':{},'parameters':[]}
    for name,capture in (('hardware',hardware),('software',software)):
        contract['views'][name]={'export_sha256':digest(capture),'source_ref':capture['source_ref'],'interface_ref':request['family'],'configuration_ref':case,
            'frontend_ref':('pyslang 12.0.0' if name=='hardware' else 'GCC 13.3.0') if native else 'owned-independent-reference',
            'fact_phase':'elaboration' if name=='hardware' else 'compile','fact_kind':'native' if native else 'reference-fixture'}
    def rule(key,source,target,numerator=1,denominator=1):
        contract['unit_rules'][key]={'kind':'identity' if source==target and numerator==denominator==1 else 'exact-scale',
            'source_unit':source,'target_unit':target,'numerator':numerator,'denominator':denominator,'evidence_ref':'owned-source-units:'+key}
    rule('bits','bits','bits');rule('bytes-to-bits','bytes','bits',8);rule('count','count','count');rule('flag','flag','flag');rule('mode','mode-index','mode-index')
    if nonintegral:rule('bits-to-bytes','bits','bytes',1,8);rule('bytes','bytes','bytes')
    for role,hname,sname,unit,required,hrule,srule,hunit,sunit in (
        ('word-width','WORD_BITS','WORD_BYTES','bytes' if nonintegral else 'bits',wanted['WORD_BITS']//8 if nonintegral else wanted['WORD_BITS'],
         'bits-to-bytes' if nonintegral else 'bits','bytes' if nonintegral else 'bytes-to-bits','bits','bytes'),
        ('depth','DEPTH','DEPTH','count',wanted['DEPTH'],'count','count','count','count'),
        ('feature','FEATURE','FEATURE','flag',wanted['FEATURE'],'flag','flag','flag','flag'),
        ('mode','MODE','MODE','mode-index',wanted['MODE'],'mode','mode','mode-index','mode-index')):
        contract['parameters'].append({'id':role,'unit':unit,'required_value':required,'evidence_ref':'request.json:wanted:'+hname,
            'hardware':{'fact_ref':symbol_map(request,'hardware')[hname],'unit':hunit,'rule_ref':hrule},
            'software':{'fact_ref':symbol_map(request,'software')[sname],'unit':sunit,'rule_ref':srule}})
    return contract

def reference_capture(request,kind,values):
    selection=fact_names(request,kind);sources={('reference.sv' if kind=='hardware' else 'reference.h'):digest(request)}
    provenance={'sources':sources,'fact_kind':'reference-fixture','fact_phase':'elaboration' if kind=='hardware' else 'compile','fact_selection':selection.copy()}
    if kind=='hardware':
        provenance.update(requested_parameters=native_values(request,kind,request['hardware_parameters']),actual_port_parameters={k:str(v) for k,v in native_values(request,kind,values).items()},selected_integral_parameters=native_values(request,kind,values))
        context={'overrides':provenance['requested_parameters'],'observed_parameters':selection}
    else:
        provenance.update(profile={'fields':[{'name':'anchor'}],'defines':{}},selected_constants=native_values(request,kind,values))
        context={'profile':provenance['profile'],'constants':selection}
    ref=source_ref(sources,context);provenance['parameter_fact_refs' if kind=='hardware' else 'constant_fact_refs']={name:ref+'#'+name for name in selection}
    width=((values['WORD_BITS']+7)//8)*8 if kind=='hardware' else 64
    fields=[{'name':'payload' if kind=='hardware' else 'anchor','offset_bits':0,'width_bits':min(width,64),'signed':False,'enum_values':{},'evidence_ref':ref+'#field'}]
    if width>64:fields.append({'name':'tail','offset_bits':64,'width_bits':width-64,'signed':False,'enum_values':{},'evidence_ref':ref+'#tail'})
    capture={'format':'opentools.record-layout.v1','kind':kind,'basis':'packed-lsb' if kind=='hardware' else 'c-object','record':'reference-configuration',
        'interface_ref':request['family'],'configuration_ref':request['case'],'source_ref':ref,'frontend_ref':'owned-independent-reference',
        'inputs_complete':True,'fields_complete':True,'size_bits':width,'provenance':provenance,
        'fields':fields}
    if kind=='software':capture.update(alignment_bytes=8,byte_order='little',integer_representation='binary-twos-complement',target_abi='reference scalar anchor')
    return capture

def example(case):
    request=case_spec(case);hvalues,svalues=effective(request)
    hardware=reference_capture(request,'hardware',hvalues);software=reference_capture(request,'software',svalues)
    return hardware,software,contract_for(case,hardware,software)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--case',choices=CASES,default='payload-stale-default');args=parser.parse_args()
    folder=Path(args.directory);folder.mkdir(parents=True,exist_ok=False);values=example(args.case)
    for key,value in zip(('hardware','software','contract'),values):save(folder/(key+'.json'),value)
    save(folder/'report.json',review(*values));print(folder)

if __name__=='__main__':main()
