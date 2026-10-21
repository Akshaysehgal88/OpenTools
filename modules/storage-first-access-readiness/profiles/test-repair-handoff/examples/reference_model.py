"""Independent physical-array replay for the owned native fixture, including fault controls."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from repair_common import OUTPUTS,STATE,decode,encode,require

def replay(plan, words):
    memory=[3]*(words+1);state=dict.fromkeys(STATE,0);state['test_owner']=1;rows=[];flags=plan['cfg']
    for step in plan['steps']:
        before=dict(state);out={k:0 for k in OUTPUTS if k not in STATE}
        op=step['operation'];word=step['word'];mask=step['byte_enable'];data=step['write_data']
        def target(initializer=False):
            bad=state['canonical_bad'] if initializer else state['decoded_bad']
            spare=state['canonical_spare'] if initializer else state['decoded_spare']
            remap=bool(state['loaded_payload']&2048) if initializer else state['repair_active']
            return spare if state['repair_loaded'] and remap and word==bad else word
        def address(index):
            out.update(address_valid=1,actual_physical=index,before_codeword=memory[index],after_codeword=memory[index])
            return index
        def write(index,code):
            memory[index]=code;out.update(after_codeword=code,committed=1)
        owner=bool(state['test_owner'])
        if op in (0,1) and (owner or flags&32) and step['physical']<len(memory):
            out['accepted']=1;p=address(step['physical'])
            if op==0:write(p,step['raw_input']);state['test_writes']|=1<<p
            else:out['internal_read']=1;state['test_reads']|=1<<p
        elif owner and op==2:
            out['accepted']=1;state['test_done']=int((state['test_writes']&state['test_reads']).bit_count()==words)
        elif owner and op==3:
            value=step['repair_input'];bad=(value>>(5 if flags&1 else 6))&15;spare=(value>>1)&15
            okay=not(value&0x421) and (not(value&2048) or (bad<words<=spare<len(memory)))
            out['accepted']=1;state.update(decoded_bad=bad,decoded_spare=spare,canonical_bad=(value>>6)&15,
                canonical_spare=spare,loaded_payload=value,repair_epoch=state['repair_epoch']+1,
                repair_loaded=int(okay),repair_active=int(okay and bool(value&2048)))
        elif owner and op in (4,10):out['accepted']=1;state['ecc_enabled']=int(op==4)
        elif owner and op==5 and state['ecc_enabled'] and (state['repair_loaded'] or flags&16):
            out['accepted']=1;p=address(target(True));write(p,encode(data)^(3 if flags&4 else 0));state['initialized']|=1<<word
        elif owner and op==6:
            out['accepted']=1
            if (state['test_done'] and state['repair_loaded'] and state['ecc_enabled'] and state['initialized']==(1<<words)-1) or flags&2:
                state.update(test_owner=0,released=1)
        elif not owner and state['released'] and op in (7,8):
            out['accepted']=1;p=address(target());decoded=decode(memory[p]);ecc=bool(state['ecc_enabled'])
            old=decoded['data'] if ecc else memory[p]&0xffffffff
            if op==7 or mask not in (0,15):
                out.update(internal_read=1,correctable=int(ecc and decoded['correctable']),
                           uncorrectable=int(ecc and decoded['uncorrectable']),
                           error=int(ecc and decoded['uncorrectable']),old_data=old)
            if op==7:out['read_data']=old
            elif mask==15:write(p,encode(data));state['initialized']|=1<<word
            elif mask and not (ecc and decoded['uncorrectable']):
                lanes=bytearray(old.to_bytes(4,'little'));incoming=data.to_bytes(4,'little')
                for lane in range(4):
                    if mask&(1<<lane):lanes[3-lane if flags&8 else lane]=incoming[lane]
                write(p,encode(int.from_bytes(lanes,'little')))
        rows.append({**{'before_'+k:v for k,v in before.items()},
                     **{'operation':op,'word_address':word,'physical_address':step['physical'],
                        'repair_input':step['repair_input'],'write_data':data,'byte_enable':mask,'raw_input':step['raw_input']},
                     **out,**state})
    return rows

def compare(evidence, plan):
    expected=replay(plan,evidence['geometry']['logical_words'])
    require(len(expected)==len(evidence['events']),'Reference length mismatch')
    checked=0
    for actual,wanted in zip(evidence['events'],expected):
        for field,value in wanted.items():
            require(actual[field]==value,'Independent reference mismatch: '+actual['event_ref']+' '+field)
            checked+=1
    return {'transactions':len(expected),'observed_fields_compared':checked,
            'model':'Independent Python physical array, owner state, repair epoch and byte-vector merge; shared parent SECDED oracle vs native position-loop codec.'}
