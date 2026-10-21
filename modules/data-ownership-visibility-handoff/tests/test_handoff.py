import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(MODULE));sys.path.insert(0,str(MODULE/'examples'))
from handoff_core import digest,exit_code,read_json,review
from create_example import example,save
from cache_model import trace


def bind(inventory,journal,policy):
    journal['inventory_sha256']=digest(inventory);policy['inventory_sha256']=digest(inventory);policy['journal_sha256']=digest(journal)


def kinds(report,field='findings'):return {item['kind'] for item in report[field]}


def event(journal,ref):return next(e for e in journal['events'] if e['event_ref']==ref)


class HandoffTests(unittest.TestCase):
    def test_coherent_control_does_not_make_noncoherent_payload_fresh(self):
        report=review(*example('dma-no-clean'));self.assertEqual(exit_code(report),1)
        self.assertTrue(report['reads'][0]['control_seen']);self.assertEqual(report['reads'][0]['value'],17)
        self.assertIn('publication_before_payload_maintenance_complete',kinds(report));self.assertIn('consumer_payload_mismatch',kinds(report))

    def test_completed_clean_and_genuine_coherent_snoop_are_controls(self):
        for case in ('dma-clean-complete','dma-coherent','shared-queue-coherent'):
            report=review(*example(case));self.assertEqual(exit_code(report),0);self.assertEqual(report['reads'][0]['value'],165)
        coherent_row=next(r for r in trace('dma-coherent') if r['event_ref']=='consumer-read')
        self.assertEqual(coherent_row['memory_a'],17);self.assertEqual(coherent_row['cache_a'],165);self.assertEqual(coherent_row['read_data'],165)

    def test_second_shared_queue_context_uses_the_same_visibility_activity(self):
        for case,code in (('shared-queue-noncoherent',1),('shared-queue-coherent',0)):
            report=review(*example(case));self.assertEqual(exit_code(report),code)
            self.assertEqual(report['reads'][0]['mapping_ref'],'consumer-payload')

    def test_clean_issue_and_late_completion_do_not_repair_earlier_stale_read(self):
        inventory,journal,policy=example('dma-clean-pending');report=review(inventory,journal,policy)
        self.assertLess(event(journal,'consumer-read')['seq'],event(journal,'clean-complete')['seq'])
        self.assertEqual(report['reads'][0]['value'],17);self.assertIsNone(report['publications'][0]['completed_payload_image'])
        self.assertIn('publication_before_payload_maintenance_complete',kinds(report))

    def test_clean_completion_uses_captured_alias_target_not_current_command_line(self):
        inventory,journal,policy=example('dma-clean-wrong-alias');complete=event(journal,'clean-complete')
        self.assertEqual(complete['object_ref'],'other-buffer');self.assertEqual(complete['mapping_ref'],'producer-other')
        report=review(inventory,journal,policy);self.assertIn('publication_before_payload_maintenance_complete',kinds(report))
        self.assertEqual(report['reads'][0]['value'],17)

    def test_release_order_does_not_flush_a_dirty_cache(self):
        report=review(*example('dma-no-clean'))
        self.assertEqual(report['publications'][0]['ordered_version'],1)
        self.assertFalse(report['publications'][0]['payload_coherent']);self.assertIsNone(report['publications'][0]['completed_payload_image'])

    def test_coherent_data_does_not_remove_the_ordering_contract(self):
        report=review(*example('dma-coherent-no-order'))
        self.assertEqual(report['reads'][0]['value'],165);self.assertEqual(kinds(report),{'publication_without_required_release_order'})

    def test_correct_read_does_not_excuse_producer_write_during_consumer_ownership(self):
        report=review(*example('dma-write-while-consumer-owned'))
        self.assertEqual(report['reads'][0]['value'],165);self.assertEqual(kinds(report),{'producer_write_while_consumer_owned'})
        good=review(*example('dma-clean-complete'));self.assertNotIn('producer_write_while_consumer_owned',kinds(good))

    def test_completion_before_consumption_cannot_authorize_reclaim(self):
        report=review(*example('dma-completion-before-read'))
        self.assertEqual(report['reads'][0]['value'],165)
        self.assertTrue({'completion_before_required_consumption','reclaim_without_qualified_completion','consumer_read_without_consumer_ownership'}<=kinds(report))

    def test_consumer_mapping_identity_is_independent_of_matching_control(self):
        report=review(*example('dma-consumer-wrong-map'))
        self.assertTrue(report['reads'][0]['control_seen']);self.assertEqual(report['reads'][0]['value'],34)
        self.assertIn('consumer_payload_identity_mismatch',kinds(report))

    def test_expected_payload_is_not_replaced_by_current_cache_or_read_value(self):
        inventory,journal,policy=example('dma-coherent');event(journal,'consumer-read')['value']=60
        bind(inventory,journal,policy);report=review(inventory,journal,policy)
        mismatch=next(f for f in report['findings'] if f['kind']=='consumer_payload_mismatch' and f['field']=='value')
        self.assertEqual(mismatch['expected'],165);self.assertEqual(mismatch['observed'],60)

    def test_unknown_expected_value_or_version_is_incomplete(self):
        for key in ('expected_value','expected_version'):
            inventory,journal,policy=example('dma-clean-complete');policy[key]=None
            report=review(inventory,journal,policy);self.assertEqual(exit_code(report),2);self.assertIn('expected_payload_unknown',kinds(report,'gaps'))

    def test_unknown_capture_order_or_read_evidence_is_not_synthesized(self):
        for variant in ('capture','order','read','effect'):
            inventory,journal,policy=example('dma-clean-complete')
            if variant=='capture':event(journal,'clean-request')['version']=None;event(journal,'clean-complete')['version']=None
            elif variant=='order':event(journal,'release-order')['version']=None
            elif variant=='read':event(journal,'consumer-read')['value']=None
            else:event(journal,'consumer-complete')['effect_observed']=None
            bind(inventory,journal,policy);report=review(inventory,journal,policy)
            self.assertEqual(exit_code(report),2,report);self.assertTrue(report['gaps'])

    def test_wrong_clean_receipt_version_or_request_is_not_visibility_credit(self):
        for variant in ('version','request'):
            inventory,journal,policy=example('dma-clean-complete');receipt=event(journal,'clean-complete')
            receipt['version' if variant=='version' else 'request_ref']=0 if variant=='version' else 'absent'
            bind(inventory,journal,policy);report=review(inventory,journal,policy)
            self.assertTrue({'maintenance_completion_capture_mismatch','maintenance_request_absent'}&(kinds(report)|kinds(report,'gaps')))
            self.assertIsNone(report['publications'][0]['completed_payload_image'])

    def test_missing_required_object_mapping_or_role_cannot_shrink_intent(self):
        for variant in ('object','mapping','role'):
            inventory,journal,policy=example('dma-coherent')
            if variant=='object':inventory['objects'].pop(0)
            elif variant=='mapping':inventory['mappings']=[m for m in inventory['mappings'] if m['id']!='consumer-payload']
            else:inventory['objects'][0]['role_ref']='unrelated-control'
            bind(inventory,journal,policy);report=review(inventory,journal,policy)
            self.assertTrue({'required_definition_absent','required_definition_mismatch'}&kinds(report,'gaps'));self.assertNotEqual(exit_code(report),0)

    def test_unknown_path_cacheability_shareability_or_mapping_epoch_is_not_coherence(self):
        for variant in ('path_ref','shareability_ref','coherent','cacheability','mapping_epoch_ref'):
            inventory,journal,policy=example('dma-coherent');mapping=next(m for m in inventory['mappings'] if m['id']=='consumer-payload')
            mapping[variant]='unknown' if variant=='cacheability' else 'old-mapping' if variant=='mapping_epoch_ref' else None
            bind(inventory,journal,policy);report=review(inventory,journal,policy)
            self.assertEqual(exit_code(report),2);self.assertTrue(report['gaps'])

    def test_alias_address_and_actor_mismatch_are_not_ignored(self):
        for variant in ('address','actor'):
            inventory,journal,policy=example('dma-clean-complete');write=event(journal,'payload-write')
            write['address' if variant=='address' else 'actor_ref']=20480 if variant=='address' else 'foreign-agent'
            bind(inventory,journal,policy);report=review(inventory,journal,policy)
            self.assertIn('event_mapping_identity_mismatch' if variant=='address' else 'mapping_actor_mismatch',kinds(report))

    def test_overlapping_physical_objects_require_reviewed_alias_identity(self):
        inventory,journal,policy=example('dma-coherent');inventory['objects'][1]['physical_address']=4096
        bind(inventory,journal,policy);report=review(inventory,journal,policy)
        self.assertEqual(exit_code(report),2);self.assertIn('overlapping_physical_object_definitions',kinds(report,'gaps'))

    def test_stale_foreign_or_wrong_window_evidence_supplies_no_lifecycle(self):
        for variant in ('scope','inventory','journal','window'):
            inventory,journal,policy=example('dma-no-clean');journal=copy.deepcopy(journal)
            if variant=='scope':journal['scope']['handoff_ref']='previous-transfer'
            elif variant=='inventory':journal['inventory_sha256']='0'*64
            elif variant=='journal':policy['journal_sha256']='0'*64
            else:policy['window_ref']='different-window'
            report=review(inventory,journal,policy);self.assertEqual(exit_code(report),2);self.assertFalse(report['reads'] or report['ownership'])

    def test_missing_milestone_prefix_or_partial_epoch_is_visible(self):
        for variant in ('milestone','prefix','epoch','open','coverage'):
            inventory,journal,policy=example('dma-coherent')
            if variant=='milestone':policy['read_ref']='missing-read'
            elif variant=='prefix':journal['events'].pop(0)
            elif variant=='epoch':journal['epoch_isolated']=None
            elif variant=='open':journal['window_closed']=False
            else:journal['events_complete']=False
            bind(inventory,journal,policy);report=review(inventory,journal,policy)
            self.assertNotEqual(exit_code(report),0);self.assertTrue(report['gaps'])

    def test_known_stale_read_is_retained_with_missing_owner(self):
        inventory,journal,policy=example('dma-no-clean');journal['initial_owner_ref']=None
        bind(inventory,journal,policy);report=review(inventory,journal,policy)
        self.assertEqual(exit_code(report),1);self.assertIn('consumer_payload_mismatch',kinds(report));self.assertTrue(report['gaps'])

    def test_invalid_values_flags_duplicates_sequence_and_geometry_rejected(self):
        for variant in ('value','flag','duplicate','sequence','geometry','policy-boolean'):
            inventory,journal,policy=example('dma-coherent')
            if variant=='value':event(journal,'consumer-read')['value']=1<<32
            elif variant=='flag':event(journal,'consumer-read')['control_seen']=1
            elif variant=='duplicate':inventory['objects'][1]['id']='payload'
            elif variant=='sequence':journal['events'][-1]['seq']=0
            elif variant=='geometry':inventory['objects'][0]['line_bytes']=3
            else:policy['required_mappings'][0]['coherent']=0
            bind(inventory,journal,policy)
            with self.assertRaises(ValueError):review(inventory,journal,policy)

    def test_cli_strict_json_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            for name,value in zip(('inventory','journal','policy'),example('dma-coherent')):save(folder/(name+'.json'),value)
            command=[sys.executable,str(MODULE/'handoff_review.py')]+[str(folder/(name+'.json')) for name in ('inventory','journal','policy')]
            result=subprocess.run(command,capture_output=True,text=True);self.assertEqual(result.returncode,0);self.assertEqual(json.loads(result.stdout)['status'],'within_observed_contract')
            original=(folder/'inventory.json').read_bytes();refused=subprocess.run(command+['--output',str(folder/'inventory.json')],capture_output=True,text=True)
            self.assertEqual(refused.returncode,3);self.assertEqual((folder/'inventory.json').read_bytes(),original)
            for raw in ('{"x":1,"x":2}','{"x":NaN}'):
                (folder/'bad.json').write_text(raw,encoding='utf-8')
                with self.assertRaises(ValueError):read_json(folder/'bad.json')

    @unittest.skipUnless(os.environ.get('OPENTOOLS_VERILATOR') and os.environ.get('OPENTOOLS_VERILATOR_ROOT'),'Native tools not configured')
    def test_native_cache_backing_and_read_ledger(self):
        from run_native import run
        with tempfile.TemporaryDirectory() as temporary:
            result=run(Path(temporary)/'proof',os.environ['OPENTOOLS_VERILATOR'],os.environ['OPENTOOLS_VERILATOR_ROOT'])
            self.assertEqual(len(result['cases']),11);self.assertEqual(sum(c['native_rows'] for c in result['cases']),98)
            self.assertTrue(all(c['read_control'] for c in result['cases']))
            self.assertEqual(sum(r['status']=='within_observed_contract' for r in result['reviews']),3)


if __name__=='__main__':unittest.main()
