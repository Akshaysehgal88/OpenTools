#!/usr/bin/env python3
"""Create reviewed reference records; native records come from run_native.py."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

MODULE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(MODULE))
from handoff_core import digest,review
from reference_model import ALPHA,BETA,CODE,PAGE,CASES,config,expected,fixture_image

def save(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def revision():
    sources={name:hashlib.sha256((MODULE/'examples'/name).read_bytes()).hexdigest() for name in ('receiver.S','reference_model.py','run_native.py')}
    return 'sha256:'+digest(sources)

def events_for(case,images,accesses,value):
    cfg=config(case);events=[]
    def emit(kind,**fields):events.append(dict(seq=len(events),kind=kind,evidence_ref='owned-stage-events:'+str(len(events)),**fields))
    state={'clock-ready':True,'reset-asserted':False,'stack-alpha-ready':cfg['alpha_ready'],'stack-beta-ready':cfg['beta_ready']}
    for key,ready in state.items():emit('fact',id=key,value=ready)
    image=images[cfg['loaded_image']];emit('image_load',image_sha256=image['sha256'])
    emit('handoff',successor_ref=cfg['successor_ref'],image_sha256=image['sha256'],entry=cfg['entry'],initial_sp=cfg['initial_sp'],state=state.copy())
    for access in accesses:
        emit('access',actor_ref=cfg['successor_ref'],**{k:access[k] for k in ('purpose','operation','address','size','successful')})
    emit('result',actor_ref=cfg['successor_ref'],value=value)
    if cfg['late_ready']:emit('fact',id='stack-alpha-ready',value=True)
    return events

def records(case,images=None,raw=None):
    cfg=config(case);images=images or {stage:fixture_image(stage) for stage in ('loader','firmware')}
    scope={'project':'owned-execution-handoff','configuration':case,'handoff_ref':cfg['mode'],'mode':cfg['mode']}
    common={'scope':scope,'basis_ref':'owned-x86-page-readiness.v1','inputs_complete':True}
    inventory=dict(common,format='opentools.stage.inventory.v1',source_kind='instruction-emulation' if raw else 'reference-fixture',
        method_ref='Unicorn-2.1.4-x86_64+owned-page-readiness.v1' if raw else 'independent-push-pop-store-reference.v1',
        source_revision_ref=revision(),image=images[cfg['loaded_image']])
    oracle=expected(case)
    events=raw['journal_events'] if raw else events_for(case,images,oracle['accesses'],oracle['value'])
    journal=dict(common,format='opentools.stage.journal.v1',inventory_sha256=digest(inventory),events_complete=True,events=events)
    base=BETA if cfg['required_image']=='firmware' else ALPHA
    policy=dict(common,format='opentools.stage.policy.v1',inventory_sha256=digest(inventory),journal_sha256=digest(journal),
        requirements_ref='owned-successor-'+cfg['required_image']+'.v1',source_revision_ref=revision(),successor_ref=cfg['successor_ref'],
        image_sha256=images[cfg['required_image']]['sha256'],entry=CODE,initial_sp=base+PAGE,stack_region={'start':base,'size':PAGE},stack_alignment=16,
        requirements={'clock-ready':True,'reset-asserted':False,('stack-beta-ready' if base==BETA else 'stack-alpha-ready'):True},
        expected_result=165 if cfg['required_image']=='firmware' else 90)
    return inventory,journal,policy

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--case',choices=CASES,default='rom-early');args=parser.parse_args()
    folder=Path(args.directory);folder.mkdir(parents=True,exist_ok=False);values=records(args.case)
    for key,value in zip(('inventory','journal','policy'),values):save(folder/(key+'.json'),value)
    save(folder/'report.json',review(*values));print(folder)

if __name__=='__main__':main()
