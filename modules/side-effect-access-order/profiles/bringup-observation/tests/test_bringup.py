"""Observation validity,source time and original-condition controls."""
import copy,os,shutil,sys,tempfile,unittest
from pathlib import Path
PROFILE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(PROFILE),str(PROFILE/'examples')]
from bringup_common import qualified_compiler,read_json,save
from bringup_core import markdown,review,validate
from native_bringup import load,program
from fixture import FAMILIES

class Inputs(unittest.TestCase):
    def test_resolved_compiler_alias_supported(self):self.assertTrue(qualified_compiler('x86_64-linux-gnu-g++-13 (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0\n'));self.assertFalse(qualified_compiler('g++ (Ubuntu 14.1.0) 14.1.0\n'))
    def test_duplicate_json_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x';p.write_text('{"revision":"A","revision":"B"}')
            with self.assertRaises(ValueError):read_json(p)
    def test_command_image_injection_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x';p.write_text('1 POR;exec\n')
            with self.assertRaises(ValueError):program(p)
    def test_nonmonotonic_image_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x';p.write_text('1 POR\n1 READ\n')
            with self.assertRaises(ValueError):program(p)
    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x';save(p,{'old':True})
            with self.assertRaises(FileExistsError):save(p,{})
            self.assertEqual(read_json(p),{'old':True})

class NativeObservations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value=os.environ.get('OPENTOOLS_BRINGUP_NATIVE')
        if not value:raise unittest.SkipTest('Set OPENTOOLS_BRINGUP_NATIVE to actual run_native.py output')
        cls.root=Path(value);cls.collection=read_json(cls.root/'collection.json')
        if cls.collection['native_executions']!=18:raise ValueError('Complete actual18-case corpus required')
    def question(self,case='early',family='cold-start'):return read_json(self.root/(family+'-'+case)/'capture-question.json')
    def result(self,case='early',family='cold-start'):return review(self.root,self.question(case,family))
    def test_both_retained_early_captures_support_bounded_comparison(self):
        for f in FAMILIES:
            r=self.result(family=f);self.assertEqual(r['status'],'SUPPORTED_WITHIN_EMULATION');self.assertEqual(r['diagnostic']['report']['evidence_answer'],'present');self.assertFalse(r['question_changed'])
    def test_source_read_time_is_not_later_viewer_time(self):
        r=self.result();s=r['source_observation'];self.assertEqual((s['origin_tick'],s['loaded_tick']),(3,6));self.assertEqual(r['timing']['interval_ns'],[20,20]);self.assertEqual(s['loaded_host_ns']-s['entry_host_ns'],50);self.assertTrue(s['source_ref'].endswith('tick=3') and s['loaded_ref'].endswith('tick=6'))
    def test_zero_after_clearing_reset_does_not_refute_earlier_fault(self):
        for f in FAMILIES:
            r=self.result('late',f);self.assertEqual(r['status'],'INCONCLUSIVE');self.assertFalse(r['source_observation']['cause_bit_set']);self.assertEqual(r['diagnostic']['report']['evidence_answer'],'unknown')
    def test_monitor_can_consume_the_status_before_firmware(self):
        r=self.result('monitor');self.assertEqual(r['diagnostic']['report']['evidence_answer'],'unknown');self.assertFalse(r['source_observation']['cause_bit_set'])
    def test_qualified_present_read_can_still_miss_original_time_window(self):
        r=self.result('monitor','wake-entry');self.assertEqual(r['diagnostic']['report']['evidence_answer'],'present');self.assertEqual(r['source_observation']['origin_tick'],4);self.assertEqual(r['timing']['interval_ns'],[30,30]);self.assertEqual(r['status'],'INCONCLUSIVE')
    def test_fault_free_control_supports_only_observed_prefix_absence(self):
        for f in FAMILIES:
            r=self.result('fault-free',f);self.assertEqual(r['status'],'SUPPORTED_WITHIN_EMULATION');self.assertEqual(r['diagnostic']['report']['evidence_answer'],'absent_in_observed_prefix');self.assertEqual(r['diagnostic']['report']['negative_through_seq'],3)
    def test_matching_bits_do_not_equate_warm_reset_and_por(self):
        r=self.result('wrong-entry');self.assertTrue(r['source_observation']['cause_bit_set']);self.assertEqual(r['status'],'INAPPLICABLE');self.assertTrue(any(v['field']=='reset.entry' and v['status']=='different' for v in r['conditions']))
    def test_alternate_image_can_return_identical_bits_but_be_inapplicable(self):
        r=self.result('wrong-image');self.assertEqual(r['source_observation']['returned_value'],1);self.assertEqual(r['status'],'INAPPLICABLE');self.assertTrue(any(v['field']=='firmware.image_sha256' and v['status']=='different' for v in r['conditions']))
    def test_revision_and_fuses_are_native_model_values_not_expected_labels(self):
        r=self.result('wrong-revision');self.assertEqual(r['status'],'INAPPLICABLE');rows={v['field']:v for v in r['conditions']};self.assertEqual(rows['silicon.revision']['observed']['value'],'B');self.assertEqual(rows['silicon.fuses']['observed']['value'],0)
    def test_wrong_clock_retains_condition_and_time_findings(self):
        r=self.result('wrong-clock');self.assertEqual(r['status'],'INAPPLICABLE');self.assertFalse(r['timing']['entire_interval_within_window']);self.assertTrue(r['findings'] and r['gaps'])
    def test_matching_numeric_anchors_cannot_invent_missing_clock_mapping(self):
        r=self.result('unknown-correlation');self.assertEqual(r['status'],'INCONCLUSIVE');self.assertIsNone(r['timing']);self.assertEqual(r['diagnostic']['report']['evidence_answer'],'present')
    def test_correlated_contrary_observation_is_distinct_from_inconclusive(self):
        q=self.question();q['expected_answer']='absent_in_observed_prefix';r=review(self.root,q);self.assertEqual(r['status'],'CONTRADICTED_WITHIN_EMULATION');self.assertTrue(r['question_changed']);self.assertEqual(r['captured_question']['expected_answer'],'present')
    def test_negative_control_can_contradict_bounded_present_expectation(self):
        q=self.question('fault-free');q['expected_answer']='present';r=review(self.root,q);self.assertEqual(r['status'],'CONTRADICTED_WITHIN_EMULATION')
    def test_partial_interval_overlap_is_not_full_window_correspondence(self):
        q=self.question();q['uncertainty_ns']=1;r=review(self.root,q);self.assertEqual(r['timing']['interval_ns'],[18,22]);self.assertEqual(r['status'],'INCONCLUSIVE')
    def test_existing_receipt_can_answer_a_sourced_new_window_without_rerun(self):
        q=self.question();q['window_ns']=[18,22];q['uncertainty_ns']=.5;q['expectation_ref']='owned/new-question-source';r=review(self.root,q);self.assertEqual(r['status'],'SUPPORTED_WITHIN_EMULATION');self.assertTrue(r['question_changed']);self.assertEqual(r['captured_question']['window_ns'],[19,21])
    def test_missing_window_or_uncertainty_remains_unknown(self):
        for key,value in [('window_ns',[None,21]),('uncertainty_ns',None)]:
            q=self.question();q[key]=value;self.assertEqual(review(self.root,q)['status'],'INCONCLUSIVE')
    def test_nonfinite_or_reversed_window_rejected(self):
        for value in ([float('nan'),21],[22,19]):
            q=self.question();q['window_ns']=value
            with self.assertRaises(ValueError):validate(q)
    def test_missing_owner_keeps_handoff_open(self):
        q=self.question();q['owner_ref']=None;self.assertEqual(review(self.root,q)['status'],'INCONCLUSIVE')
    def test_missing_observation_not_inferred_fault_free(self):
        q=self.question();q['run_ref']=None;r=review(self.root,q);self.assertEqual(r['status'],'INCONCLUSIVE');self.assertIsNone(r['source_observation'])
    def test_foreign_scope_quarantined(self):
        q=self.question();q['scope_ref']='foreign/scope';r=review(self.root,q);self.assertEqual(r['status'],'INAPPLICABLE');self.assertTrue(r['quarantine'])
    def test_stale_source_binding_not_admitted(self):
        q=self.question();q['binding']['sources']['firmware.txt']='0'*64;r=review(self.root,q);self.assertEqual(r['status'],'INAPPLICABLE');self.assertIn('stale_or_foreign_source',{v['code'] for v in r['quarantine']})
    def test_missing_expected_source_keeps_evidence_open(self):
        q=self.question();q['binding']['sources']['device.cpp']=None;self.assertEqual(review(self.root,q)['status'],'INCONCLUSIVE')
    def test_retargeting_epoch_does_not_rewrite_selected_diagnostic_question(self):
        q=self.question('late');q['selection']['target_epoch']=2;r=review(self.root,q);self.assertEqual(r['status'],'INAPPLICABLE');self.assertIn('selection_differs_from_capture',{v['code'] for v in r['findings']})
    def test_required_condition_cannot_be_deleted(self):
        q=self.question();del q['required_conditions']['silicon.fuses']
        with self.assertRaises(ValueError):validate(q)
    def test_unknown_condition_source_not_inferred_from_values(self):
        q=self.question();q['required_conditions']['reset.entry']['evidence_ref']=None;self.assertEqual(review(self.root,q)['status'],'INCONCLUSIVE')
    def test_boolean_and_integer_condition_values_remain_distinct(self):
        q=self.question();q['required_conditions']['board.power_on']['value']=1;self.assertEqual(review(self.root,q)['status'],'INAPPLICABLE')
    def test_stronger_instrument_or_all_mode_claim_remains_open(self):
        q=self.question();q['required_conditions']['instrument.calibration.all_modes']={'value':True,'evidence_ref':'owned/original-stronger-question'};r=review(self.root,q);self.assertEqual(r['status'],'INCONCLUSIVE');self.assertIn('condition_evidence_unknown',{v['code'] for v in r['gaps']})
    def changed(self,name,value):
        ref='cold-start-early'
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/ref;shutil.copytree(self.root/ref,p);(p/name).write_text(value)
            with self.assertRaises(ValueError):load(t,ref)
    def test_modified_original_log_rejected(self):self.changed('native.stdout.txt','OPENTOOLS_BRINGUP_RUN_COMPLETE\n')
    def test_modified_command_image_rejected(self):self.changed('firmware.txt','1 POR\n6 READ\n')
    def test_modified_original_context_rejected(self):self.changed('context.json','{}')
    def test_modified_captured_question_rejected(self):self.changed('capture-question.json','{}')
    def test_missing_native_binary_rejected(self):
        ref='cold-start-early'
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/ref;shutil.copytree(self.root/ref,p);(p/'device').unlink()
            with self.assertRaises(ValueError):load(t,ref)
    def test_all_actual_native_frames_reconstruct_exactly(self):
        for item in self.collection['cases']:
            ref=item['run_ref'];self.assertEqual(load(self.root,ref),read_json(self.root/ref/'evidence.json'))
    def test_review_preserves_input_question(self):
        q=self.question();old=copy.deepcopy(q);review(self.root,q);self.assertEqual(q,old)
    def test_markdown_preserves_owner_origin_and_limits(self):
        s=markdown(self.result());self.assertIn('bringup-owner',s);self.assertIn('origin_tick',s);self.assertIn('No real silicon',s)
    def test_markdown_escapes_source_prose(self):
        q=self.question();q['owner_ref']='<script>x|y</script>';s=markdown(review(self.root,q));self.assertNotIn('<script>',s);self.assertIn('&lt;script&gt;x&#124;y',s)

if __name__=='__main__':unittest.main()
