#!/usr/bin/env python3
"""Generate an explicitly synthetic coverage plateau with incomplete stress work."""
import argparse
import copy
import json
from pathlib import Path


def example():
    contract={'format':'opentools.campaign-contract.v1','campaign_ref':'synthetic:stress-campaign','scope_ref':'synthetic:scope-A',
        'configuration_ref':'synthetic:config-A','model_ref':'synthetic:model-A','population_ref':'synthetic:independent planned population',
        'population_complete':True,'required_run_refs':['a','b','c'],'evidence_ref':'synthetic:objectives declared before review',
        'objectives':[
            {'id':'required','kind':'execution','description':'Required native checker passes','basis_ref':'synthetic:checker verdict mapping','policy_ref':'synthetic:execution policy',
             'eligible_states':['passed'],'target':{'run_refs':['a','b','c']}},
            {'id':'coverage','kind':'coverage','description':'Named functional goals, not generic weighted coverage','basis_ref':'synthetic:four named goals v1','policy_ref':'synthetic:coverage policy',
             'eligible_states':['passed'],'target':{'population_ids':['bin0','bin1','bin2','bin3'],'required_ids':['bin0','bin1','bin2','bin3']}},
            {'id':'stress','kind':'exposure','description':'Qualified effective transaction events; no independent-trial claim','basis_ref':'synthetic:accepted and checked events v1','policy_ref':'synthetic:event-count policy',
             'eligible_states':['passed'],'target':{'value':192,'unit':'checked_handshake'}}],
        'policy':{'ref':'synthetic:local campaign policy','evidence_ref':'synthetic:review authority, no automatic stopping',
            'allowed_recommendations':['continue','inspect_effectiveness','redirect','seek_policy'],'limits':['No automatic termination or statistical assurance.']}}
    def run(ref,executed):
        return {'run_ref':ref,'configuration_ref':contract['configuration_ref'],'model_ref':contract['model_ref'],
            'native_state':'CHECKER_PASS' if executed else 'PLANNED','state':'passed' if executed else 'not_run',
            'evidence_ref':'synthetic:'+ref+(':checker output' if executed else ':planned obligation'),'resources':[],
            'measurements':[
                {'objective_id':'coverage','basis_ref':contract['objectives'][1]['basis_ref'],'evidence_ref':'synthetic:'+ref+':named goal export',
                 'qualified':True,'complete':True,'data':{'population_ids':['bin0','bin1','bin2','bin3'],'hit_ids':['bin0','bin1','bin2']}},
                {'objective_id':'stress','basis_ref':contract['objectives'][2]['basis_ref'],'evidence_ref':'synthetic:'+ref+':qualified counter',
                 'qualified':True,'complete':True,'data':{'unit':'checked_handshake','ranges':[{'space_ref':'synthetic:events:'+ref,'start':0,'stop':64,'evidence_ref':'synthetic:'+ref+':event journal'}]}}
            ] if executed else []}
    before={'format':'opentools.campaign-snapshot.v1','campaign_ref':contract['campaign_ref'],'snapshot_ref':'synthetic:before','scope_ref':contract['scope_ref'],
        'captured_at':'2026-01-01T00:00:00+00:00','mode':'cumulative','complete':True,'evidence_ref':'synthetic:full cumulative export',
        'runs':[run('a',True),run('b',False),run('c',False)]}
    after=copy.deepcopy(before);after.update(snapshot_ref='synthetic:after',captured_at='2026-01-01T01:00:00+00:00')
    after['runs'][1]=run('b',True)
    return contract,before,after


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');args=parser.parse_args()
    out=Path(args.directory);out.mkdir(parents=True,exist_ok=False)
    for name,value in zip(('contract','before','after'),example()):
        (out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Created synthetic offline campaign records; no job executed.')


if __name__=='__main__':main()
