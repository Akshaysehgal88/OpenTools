#!/usr/bin/env python3
"""Create or normalize one scalar visibility/ownership handoff."""
import argparse
import json
from pathlib import Path
import sys

MODULE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(MODULE))
from handoff_core import digest,exit_code,require,review
from cache_model import CASES,coherent,schedule,trace


def save(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def agents(case):return ('queue-producer','queue-consumer','cache-writeback') if case.startswith('shared-queue') else ('cpu-producer','device-consumer','cache-writeback')


def object_specs():
    return [{'id':name,'role_ref':role,'width_bits':32,'physical_address':address,'line_bytes':4,'evidence_ref':'cache_handoff.sv:owned-scalar-object-'+name}
        for name,role,address in (('payload','required-payload',4096),('other-buffer','distinct-buffer',4100),('control','publication-control',8192))]


def mapping_specs(case):
    producer,consumer,_=agents(case);cf=coherent(case)
    specs=(('producer-payload',producer,'payload',16384,False,'write-back','private-cache'),
           ('producer-other',producer,'other-buffer',20480,False,'write-back','private-cache'),
           ('consumer-payload',consumer,'payload',4096,cf,'uncached','payload-snoop' if cf else 'backing-only'),
           ('consumer-other',consumer,'other-buffer',4100,cf,'uncached','payload-snoop' if cf else 'backing-only'),
           ('producer-control',producer,'control',24576,True,'uncached','control-register'),
           ('consumer-control',consumer,'control',8192,True,'uncached','control-register'))
    return [{'id':name,'agent_ref':agent,'object_ref':obj,'address':address,'coherent':is_coherent,
             'cacheability':cacheability,'path_ref':path,'shareability_ref':'owned-two-agent-domain',
             'mapping_epoch_ref':'mapping-1','evidence_ref':'owned-mapping:'+name} for name,agent,obj,address,is_coherent,cacheability,path in specs]


def inventory_for(case):
    producer,consumer,maintenance=agents(case)
    return {'format':'opentools.handoff.inventory.v1','scope':{'project':'owned-cache-handoff','configuration':case,
        'mode':'producer-to-consumer','handoff_ref':'first-payload-epoch'},'basis_ref':'owned-cache-source-v1','inputs_complete':True,
        'mapping_epoch_ref':'mapping-1','producer_ref':producer,'consumer_ref':consumer,'maintenance_agent_ref':maintenance,
        'platform_contract_ref':'owned-scalar-cache-and-logical-release-order','objects':object_specs(),'mappings':mapping_specs(case)}


def normalize(inventory,row,evidence):
    producer,consumer,maintenance=(inventory[k] for k in ('producer_ref','consumer_ref','maintenance_agent_ref'))
    op,line=row['op'],row['line'];mapping=None;value=version=None;control_seen=None
    obj='payload';actor=producer;effect=True
    kind={0:'initial',1:'write',2:'clean_request',3:'clean_complete',4:'publish',5:'release_order',6:'read',7:'complete',8:'reclaim'}[op]
    if op==1:
        mapping='producer-other' if line else 'producer-payload';obj='other-buffer' if line else 'payload'
        value=row['data'];version=row['cache_epoch_b' if line else 'cache_epoch_a']
    elif op in (2,3):
        target=row['pending_line'];mapping='producer-other' if target else 'producer-payload';obj='other-buffer' if target else 'payload'
        value=row['pending_data'];version=row['pending_epoch']
        if op==3:actor=maintenance;effect=bool(row['clean_done'])
    elif op==4:mapping='producer-control';obj='control';value=row['published'];effect=bool(row['published'])
    elif op==5:version=row['order_epoch'];effect=bool(row['order_seen'])
    elif op==6:
        actor=consumer;mapping='consumer-other' if line else 'consumer-payload';obj='other-buffer' if line else 'payload'
        value=row['read_data'];version=row['read_epoch'];control_seen=bool(row['read_control']);effect=bool(row['read_valid'])
    elif op==7:actor=consumer;effect=bool(row['completed'])
    elif op==8:effect=not bool(row['owner_consumer'])
    event={'event_ref':row['event_ref'],'seq':row['seq'],'time_tick':row.get('time_tick',row['seq']),'kind':kind,
        'actor_ref':actor,'object_ref':obj,'mapping_ref':mapping,
        'address':next(m['address'] for m in inventory['mappings'] if m['id']==mapping) if mapping else None,
        'accepted':True,'effect_observed':effect,'value':value,'version':version,'control_seen':control_seen,
        'owner_after_ref':consumer if row['owner_consumer'] else producer,'evidence_ref':evidence}
    if op==3:event['request_ref']='clean-request'
    if op==6:event['control_mapping_ref']='consumer-control'
    return event


def journal_for(inventory,events,initial_owner):
    return {'format':'opentools.handoff.journal.v1','scope':inventory['scope'],'basis_ref':inventory['basis_ref'],'inputs_complete':True,
        'inventory_sha256':digest(inventory),'window_ref':'first-write-through-reuse','epoch_isolated':True,'window_closed':True,
        'events_complete':True,'initial_owner_ref':initial_owner,'events':events}


def policy_for(inventory,journal,case):
    producer,consumer,maintenance=agents(case)
    # Independent application identities/intent, not a census of observed events or values.
    return {'format':'opentools.handoff.policy.v1','scope':inventory['scope'],'basis_ref':inventory['basis_ref'],'inputs_complete':True,
        'inventory_sha256':digest(inventory),'journal_sha256':digest(journal),'window_ref':journal['window_ref'],
        'payload_ref':'payload','control_ref':'control','payload_mapping_ref':'consumer-payload','control_mapping_ref':'consumer-control',
        'producer_ref':producer,'consumer_ref':consumer,'maintenance_agent_ref':maintenance,'mapping_epoch_ref':'mapping-1',
        'ordering_contract_ref':'owned-release-marker-after-produced-version','completion_contract_ref':'consumer-read-precedes-complete-and-reclaim',
        'expected_write_ref':'payload-write','publish_ref':'publish-control','read_ref':'consumer-read','completion_ref':'consumer-complete',
        'reclaim_ref':'producer-reclaim','require_release_order':True,'expected_value':165,'expected_version':1,
        'required_objects':[{k:o[k] for k in ('id','role_ref','width_bits','evidence_ref')} for o in object_specs()],
        'required_mappings':[{k:m[k] for k in ('id','agent_ref','object_ref','mapping_epoch_ref','coherent','path_ref','evidence_ref')} for m in mapping_specs(case)],
        'start_seq':0,'end_seq':len(schedule(case))-1}


def example(case):
    inventory=inventory_for(case);events=[normalize(inventory,row,'fixture:image-ledger:'+str(row['seq'])) for row in trace(case)]
    journal=journal_for(inventory,events,inventory['producer_ref']);return inventory,journal,policy_for(inventory,journal,case)


def from_native(output):
    observation=json.loads((output/'observation.json').read_text(encoding='utf-8'));summary=[]
    for case in CASES:
        folder=output/case;raw=json.loads((folder/'raw.json').read_text(encoding='utf-8'));inventory=inventory_for(case)
        inventory['provenance']={'source_sha256':observation['source_sha256'],
            'role':'Owned scalar cache/backing/snoop model and explicit alias map; not a Linux DMA or production coherency exporter.'}
        events=[normalize(inventory,row,row['evidence_ref']) for row in raw]
        initial=inventory['consumer_ref'] if raw[0]['owner_consumer'] else inventory['producer_ref']
        journal=journal_for(inventory,events,initial);policy=policy_for(inventory,journal,case);report=review(inventory,journal,policy)
        require(exit_code(report)==(0 if case in ('dma-clean-complete','dma-coherent','shared-queue-coherent') else 1),'Unexpected handoff disposition: '+case)
        require(not report['gaps'],'Native owned handoff unexpectedly incomplete: '+case)
        for name,value in (('inventory',inventory),('journal',journal),('policy',policy),('report',report)):save(folder/(name+'.json'),value)
        summary.append({'case':case,'status':report['status'],'findings':report['findings'],'gaps':report['gaps'],'reads':report['reads']})
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--case',choices=CASES,default='dma-no-clean');args=parser.parse_args()
    directory=Path(args.directory);directory.mkdir(parents=True,exist_ok=False);values=example(args.case)
    for name,value in zip(('inventory','journal','policy'),values):save(directory/(name+'.json'),value)
    save(directory/'report.json',review(*values));print(directory)


if __name__=='__main__':main()
