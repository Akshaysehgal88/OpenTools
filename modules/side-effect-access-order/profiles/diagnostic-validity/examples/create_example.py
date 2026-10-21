#!/usr/bin/env python3
"""Create or normalize one scoped diagnostic-evidence lifecycle."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

PROFILE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROFILE))
from diagnostic_core import digest,review
from reference_model import CASES,commands,config,trace

def save(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def revision():
    sources={name:hashlib.sha256((PROFILE/'examples'/name).read_bytes()).hexdigest() for name in ('diagnostic_path.sv','reference_model.py','create_example.py')}
    return 'sha256:'+digest(sources),sources
def record_value(row):return {'value':row['saved_value'],'valid':bool(row['saved_valid']),'epoch':row['saved_epoch']}

def normalize(case,rows,native=False):
    cfg=config(case);rev,sources=revision();engine=case.startswith('engine-')
    scope={'project':'owned-recovery','configuration':case,'recovery_ref':'engine-soft-recovery' if engine else 'peripheral-local-recovery','mode':'functional'}
    common={'scope':scope,'basis_ref':'owned-sticky-cause-lifecycle.v1','inputs_complete':True}
    spec=dict(common,format='opentools.diagnostic.spec.v1',source_revision_ref=rev,source_sha256=sources,
        status={'id':'engine-fatal-status' if engine else 'peripheral-status','width':8,'latch_kind':'sticky-cause',
            'onread':'clear' if cfg['read_clears'] else 'none','reset_effect':'clear' if cfg['status_reset_clears'] else 'retain','evidence_ref':'diagnostic_path.sv:status-owner'},
        record={'id':'firmware-capture','reset_effect':'clear' if cfg['saved_reset_clears'] else 'retain','evidence_ref':'diagnostic_path.sv:saved-response'})
    events=[];last_read=None
    for row in rows[1:]:
        command=row['command'];seq=row['seq'];source=row.get('evidence_ref','owned-reference-row:'+str(seq));event={'seq':seq,'evidence_ref':source}
        if command in (2,8,7):
            event.update(id='read-'+str(seq),kind='read',source='record' if command==7 else 'status',
                actor_ref='monitor' if command==8 else 'recovery-fw',data=row['rd_data'],epoch=row['rd_epoch'],
                accepted=bool(row['accepted']),error=bool(row['access_error']),available=bool(row['path_available']),hardware_quiet=True)
            if command==7:event['record_valid']=bool(row['saved_valid'])
            last_read=event['id'] if row['rd_valid'] else None
        elif command==3:event.update(id='save-'+str(seq),kind='save',actor_ref='recovery-fw',accepted=bool(row['save_done']),source_read_ref=last_read,record=record_value(row))
        elif command==4:
            event.update(id='recovery-'+str(seq),kind='recovery',observed=bool(row['recovery_seen']),epoch_after=row['epoch']);last_read=None
        elif command in (5,6):event.update(id='availability-'+str(seq),kind='availability',value=bool(row['path_available']))
        elif command==9:event.update(id='external-'+str(seq),kind='record_external',record=record_value(row))
        else:continue
        events.append(event)
    initial=rows[0]
    journal=dict(common,format='opentools.diagnostic.journal.v1',spec_sha256=digest(spec),
        source_kind='owned-rtl-simulation' if native else 'owned-reference-fixture',
        method_ref='Verilator-5.020/owned-diagnostic-path' if native else 'independent-cause-set-and-read-receipts',
        coverage_scope_ref='all-owned-access-erasure-and-capture-events',history_complete=True,source_latching_complete=True,
        initial_status=initial['status'],initial_epoch=initial['epoch'],initial_available=bool(initial['path_available']),initial_record=record_value(initial),events=events)
    claim='undetermined' if case=='post-reset-undetermined' else 'absent' if case in ('post-reset-zero','monitor-consumes','clock-unavailable','no-fault-control','engine-local-clear','engine-fault-free') else 'present'
    selected_seq=max(i for i,command in enumerate(commands(case)) if command in (2,7))
    policy=dict(common,format='opentools.diagnostic.policy.v1',spec_sha256=digest(spec),journal_sha256=digest(journal),source_revision_ref=rev,
        requirements_ref='owned-pre-recovery-diagnostic-question.v1',fault_mask=4 if engine else 1,target_epoch=0,required_through_seq=2,
        consumer_ref='recovery-fw',allowed_capture_actors=['recovery-fw'],selected_read_ref='read-'+str(selected_seq),claim=claim)
    return spec,journal,policy

def example(case):return normalize(case,trace(case))
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--case',choices=CASES,default='post-reset-zero');args=parser.parse_args()
    folder=Path(args.directory);folder.mkdir(parents=True,exist_ok=False);values=example(args.case)
    for key,value in zip(('spec','journal','policy'),values):save(folder/(key+'.json'),value)
    save(folder/'report.json',review(*values));print(folder)

if __name__=='__main__':main()
