import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROFILE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROFILE));sys.path.insert(0,str(PROFILE/'examples'))
from transition_core import digest,exit_code,read_json,review
from create_example import example,save


def bind(model,journal,policy):journal['model_sha256']=digest(model);policy['model_sha256']=digest(model);policy['journal_sha256']=digest(journal)
def event(journal,ref):return next(e for e in journal['events'] if e['event_ref']==ref)
def kinds(report,field='findings'):return {f['kind'] for f in report[field]}


class TransitionTests(unittest.TestCase):
    def test_premature_grant_or_reclaim_overlaps_actual_old_permissions(self):
        for case in ('directory-premature-grant','ring-premature-completion'):
            report=review(*example(case));self.assertEqual(exit_code(report),1)
            self.assertIn('grant_with_pending_obligations',kinds(report));self.assertIn('exclusive_permission_overlaps_old_holders',kinds(report))
            self.assertEqual(report['grants'][0]['pending'],['release-1'])

    def test_both_protocol_profiles_complete_after_distinct_holder_receipts(self):
        for case in ('directory-complete','ring-complete'):
            report=review(*example(case));self.assertEqual(exit_code(report),0);self.assertEqual(report['grants'][0]['pending'],[])

    def test_data_and_release_obligations_are_separate(self):
        report=review(*example('directory-data-late'));self.assertEqual(report['grants'][0]['pending'],['returned-data'])
        self.assertIn('consumer_data_mismatch',kinds(report));self.assertNotIn('exclusive_permission_overlaps_old_holders',kinds(report))
        read=next(r for r in report['reads'] if r['event_ref']=='new-read');self.assertEqual(read['value'],0)

    def test_duplicate_source_cannot_discharge_another_holders_obligation(self):
        report=review(*example('directory-duplicate-count'))
        self.assertEqual(report['duplicate_receipts'],[{'event_ref':'duplicate-release-0','obligation':'release-0'}])
        self.assertIn('reported_pending_count_mismatch',kinds(report));self.assertEqual(report['grants'][0]['pending'],['release-1'])

    def test_stale_epoch_receipt_is_ignored_and_control_still_completes(self):
        report=review(*example('directory-stale-ack-ignored'));self.assertEqual(exit_code(report),0)
        self.assertEqual(report['ignored_messages'][0]['event_ref'],'stale-release-0');self.assertFalse(report['duplicate_receipts'])

    def test_offered_held_token_is_not_an_accepted_grant(self):
        model,journal,policy=example('directory-backpressured-grant');report=review(model,journal,policy)
        self.assertEqual(exit_code(report),0);self.assertTrue(event(journal,'grant-held')['offered'])
        self.assertFalse(event(journal,'grant-offered')['accepted']);self.assertFalse(next(r for r in report['ledger'] if r['event_ref']=='grant-held')['accepted_grant'])
        self.assertEqual(len(report['grants']),1)

    def test_late_release_and_good_final_state_do_not_erase_early_grant(self):
        report=review(*example('directory-premature-grant'));self.assertEqual(report['ledger'][-1]['pending'],[])
        self.assertTrue(report['ledger'][-1]['finished']);self.assertIn('grant_with_pending_obligations',kinds(report))
        self.assertEqual(report['grants'][0]['state_label'],'exclusive-stable')

    def test_counter_or_mask_cannot_substitute_for_receipt_history(self):
        model,journal,policy=example('directory-premature-grant')
        for e in journal['events']:
            if e['seq']>=event(journal,'grant')['seq']:e['reported_pending_count']=0;e['reported_pending']={k:False for k in e['reported_pending']}
        bind(model,journal,policy);report=review(model,journal,policy)
        self.assertIn('reported_pending_source_mismatch',kinds(report));self.assertEqual(report['grants'][0]['pending'],['release-1'])

    def test_ack_must_observe_actual_permission_release(self):
        model,journal,policy=example('directory-complete');event(journal,'release-1')['holders']['sharer-1']=True
        bind(model,journal,policy);report=review(model,journal,policy)
        self.assertIn('release_ack_without_permission_release',kinds(report));self.assertIn('grant_with_pending_obligations',kinds(report))

    def test_unknown_data_bytes_are_a_gap_not_absent_receipt(self):
        model,journal,policy=example('directory-complete');event(journal,'data')['data_value']=None
        bind(model,journal,policy);report=review(model,journal,policy)
        self.assertEqual(exit_code(report),2);self.assertEqual(report['grants'][0]['pending'],[])
        self.assertIn('returned_data_unknown',kinds(report,'gaps'))

    def test_unknown_receipt_identity_acceptance_or_release_preserves_uncertainty(self):
        for variant in ('message_epoch','accepted','permission'):
            model,journal,policy=example('directory-complete');receipt=event(journal,'release-1')
            if variant=='permission':receipt['holders']['sharer-1']=None
            else:receipt[variant]=None
            bind(model,journal,policy);report=review(model,journal,policy)
            self.assertEqual(exit_code(report),2,report);self.assertIn('grant_obligations_unknown',kinds(report,'gaps'))
            self.assertNotIn('grant_with_pending_obligations',kinds(report))

    def test_missing_receipt_sample_is_incomplete_instead_of_a_proven_early_grant(self):
        model,journal,policy=example('directory-complete');journal['events'].remove(event(journal,'release-1'))
        bind(model,journal,policy);report=review(model,journal,policy)
        self.assertEqual(exit_code(report),2);self.assertIn('required_sample_absent',kinds(report,'gaps'))
        self.assertNotIn('grant_with_pending_obligations',kinds(report))

    def test_foreign_scope_protocol_hash_or_window_supplies_no_ledger(self):
        for variant in ('protocol','epoch','hash','window'):
            model,journal,policy=example('directory-premature-grant');journal=copy.deepcopy(journal)
            if variant=='protocol':journal['scope']['protocol_ref']='unrelated-protocol'
            elif variant=='epoch':journal['scope']['epoch_ref']='previous-epoch'
            elif variant=='hash':policy['journal_sha256']='0'*64
            else:policy['window_ref']='different-window'
            report=review(model,journal,policy);self.assertEqual(exit_code(report),2);self.assertFalse(report['ledger'] or report['grants'])

    def test_current_id_with_foreign_message_epoch_does_not_credit_a_holder(self):
        model,journal,policy=example('directory-complete');event(journal,'release-1')['message_epoch']=0
        bind(model,journal,policy);report=review(model,journal,policy)
        self.assertIn('grant_with_pending_obligations',kinds(report));self.assertTrue(report['ignored_messages'])

    def test_missing_obligation_participant_or_holder_cannot_shrink_required_roster(self):
        for variant in ('obligation','participant','holder','role'):
            model,journal,policy=example('directory-complete')
            if variant=='obligation':model['obligations'].pop(1)
            elif variant=='participant':model['participants'].pop(1)
            elif variant=='holder':model['initial_holders'].pop()
            else:model['participants'][0]['role_ref']='unrelated'
            bind(model,journal,policy);report=review(model,journal,policy)
            self.assertEqual(exit_code(report),2);self.assertTrue(report['gaps'])

    def test_old_permission_can_drop_before_ack_but_does_not_discharge_ack(self):
        model,journal,policy=example('directory-premature-grant')
        for e in journal['events']:
            if e['seq']>=event(journal,'grant')['seq']:e['holders']['sharer-1']=False
        bind(model,journal,policy);report=review(model,journal,policy)
        self.assertNotIn('exclusive_permission_overlaps_old_holders',kinds(report));self.assertIn('grant_with_pending_obligations',kinds(report))

    def test_state_label_does_not_create_accepted_permission(self):
        model,journal,policy=example('directory-complete');event(journal,'grant')['accepted']=False
        bind(model,journal,policy);report=review(model,journal,policy)
        self.assertIn('permission_without_accepted_grant',kinds(report));self.assertIn('consumer_use_without_accepted_permission',kinds(report))

    def test_unknown_grant_frontier_is_a_gap_not_a_known_permission_violation(self):
        model,journal,policy=example('directory-complete');event(journal,'grant')['accepted']=None
        bind(model,journal,policy);report=review(model,journal,policy)
        self.assertEqual(exit_code(report),2);self.assertIn('permission_grant_frontier_unknown',kinds(report,'gaps'))
        self.assertNotIn('permission_without_accepted_grant',kinds(report))

    def test_unknown_permissions_keep_known_premature_grant_finding(self):
        model,journal,policy=example('directory-premature-grant');event(journal,'grant')['holders']['sharer-1']=None
        bind(model,journal,policy);report=review(model,journal,policy)
        self.assertEqual(exit_code(report),1);self.assertTrue(report['gaps']);self.assertIn('grant_with_pending_obligations',kinds(report))

    def test_consumer_read_identity_and_data_are_not_substituted(self):
        for variant in ('epoch','data'):
            model,journal,policy=example('directory-complete');read=event(journal,'new-read')
            read['message_epoch' if variant=='epoch' else 'read_value']=0 if variant=='epoch' else 99
            bind(model,journal,policy);report=review(model,journal,policy)
            self.assertIn('consumer_transaction_identity_mismatch' if variant=='epoch' else 'consumer_data_mismatch',kinds(report))

    def test_old_read_cannot_escape_the_permission_or_participant_census(self):
        for variant in ('permission','source'):
            model,journal,policy=example('directory-premature-grant');read=event(journal,'old-read')
            if variant=='permission':read['holders']['sharer-1']=False
            else:read['source_ref']='unmapped-peer'
            bind(model,journal,policy);report=review(model,journal,policy)
            self.assertIn('old_holder_read_without_permission' if variant=='permission' else 'old_reader_not_in_holder_census',kinds(report) if variant=='permission' else kinds(report,'gaps'))

    def test_partial_window_or_unknown_initial_rights_stay_visible(self):
        for variant in ('window_closed','epoch_isolated','events_complete','initial'):
            model,journal,policy=example('directory-complete')
            if variant=='initial':journal['initial_holders']['sharer-0']=None
            else:journal[variant]=None
            bind(model,journal,policy);report=review(model,journal,policy);self.assertEqual(exit_code(report),2);self.assertTrue(report['gaps'])

    def test_bad_flags_sequence_duplicate_and_count_are_invalid(self):
        for variant in ('flag','sequence','duplicate','count'):
            model,journal,policy=example('directory-complete')
            if variant=='flag':event(journal,'grant')['accepted']=1
            elif variant=='sequence':journal['events'][-1]['seq']=0
            elif variant=='duplicate':model['obligations'][1]['id']=model['obligations'][0]['id']
            else:journal['events'][0]['reported_pending_count']=-1
            bind(model,journal,policy)
            with self.assertRaises(ValueError):review(model,journal,policy)

    def test_cli_json_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            for key,value in zip(('model','journal','policy'),example('directory-complete')):save(folder/(key+'.json'),value)
            command=[sys.executable,str(PROFILE/'transition_review.py')]+[str(folder/(key+'.json')) for key in ('model','journal','policy')]
            result=subprocess.run(command,capture_output=True,text=True);self.assertEqual(result.returncode,0);self.assertEqual(json.loads(result.stdout)['status'],'within_observed_contract')
            before=(folder/'model.json').read_bytes();refused=subprocess.run(command+['--output',str(folder/'model.json')],capture_output=True,text=True)
            self.assertEqual(refused.returncode,3);self.assertEqual((folder/'model.json').read_bytes(),before)
            for raw in ('{"x":1,"x":2}','{"x":NaN}'):
                (folder/'bad.json').write_text(raw,encoding='utf-8')
                with self.assertRaises(ValueError):read_json(folder/'bad.json')

    @unittest.skipUnless(os.environ.get('OPENTOOLS_VERILATOR') and os.environ.get('OPENTOOLS_VERILATOR_ROOT'),'Native tools not configured')
    def test_native_transfer_invariant_and_consumption(self):
        from run_native import run
        with tempfile.TemporaryDirectory() as temporary:
            result=run(Path(temporary)/'proof',os.environ['OPENTOOLS_VERILATOR'],os.environ['OPENTOOLS_VERILATOR_ROOT'])
            self.assertEqual(len(result['cases']),8);self.assertEqual(sum(c['native_rows'] for c in result['cases']),84)
            self.assertEqual(sum(c['old_read_valid'] for c in result['cases']),3)
            self.assertEqual(sum(r['status']=='within_observed_contract' for r in result['reviews']),4)


if __name__=='__main__':unittest.main()
