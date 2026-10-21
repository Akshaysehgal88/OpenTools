"""Owned scalar restore bundles; consumer expectations are separate from selection."""
import argparse
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from restore_core import digest,require

CASES=("cache-payload-only","cache-metadata-only","cache-paired","cache-dirty-lost","cache-valid-before-init","cache-init-before-valid","cache-cold-reinitialize","context-metadata-only","context-paired")
STATE_IDS=("payload","identity","valid","auxiliary","initialized")
RAW_FIELDS=STATE_IDS+("response_valid","read_hit","read_error","read_data","read_count")


def config(case):
    require(case in CASES,"Unknown example");index=CASES.index(case)
    return {"context":index>=7,"keep_mask":(1,30,31,23,15,11,0,30,31)[index],"staged":index==5,"cold":index==6,"early":index==4}


def role_refs(context):
    return ("context-payload" if context else "cache-line-payload","context-owner" if context else "cache-tag","consumer-eligibility","context-flag" if context else "dirty-bit","initialization-ready")


def inventory_for(case):
    cfg=config(case);context=cfg['context']
    inventory={"format":"opentools.restore.inventory.v1","scope":{"project":"restore-example","configuration":case,"mode":"cold-rebuild" if cfg['cold'] else "warm-resume","transition_ref":"loss-restore-1"},
        "basis_ref":"owned-scalar-restore-v1","inputs_complete":True,"selection_basis_ref":"owned-logical-loss-parameters-v1","states":[]}
    for bit,(state_id,width,role) in enumerate(zip(STATE_IDS,(8,4,1,1,1),role_refs(context))):
        inventory['states'].append({'id':state_id,'width':width,'role_ref':role,'owner_ref':'context-store' if context else 'cache-array',
            'power_domain_ref':'context-domain' if context else 'line-domain','reset_domain_ref':'context-reset' if context else 'line-reset',
            'selection':'retained' if cfg['keep_mask'] & (1<<bit) else 'lost','evidence_ref':'restore_path.sv:KEEP_MASK:'+state_id})
    return inventory


def journal_for(inventory,samples):
    return {'format':'opentools.restore.journal.v1','scope':copy.deepcopy(inventory['scope']),'basis_ref':inventory['basis_ref'],'inputs_complete':True,
        'inventory_sha256':digest(inventory),'before_seq':2,'window_ref':'root-ticks-0-through-11','window_closed':True,'transition_isolated':True,'samples':samples}


def policy_for(inventory,journal,case):
    # Consumer contract, independent of the observed KEEP_MASK/selection census.
    cfg=config(case);context=case.startswith('context');cold=case=='cache-cold-reinitialize'
    expected_cold=dict(zip(STATE_IDS,(60,2,1,0,1)))
    members=[]
    for state_id,role in zip(STATE_IDS,role_refs(context)):
        member={'state_ref':state_id,'role_ref':role,'expected':'constant' if cold else 'preserve_before','evidence_ref':'consumer:restore-bundle:'+role}
        if cold:member['value']=expected_cold[state_id]
        members.append(member)
    bundle={'id':'restored-structure','consumer_ref':'context-resume-port' if context else 'cache-read-port','eligible_ref':'valid','require_ready':True,
        'evidence_ref':'consumer:explicit-cold-rebuild' if cold else 'consumer:resume-saved-bundle','members':members,
        'prerequisites':[{'state_ref':'initialized','equals':1,'evidence_ref':'consumer:initialized-before-valid-exposure'}],
        'read':{'required':True,'expected_hit':True,'expected_error':False,'data_state_ref':'payload','evidence_ref':'consumer:post-wake-data-contract',
            'prerequisites':[{'control':key,'equals':True,'evidence_ref':'consumer:read-availability:'+key} for key in ('power_available','consumer_enabled')]}}
    return {'format':'opentools.restore.policy.v1','scope':copy.deepcopy(inventory['scope']),'basis_ref':inventory['basis_ref'],'inputs_complete':True,
        'inventory_sha256':digest(inventory),'journal_sha256':digest(journal),'window_ref':journal['window_ref'],'bundles':[bundle]}


def reference(case):
    """Separate state-image ledger: loss selects saved fields, then explicit rebuilds."""
    cfg=config(case);image=dict.fromkeys(STATE_IDS,0)
    read_state=dict.fromkeys(RAW_FIELDS[5:],0);rows=[]
    for step in range(12):
        old=dict(image);read_state['response_valid']=0
        seed=step==1;loss=step==3;cold=cfg['cold'] and step==6
        init=(cfg['staged'] and step==6) or (cfg['early'] and step==7)
        publish=(cfg['staged'] or cfg['cold']) and step==7
        request=step==(5 if cfg['early'] else 8);identity=2 if cfg['cold'] else 9 if cfg['context'] else 5
        if seed:image=dict(zip(STATE_IDS,(109 if cfg['context'] else 165,9 if cfg['context'] else 5,1,0 if cfg['context'] or cfg['cold'] else 1,1)))
        if loss:image={state_id:image[state_id] if cfg['keep_mask'] & (1<<bit) else 0 for bit,state_id in enumerate(STATE_IDS)}
        if cold:image=dict(zip(STATE_IDS,(60,2,0,0,1)))
        if init:image['initialized']=1
        if publish:image['valid']=1
        if request:
            hit=old['valid']==1 and old['identity']==identity
            read_state.update(response_valid=1,read_hit=int(hit),read_error=int(hit and old['initialized']==0),read_data=old['payload'] if hit else 0,read_count=read_state['read_count']+1)
        rows.append({'step':step,'state':dict(image,**read_state),'power':int(not loss),'enabled':int(step>=4),'ready':int(step>=7),'loss':int(loss),
            'request':int(request),'requested_identity':identity,'initialize':int(init),'reinitialize':int(cold),'publish':int(publish),'seed':int(seed)})
    return rows


def normalize(row,evidence_ref):
    state=row['state'];reads=[]
    if row['request'] or state['response_valid']:
        reads.append({'read_ref':'post-wake-read-1','bundle_ref':'restored-structure','requested':bool(row['request']),'response_valid':bool(state['response_valid']),
            'hit':bool(state['read_hit']),'error':bool(state['read_error']),'data':state['read_data'],'evidence_ref':evidence_ref})
    return {'seq':row['step'],'time_tick':row.get('time_tick',row['step']),'controls':{'transition_active':bool(row['loss']),'power_available':bool(row['power']),
        'consumer_enabled':bool(row['enabled']),'restore_ready':bool(row['ready'])},'values':{key:state[key] for key in STATE_IDS},'reads':reads,
        'native_read_count':state['read_count'],'requested_identity':row['requested_identity'],'evidence_ref':evidence_ref}


def example(case='cache-payload-only'):
    inventory=inventory_for(case);journal=journal_for(inventory,[normalize(row,'owned-reference:step-'+str(row['step'])) for row in reference(case)])
    return inventory,journal,policy_for(inventory,journal,case)


def save(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--case',choices=CASES,default='cache-payload-only');args=parser.parse_args()
    output=Path(args.directory);output.mkdir(parents=True,exist_ok=False)
    for name,value in zip(('inventory','journal','policy'),example(args.case)):save(output/(name+'.json'),value)


if __name__=='__main__':main()
