"""Review first-access prerequisites for one explicitly mapped storage wrapper."""
import hashlib
import json
from pathlib import Path

from ecc39 import PROFILE, decode, encode

TRAITS = ('partial_write_reads_old', 'full_write_reads_old', 'full_write_initializes',
          'zero_mask_noop', 'abort_on_uncorrectable', 'global_done_covers_all')
FLAGS = ('accepted', 'internal_read', 'correctable', 'uncorrectable', 'committed',
         'error', 'before_ready', 'after_ready', 'global_done', 'released')


def require(condition, message):
    if not condition: raise ValueError(message)


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), label+' required')


def boolean(value, label):
    require(type(value) is bool or value is None, label+' must be boolean or null')


def uint(value, maximum, label, nullable=False):
    require(nullable and value is None or type(value) is int and 0 <= value <= maximum, label+' out of unsigned range')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON key: '+key);result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON value')))


def review(inventory, journal, policy):
    for record, kind in ((inventory,'inventory'), (journal,'journal'), (policy,'policy')):
        require(isinstance(record, dict) and record.get('format') == 'opentools.storage.'+kind+'.v1', 'Unsupported '+kind+' format')
        require(isinstance(record.get('scope'), dict) and set(record['scope']) == {'project','configuration','mode','init_epoch_ref'}, 'Exact initialization scope required')
        for value in record['scope'].values(): text(value, 'scope')
        text(record.get('basis_ref'), 'basis_ref')
        require(type(record.get('inputs_complete')) is bool, 'Explicit inputs_complete required')
    report = {'format':'opentools.storage.report.v1', 'scope':inventory['scope'],
        'bindings':{kind+'_sha256':digest(value) for kind,value in (('inventory',inventory),('journal',journal),('policy',policy))},
        'findings':[], 'gaps':[], 'accesses':[], 'releases':[],
        'limits':['One mapped word array and one isolated initialization epoch; source roles, initial coverage and access completeness require review.',
                  'Owned codec checks cover Hamming (39,32) only. No physical memory, X, power, timing, coherency or arbitrary ECC qualification.']}
    def gap(kind, **details): report['gaps'].append(dict(kind=kind, **details))
    def finding(kind, **details): report['findings'].append(dict(kind=kind, **details))
    bound = True
    for record, name in ((journal,'journal'), (policy,'policy')):
        if record['scope'] != inventory['scope'] or record['basis_ref'] != inventory['basis_ref'] or record.get('inventory_sha256') != digest(inventory):
            gap('scope_or_inventory_binding', record=name);bound = False
    for record in (journal, policy): text(record.get('window_ref'), 'window_ref')
    if policy.get('journal_sha256') != digest(journal) or policy['window_ref'] != journal['window_ref']:
        gap('journal_or_window_binding');bound = False
    for record, name in ((inventory,'inventory'), (journal,'journal'), (policy,'policy')):
        if not record['inputs_complete']: gap('partial_inputs', record=name)
    for key in ('isolated_epoch', 'window_closed', 'accesses_complete'):
        require(key in journal, 'Explicit '+key+' required');boolean(journal[key], key)
        if journal[key] is not True: gap(key+'_unqualified')
    for key in ('memory_ref','initializer_ref','test_port_ref','geometry_evidence_ref','traits_evidence_ref','ecc_profile_ref'):
        text(inventory.get(key), key)
    geometry = inventory.get('geometry')
    require(isinstance(geometry, dict) and set(geometry) == {'base_address','size_bytes','word_bytes','word_count','data_bits','ecc_bits','codeword_bits','byte_order'}, 'Exact geometry required')
    for key in ('base_address','size_bytes'): uint(geometry[key], (1<<64)-1, key)
    for key in ('word_bytes','word_count','data_bits','ecc_bits','codeword_bits'): uint(geometry[key], 4096, key);require(geometry[key] > 0, 'Positive geometry required')
    require(geometry['byte_order'] in ('little','big','unknown'), 'Explicit byte order required')
    require(geometry['data_bits'] == 8*geometry['word_bytes'] and geometry['size_bytes'] == geometry['word_bytes']*geometry['word_count'] and geometry['codeword_bits'] == geometry['data_bits']+geometry['ecc_bits'], 'Inconsistent geometry')
    require(geometry['base_address'] % geometry['word_bytes'] == 0 and geometry['base_address']+geometry['size_bytes'] <= 1<<64, 'Invalid address range')
    traits = inventory.get('traits');require(isinstance(traits, dict) and set(traits) == set(TRAITS), 'Exact wrapper traits required')
    for key, value in traits.items():
        boolean(value, key)
        if value is None: gap('wrapper_trait_unknown', trait=key)
    if geometry['byte_order'] == 'unknown': gap('byte_order_unknown')
    owned = inventory['ecc_profile_ref'] == PROFILE and [geometry[k] for k in ('data_bits','ecc_bits','word_bytes')] == [32,7,4]
    for key in ('require_codec_check','require_global_done','allow_correctable'):
        require(type(policy.get(key)) is bool, 'Explicit '+key+' required')
    if policy['require_codec_check'] and not owned: gap('codec_profile_unqualified')
    words, width, base = geometry['word_count'], geometry['word_bytes'], geometry['base_address']
    word_max, data_max, lane_max = (1<<geometry['codeword_bits'])-1, (1<<geometry['data_bits'])-1, (1<<width)-1
    def address_word(address):
        uint(address, (1<<64)-1, 'address')
        require(base <= address < base+geometry['size_bytes'] and (address-base)%width == 0, 'Address outside aligned region')
        return (address-base)//width
    require(isinstance(policy.get('masters'), list) and policy['masters'], 'Independent first-master roster required')
    masters = {};required_refs = set()
    for master in policy['masters']:
        for key in ('id','release_event_ref','evidence_ref'): text(master.get(key), key)
        require(master['id'] not in masters, 'Duplicate master')
        require(type(master.get('allow_full_write_before_release')) is bool, 'Explicit full-write release exception required')
        require(isinstance(master.get('release_addresses'), list) and master['release_addresses'], 'Required release words required')
        selected = [address_word(a) for a in master['release_addresses']];require(len(set(selected)) == len(selected), 'Duplicate release word')
        require(isinstance(master.get('required_accesses'), list) and master['required_accesses'], 'Independent first-access roster required')
        for expected in master['required_accesses']:
            text(expected.get('event_ref'), 'expected event');text(expected.get('evidence_ref'), 'access intent evidence')
            require(expected['event_ref'] not in required_refs and expected.get('kind') in ('read','write'), 'Unique read/write intent required')
            required_refs.add(expected['event_ref']);address_word(expected.get('address'))
        masters[master['id']] = master
    require(inventory['initializer_ref'] not in masters and inventory['test_port_ref'] not in masters and inventory['initializer_ref'] != inventory['test_port_ref'], 'Separate initializer/test/consumer roles required')
    initial = journal.get('initial');require(isinstance(initial, list), 'Initial word evidence required')
    readiness, codewords = [None]*words, [None]*words
    initial_seen = set()
    for item in initial:
        index = address_word(item.get('address'));require(index not in initial_seen, 'Duplicate initial word');initial_seen.add(index)
        require('ready' in item and 'codeword' in item, 'Explicit initial values required')
        boolean(item['ready'], 'initial readiness');uint(item['codeword'], word_max, 'initial codeword', True);text(item.get('evidence_ref'), 'initial evidence')
        readiness[index], codewords[index] = item['ready'], item['codeword']
    for index in range(words):
        if index not in initial_seen or readiness[index] is None: gap('initial_readiness_unknown', address=base+index*width)
        if codewords[index] is None: gap('initial_codeword_unknown', address=base+index*width)
    events = journal.get('events');require(isinstance(events, list) and events, 'Ordered events required')
    event_map = {};previous_seq = previous_time = -1
    for event in events:
        for key in ('event_ref','master_ref','evidence_ref'): text(event.get(key), key)
        require(event['event_ref'] not in event_map, 'Duplicate event ref');event_map[event['event_ref']] = event
        for key in ('seq','time_tick'): uint(event.get(key), (1<<64)-1, key)
        require(event['seq'] > previous_seq and event['time_tick'] >= previous_time, 'Events must be ordered')
        previous_seq, previous_time = event['seq'], event['time_tick']
        require(event.get('kind') in ('initialize','read','write','inject','release'), 'Unsupported storage event')
        if event['kind'] == 'release':
            for key in ('released','global_done'): require(key in event, 'Explicit release flags required');boolean(event[key], key)
        else:
            address_word(event.get('address'))
            for key in FLAGS: require(key in event, 'Explicit observation '+key+' required');boolean(event[key], key)
            for key, maximum in (('write_data',data_max),('byte_enable',lane_max),('inject_mask',word_max),('before_codeword',word_max),('after_codeword',word_max),('old_data',data_max),('read_data',data_max)):
                require(key in event, 'Explicit observation '+key+' required');uint(event[key], maximum, key, True)
    # Cross-scope observations are retained but must not supply readiness credit.
    if not bound:
        report['status'] = 'incomplete';return report
    for master in masters.values():
        release = event_map.get(master['release_event_ref'])
        if release is None or release['kind'] != 'release' or release['master_ref'] != master['id']: gap('required_release_absent', master=master['id'])
        for expected in master['required_accesses']:
            event = event_map.get(expected['event_ref'])
            if event is None: gap('required_access_absent', event_ref=expected['event_ref'])
            elif [event.get(k) for k in ('kind','address','master_ref')] != [expected['kind'],expected['address'],master['id']]:
                finding('required_access_identity_mismatch', event_ref=expected['event_ref'])
            elif event['accepted'] is False: finding('required_access_not_accepted', event_ref=expected['event_ref'])
            elif event['accepted'] is None: gap('required_access_acceptance_unknown', event_ref=expected['event_ref'])
    released = {master:False for master in masters}
    for event in events:
        ref, master_ref, kind = event['event_ref'], event['master_ref'], event['kind']
        master = masters.get(master_ref)
        def issue(name, **details): finding(name, event_ref=ref, **details)
        def missing(name, **details): gap(name, event_ref=ref, **details)
        if kind == 'release':
            if master is None: missing('release_master_unmapped');continue
            if ref != master['release_event_ref']: missing('unexpected_release_event')
            if event['released'] is not True: missing('release_not_observed');continue
            if released[master_ref]: missing('multiple_release_events')
            for address in master['release_addresses']:
                ready = readiness[address_word(address)]
                if ready is False: issue('release_before_target_initialized', address=address)
                elif ready is None: missing('release_target_readiness_unknown', address=address)
            if policy['require_global_done']:
                if event['global_done'] is False: issue('release_before_global_done')
                elif event['global_done'] is None: missing('release_global_done_unknown')
            released[master_ref] = True
            report['releases'].append({'event_ref':ref,'master_ref':master_ref,'required_addresses':master['release_addresses']})
            continue
        index = address_word(event['address']);ready = readiness[index];before = codewords[index]
        for key in FLAGS:
            if event[key] is None: missing('observation_unknown', field=key)
        for key in ('write_data','byte_enable','inject_mask','before_codeword','after_codeword','old_data','read_data'):
            if event[key] is None: missing('observation_unknown', field=key)
        if ready is not None and event['before_ready'] is not None and ready != event['before_ready']: issue('readiness_history_mismatch', field='before_ready')
        if before is not None and event['before_codeword'] is not None and before != event['before_codeword']: issue('codeword_history_mismatch')
        if kind == 'initialize' and master_ref != inventory['initializer_ref']: issue('initializer_owner_mismatch')
        if kind == 'inject' and master_ref != inventory['test_port_ref']: missing('test_injection_owner_unmapped')
        if kind in ('read','write') and master is None: issue('consumer_master_unmapped')
        lanes = event['byte_enable'];full = lanes == lane_max
        old_read = True if kind == 'read' else False
        if kind == 'write':
            if lanes is None: old_read = None
            elif full: old_read = traits['full_write_reads_old']
            elif lanes == 0 and traits['zero_mask_noop'] is None: old_read = None
            else: old_read = False if lanes == 0 and traits['zero_mask_noop'] is True else traits['partial_write_reads_old']
        if event['accepted'] is False:
            if event['internal_read'] is True: missing('unaccepted_internal_read_requires_native_review')
            if event['committed'] is True or event['after_codeword'] != event['before_codeword']: issue('unaccepted_access_changed_storage')
            old_read = False if event['internal_read'] is not True else True
        elif event['accepted'] is None: old_read = None
        if old_read is None: missing('effective_old_read_unknown')
        elif event['internal_read'] is not None and old_read != event['internal_read']: issue('internal_read_contract_mismatch')
        effective_read = old_read is True or event['internal_read'] is True
        if effective_read:
            if ready is False: issue('old_data_read_before_initialized', address=event['address'])
            elif ready is None: missing('old_data_readiness_unknown')
        if master is not None:
            if event['released'] is not None and event['released'] != released[master_ref]: issue('release_history_mismatch')
            if event['accepted'] is True and not released[master_ref] and not (kind == 'write' and full and master['allow_full_write_before_release'] and old_read is False): issue('access_before_release')
        if effective_read and event['uncorrectable'] is True: issue('uncorrectable_old_data', address=event['address'])
        if effective_read and event['correctable'] is True and not policy['allow_correctable']: issue('correctable_event_disallowed')
        next_ready = ready
        if event['accepted'] is True and event['committed'] is True:
            if kind == 'initialize' and master_ref == inventory['initializer_ref']: next_ready = True
            elif kind == 'write' and full and traits['full_write_initializes'] is True and master is not None: next_ready = True
            elif kind == 'write' and full and traits['full_write_initializes'] is None: next_ready = None
        elif kind in ('initialize','write') and (event['accepted'] is None or event['committed'] is None): next_ready = None
        expected_word = before
        # Full semantic cross-check is deliberately restricted to the owned wrapper contract.
        qualified = owned and geometry['byte_order'] == 'little' and all(traits[k] == v for k,v in {
            'partial_write_reads_old':True,'full_write_reads_old':False,'full_write_initializes':True,'zero_mask_noop':True,'abort_on_uncorrectable':True}.items())
        if policy['require_codec_check'] and not qualified: missing('wrapper_codec_semantics_unqualified')
        if qualified and before is not None and all(event[k] is not None for k in ('write_data','byte_enable','inject_mask','accepted')):
            decoded = decode(before);expected_commit = False
            if event['accepted']:
                if kind == 'initialize' or kind == 'write' and full:
                    expected_word = encode(event['write_data']);expected_commit = True
                elif kind == 'inject': expected_word = before^event['inject_mask'];expected_commit = True
                elif kind == 'write' and lanes != 0 and not decoded['uncorrectable']:
                    merged = decoded['data']
                    for lane in range(width):
                        if lanes & (1<<lane): merged = (merged & ~(255<<(8*lane))) | (event['write_data'] & (255<<(8*lane)))
                    expected_word = encode(merged);expected_commit = True
            for key, expected in (('committed',expected_commit), ('after_codeword',expected_word)):
                if event[key] is not None and event[key] != expected: issue('codec_or_wrapper_mismatch', field=key, expected=expected, observed=event[key])
            if effective_read:
                for key, expected in (('correctable',decoded['correctable']),('uncorrectable',decoded['uncorrectable']),('error',decoded['uncorrectable']),('old_data',decoded['data'])):
                    if event[key] is not None and event[key] != expected: issue('codec_or_wrapper_mismatch', field=key, expected=expected, observed=event[key])
                if kind == 'read' and event['read_data'] is not None and event['read_data'] != decoded['data']: issue('read_data_mismatch', expected=decoded['data'], observed=event['read_data'])
            elif event['accepted']:
                for key in ('correctable','uncorrectable','error'):
                    if event[key] is True: issue('codec_status_without_old_read', field=key)
        codewords[index] = event['after_codeword']
        readiness[index] = next_ready
        if next_ready is not None and event['after_ready'] is not None and event['after_ready'] != next_ready: issue('readiness_history_mismatch', field='after_ready')
        if traits['global_done_covers_all'] is True and event['global_done'] is True and any(v is False for v in readiness): issue('global_done_with_uninitialized_words')
        report['accesses'].append({'event_ref':ref,'kind':kind,'address':event['address'],'master_ref':master_ref,
            'ready_before':ready,'ready_after':next_ready,'effective_old_read':old_read,'observed_internal_read':event['internal_read'],
            'correctable':event['correctable'],'uncorrectable':event['uncorrectable'],'committed':event['committed'],'read_data':event['read_data']})
    report['final_readiness'] = [{'address':base+i*width,'ready':r} for i,r in enumerate(readiness)]
    report['status'] = 'violated' if report['findings'] else 'incomplete' if report['gaps'] else 'satisfied'
    return report


def exit_code(report):
    return {'satisfied':0,'violated':1,'incomplete':2}[report['status']]
