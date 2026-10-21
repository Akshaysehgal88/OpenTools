import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROFILE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROFILE));sys.path.insert(0,str(PROFILE/'examples'))
from diagnostic_core import digest,exit_code,read_json,review
from create_example import example,save
from reference_model import trace

def bind(values):
    spec,journal,policy=values;journal['spec_sha256']=policy['spec_sha256']=digest(spec);policy['journal_sha256']=digest(journal)
def kinds(report,field='findings'):return {item['kind'] for item in report[field]}
def select(values):return next(e for e in values[1]['events'] if e['id']==values[2]['selected_read_ref'])

class DiagnosticTests(unittest.TestCase):
    def test_saved_capture_uses_response_before_read_clear_and_survives_recovery(self):
        rows=trace('pre-reset-snapshot');self.assertEqual(rows[2]['status'],0);self.assertEqual(rows[2]['rd_data'],1)
        self.assertEqual(rows[3]['saved_value'],1);self.assertEqual(rows[4]['status'],0)
        result=review(*example('pre-reset-snapshot'));self.assertEqual(exit_code(result),0);self.assertEqual(result['evidence_answer'],'present')
        self.assertEqual(result['selected_observation']['epoch'],0);self.assertEqual(result['selected_observation']['origin_read_ref'],'read-2')

    def test_post_reset_zero_does_not_establish_pre_reset_absence(self):
        result=review(*example('post-reset-zero'));self.assertFalse(result['selected_cause_bit_set'])
        self.assertEqual(result['evidence_answer'],'unknown');self.assertIn('selected_epoch_mismatch',kinds(result,'gaps'));self.assertEqual(exit_code(result),1)

    def test_undetermined_is_valid_when_selected_evidence_was_erased(self):
        result=review(*example('post-reset-undetermined'));self.assertEqual(exit_code(result),2)
        self.assertEqual(result['evidence_answer'],'unknown');self.assertFalse(result['findings'])

    def test_monitor_consumption_changes_later_read_basis(self):
        rows=trace('monitor-consumes');self.assertEqual(rows[2]['rd_data'],1);self.assertEqual(rows[3]['rd_data'],0)
        result=review(*example('monitor-consumes'));self.assertEqual(result['selected_observation']['epoch'],1)
        self.assertEqual(result['evidence_answer'],'unknown');self.assertEqual(len(result['erasures']),2)

    def test_unavailable_access_does_not_turn_idle_response_zero_into_absence(self):
        result=review(*example('clock-unavailable'));self.assertIsNone(result['selected_cause_bit_set'])
        self.assertEqual(result['evidence_answer'],'unknown');self.assertIn('read_not_qualified',kinds(result,'gaps'))

    def test_no_fault_control_has_only_bounded_negative_support(self):
        result=review(*example('no-fault-control'));self.assertEqual(exit_code(result),0)
        self.assertEqual(result['evidence_answer'],'absent_in_observed_prefix');self.assertEqual(result['negative_through_seq'],2)

    def test_negative_needs_complete_latching_and_required_prefix(self):
        for variant in ('latching','deadline','baseline'):
            values=example('no-fault-control')
            if variant=='latching':values[1]['source_latching_complete']=None
            elif variant=='deadline':values[2]['required_through_seq']=100
            else:values[1]['initial_status']=None
            bind(values);result=review(*values);self.assertEqual(result['evidence_answer'],'unknown');self.assertEqual(exit_code(result),1)

    def test_positive_observation_does_not_need_negative_latching_completeness(self):
        values=example('engine-retains-status');values[1]['source_latching_complete']=None;bind(values)
        result=review(*values);self.assertEqual(exit_code(result),0);self.assertEqual(result['evidence_answer'],'present')

    def test_second_context_retains_status_across_local_recovery(self):
        retained=review(*example('engine-retains-status'));cleared=review(*example('engine-local-clear'))
        self.assertEqual(retained['evidence_answer'],'present');self.assertEqual(cleared['evidence_answer'],'unknown')
        self.assertEqual(exit_code(review(*example('engine-fault-free'))),0)

    def test_stale_crash_record_has_real_set_bit_without_current_epoch_proof(self):
        result=review(*example('old-crash-record'));self.assertTrue(result['selected_cause_bit_set'])
        self.assertEqual(result['selected_observation']['data'],1);self.assertEqual(result['evidence_answer'],'unknown')
        self.assertIn('record_capture_provenance_unverified',kinds(result,'gaps'))

    def test_reset_of_saved_record_prevents_credit_from_earlier_capture(self):
        result=review(*example('snapshot-cleared-by-reset'));self.assertEqual(result['evidence_answer'],'unknown')
        self.assertIn('loaded_record_unknown_or_invalid',kinds(result,'gaps'));self.assertEqual(exit_code(result),1)

    def test_dirty_initial_status_does_not_establish_new_epoch_fault(self):
        values=example('engine-retains-status');values[1]['initial_status']=4;bind(values)
        result=review(*values);self.assertTrue(result['selected_cause_bit_set']);self.assertEqual(result['evidence_answer'],'unknown')
        self.assertIn('target_epoch_clean_start_unproven',kinds(result,'gaps'))

    def test_foreign_scope_or_spec_returns_no_selected_observation(self):
        spec,_,policy=example('pre-reset-snapshot');_,journal,_=example('engine-retains-status')
        result=review(spec,journal,policy);self.assertEqual(exit_code(result),2);self.assertIsNone(result['selected_observation'])
        self.assertFalse(result['findings'])

    def test_stale_source_basis_is_not_qualified_by_equal_values(self):
        values=example('pre-reset-snapshot');values[2]['source_revision_ref']='previous-source'
        result=review(*values);self.assertEqual(result['evidence_answer'],'unknown');self.assertIn('source_revision_mismatch',kinds(result,'gaps'))

    def test_missing_selected_read_retains_unknown_instead_of_no_fault(self):
        values=example('pre-reset-snapshot');values[1]['events'].remove(select(values));values[2]['claim']='undetermined';bind(values)
        result=review(*values);self.assertEqual(exit_code(result),2);self.assertEqual(result['evidence_answer'],'unknown')

    def test_unknown_acceptance_cannot_create_response_or_clear_basis(self):
        values=example('monitor-consumes');values[1]['events'][0]['accepted']=None;bind(values)
        result=review(*values);self.assertEqual(result['evidence_answer'],'unknown')
        self.assertIn('possible_unobserved_read_effect',kinds(result,'gaps'))

    def test_unknown_reset_or_prior_read_effect_preserves_epoch_uncertainty(self):
        for variant in ('reset','read'):
            values=example('post-reset-undetermined' if variant=='reset' else 'monitor-consumes')
            values[0]['status']['reset_effect' if variant=='reset' else 'onread']='unknown';values[2]['claim']='undetermined';bind(values)
            result=review(*values);self.assertEqual(result['evidence_answer'],'unknown');self.assertEqual(exit_code(result),2)

    def test_missing_capture_source_does_not_gain_provenance_from_valid_tag(self):
        values=example('pre-reset-snapshot');next(e for e in values[1]['events'] if e['kind']=='save')['source_read_ref']='absent-read';bind(values)
        result=review(*values);self.assertTrue(result['selected_cause_bit_set']);self.assertEqual(result['evidence_answer'],'unknown')
        self.assertIn('capture_source_read_missing',kinds(result,'gaps'))

    def test_saved_value_or_epoch_mismatch_cannot_supply_original_read(self):
        for variant in ('value','epoch'):
            values=example('pre-reset-snapshot');capture=next(e for e in values[1]['events'] if e['kind']=='save')
            capture['record'][variant]=0 if variant=='value' else 99;bind(values);result=review(*values)
            self.assertIn('saved_value_disagrees_with_source' if variant=='value' else 'saved_epoch_disagrees_with_source',kinds(result))
            self.assertEqual(result['evidence_answer'],'unknown')

    def test_loaded_record_must_match_capture_data_and_known_epoch(self):
        for variant in ('data','epoch'):
            values=example('pre-reset-snapshot');select(values)[variant]=0 if variant=='data' else 99;bind(values)
            result=review(*values);self.assertEqual(result['evidence_answer'],'unknown')
            self.assertIn('loaded_record_value_disagreement' if variant=='data' else 'loaded_record_epoch_disagreement',kinds(result))

    def test_unknown_save_tag_cannot_hide_conflicting_loaded_tag(self):
        values=example('pre-reset-snapshot');next(e for e in values[1]['events'] if e['kind']=='save')['record']['epoch']=None
        select(values)['epoch']=99;bind(values);result=review(*values)
        self.assertIn('loaded_record_epoch_disagreement',kinds(result));self.assertEqual(result['evidence_answer'],'unknown')

    def test_hardware_tags_optional_with_complete_known_capture_history(self):
        values=example('pre-reset-snapshot')
        for e in values[1]['events']:
            if e['kind']=='read':e['epoch']=None
            if e['kind']=='save':e['record']['epoch']=None
        bind(values);self.assertEqual(review(*values)['evidence_answer'],'present')

    def test_unknown_record_validity_or_data_is_not_zero_or_valid_capture(self):
        for variant in ('record_valid','data'):
            values=example('pre-reset-snapshot');select(values)[variant]=None;bind(values)
            result=review(*values);self.assertEqual(result['evidence_answer'],'unknown')

    def test_selected_consumer_and_capture_roles_are_independent(self):
        for variant in ('consumer','capture'):
            values=example('pre-reset-snapshot')
            if variant=='consumer':values[2]['consumer_ref']='other-consumer'
            else:values[2]['allowed_capture_actors']=['other-capturer']
            result=review(*values);self.assertEqual(result['evidence_answer'],'unknown')

    def test_concurrent_or_unsettled_read_is_not_this_sampled_profile(self):
        values=example('pre-reset-snapshot');next(e for e in values[1]['events'] if e['kind']=='read')['hardware_quiet']=False;bind(values)
        result=review(*values);self.assertEqual(result['evidence_answer'],'unknown');self.assertIn('read_effect_unqualified',kinds(result,'gaps'))

    def test_partial_history_keeps_observed_bits_but_not_epoch_attribution(self):
        values=example('pre-reset-snapshot');values[1]['history_complete']=False;bind(values)
        result=review(*values);self.assertTrue(result['selected_cause_bit_set']);self.assertEqual(result['evidence_answer'],'unknown')
        self.assertIn('epoch_history_unproven',kinds(result,'gaps'))

    def test_epoch_overflow_is_unqualified_instead_of_wrapping_to_old_incident(self):
        values=example('post-reset-undetermined');values[1]['initial_epoch']=(1<<64)-1;bind(values)
        result=review(*values);self.assertIn('epoch_capacity_unqualified',kinds(result,'gaps'));self.assertEqual(result['evidence_answer'],'unknown')

    def test_wide_cause_data_is_not_truncated_to_native_example_width(self):
        values=example('pre-reset-snapshot');spec,journal,policy=values;spec['status']['width']=128;policy['fault_mask']=1<<100
        journal['initial_status']<<=100;journal['initial_record']['value']<<=100
        for e in journal['events']:
            if e['kind']=='read' and e['data'] is not None:e['data']<<=100
            if e['kind']=='save':e['record']['value']<<=100
        bind(values);result=review(*values);self.assertEqual(exit_code(result),0);self.assertEqual(result['selected_observation']['data'],1<<100)

    def test_strict_boolean_integer_masks_and_duplicate_events(self):
        for variant in ('data','mask','id','coverage'):
            values=example('pre-reset-snapshot')
            if variant=='data':select(values)['data']=True
            elif variant=='mask':values[2]['fault_mask']=3
            elif variant=='id':values[1]['events'][-1]['id']=values[1]['events'][0]['id']
            else:values[1]['history_complete']=1
            bind(values)
            with self.assertRaises(ValueError):review(*values)

    def test_cli_strict_json_no_overwrite_and_reference_kind(self):
        values=example('pre-reset-snapshot');self.assertEqual(values[1]['source_kind'],'owned-reference-fixture')
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            for key,value in zip(('spec','journal','policy'),values):save(folder/(key+'.json'),value)
            command=[sys.executable,str(PROFILE/'diagnostic_review.py')]+[str(folder/(key+'.json')) for key in ('spec','journal','policy')]
            result=subprocess.run(command,capture_output=True,text=True);self.assertEqual(result.returncode,0);self.assertEqual(json.loads(result.stdout)['evidence_answer'],'present')
            before=(folder/'spec.json').read_bytes();refused=subprocess.run(command+['--output',str(folder/'spec.json')],capture_output=True,text=True)
            self.assertEqual(refused.returncode,3);self.assertEqual((folder/'spec.json').read_bytes(),before)
            for raw in ('{"x":1,"x":2}','{"x":NaN}'):
                (folder/'bad.json').write_text(raw,encoding='utf-8')
                with self.assertRaises(ValueError):read_json(folder/'bad.json')

    @unittest.skipUnless(os.environ.get('OPENTOOLS_VERILATOR') and os.environ.get('OPENTOOLS_VERILATOR_ROOT'),'Native tools not configured')
    def test_native_recovery_capture_and_actual_responses(self):
        from run_native import run
        with tempfile.TemporaryDirectory() as temporary:
            result=run(Path(temporary)/'proof',os.environ['OPENTOOLS_VERILATOR'],os.environ['OPENTOOLS_VERILATOR_ROOT'])
            self.assertEqual(len(result['cases']),11);self.assertEqual(sum(c['rows'] for c in result['cases']),47)
            self.assertEqual(sum(c['status']=='within_observed_evidence' for c in result['cases']),4)
            self.assertEqual(sum(c['status']=='incomplete' for c in result['cases']),1)

if __name__=='__main__':unittest.main()
