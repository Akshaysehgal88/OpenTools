#!/usr/bin/env python3
"""Create or normalize one explicitly scoped owned publication litmus family."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

PROFILE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROFILE))
from ordering_core import METHOD,MODEL,digest,exit_code,program_digest,require,review
from reference_model import CASES,DOMAINS,config,enumerate_outcomes,prefix,trace


def save(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def revision():
    sources={name:hashlib.sha256((PROFILE/'examples'/name).read_bytes()).hexdigest() for name in ('buffered_publication.sv','reference_model.py')}
    return 'sha256:'+digest(sources),sources


def attributes(case):
    io=config(case)['flag_io']
    return {role:{'path_ref':path,'cacheability_ref':'owned-no-cache','shareability_ref':'owned-observer-registers',
        'mapping_revision_ref':'owned-map-v1','evidence_ref':'owned-path:'+role} for role,path in
        (('payload','owned-normal-write-queue'),('publication','owned-mmio-output-queue' if io else 'owned-normal-publication-queue'))}


def program(case):
    cfg=config(case);steps=[]
    for command in prefix(case):
        if command==0:continue
        if command==2:
            step={'id':'ordering-control','kind':'ordering_control','actor_ref':'producer',
                  'predecessors':[d for d,b in DOMAINS.items() if cfg['pred']&b],'successors':[d for d,b in DOMAINS.items() if cfg['succ']&b]}
        else:step={'id':'payload-issue' if command==1 else 'publication-issue','kind':'store','actor_ref':'producer',
                   'object_ref':'payload' if command==1 else 'publication','domain':'W' if command==1 or not cfg['flag_io'] else 'O','value':1}
        step['evidence_ref']='buffered_publication.sv:producer-prefix';steps.append(step)
    return steps


def contract_for(case):
    rev,sources=revision();io=config(case)['flag_io']
    return {'format':'opentools.ordering.contract.v1','scope':{'project':'owned-publication','configuration':case,
        'boundary_ref':'normal-to-mmio-output' if io else 'normal-to-normal-flag','mode':'single-producer-ordered-observer'},
        'basis_ref':'owned-buffered-path-v1','inputs_complete':True,'model_ref':MODEL,'model_kind':'owned-implementation',
        'model_revision_ref':rev,'source_sha256':sources,'sentinel_bits':1,'observer_ordered':True,
        'producer_ref':'producer','observer_ref':'device-observer' if io else 'memory-observer',
        'producer_contract_ref':'owned-sequenced-command-driver.v1','observer_contract_ref':'owned-ordered-poll-and-read.v1',
        'attribute_basis_ref':'owned-uncached-register-paths.v1','visibility_basis_ref':'owned-independent-commit-queues.v1',
        'instruction_scope_ref':'owned-HDL-commands-not-ISA','program':program(case),'attributes':attributes(case)}


def model_result(contract,enumeration):
    return {'kind':METHOD,'model_ref':contract['model_ref'],'model_revision_ref':contract['model_revision_ref'],
        'program_sha256':program_digest(contract),'complete':True,'outcomes':enumeration['outcomes'],
        'witnesses':[dict(item,evidence_ref='enumeration.json:linearizations:'+str(i)) for i,item in enumerate(enumeration['linearizations'])],
        'evidence_ref':'enumeration.json:complete-owned-three-event-orderings'}


def normalize_observation(contract,run,rows,kind):
    final=rows[-1]
    return {'run_ref':'schedule-'+str(run),'kind':kind,'model_revision_ref':contract['model_revision_ref'],
        'program_sha256':program_digest(contract),'payload_read_valid':bool(final['rpayload_valid']),
        'all_steps_enabled':all(row['step_enabled'] for row in rows[-3:]),'flag':final['rflag'],
        'payload':final['rpayload'] if final['rpayload_valid'] else None,'evidence_ref':'run-'+str(run)+'.json:seq-'+str(final['seq'])}


def evidence_for(contract,enumeration,observations):
    return {'format':'opentools.ordering.evidence.v1','scope':contract['scope'],'basis_ref':contract['basis_ref'],
        'inputs_complete':True,'contract_sha256':digest(contract),'model_result':model_result(contract,enumeration),'observations':observations}


def claim_for(contract,evidence,case):
    io=config(case)['flag_io'];rev,_=revision()
    return {'format':'opentools.ordering.claim.v1','scope':contract['scope'],'basis_ref':contract['basis_ref'],'inputs_complete':True,
        'contract_sha256':digest(contract),'evidence_sha256':digest(evidence),'model_ref':MODEL,'model_revision_ref':rev,
        'producer_ref':'producer','observer_ref':'device-observer' if io else 'memory-observer',
        'producer_contract_ref':'owned-sequenced-command-driver.v1','observer_contract_ref':'owned-ordered-poll-and-read.v1',
        'property':'publication_implies_payload','strength':'selected_model','payload_event_ref':'payload-issue',
        'publication_event_ref':'publication-issue','control_event_ref':'ordering-control' if config(case)['placement'] else None,
        'required_domains':{'payload':'W','publication':'O' if io else 'W'},
        'required_attributes':{role:{k:value[k] for k in ('path_ref','cacheability_ref','shareability_ref','mapping_revision_ref')} for role,value in attributes(case).items()}}


def example(case):
    contract=contract_for(case);count=1 if case=='ram-selected-good' else 6
    observations=[normalize_observation(contract,run,trace(case,run),'owned-reference-fixture') for run in range(count)]
    evidence=evidence_for(contract,enumerate_outcomes(case),observations);return contract,evidence,claim_for(contract,evidence,case)


def from_native(output):
    observed=json.loads((output/'observation.json').read_text(encoding='utf-8'));summary=[]
    actual_configs={}
    for line in (output/'native.stdout.txt').read_text(encoding='utf-8').splitlines():
        if line.startswith('CONFIG '):
            index,io,pred,succ,placement=map(int,line.split()[1:]);actual_configs[index]=[io,pred,succ,placement]
    for index,case in enumerate(CASES):
        folder=output/case;contract=contract_for(case);cfg=config(case)
        require(contract['source_sha256']['buffered_publication.sv']==observed['source_sha256'],'Current RTL differs from native source')
        require(actual_configs[index]==[int(cfg[k]) for k in ('flag_io','pred','succ','placement')],'Native config differs from current normalization')
        runs=1 if case=='ram-selected-good' else 6;observations=[]
        for run in range(runs):
            rows=json.loads((folder/('run-'+str(run)+'.json')).read_text(encoding='utf-8'));expected=trace(case,run)
            require(len(rows)==len(expected) and all(all(row[k]==v for k,v in reference.items()) for row,reference in zip(rows,expected)),'Retained native trace differs from current reference')
            observations.append(normalize_observation(contract,run,rows,'owned-rtl-simulation'))
        enumeration=json.loads((folder/'enumeration.json').read_text(encoding='utf-8'))
        require(enumeration==enumerate_outcomes(case),'Native run enumeration differs from current reference')
        evidence=evidence_for(contract,enumeration,observations);claim=claim_for(contract,evidence,case);report=review(contract,evidence,claim)
        require(exit_code(report)==(0 if case in ('ram-ww','mmio-wo','mmio-full') else 1),'Unexpected ordering disposition: '+case)
        require(not report['gaps'],'Unexpected owned profile gaps: '+case)
        for key,value in (('contract',contract),('evidence',evidence),('claim',claim),('report',report)):save(folder/(key+'.json'),value)
        summary.append({'case':case,'status':report['status'],'control_covers_boundary':report['control_covers_boundary'],
            'model_permits_stale':report['model_permits_stale'],'model_witness':report['model_witness'],
            'observed_stale_runs':report['observed_stale_runs'],'findings':report['findings'],'gaps':report['gaps']})
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--case',choices=CASES,default='mmio-ww');args=parser.parse_args()
    output=Path(args.directory);output.mkdir(parents=True,exist_ok=False);values=example(args.case)
    for key,value in zip(('contract','evidence','claim'),values):save(output/(key+'.json'),value)
    save(output/'enumeration.json',enumerate_outcomes(args.case));save(output/'report.json',review(*values));print(output)


if __name__=='__main__':main()
