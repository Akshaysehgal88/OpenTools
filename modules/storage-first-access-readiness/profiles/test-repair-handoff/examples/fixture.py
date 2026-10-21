"""Independent owned memory/repair contracts and native stimulus plans."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from ecc39 import PROFILE,encode
FAMILIES={'word-bank':{'words':4,'bad':1,'reset_asserted':1,'base':0,'pattern':0x10203040},'row-bank':{'words':8,'bad':2,'reset_asserted':0,'base':0x8000,'pattern':0x5a6b7c8d}}
CASES=('good','mapping-mismatch','premature-release','stale-ecc','byte-lane-reversal','repair-load-late','test-owner-leak','no-repair','ecc-disabled','invalid-repair','test-target-mismatch','early-release-denied')
FLAGS={'mapping-mismatch':1,'premature-release':2,'stale-ecc':4,'byte-lane-reversal':8,'repair-load-late':16,'test-owner-leak':32,'ecc-disabled':2,'invalid-repair':2}
INPUTS={'clk':1,'reset':1,'valid':1,'cfg':8,'operation':4,'word_address':'aw','physical_address':'paw','repair_input':12,'write_data':32,'byte_enable':4,'raw_input':39}
OUTPUTS={'accepted':1,'address_valid':1,'committed':1,'error':1,'internal_read':1,'correctable':1,'uncorrectable':1,'test_owner':1,'test_done':1,'repair_loaded':1,'repair_active':1,'ecc_enabled':1,'released':1,'initialized':'words','decoded_bad':4,'decoded_spare':4,'canonical_bad':4,'canonical_spare':4,'repair_epoch':16,'loaded_payload':12,'actual_physical':'paw','before_codeword':39,'after_codeword':39,'read_data':32,'old_data':32,'test_writes':'physical','test_reads':'physical'}
STATE=('test_owner','test_done','repair_loaded','repair_active','ecc_enabled','initialized','released','repair_epoch','loaded_payload','decoded_bad','decoded_spare','canonical_bad','canonical_spare','test_writes','test_reads')
FIELDS=tuple('before_'+k for k in STATE)+tuple(k for k in INPUTS if k not in ('clk','reset','valid','cfg'))+tuple(OUTPUTS)+('checks','failures')
def role_map(family):return {k:k if family=='word-bank' else 'port_'+('reset_n' if k=='reset' else k) for k in (*INPUTS,*OUTPUTS)}
def width(c,value):return {'aw':(c['words']-1).bit_length(),'paw':c['words'].bit_length(),'words':c['words'],'physical':c['words']+1}.get(value,value)
def top(family,c):
    r=role_map(family);ports=[]
    for direction,items in [('input',INPUTS),('output',OUTPUTS)]:
        for role,bits in items.items():
            n=width(c,bits);ports.append(direction+' logic '+(f'[{n-1}:0] ' if n>1 else '')+r[role])
    return 'module top('+',\n '.join(ports)+');\nmemory_bank #(.WORDS('+str(c['words'])+'),.RESET_ASSERTED('+str(c['reset_asserted'])+')) bank ('+', '.join('.'+k+'('+v+')' for k,v in r.items())+');\nendmodule\n'
def payload(c,required=True):return (1<<11)|(c['bad']<<6)|(c['words']<<1) if required else 0
def desired_data(c):return [(c['pattern']^(word*0x01020304))&0xffffffff for word in range(c['words'])]
def plan(family,c,case):
    required=case!='no-repair';expected=payload(c,required);actual=expected
    if case=='invalid-repair':actual=(expected&~30)|((c['words']-1)<<1)
    values=desired_data(c);wanted=list(values);steps=[];target=lambda w:c['words'] if required and w==c['bad'] else w
    def add(id,op,word=0,physical=0,data=0,mask=15,raw=0,accept=True,release=-1,after=None,expected_data=0):
        steps.append({'id':id,'operation':op,'word':word,'physical':physical,'write_data':data,'byte_enable':mask,'raw_input':raw,'repair_input':actual,'expect_accept':accept,'expect_release':release,'expected_after':after,'expected_data':expected_data})
    for op,label in [(0,'test-write'),(1,'test-read')]:
        for w in range(c['words']):
            physical=w if case=='test-target-mismatch' else target(w)
            add(label+'-'+str(w),op,w,physical,raw=encode(values[w])^3)
    add('test-complete',2)
    if case!='repair-load-late':add('repair-load',3)
    add('ecc-enable',4)
    if case=='early-release-denied':add('release-probe',6,release=0)
    if case!='premature-release':
        for w in range(c['words']):add('scrub-'+str(w),5,w,data=values[w],after=encode(values[w]))
    if case=='repair-load-late':add('repair-load',3)
    if case=='ecc-disabled':add('ecc-disable',10)
    add('functional-release',6,release=1)
    for w in range(c['words']):add('first-read-'+str(w),7,w,expected_data=wanted[w])
    w=c['bad'];wanted[w]=(wanted[w]&0xffffff00)|0xa5;add('partial-write',8,w,data=0xa5,mask=1,after=encode(wanted[w]));add('read-partial',7,w,expected_data=wanted[w])
    w=c['words']-1;wanted[w]=0xa5c3098e;add('full-write',8,w,data=wanted[w],after=encode(wanted[w]));add('read-full',7,w,expected_data=wanted[w])
    add('zero-write',8,0,data=0xffffffff,mask=0);add('read-zero',7,0,expected_data=wanted[0])
    add('test-after-handoff',0,0,physical=target(0),raw=encode(0xcafebeef),accept=False);add('read-after-test',7,0,expected_data=wanted[0])
    return {'case':case,'case_index':CASES.index(case),'cfg':FLAGS.get(case,0),'repair_required':required,'expected_payload':expected,'actual_payload':actual,'steps':steps}
def header(family,c):
    lines=['#include <cstdint>','#define WORDS '+str(c['words']),'#define PHYSICAL '+str(c['words']+1),'#define RESET_ASSERTED '+str(c['reset_asserted'])]
    lines+=['#define P_'+k.upper()+' '+v for k,v in role_map(family).items()]
    lines+=['struct Step {const char* id;unsigned operation,word,physical,write_data,byte_enable;uint64_t raw_input;unsigned repair_input;bool expect_accept;int expect_release;uint64_t expected_after;bool check_after;unsigned expected_data;};','struct Plan {const char* name;unsigned cfg;bool repair_required;unsigned expected_payload;const Step* steps;unsigned count;};']
    for index,case in enumerate(CASES):
        p=plan(family,c,case);lines+=['static const Step STEPS_'+str(index)+'[]={']
        for s in p['steps']:
            values=[json.dumps(s['id']),*map(str,(s['operation'],s['word'],s['physical'],s['write_data'],s['byte_enable'])),str(s['raw_input'])+'ull',str(s['repair_input']),str(s['expect_accept']).lower(),str(s['expect_release']),str(s['expected_after'] or 0)+'ull',str(s['expected_after'] is not None).lower(),str(s['expected_data'])];lines.append('{'+','.join(values)+'},')
        lines+=['};']
    lines+=['static const Plan PLANS[]={']
    for index,case in enumerate(CASES):
        p=plan(family,c,case);lines.append('{'+','.join((json.dumps(case),str(p['cfg']),str(p['repair_required']).lower(),str(p['expected_payload']),'STEPS_'+str(index),str(len(p['steps']))))+'},')
    return '\n'.join(lines+['};',''])
def context(family,c,case):
    base='owned/'+family
    return {'format':'opentools.repair-context.v1','run_ref':family+'-'+case,'scope_ref':base,'design_ref':base+'/memory-model','configuration_ref':base+'/profile-r1','memory_ref':base+'/ram','init_epoch_ref':base+'/single-test-epoch','transition_ref':base+'/test-to-functional','unit_instance':'bank','unit_type':'memory_bank','memory_variable':'memory','role_map':role_map(family),'reset_asserted':c['reset_asserted'],'ecc_profile_ref':PROFILE,**{k:base+'/'+k for k in ('mapping_basis_ref','macro_view_ref','wrapper_basis_ref','repair_basis_ref','test_basis_ref','initializer_basis_ref','instrumentation_basis_ref','owner_ref')}}
def policy(family,c,case):
    p=plan(family,c,case);base='owned/'+family;target=lambda w:c['words'] if p['repair_required'] and w==c['bad'] else w
    return {'geometry':{'logical_words':c['words'],'physical_words':c['words']+1,'data_bits':32,'codeword_bits':39,'byte_lanes':4,'command_ports':1,'byte_order':'little','base_address':c['base']},'repair':{'payload_bits':12,'valid_bit':11,'bad_lsb':6,'bad_bits':4,'spare_lsb':1,'spare_bits':4,'reserved_mask':0x421,'required':p['repair_required'],'expected_payload':p['expected_payload']},'required_init_words':list(range(c['words'])),'required_test_physical_words':sorted(target(w) for w in range(c['words'])),'release_event_ref':'functional-release','required_accesses':[{'event_ref':s['id'],'operation':s['operation'],'word':s['word'],'expected_data':s['expected_data']} for s in p['steps'] if s['operation']==7],'source_ref':base+'/independent-handoff-contract','owner_ref':base+'/fixture-receiving-owner'}
