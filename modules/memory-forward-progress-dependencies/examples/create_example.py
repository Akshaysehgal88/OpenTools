#!/usr/bin/env python3
"""Create explicit wait/release fixtures or normalize retained native observations."""
import argparse
import json
from pathlib import Path
import sys

MODULE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(MODULE))
from progress_core import digest,exit_code,require,review
from episode_model import CASES,config,explore,trace


def save(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def names(case):
    accelerator=case.startswith('accelerator')
    return (['output-slot','work-slot','escape-slot'] if accelerator else ['response-slot','snoop-ack-slot','escape-slot'],
            ['producer-stage','consumer-stage'] if accelerator else ['request-owner','snoop-owner'])


def model_for(case):
    strategy,external=config(case);resources,actors=names(case);resources=resources[:3 if strategy==1 else 2]
    actor_roles=['episode-first-owner','episode-second-owner']
    resource_roles=['retained-first-path','opposing-completion-path','independent-escape-path']
    waits=[]
    for actor in range(2):
        first=0 if actor==0 or strategy==3 else 1
        second=1 if actor==0 or strategy==3 else 2 if strategy==1 else 0
        waits.append({'id':'retained-wait-'+str(actor),'actor_ref':actors[actor],
            'held_resource_ref':resources[first],'requested_resource_ref':resources[second],
            'active':True,'retains_until_acquire':not(actor==0 and strategy==2),
            'mode_ref':'owned-strategy-'+str(strategy),'release_condition_ref':'early-drop' if actor==0 and strategy==2 else 'complete-after-second-acquire',
            'evidence_ref':'resource_episode.sv:request_for-and-stage-transitions'})
    return {'format':'opentools.progress.model.v1',
        'scope':{'project':'owned-resource-episode','configuration':case,'mode':'finite-two-transaction',
                 'episode_ref':'reset-through-completion','traffic_class_ref':'owned-accelerator-like' if case.startswith('accelerator') else 'owned-coherence-like'},
        'basis_ref':'owned-episode-source-v1','inputs_complete':True,'semantics':'finite-retained-resource-episode',
        'premises':{'closed_resource_census':True,'release_paths_complete':True,'autonomous_updates_absent':True,
            'external_actions_absent':None if case=='coherence-open-environment' else not external},
        'premises_evidence_ref':'resource_episode.sv:owned-finite-no-arrivals-no-timers-contract',
        'fair_scheduling':False if case=='coherence-starved-escape' else True,
        'resources':[{'id':r,'role_ref':resource_roles[i],'capacity':1,'unit':'slot','evidence_ref':'resource_episode.sv:exclusive-held-bits'} for i,r in enumerate(resources)],
        'actors':[{'id':actor,'role_ref':actor_roles[i],'evidence_ref':'resource_episode.sv:phase-and-held-owner-'+str(i)} for i,actor in enumerate(actors)],
        'waits':waits,'external_actions':[{'id':'reclaim-first-owner','may_release':[resources[0]],'evidence_ref':'resource_episode.sv:selected-2-external_enabled'}] if external else []}


def normalize(model,row,evidence):
    resources=[r['id'] for r in model['resources']];actors=[a['id'] for a in model['actors']];states=[]
    for index,suffix in enumerate(('a','b')):
        held=row['held_'+suffix];requested=row['request_'+suffix]
        require(held < 1<<len(resources) and requested < 1<<len(resources),'Observed resource bit outside selected mapping')
        states.append({'actor_ref':actors[index],'state_ref':'phase-'+str(row['phase_'+suffix]),
            'pending':not bool(row['done_'+suffix]),'complete':bool(row['done_'+suffix]),
            'held':{r:int(bool(held&(1<<i))) for i,r in enumerate(resources)},
            'requested':{r:int(bool(requested&(1<<i))) for i,r in enumerate(resources)},
            'release_enabled':bool(row['release_'+suffix]),'advance_enabled':bool(row['enabled_'+suffix]),'evidence_ref':evidence})
    require(bool(model['external_actions']) or row['external_enabled']==0,'Unmapped external release observed')
    return {'seq':row['seq'],'time_tick':row.get('time_tick',row['seq']),'selected_action_ref':'native-selector-'+str(row['selected']),
        'actors':states,'external_enabled':{'reclaim-first-owner':bool(row['external_enabled'])} if model['external_actions'] else {},'evidence_ref':evidence}


def journal_for(model,samples,basis):
    return {'format':'opentools.progress.journal.v1','scope':model['scope'],'basis_ref':model['basis_ref'],
        'inputs_complete':True,'model_sha256':digest(model),'window_ref':'sample-0-through-12','window_closed':True,
        'observations_complete':True,'reachable_prefix_confirmed':True,'reachability_basis_ref':basis,'samples':samples}


def policy_for(model,journal,case):
    resources,actors=names(case);resources=resources[:3 if config(case)[0]==1 else 2]
    # Independent expected application census; never generated from observed samples.
    return {'format':'opentools.progress.policy.v1','scope':model['scope'],'basis_ref':model['basis_ref'],
        'inputs_complete':True,'model_sha256':digest(model),'journal_sha256':digest(journal),'window_ref':journal['window_ref'],
        'required_resources':[{'id':r,'role_ref':['retained-first-path','opposing-completion-path','independent-escape-path'][i],
            'unit':'slot','evidence_ref':'application:resource-obligation-'+str(i)} for i,r in enumerate(resources)],
        'required_actors':[{'id':actor,'role_ref':['episode-first-owner','episode-second-owner'][i],
            'evidence_ref':'application:both-transactions-must-be-covered'} for i,actor in enumerate(actors)],
        'start_seq':0,'end_seq':12,'require_completion_at_end':True}


def example(case):
    model=model_for(case);samples=[normalize(model,row,'fixture:independent-ledger:'+str(row['seq'])) for row in trace(case)]
    journal=journal_for(model,samples,'fixture:exhaustive-owned-episode-model')
    return model,journal,policy_for(model,journal,case)


def from_native(output):
    observation=json.loads((output/'observation.json').read_text(encoding='utf-8'));summary=[]
    for case in CASES:
        folder=output/case;raw=json.loads((folder/'raw.json').read_text(encoding='utf-8'))
        model=model_for(case);model['provenance']={'source_sha256':observation['source_sha256'],
            'role':'Owned abstract finite-resource episode; role mapping is not an export from an actual coherence/accelerator implementation.'}
        samples=[normalize(model,row,row['evidence_ref']) for row in raw]
        journal=journal_for(model,samples,'state-search.json:reachable_states-and-per-action-native-oracle-comparison')
        policy=policy_for(model,journal,case);report=review(model,journal,policy)
        require(exit_code(report)==(0 if case in ('coherence-escape','coherence-release-before-wait','accelerator-ordered') else 1),'Unexpected review disposition: '+case)
        require(bool(report['blocking_witnesses'])==(case in ('coherence-opposite','accelerator-opposite')),'Unexpected conditional blocking classification: '+case)
        for name,value in (('model',model),('journal',journal),('policy',policy),('report',report)):save(folder/(name+'.json'),value)
        summary.append({'case':case,'status':report['status'],'candidate_cycles':report['candidate_cycles'],
            'blocking_witness_samples':len(report['blocking_witnesses']),'findings':report['findings'],'gaps':report['gaps']})
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--case',choices=CASES,default='coherence-opposite');args=parser.parse_args()
    directory=Path(args.directory);directory.mkdir(parents=True,exist_ok=False)
    values=example(args.case)
    for name,value in zip(('model','journal','policy'),values):save(directory/(name+'.json'),value)
    save(directory/'report.json',review(*values));save(directory/'state-search.json',explore(config(args.case)))
    print(directory)


if __name__=='__main__':main()
