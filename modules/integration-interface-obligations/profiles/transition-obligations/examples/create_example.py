#!/usr/bin/env python3
"""Create typed obligation records or normalize actual owned transfer events."""
import argparse
import json
from pathlib import Path
import sys

PROFILE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROFILE))
from transition_core import digest,exit_code,require,review
from reference_model import CASES,schedule,trace


def save(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def names(case):return ['worker-0','worker-1','slot-producer','slot-data','ring-tracker'] if case.startswith('ring') else ['sharer-0','sharer-1','requester','memory-data','directory']


def definitions(case):
    agents=names(case);ring=case.startswith('ring');release_class='worker-complete' if ring else 'invalidate-ack'
    participants=[{'id':agent,'role_ref':['old-reader-claim','old-reader-claim','new-exclusive-user','data-return-source','transfer-controller'][i],
        'evidence_ref':'owned-role:'+str(i)} for i,agent in enumerate(agents)]
    obligations=[{'id':'release-'+str(i),'kind':'release','source_ref':agents[i],'message_class_ref':release_class,
        'evidence_ref':'application:distinct-old-holder-'+str(i)} for i in (0,1)]
    if not ring:obligations.append({'id':'returned-data','kind':'data','source_ref':agents[3],'message_class_ref':'returned-data','evidence_ref':'application:data-before-exclusive-use'})
    return participants,obligations


def model_for(case):
    agents=names(case);participants,obligations=definitions(case);ring=case.startswith('ring')
    return {'format':'opentools.transition.model.v1',
        'scope':{'project':'owned-transfer','configuration':case,'mode':'single-resource-exclusive-handoff',
            'protocol_ref':'owned-two-worker-reclaim.v1' if ring else 'owned-directory-transfer.v1','transaction_ref':'transaction-7','epoch_ref':'epoch-1'},
        'basis_ref':'owned-transfer-source-v1','inputs_complete':True,'semantics':'accepted-exclusive-handoff',
        'resource_ref':'resource-0','grantor_ref':agents[4],'requestor_ref':agents[2],
        'request_class_ref':'reclaim-request' if ring else 'exclusive-request',
        'grant_class_ref':'reclaim-complete' if ring else 'exclusive-grant','completion_class_ref':'token-consumed',
        'protocol_contract_ref':'two-holder-reclaim-contract-v1' if ring else 'directory-ack-and-data-contract-v1',
        'transaction_id':7,'epoch':1,'participants':participants,'initial_holders':agents[:2],'obligations':obligations}


def normalize(model,row,evidence):
    agents=[p['id'] for p in model['participants']];ring=model['scope']['protocol_ref']=='owned-two-worker-reclaim.v1'
    classes={0:'none',1:model['request_class_ref'],2:'returned-data',3:'worker-complete' if ring else 'invalidate-ack',
             4:model['grant_class_ref'],5:'new-user-read',6:'new-user-write',7:'old-holder-read',8:model['completion_class_ref']}
    kinds={0:'initial' if row['seq']==0 else 'idle',1:'request',2:'data',3:'release',4:'grant',5:'new_read',6:'new_write',7:'old_read',8:'finish'}
    op=row['op'];accepted=row['grant_accepted'] if op==4 else row['read_valid'] if op in (5,7) else row['write_committed'] if op==6 else row['message_accepted']
    return {'event_ref':row['event_ref'],'seq':row['seq'],'time_tick':row.get('time_tick',row['seq']),'kind':kinds[op],
        'source_ref':agents[row['source']],'message_class_ref':classes[op],'resource_ref':'resource-0','message_id':row['message_id'],
        'message_epoch':row['message_epoch'],'accepted':bool(accepted),'offered':bool(row['offered']),
        'holders':{agents[i]:bool(row['old_permissions']&(1<<i)) for i in (0,1)},
        'reported_pending':{agents[i]:bool(row['pending_mask']&(1<<i)) for i in (0,1)},'reported_pending_count':row['pending_count'],
        'requestor_permission':bool(row['writer_permission']),'data_valid':bool(row['data_valid']),'active':bool(row['active']),
        'read_valid':bool(row['read_valid']),'write_committed':bool(row['write_committed']),
        'data_value':row['transfer_data'],'read_value':row['read_data'],
        'state_label':'exclusive-stable' if row['stable_label'] else 'busy-transient' if row['active'] else 'shared-initial',
        'evidence_ref':evidence}


def journal_for(model,events,initial):
    return {'format':'opentools.transition.journal.v1','scope':model['scope'],'basis_ref':model['basis_ref'],'inputs_complete':True,
        'model_sha256':digest(model),'window_ref':'request-through-token-consumed','epoch_isolated':True,'window_closed':True,
        'events_complete':True,'initial_holders':initial,'events':events}


def policy_for(model,journal,case):
    agents=names(case);participants,obligations=definitions(case);ring=case.startswith('ring')
    return {'format':'opentools.transition.policy.v1','scope':model['scope'],'basis_ref':model['basis_ref'],'inputs_complete':True,
        'model_sha256':digest(model),'journal_sha256':digest(journal),'window_ref':journal['window_ref'],
        'resource_ref':'resource-0','grantor_ref':agents[4],'requestor_ref':agents[2],
        'request_class_ref':'reclaim-request' if ring else 'exclusive-request','grant_class_ref':'reclaim-complete' if ring else 'exclusive-grant',
        'completion_class_ref':'token-consumed','protocol_contract_ref':'two-holder-reclaim-contract-v1' if ring else 'directory-ack-and-data-contract-v1',
        'transaction_id':7,'epoch':1,'check_returned_data':not ring,'expected_data':17,
        'required_participants':participants,'required_initial_holders':agents[:2],'required_obligations':obligations,
        'required_events':[{'event_ref':ref,'kind':kind,'evidence_ref':'application:'+ref} for ref,kind in
            (('request','request'),('grant','grant'),('new-read','new_read'),('new-write','new_write'),('finish','finish'))],
        'start_seq':0,'end_seq':len(schedule(case))-1}


def example(case):
    model=model_for(case);events=[normalize(model,row,'fixture:set-ledger:'+str(row['seq'])) for row in trace(case)]
    journal=journal_for(model,events,{agent:True for agent in names(case)[:2]});return model,journal,policy_for(model,journal,case)


def from_native(output):
    observation=json.loads((output/'observation.json').read_text(encoding='utf-8'));summary=[]
    for case in CASES:
        folder=output/case;raw=json.loads((folder/'raw.json').read_text(encoding='utf-8'));model=model_for(case)
        model['provenance']={'source_sha256':observation['source_sha256'],
            'role':'Owned identity-tagged transfer plus explicit two-worker reclaim role mapping; not a production directory/ring exporter.'}
        events=[normalize(model,row,row['evidence_ref']) for row in raw]
        journal=journal_for(model,events,{names(case)[i]:bool(raw[0]['old_permissions']&(1<<i)) for i in (0,1)})
        policy=policy_for(model,journal,case);report=review(model,journal,policy)
        require(exit_code(report)==(1 if case in ('directory-premature-grant','directory-data-late','directory-duplicate-count','ring-premature-completion') else 0),'Unexpected temporal disposition: '+case)
        require(not report['gaps'],'Unexpected native profile gaps: '+case)
        for name,value in (('model',model),('journal',journal),('policy',policy),('report',report)):save(folder/(name+'.json'),value)
        summary.append({'case':case,'status':report['status'],'findings':report['findings'],'gaps':report['gaps'],
                        'grants':report['grants'],'duplicate_receipts':report['duplicate_receipts'],'ignored_messages':report['ignored_messages']})
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--case',choices=CASES,default='directory-premature-grant');args=parser.parse_args()
    output=Path(args.directory);output.mkdir(parents=True,exist_ok=False);values=example(args.case)
    for name,value in zip(('model','journal','policy'),values):save(output/(name+'.json'),value)
    save(output/'report.json',review(*values));print(output)


if __name__=='__main__':main()
