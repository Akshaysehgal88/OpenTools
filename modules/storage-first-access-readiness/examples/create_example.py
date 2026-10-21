#!/usr/bin/env python3
"""Create bounded boot/DMA fixtures; compare actual native records with a word ledger."""
import argparse
import json
from pathlib import Path
import sys

MODULE = Path(__file__).resolve().parents[1];sys.path.insert(0,str(MODULE))
from ecc39 import PROFILE, decode, encode
from storage_core import digest, exit_code, require, review

CASES = ('boot-before-scrub','boot-after-scrub','boot-full-word-first','dma-before-scrub',
         'dma-after-scrub','dma-wrong-word-global-done','after-single-bit-error',
         'after-double-bit-error','valid-code-no-init')
ACTORS = ('boot-stack-master','dma-payload-master','scrub-owner','test-injector')
KINDS = ('initialize','read','write','inject')
MEM_FIELDS = ('master','op','word','write_data','byte_enable','inject_mask','accepted','internal_read',
              'correctable','uncorrectable','committed','error','before_codeword','after_codeword',
              'before_ready','after_ready','old_data','read_data')


def save(path, value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def config(case):
    require(case in CASES, 'Unknown fixture case')
    master = 1 if case in ('dma-before-scrub','dma-after-scrub','dma-wrong-word-global-done','valid-code-no-init') else 0
    return master, 2 if master else 0


def schedule(case):
    master, target = config(case);actions=[]
    def append(ref, actor, op, word, data=0, lanes=0, mask=0):
        actions.append({'event_ref':ref,'master':actor,'op':op,'word':word,'write_data':data,'byte_enable':lanes,'inject_mask':mask})
    if case in ('boot-after-scrub','dma-after-scrub','after-single-bit-error','after-double-bit-error'):
        for word in range(4): append('scrub-'+str(word),2,0,word,lanes=15)
    if case == 'boot-full-word-first': append('first-full',master,2,target,0x11223344,15)
    if case == 'dma-wrong-word-global-done': append('scrub-0',2,0,0,lanes=15)
    if case in ('after-single-bit-error','after-double-bit-error','valid-code-no-init'):
        append('fault-injection',3,3,target,mask={'after-single-bit-error':4,'after-double-bit-error':20,'valid-code-no-init':3}[case])
    actions.append({'event_ref':'release-master','master':master,'op':'release','word':target})
    append('first-partial',master,2,target,0xaabbccdd,2 if case == 'after-single-bit-error' else 1)
    append('first-read',master,1,target)
    return actions


def reference(case):
    """Independent array transaction ledger; codec uses data-column parity arithmetic."""
    memory, readiness = [3]*4, [False]*4;released=False;result=[]
    for action in schedule(case):
        a = dict(action);a['seq']=len(result)
        global_done = all(readiness) or case == 'dma-wrong-word-global-done' and action['event_ref'] != 'scrub-0'
        if a['op'] == 'release':
            released=True;a.update(global_done=int(global_done),released=1);result.append(a);continue
        word, op, lanes = a['word'], a['op'], a['byte_enable']
        before, before_ready = memory[word], readiness[word];decoded=decode(before)
        internal = op == 1 or op == 2 and lanes not in (0,15)
        commit = False;old_data=read_data=0
        if op == 0 or op == 2 and lanes == 15:
            memory[word]=encode(a['write_data']);readiness[word]=True;commit=True
        elif op == 3: memory[word] ^= a['inject_mask'];commit=True
        elif internal:
            old_data=decoded['data']
            if op == 1: read_data=old_data
            elif not decoded['uncorrectable']:
                # Byte-vector merge is intentionally separate from the reviewer's bit-mask merge.
                updated=bytearray(old_data.to_bytes(4,'little'));incoming=a['write_data'].to_bytes(4,'little')
                for lane in range(4):
                    if lanes & (1<<lane): updated[lane]=incoming[lane]
                memory[word]=encode(int.from_bytes(updated,'little'));commit=True
        a.update(accepted=1,internal_read=int(internal),correctable=int(internal and decoded['correctable']),
                 uncorrectable=int(internal and decoded['uncorrectable']),committed=int(commit),error=int(internal and decoded['uncorrectable']),
                 before_codeword=before,after_codeword=memory[word],before_ready=int(before_ready),after_ready=int(readiness[word]),
                 old_data=old_data,read_data=read_data,global_done=int(all(readiness) or case == 'dma-wrong-word-global-done' and a['event_ref'] != 'scrub-0'),released=int(released))
        result.append(a)
    return result


def inventory_for(case):
    return {'format':'opentools.storage.inventory.v1',
        'scope':{'project':'owned-storage-example','configuration':case,'mode':'cold-bringup','init_epoch_ref':'reset-1'},
        'basis_ref':'owned-wrapper-source-v1','inputs_complete':True,
        'memory_ref':'ram-wrapper','initializer_ref':ACTORS[2],'test_port_ref':ACTORS[3],
        'geometry_evidence_ref':'ram_wrapper.sv:memory-array','traits_evidence_ref':'ram_wrapper.sv:memory_access',
        'ecc_profile_ref':PROFILE,'geometry':{'base_address':4096,'size_bytes':16,'word_bytes':4,'word_count':4,
        'data_bits':32,'ecc_bits':7,'codeword_bits':39,'byte_order':'little'},
        'traits':{'partial_write_reads_old':True,'full_write_reads_old':False,'full_write_initializes':True,
                  'zero_mask_noop':True,'abort_on_uncorrectable':True,'global_done_covers_all':True}}


def normalize(row, evidence):
    common = {k:row[k] for k in ('event_ref','seq')};common.update(time_tick=row.get('time_tick',row['seq']),
        master_ref=ACTORS[row['master']],evidence_ref=evidence)
    if row['op'] == 'release':
        return dict(common,kind='release',released=bool(row['released']),global_done=bool(row['global_done']))
    flags=('accepted','internal_read','correctable','uncorrectable','committed','error','before_ready','after_ready','global_done','released')
    values={k:bool(row[k]) for k in flags}
    values.update({k:row[k] for k in ('write_data','byte_enable','inject_mask','before_codeword','after_codeword','old_data','read_data')})
    return dict(common,kind=KINDS[row['op']],address=4096+4*row['word'],**values)


def journal_for(inventory, events, initial=None):
    return {'format':'opentools.storage.journal.v1','scope':inventory['scope'],'basis_ref':inventory['basis_ref'],
        'inputs_complete':True,'inventory_sha256':digest(inventory),'window_ref':'reset-through-first-read',
        'isolated_epoch':True,'window_closed':True,'accesses_complete':True,
        'initial':initial if initial is not None else [{'address':4096+4*w,'ready':False,'codeword':3,'evidence_ref':'fixture:controlled-reset'} for w in range(4)],'events':events}


def policy_for(inventory, journal, case):
    actor, target = config(case)
    # This roster comes from the use case, not from an observed-event enumeration.
    required=[{'event_ref':'first-partial','kind':'write','address':4096+4*target,'evidence_ref':'application:subword-first-consumer'},
              {'event_ref':'first-read','kind':'read','address':4096+4*target,'evidence_ref':'application:verify-first-consumer'}]
    if case == 'boot-full-word-first': required.insert(0,{'event_ref':'first-full','kind':'write','address':4096,'evidence_ref':'application:full-word-initializer'})
    return {'format':'opentools.storage.policy.v1','scope':inventory['scope'],'basis_ref':inventory['basis_ref'],
        'inputs_complete':True,'inventory_sha256':digest(inventory),'journal_sha256':digest(journal),'window_ref':journal['window_ref'],
        'require_codec_check':True,'require_global_done':False,'allow_correctable':True,
        'masters':[{'id':ACTORS[actor],'release_event_ref':'release-master','release_addresses':[4096+4*target],
            'allow_full_write_before_release':True,'required_accesses':required,'evidence_ref':'application:selected-word-release'}]}


def example(case):
    inventory=inventory_for(case)
    journal=journal_for(inventory,[normalize(row,'fixture:ledger:'+str(row['seq'])) for row in reference(case)])
    return inventory,journal,policy_for(inventory,journal,case)


def from_native(output):
    lines=(output/'native.stdout.txt').read_text(encoding='utf-8').splitlines()
    rows={i:{} for i in range(9)};controls={i:{} for i in range(9)};initial={i:[] for i in range(9)};configs={}
    for number,line in enumerate(lines,1):
        tag=line.split(' ',1)[0]
        if tag not in ('CONFIG','INITIAL','MEM','CONTROL','RELEASE'): continue
        values=[int(v) for v in line.split()[1:]];case_index=values[0];require(case_index in rows,'Unknown native case')
        if tag == 'CONFIG':
            require(len(values)==3 and case_index not in configs,'Invalid native config');configs[case_index]=values[1:]
        elif tag == 'INITIAL':
            require(len(values)==5,'Invalid initial columns');_,word,time,codeword,ready=values
            require(word==len(initial[case_index]) and codeword==3 and ready==0,'Native reset precondition differs')
            initial[case_index].append({'address':4096+4*word,'codeword':codeword,'ready':bool(ready),'evidence_ref':'native.stdout.txt:'+str(number)})
        elif tag == 'CONTROL':
            require(len(values)==4 and values[1] not in controls[case_index],'Invalid native controls');controls[case_index][values[1]]=values[2:]
        else:
            seq,time=values[1:3];require(seq not in rows[case_index],'Duplicate native event')
            if tag == 'MEM':
                require(len(values)==21,'Invalid native memory columns');row=dict(zip(MEM_FIELDS,values[3:]))
            else:
                require(len(values)==6,'Invalid release columns');row={'master':values[3],'word':values[4],'global_done':values[5],'released':1,'op':'release'}
            row.update(seq=seq,time_tick=time,evidence_ref='native.stdout.txt:'+str(number));rows[case_index][seq]=row
    summary=[]
    for index,case in enumerate(CASES):
        require(configs.get(index)==list(config(case)) and len(initial[index])==4,'Native config/initial coverage differs')
        expected=reference(case);require(set(rows[index])==set(range(len(expected))),'Native event coverage differs')
        require(set(controls[index])=={r['seq'] for r in expected if r['op']!='release'},'Native control coverage differs')
        events=[]
        for expectation in expected:
            row=rows[index][expectation['seq']]
            if row['op']!='release': row['global_done'],row['released']=controls[index][row['seq']]
            for key,value in expectation.items():
                if key!='event_ref': require(row[key]==value,'Native word/transaction ledger mismatch: '+case+' '+key+' seq '+str(row['seq']))
            row['event_ref']=expectation['event_ref'];events.append(normalize(row,row['evidence_ref']))
        inventory=inventory_for(case)
        inventory['provenance']={'source_sha256':json.loads((output/'observation.json').read_text(encoding='utf-8'))['source_sha256'],
            'role':'Owned wrapper/source mapping; actual Verilator word/transaction records, not a foundry macro exporter.'}
        journal=journal_for(inventory,events,initial[index]);policy=policy_for(inventory,journal,case);report=review(inventory,journal,policy)
        require(exit_code(report)==(0 if index in (1,2,4,6) else 1),'Unexpected native first-access disposition: '+case)
        folder=output/case;folder.mkdir()
        for name,value in (('inventory',inventory),('journal',journal),('policy',policy),('report',report)): save(folder/(name+'.json'),value)
        summary.append({'case':case,'status':report['status'],'events':len(events),'findings':report['findings'],'gaps':report['gaps'],
                        'first_read':next(e for e in events if e['event_ref']=='first-read')['read_data']})
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--case',choices=CASES,default='boot-after-scrub');args=parser.parse_args()
    directory=Path(args.directory);directory.mkdir(parents=True,exist_ok=False)
    values=example(args.case)
    for name,value in zip(('inventory','journal','policy'),values): save(directory/(name+'.json'),value)
    save(directory/'report.json',review(*values))
    print(directory)


if __name__=='__main__':main()
