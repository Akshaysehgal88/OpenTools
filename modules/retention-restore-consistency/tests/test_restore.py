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
from restore_core import digest,exit_code,read_json,review
from create_example import example


def bind(inventory,journal,policy):
    journal['inventory_sha256']=digest(inventory);policy['inventory_sha256']=digest(inventory);policy['journal_sha256']=digest(journal)


class RestoreTests(unittest.TestCase):
    def test_payload_only_does_not_establish_usable_warm_bundle(self):
        report=review(*example('cache-payload-only'))
        self.assertEqual(exit_code(report),1)
        mismatches={f['state'] for f in report['findings'] if f['kind']=='bundle_member_not_restored'}
        self.assertEqual(mismatches,{'identity','valid','auxiliary','initialized'})
        self.assertTrue(any(f['kind']=='unexpected_post_wake_read_outcome' and f['field']=='hit' for f in report['findings']))

    def test_metadata_without_payload_returns_wrong_cache_or_context_data(self):
        for case,expected in (('cache-metadata-only',165),('context-metadata-only',109)):
            report=review(*example(case))
            witness=next(f for f in report['findings'] if f['kind']=='post_wake_read_data_mismatch')
            self.assertEqual(witness['expected'],expected);self.assertEqual(witness['observed'],0)

    def test_paired_retention_is_valid_for_both_consumer_profiles(self):
        for case in ('cache-paired','context-paired'):
            self.assertEqual(exit_code(review(*example(case))),0)

    def test_correct_read_does_not_hide_lost_dirty_metadata(self):
        report=review(*example('cache-dirty-lost'))
        self.assertEqual(report['reads'][0]['data'],165);self.assertTrue(report['reads'][0]['hit'])
        self.assertEqual({f['state'] for f in report['findings']},{'auxiliary'})

    def test_later_correct_snapshot_does_not_erase_early_exposure_or_fault(self):
        inventory,journal,policy=example('cache-valid-before-init')
        self.assertEqual(journal['samples'][-1]['values']['initialized'],1)
        report=review(inventory,journal,policy)
        self.assertTrue(any(f['kind']=='consumer_exposed_before_prerequisite' and f['seq']==4 for f in report['findings']))
        self.assertTrue(any(f['kind']=='unexpected_post_wake_read_outcome' and f['field']=='error' and f['seq']==5 for f in report['findings']))

    def test_lost_flags_can_be_rebuilt_before_valid_publication(self):
        inventory,journal,policy=example('cache-init-before-valid')
        lost={s['id'] for s in inventory['states'] if s['selection']=='lost'}
        self.assertEqual(lost,{'valid','initialized'})
        report=review(inventory,journal,policy);self.assertEqual(exit_code(report),0)
        self.assertEqual(report['bundles'][0]['exposed_sequences'][0],7)

    def test_explicit_cold_rebuild_uses_new_image_without_warm_assumption(self):
        inventory,journal,policy=example('cache-cold-reinitialize')
        self.assertEqual(journal['samples'][2]['values']['auxiliary'],0)
        report=review(inventory,journal,policy);self.assertEqual(exit_code(report),0)
        self.assertEqual(report['reads'][0]['data'],60)
        self.assertEqual(report['bundles'][0]['expected_members']['identity'],2)

    def test_missing_inventory_member_cannot_redefine_consumer_bundle(self):
        inventory,journal,policy=example('cache-dirty-lost')
        inventory['states']=[s for s in inventory['states'] if s['id']!='auxiliary']
        for sample in journal['samples']:sample['values'].pop('auxiliary')
        bind(inventory,journal,policy);report=review(inventory,journal,policy)
        self.assertEqual(exit_code(report),2)
        self.assertIn({'kind':'required_state_absent','state':'auxiliary'},report['gaps'])

    def test_member_role_mismatch_remains_a_gap(self):
        inventory,journal,policy=example('cache-paired');inventory['states'][0]['role_ref']='unrelated-control'
        bind(inventory,journal,policy)
        self.assertEqual(exit_code(review(inventory,journal,policy)),2)

    def test_unknown_before_value_is_not_replaced_with_reset_value(self):
        inventory,journal,policy=example('cache-paired');journal['samples'][2]['values']['payload']=None
        bind(inventory,journal,policy);report=review(inventory,journal,policy)
        self.assertEqual(exit_code(report),2)
        self.assertIn('expected_member_value_unknown',[g['kind'] for g in report['gaps']])

    def test_unknowns_do_not_hide_known_data_mismatch(self):
        inventory,journal,policy=example('cache-metadata-only');journal['samples'][-1]['values']['auxiliary']=None
        bind(inventory,journal,policy);report=review(inventory,journal,policy)
        self.assertEqual(exit_code(report),1);self.assertTrue(report['gaps'])
        self.assertTrue(any(f['kind']=='post_wake_read_data_mismatch' for f in report['findings']))

    def test_unknown_wake_boundary_cannot_pass_from_later_good_state(self):
        inventory,journal,policy=example('cache-paired');journal['samples'][4]['controls']['power_available']=None
        bind(inventory,journal,policy);report=review(inventory,journal,policy)
        self.assertEqual(exit_code(report),2)
        self.assertIn('transition_boundary_unknown',[g['kind'] for g in report['gaps']])

    def test_missing_loss_snapshot_and_multiple_cycles_are_distinct(self):
        for variant,code in (('before',2),('no-loss',1),('two-loss',2)):
            inventory,journal,policy=example('cache-paired')
            if variant=='before':journal['samples']=[s for s in journal['samples'] if s['seq']!=2]
            if variant=='no-loss':
                for sample in journal['samples']:sample['controls'].update(power_available=True,transition_active=False)
            if variant=='two-loss':journal['samples'][10]['controls'].update(power_available=False,transition_active=True)
            bind(inventory,journal,policy)
            self.assertEqual(exit_code(review(inventory,journal,policy)),code,variant)

    def test_missing_post_read_or_request_attribution_is_incomplete(self):
        for variant in ('response','request'):
            inventory,journal,policy=example('cache-paired')
            for sample in journal['samples']:
                for event in sample['reads']:
                    event['response_valid' if variant=='response' else 'requested']=False
            bind(inventory,journal,policy)
            self.assertEqual(exit_code(review(inventory,journal,policy)),2)

    def test_read_availability_false_and_unknown_have_different_results(self):
        for value,code in ((False,1),(None,2)):
            inventory,journal,policy=example('cache-paired');journal['samples'][8]['controls']['consumer_enabled']=value
            bind(inventory,journal,policy)
            self.assertEqual(exit_code(review(inventory,journal,policy)),code)

    def test_partial_coverage_and_unisolated_window_do_not_pass(self):
        for variant in ('partial','isolation','open','selection'):
            inventory,journal,policy=example('cache-paired')
            if variant=='partial':journal['inputs_complete']=False
            if variant=='isolation':journal['transition_isolated']=False
            if variant=='open':journal['window_closed']=False
            if variant=='selection':inventory['states'][0]['selection']='unknown'
            bind(inventory,journal,policy)
            self.assertEqual(exit_code(review(inventory,journal,policy)),2)

    def test_foreign_scope_stale_inputs_and_wrong_window_are_not_compared(self):
        for variant in ('scope','inventory','journal','window'):
            inventory,journal,policy=example('cache-paired')
            if variant=='scope':journal['scope']['transition_ref']='another-cycle'
            if variant=='inventory':journal['inventory_sha256']='0'*64
            if variant=='journal':policy['journal_sha256']='0'*64
            if variant=='window':policy['window_ref']='later'
            report=review(inventory,journal,policy)
            self.assertEqual(exit_code(report),2);self.assertFalse(report['bundles'])

    def test_wide_scalar_payload_is_compared_losslessly(self):
        inventory,journal,policy=example('cache-paired');inventory['states'][0]['width']=512
        wide=(1<<511)+165
        for sample in journal['samples']:
            if sample['seq']>=1:sample['values']['payload']=wide
            for event in sample['reads']:event['data']=wide
        bind(inventory,journal,policy);self.assertEqual(exit_code(review(inventory,journal,policy)),0)
        journal['samples'][8]['reads'][0]['data']^=1;bind(inventory,journal,policy)
        self.assertTrue(any(f['kind']=='post_wake_read_data_mismatch' for f in review(inventory,journal,policy)['findings']))

    def test_no_consumer_or_ready_observation_is_not_a_vacuous_pass(self):
        inventory,journal,policy=example('cache-paired')
        policy['bundles'][0]['require_ready']=False;policy['bundles'][0]['read']['required']=False
        for sample in journal['samples']:
            sample['controls'].update(restore_ready=False,consumer_enabled=False);sample['reads']=[]
        bind(inventory,journal,policy)
        self.assertEqual(exit_code(review(inventory,journal,policy)),2)

    def test_unused_ready_signal_can_be_unknown_when_exposure_is_established(self):
        inventory,journal,policy=example('cache-paired');policy['bundles'][0]['require_ready']=False
        for sample in journal['samples']:sample['controls']['restore_ready']=None
        bind(inventory,journal,policy)
        self.assertEqual(exit_code(review(inventory,journal,policy)),0)

    def test_invalid_types_duplicate_obligations_and_read_width_are_rejected(self):
        for variant in ('boolean','sequence','duplicate','data-width'):
            inventory,journal,policy=example('cache-paired')
            if variant=='boolean':journal['samples'][2]['values']['valid']=True
            if variant=='sequence':journal['samples'].reverse()
            if variant=='duplicate':policy['bundles'][0]['members'].append(copy.deepcopy(policy['bundles'][0]['members'][0]))
            if variant=='data-width':journal['samples'][8]['reads'][0]['data']=256
            bind(inventory,journal,policy)
            with self.assertRaises(ValueError):review(inventory,journal,policy)

    def test_cli_refuses_overwrite_and_duplicate_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            for name,record in zip(('inventory','journal','policy'),example('cache-paired')):
                (folder/(name+'.json')).write_text(json.dumps(record),encoding='utf-8')
            command=[sys.executable,str(MODULE/'restore_review.py'),'review']+[str(folder/(n+'.json')) for n in ('inventory','journal','policy')]
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)
            self.assertEqual(subprocess.run(command+['--json-out',str(folder/'journal.json')],capture_output=True).returncode,3)
            (folder/'duplicate.json').write_text('{"x":1,"x":2}',encoding='utf-8')
            with self.assertRaises(ValueError):read_json(folder/'duplicate.json')

    @unittest.skipUnless(os.environ.get('OPENTOOLS_VERILATOR') and os.environ.get('OPENTOOLS_VERILATOR_ROOT'),'Native Linux simulation tools not configured')
    def test_native_selected_loss_staged_restore_and_actual_post_wake_reads(self):
        from run_native import run
        with tempfile.TemporaryDirectory() as temporary:
            result=run(Path(temporary)/'native',os.environ['OPENTOOLS_VERILATOR'],os.environ['OPENTOOLS_VERILATOR_ROOT'])
            self.assertEqual(len(result['cases']),9)
            self.assertEqual([r['read']['error'] for r in result['cases']],[0,0,0,0,1,0,0,0,0])


if __name__=='__main__':unittest.main()
