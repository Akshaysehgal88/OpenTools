"""Compare a receiving memory-handoff contract with captured native transactions."""
from repair_common import BASIS,IDENTITY,PROFILE,decode,digest,encode,require,text,uint

ABI={'payload_bits':12,'valid_bit':11,'bad_lsb':6,'bad_bits':4,
     'spare_lsb':1,'spare_bits':4,'reserved_mask':0x421}

def review(evidence, policy):
    require(evidence.get('format')=='opentools.repair-evidence.v1','Unsupported evidence')
    require(policy.get('format')=='opentools.repair-policy.v1','Unsupported receiving contract')
    result={'format':'opentools.repair-review.v1','status':'incomplete',
            'scope':{k:evidence['context'][k] for k in IDENTITY},
            'native_result':evidence['native_result'],'findings':[],'gaps':[],
            'initialization':[],'handoffs':[],'accesses':[],
            'evidence_sha256':digest(evidence),'policy_sha256':digest(policy),
            'owner_ref':policy.get('owner_ref'),
            'recheck_when':['repair payload or decoder changes','macro/wrapper geometry or byte lanes change',
                            'test population or ownership changes','initialization/ECC/release order changes',
                            'reset/configuration/mode or required consumers change'],
            'limits':'This selected test-to-functional transition is the review unit. Owned native semantics do not qualify a foundry macro, fuse format, MBIST algorithm, fault coverage, reset retention or physical initialization. Approval remains with the receiving owner.'}
    def finding(kind, event=None, **values):
        result['findings'].append(dict(kind=kind,**({'event_ref':event} if event else {}),**values))
    def gap(kind, **values):result['gaps'].append(dict(kind=kind,**values))
    def finish():
        result['status']='findings' if result['findings'] else 'incomplete' if result['gaps'] else 'aligned'
        return result
    # Native PASS/FAIL is kept even when the receiving basis is quarantined.
    if evidence['native_result']['failures']:finding('native_assertions_failed',count=evidence['native_result']['failures'])
    quarantined=False
    expected=policy.get('identity',{})
    for k in IDENTITY:
        if not expected.get(k) or expected[k]!=evidence['context'][k]:
            gap('scope_not_admitted',field=k,expected=expected.get(k),observed=evidence['context'][k]);quarantined=True
    for key,actual in [('source_sha256',evidence['source_sha256']),
                       ('plan_sha256',evidence['file_sha256']['plan.json']),
                       ('run_command_sha256',evidence['file_sha256']['run.command.json']),
                       ('binary_sha256',evidence['file_sha256']['Vtop'])]:
        if policy.get(key)!=actual:gap('artifact_not_admitted',field=key);quarantined=True
    if quarantined:return finish()
    for k in BASIS:
        if not evidence['context'].get(k):gap('missing_source_basis',field=k)
    for k in ('source_ref','owner_ref'):
        if not policy.get(k):gap('missing_receiving_basis',field=k)
        else:text(policy[k],k)
    if policy.get('inputs_complete') is not True:gap('incomplete_review_window')
    g=policy['geometry'];native=evidence['geometry'];n=native['logical_words'];physical=native['physical_words']
    for k in ('logical_words','physical_words','data_bits','codeword_bits','byte_lanes','command_ports'):
        uint(g.get(k),1<<32,'geometry '+k)
        if g[k]!=native[k]:finding('geometry_mismatch',field=k,expected=g[k],observed=native[k])
    require(g.get('byte_order')=='little','Owned profile requires little-endian byte lanes')
    uint(g.get('base_address'),(1<<64)-1,'base address')
    if any(g[k]!=native[k] for k in ('logical_words','physical_words','data_bits','codeword_bits','byte_lanes','command_ports')):return finish()
    repair=policy['repair'];require(all(repair.get(k)==v and type(repair.get(k)) is int for k,v in ABI.items()),'Unsupported repair ABI')
    require(type(repair.get('required')) is bool,'Explicit repair requirement needed')
    payload=uint(repair['expected_payload'],4095,'expected repair payload')
    active=bool(payload&2048);bad=(payload>>6)&15;spare=(payload>>1)&15
    require(payload&0x421==0 and active==repair['required'] and (not active or bad<n<=spare<physical),'Invalid independent repair contract')
    target=lambda w:spare if active and w==bad else w
    def roster(name, maximum):
        values=policy[name];require(isinstance(values,list) and values and len(values)==len(set(values)),'Invalid '+name)
        return {uint(w,maximum,name) for w in values}
    required=roster('required_init_words',n-1);test_required=roster('required_test_physical_words',physical-1)
    if not {target(w) for w in required}.issubset(test_required):finding('contract_test_population_misses_required_view')
    init_values=policy.get('required_init_data',[]);wanted_init={}
    for entry in init_values:
        w=uint(entry['word'],n-1,'initialization word');require(w not in wanted_init,'Duplicate initialization word')
        wanted_init[w]=uint(entry['data'],0xffffffff,'initialization data')
    if set(wanted_init)!=required:gap('incomplete_initialization_data_contract')
    release_ref=text(policy.get('release_event_ref'),'required release event')
    accesses=policy['required_accesses'];require(isinstance(accesses,list) and accesses,'Required consumer roster needed')
    required_accesses={}
    for a in accesses:
        ref=text(a['event_ref'],'required access');require(ref not in required_accesses,'Duplicate required access')
        require(a['operation']==7,'Owned required-access profile currently supports read obligations')
        uint(a['word'],n-1,'required access word');uint(a['expected_data'],0xffffffff,'required read data')
        required_accesses[ref]=a
    memory={p:3 for p in range(physical)};tested_write=set();tested_read=set();credited={}
    seen_accesses=set();seen_release=False;ever_released=False;loaded_epoch=None
    for e in evidence['events']:
        ref=e['event_ref'];op=e['operation'];w=e['word_address'];p=e['actual_physical']
        before=lambda k:e['before_'+k]
        current_payload=e['loaded_payload'];current_epoch=e['repair_epoch']
        mapping_ok=e['repair_loaded'] and current_payload==payload and bool(e['repair_active'])==active and (not active or (e['decoded_bad']==bad and e['decoded_spare']==spare))
        if e['address_valid']:
            if p>=physical: finding('physical_address_out_of_range',ref,physical_word=p);continue
            if e['before_codeword']!=memory[p]:finding('physical_word_history_mismatch',ref,physical_word=p)
            if e['committed']:memory[p]=e['after_codeword']
            elif e['after_codeword']!=e['before_codeword']:finding('uncommitted_word_changed',ref)
        elif e['committed']:finding('commit_without_address',ref)
        if op in (0,1) and e['accepted']:
            if not before('test_owner') or ever_released:
                finding('test_port_access_after_handoff',ref,physical_word=p)
                credited={k:v for k,v in credited.items() if target(k)!=p}
            elif e['address_valid']:
                (tested_write if op==0 else tested_read).add(p)
            if op==0 and e['after_codeword']!=e['raw_input']:finding('raw_test_write_mismatch',ref)
        if op==3 and e['accepted']:
            loaded_epoch=current_epoch
            if e['repair_input']!=payload or current_payload!=payload:finding('repair_payload_mismatch',ref,expected=payload,observed=e['repair_input'])
            if not mapping_ok:finding('functional_repair_view_mismatch',ref,expected_bad=bad,expected_spare=spare,observed_bad=e['decoded_bad'],observed_spare=e['decoded_spare'],loaded=bool(e['repair_loaded']))
        if op==5:
            admitted=bool(e['accepted'] and e['committed'] and before('test_owner') and before('ecc_enabled') and before('repair_loaded') and loaded_epoch==current_epoch and mapping_ok and p==target(w) and e['after_codeword']==encode(e['write_data']))
            if w in wanted_init and e['write_data']!=wanted_init[w]:admitted=False;finding('initialization_data_mismatch',ref,word=w)
            if e['accepted'] and not admitted:finding('initialization_not_admitted',ref,word=w,physical_word=p,mapping_epoch=current_epoch)
            if admitted:credited[w]=current_epoch
            result['initialization'].append({'event_ref':ref,'word':w,'physical_word':p,'mapping_epoch':current_epoch,'admitted':admitted})
        transitioned=not before('released') and bool(e['released'])
        if ref==release_ref:
            seen_release=True
            if op!=6 or not transitioned:finding('required_handoff_not_completed',ref)
        if transitioned:
            ever_released=True
            missing_init=sorted(w for w in required if credited.get(w)!=current_epoch)
            missing_test=sorted(test_required-(tested_write&tested_read))
            accepted=bool(ref==release_ref and op==6 and e['accepted'] and before('test_owner') and not e['test_owner'] and mapping_ok and e['ecc_enabled'] and e['test_done'] and not missing_init and not missing_test)
            if not accepted:finding('handoff_prerequisites_not_met',ref,missing_init_words=missing_init,missing_test_physical_words=missing_test,mapping_ok=bool(mapping_ok),ecc_enabled=bool(e['ecc_enabled']))
            result['handoffs'].append({'event_ref':ref,'mapping_epoch':current_epoch,'admitted':accepted,'missing_init_words':missing_init,'missing_test_physical_words':missing_test})
        if op in (7,8) and e['accepted']:
            if not before('released') or before('test_owner'):finding('consumer_ownership_not_established',ref)
            if not before('ecc_enabled'):finding('consumer_ecc_disabled',ref)
            if not mapping_ok or p!=target(w):finding('consumer_physical_view_mismatch',ref,word=w,expected_physical=target(w),observed_physical=p)
            old_read=op==7 or e['byte_enable'] not in (0,15)
            if old_read and credited.get(w)!=current_epoch:finding('old_read_before_current_epoch_initialization',ref,word=w)
            if bool(e['internal_read'])!=old_read:finding('old_read_semantics_mismatch',ref)
            if not old_read and any(e[k] for k in ('correctable','uncorrectable','error')):finding('unexpected_old_read_status',ref)
            decoded=decode(e['before_codeword']);ecc=bool(before('ecc_enabled'))
            if old_read:
                ce=bool(ecc and decoded['correctable']);ue=bool(ecc and decoded['uncorrectable'])
                expected_old=decoded['data'] if ecc else e['before_codeword']&0xffffffff
                if (bool(e['correctable']),bool(e['uncorrectable']),bool(e['error']),e['old_data'])!=(ce,ue,ue,expected_old):finding('codec_observation_mismatch',ref)
                if ue:finding('consumer_uncorrectable_word',ref,word=w)
                if op==7 and e['read_data']!=expected_old:finding('codec_read_data_mismatch',ref)
            if op==8:
                mask=e['byte_enable'];expected_after=e['before_codeword'];commit=False
                if mask==15:expected_after=encode(e['write_data']);commit=True
                elif mask and not (ecc and decoded['uncorrectable']):
                    prior=decoded['data'] if ecc else e['before_codeword']&0xffffffff
                    # Byte-vector merge differs from the RTL's variable bit slices.
                    merged=bytearray(prior.to_bytes(4,'little'));incoming=e['write_data'].to_bytes(4,'little')
                    for lane in range(4):
                        if mask&(1<<lane):merged[lane]=incoming[lane]
                    expected_after=encode(int.from_bytes(merged,'little'));commit=True
                if (bool(e['committed']),e['after_codeword'])!=(commit,expected_after):finding('byte_write_semantics_mismatch',ref)
                if mask==0 and (e['internal_read'] or e['error']):finding('zero_mask_side_effect',ref)
                if commit and mask==15 and mapping_ok and p==target(w):credited[w]=current_epoch
            result['accesses'].append({'event_ref':ref,'word':w,'physical_word':p,'mapping_epoch':current_epoch,'internal_old_read':old_read,'read_data':e['read_data'],'error':bool(e['error'])})
        if ref in required_accesses:
            seen_accesses.add(ref);a=required_accesses[ref]
            if (op,w,e['accepted'])!=(a['operation'],a['word'],1):finding('required_access_identity_or_acceptance',ref)
            elif e['read_data']!=a['expected_data'] or e['error']:finding('required_readback_mismatch',ref,word=w,expected=a['expected_data'],observed=e['read_data'])
    if not seen_release:gap('required_handoff_missing',event_ref=release_ref)
    for ref in sorted(set(required_accesses)-seen_accesses):gap('required_access_missing',event_ref=ref)
    if not result['handoffs']:gap('functional_ownership_transition_unobserved')
    return finish()
