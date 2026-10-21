import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(MODULE));sys.path.insert(0,str(MODULE/'examples'))
from ecc39 import decode,encode,systematic
from storage_core import digest,exit_code,read_json,review
from create_example import CASES,example,save


def bind(inventory,journal,policy):
    journal['inventory_sha256']=digest(inventory);policy['inventory_sha256']=digest(inventory);policy['journal_sha256']=digest(journal)


def kinds(report,field='findings'):
    return {item['kind'] for item in report[field]}


class StorageTests(unittest.TestCase):
    def test_clean_basis_and_known_systematic_vector(self):
        self.assertEqual(encode(1),(1<<38)|7);self.assertEqual(systematic(encode(1)),0x4300000001)
        for data in [0,0xffffffff,0xa5a5f00d]+[1<<b for b in range(32)]:
            decoded=decode(encode(data));self.assertEqual(decoded['data'],data)
            self.assertFalse(decoded['correctable'] or decoded['uncorrectable'])

    def test_single_and_double_faults_include_check_and_overall_bits(self):
        for data in (0,0xffffffff,0xa5a5f00d):
            word=encode(data)
            for bit in range(39):
                d=decode(word^(1<<bit));self.assertTrue(d['correctable']);self.assertFalse(d['uncorrectable']);self.assertEqual(d['data'],data)
                for other in range(bit+1,39):
                    d=decode(word^(1<<bit)^(1<<other));self.assertTrue(d['uncorrectable']);self.assertFalse(d['correctable'])

    def test_bad_before_scrub_and_good_after_for_two_master_profiles(self):
        for prefix in ('boot','dma'):
            bad=review(*example(prefix+'-before-scrub'));good=review(*example(prefix+'-after-scrub'))
            self.assertEqual(exit_code(bad),1);self.assertEqual(exit_code(good),0)
            self.assertIn('old_data_read_before_initialized',kinds(bad));self.assertIn('release_before_target_initialized',kinds(bad))
            self.assertEqual(good['accesses'][-1]['read_data'],0xdd)

    def test_full_word_first_initializes_without_reading_invalid_old_ecc(self):
        report=review(*example('boot-full-word-first'));self.assertEqual(exit_code(report),0)
        first=report['accesses'][0];self.assertFalse(first['ready_before']);self.assertTrue(first['ready_after']);self.assertFalse(first['effective_old_read'])
        self.assertEqual(report['accesses'][-1]['read_data'],0x112233dd)

    def test_selected_word_policy_does_not_require_unrelated_global_scrub(self):
        inventory,journal,policy=example('boot-full-word-first')
        self.assertFalse(next(e for e in journal['events'] if e['kind']=='release')['global_done'])
        self.assertEqual(exit_code(review(inventory,journal,policy)),0)
        policy['require_global_done']=True
        self.assertIn('release_before_global_done',kinds(review(inventory,journal,policy)))

    def test_wrong_word_scrub_and_forced_global_flag_do_not_supply_credit(self):
        report=review(*example('dma-wrong-word-global-done'))
        self.assertIn('global_done_with_uninitialized_words',kinds(report));self.assertIn('release_before_target_initialized',kinds(report))
        self.assertFalse(next(a for a in report['accesses'] if a['event_ref']=='first-partial')['ready_before'])

    def test_single_error_is_corrected_before_partial_byte_merge(self):
        inventory,journal,policy=example('after-single-bit-error');report=review(inventory,journal,policy)
        self.assertEqual(exit_code(report),0);self.assertEqual(report['accesses'][-1]['read_data'],0xcc00)
        partial=next(e for e in journal['events'] if e['event_ref']=='first-partial')
        self.assertTrue(partial['correctable']);self.assertEqual(partial['old_data'],0)
        partial['after_codeword']=encode(0xcc01);bind(inventory,journal,policy)
        self.assertIn('codec_or_wrapper_mismatch',kinds(review(inventory,journal,policy)))

    def test_double_error_aborts_rmw_even_when_initialized(self):
        inventory,journal,policy=example('after-double-bit-error')
        partial=next(e for e in journal['events'] if e['event_ref']=='first-partial')
        self.assertFalse(partial['committed']);self.assertEqual(partial['before_codeword'],partial['after_codeword'])
        report=review(inventory,journal,policy);self.assertIn('uncorrectable_old_data',kinds(report));self.assertNotIn('old_data_read_before_initialized',kinds(report))

    def test_valid_codeword_and_successful_rmw_do_not_prove_initialization(self):
        inventory,journal,policy=example('valid-code-no-init');report=review(inventory,journal,policy)
        self.assertEqual(report['accesses'][-1]['read_data'],0xdd)
        self.assertIn('old_data_read_before_initialized',kinds(report));self.assertNotIn('uncorrectable_old_data',kinds(report))
        self.assertFalse(report['final_readiness'][2]['ready'])

    def test_correctable_policy_is_separate_from_codec_behavior(self):
        inventory,journal,policy=example('after-single-bit-error');policy['allow_correctable']=False
        self.assertIn('correctable_event_disallowed',kinds(review(inventory,journal,policy)))

    def test_bus_write_cannot_hide_internal_old_read(self):
        inventory,journal,policy=example('boot-before-scrub')
        partial=next(e for e in journal['events'] if e['event_ref']=='first-partial');partial['internal_read']=False
        bind(inventory,journal,policy);report=review(inventory,journal,policy)
        self.assertIn('internal_read_contract_mismatch',kinds(report));self.assertIn('old_data_read_before_initialized',kinds(report))

    def test_initializer_role_cannot_be_aliased_as_consumer(self):
        inventory,journal,policy=example('boot-after-scrub');journal['events'][0]['master_ref']=policy['masters'][0]['id']
        bind(inventory,journal,policy)
        self.assertIn('initializer_owner_mismatch',kinds(review(inventory,journal,policy)))

    def test_missing_initial_coverage_and_unknowns_stay_incomplete(self):
        for key in ('missing','ready','codeword'):
            inventory,journal,policy=example('boot-after-scrub')
            if key=='missing':journal['initial'].pop()
            else:journal['initial'][0][key]=None
            bind(inventory,journal,policy);report=review(inventory,journal,policy)
            self.assertEqual(exit_code(report),2);self.assertTrue(report['gaps'])

    def test_observed_ready_flag_cannot_replace_initializer_history(self):
        inventory,journal,policy=example('valid-code-no-init')
        for event in journal['events']:
            if event['kind']!='release':event['before_ready']=event['after_ready']=True
        bind(inventory,journal,policy);report=review(inventory,journal,policy)
        self.assertIn('readiness_history_mismatch',kinds(report));self.assertIn('old_data_read_before_initialized',kinds(report))

    def test_missing_required_consumer_event_cannot_rewrite_roster(self):
        inventory,journal,policy=example('dma-after-scrub');journal['events'].pop()
        bind(inventory,journal,policy);report=review(inventory,journal,policy)
        self.assertEqual(exit_code(report),2);self.assertIn('required_access_absent',kinds(report,'gaps'))

    def test_required_access_identity_and_acceptance_checked(self):
        for variant in ('identity','accepted'):
            inventory,journal,policy=example('boot-after-scrub');event=journal['events'][-1]
            event['address' if variant=='identity' else 'accepted']=4100 if variant=='identity' else False
            bind(inventory,journal,policy)
            self.assertIn('required_access_identity_mismatch' if variant=='identity' else 'required_access_not_accepted',kinds(review(inventory,journal,policy)))

    def test_stale_or_foreign_binding_cannot_grant_readiness(self):
        for variant in ('epoch','scope','inventory','journal','window'):
            inventory,journal,policy=example('boot-after-scrub')
            if variant=='epoch':journal=copy.deepcopy(journal);journal['scope']['init_epoch_ref']='previous-reset'
            elif variant=='scope':policy=copy.deepcopy(policy);policy['scope']['project']='foreign'
            elif variant=='inventory':journal['inventory_sha256']='0'*64
            elif variant=='journal':policy['journal_sha256']='0'*64
            else:policy['window_ref']='different-window'
            report=review(inventory,journal,policy);self.assertEqual(exit_code(report),2);self.assertFalse(report['accesses'])

    def test_partial_window_and_unknown_macro_semantics_not_qualified(self):
        for variant in ('open','incomplete','reset','trait','order','codec'):
            inventory,journal,policy=example('dma-after-scrub')
            if variant=='open':journal['window_closed']=False
            elif variant=='incomplete':journal['accesses_complete']=None
            elif variant=='reset':journal['isolated_epoch']=False
            elif variant=='trait':inventory['traits']['partial_write_reads_old']=None
            elif variant=='order':inventory['geometry']['byte_order']='big'
            else:inventory['ecc_profile_ref']='some-other-39-32-code'
            bind(inventory,journal,policy);self.assertEqual(exit_code(review(inventory,journal,policy)),2)

    def test_known_violation_is_retained_with_missing_observation(self):
        inventory,journal,policy=example('boot-before-scrub');journal['events'][-1]['read_data']=None
        bind(inventory,journal,policy);report=review(inventory,journal,policy)
        self.assertEqual(exit_code(report),1);self.assertTrue(report['gaps']);self.assertIn('uncorrectable_old_data',kinds(report))

    def test_release_history_and_release_exception_enforced(self):
        inventory,journal,policy=example('boot-full-word-first');policy['masters'][0]['allow_full_write_before_release']=False
        self.assertIn('access_before_release',kinds(review(inventory,journal,policy)))
        inventory,journal,policy=example('boot-after-scrub');journal['events'][-1]['released']=False
        bind(inventory,journal,policy);self.assertIn('release_history_mismatch',kinds(review(inventory,journal,policy)))

    def test_zero_mask_does_not_read_old_data_or_initialize(self):
        inventory,journal,policy=example('boot-before-scrub');event=journal['events'][-2]
        event.update(byte_enable=0,internal_read=False,correctable=False,uncorrectable=False,committed=False,error=False)
        bind(inventory,journal,policy);report=review(inventory,journal,policy)
        result=next(a for a in report['accesses'] if a['event_ref']=='first-partial')
        self.assertFalse(result['effective_old_read']);self.assertFalse(result['ready_after'])
        self.assertFalse(any(f['event_ref']=='first-partial' and f['kind']=='old_data_read_before_initialized' for f in report['findings']))

    def test_geometry_and_types_are_not_silently_reinterpreted(self):
        for variant in ('geometry','address','bool','duplicate','order'):
            inventory,journal,policy=example('boot-after-scrub')
            if variant=='geometry':inventory['geometry']['size_bytes']=15
            elif variant=='address':journal['events'][-1]['address']=4097
            elif variant=='bool':journal['events'][-1]['committed']=1
            elif variant=='duplicate':journal['events'][-1]['event_ref']=journal['events'][0]['event_ref']
            else:journal['events'][-1]['seq']=0
            bind(inventory,journal,policy)
            with self.assertRaises(ValueError):review(inventory,journal,policy)

    def test_cli_and_json_reject_nonfinite_duplicate_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            for name,value in zip(('inventory','journal','policy'),example('boot-after-scrub')):save(folder/(name+'.json'),value)
            result=subprocess.run([sys.executable,str(MODULE/'storage_review.py')]+[str(folder/(n+'.json')) for n in ('inventory','journal','policy')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0);self.assertEqual(json.loads(result.stdout)['status'],'satisfied')
            original=(folder/'inventory.json').read_bytes()
            refused=subprocess.run([sys.executable,str(MODULE/'storage_review.py')]+[str(folder/(n+'.json')) for n in ('inventory','journal','policy')]+['--output',str(folder/'inventory.json')],capture_output=True,text=True)
            self.assertEqual(refused.returncode,3);self.assertEqual((folder/'inventory.json').read_bytes(),original)
            for raw in ('{"a":1,"a":2}','{"a":NaN}'):
                (folder/'bad.json').write_text(raw,encoding='utf-8')
                with self.assertRaises(ValueError):read_json(folder/'bad.json')

    @unittest.skipUnless(os.environ.get('OPENTOOLS_VERILATOR') and os.environ.get('OPENTOOLS_VERILATOR_ROOT'),'Native tools not configured')
    def test_native_array_ledger_and_codec(self):
        from run_native import run
        with tempfile.TemporaryDirectory() as temporary:
            result=run(Path(temporary)/'proof',os.environ['OPENTOOLS_VERILATOR'],os.environ['OPENTOOLS_VERILATOR_ROOT'],os.environ.get('OPENTOOLS_ECC_REFERENCE'))
            self.assertEqual(result['codec_probes'],2375);self.assertEqual(len(result['cases']),9)
            self.assertFalse(any(c['gaps'] for c in result['cases']));self.assertEqual(sum(c['events'] for c in result['cases']),48)


if __name__=='__main__':unittest.main()
