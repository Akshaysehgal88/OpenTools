"""Source-preserving applicability,efficacy,interaction and approval controls."""
import copy,os,shutil,sys,tempfile,unittest
from pathlib import Path
PROFILE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(PROFILE),str(PROFILE/'examples')]
from erratum_common import digest,read_json,save
from erratum_core import review,markdown,validate_request
from native_erratum import image,load,snapshot
from predicates import evaluate,validate as validate_predicate
from fixture import FAMILIES,notice

def fact(v):return {'value':v,'evidence_ref':'owned/original-field'}
def leaf(field,value):return {'op':'equal','field':field,'value':value,'basis_ref':'owned/original-rule'}
class Predicates(unittest.TestCase):
    def test_all_false_can_decide_with_an_unknown_sibling(self):
        t={'op':'all','terms':[leaf('off',True),leaf('missing',1)],'basis_ref':'owned/relationship'};r=evaluate(t,{'off':fact(False)});self.assertIs(r['truth'],False);self.assertTrue(r['unknown_nodes'])
    def test_any_true_can_decide_with_an_unknown_sibling(self):
        t={'op':'any','terms':[leaf('on',True),leaf('missing',1)],'basis_ref':'owned/relationship'};self.assertIs(evaluate(t,{'on':fact(True)})['truth'],True)
    def test_unknown_does_not_become_false(self):self.assertIsNone(evaluate(leaf('fuse',False),{'fuse':fact(None)})['truth'])
    def test_boolean_and_integer_predicates_remain_distinct(self):self.assertIs(evaluate(leaf('fuse',False),{'fuse':fact(0)})['truth'],False)
    def test_missing_relationship_source_remains_unknown(self):
        t={'op':'all','terms':[leaf('on',True)],'basis_ref':None};self.assertIsNone(evaluate(t,{'on':fact(True)})['truth'])
    def test_code_operator_rejected(self):
        with self.assertRaises(ValueError):validate_predicate({'op':'eval','field':'exec bad','value':1,'basis_ref':'owned'})
    def test_tree_size_and_depth_bounded(self):
        t=leaf('x',1)
        for _ in range(7):t={'op':'all','terms':[t],'basis_ref':'owned'}
        with self.assertRaises(ValueError):validate_predicate(t)
    def test_duplicate_json_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x';p.write_text('{"revision":1,"revision":2}')
            with self.assertRaises(ValueError):read_json(p)
    def test_command_injection_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x';p.write_text('WRITE 42\nISSUE;exec 0\n')
            with self.assertRaises(ValueError):image(p)
    def test_late_baseline_label_cannot_hide_workaround_origin(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x';p.write_text('WRITE 42\nWA_FENCE 0\nBASE_FENCE 0\nISSUE 0\n')
            with self.assertRaises(ValueError):image(p)
    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x';save(p,{'original':True})
            with self.assertRaises(FileExistsError):save(p,{})
            self.assertEqual(read_json(p),{'original':True})

class NativeMaintenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value=os.environ.get('OPENTOOLS_ERRATUM_NATIVE')
        if not value:raise unittest.SkipTest('Set OPENTOOLS_ERRATUM_NATIVE to actual run_native.py output')
        cls.root=Path(value);cls.collection=read_json(cls.root/'collection.json')
        if cls.collection['native_executions']!=24:raise ValueError('Complete actual24-run corpus required')
    def inputs(self,case='affected-mitigated',family='ordering-boundary'):
        folder=self.root/(family+'-'+case);return read_json(folder/'capture-notice.json'),read_json(folder/'capture-request.json')
    def result(self,case='affected-mitigated',family='ordering-boundary'):
        n,q=self.inputs(case,family);return review(self.root,n,q)
    def variant(self,variant,family='ordering-boundary'):
        n,_=self.inputs(family=family);q=read_json(self.root/'requests'/(family+'-'+variant+'.json'));return review(self.root,n,q)
    def test_passing_workaround_does_not_erase_underlying_applicability(self):
        for family in FAMILIES:
            r=self.result(family=family);self.assertEqual(r['status'],'REVIEW_PACKET_ACCOUNTED');self.assertIs(r['applicability']['truth'],True);self.assertEqual(r['native_result']['outcome'],'pass');self.assertTrue(r['mitigation']['effective_within_selected_model'])
    def test_base_and_workaround_ordering_are_distinct_observations(self):
        r=self.result();o=r['implementation_observation'];self.assertFalse(o['firmware.base_ordered']['value']);self.assertTrue(o['firmware.wa_ordered']['value'])
    def test_fixed_stepping_can_still_use_vulnerable_firmware_path(self):
        r=self.result('fixed-base-vulnerable');self.assertIs(r['applicability']['truth'],True);self.assertEqual(r['native_result']['outcome'],'fail');self.assertIn('observed_delivery_check_failure',{v['code'] for v in r['findings']})
    def test_unaffected_requires_full_selected_conditions(self):
        for family in FAMILIES:
            for case in ('unaffected','fuse-repaired','normal-mode','feature-disabled'):
                r=self.result(case,family);self.assertIs(r['applicability']['truth'],False);self.assertEqual(r['status'],'REVIEW_PACKET_ACCOUNTED')
    def test_unknown_fuse_not_inferred_from_private_oracle_or_green_result(self):
        r=self.result('unknown-fuse');e=load(self.root,'ordering-boundary-unknown-fuse');self.assertEqual(r['native_result']['outcome'],'pass');self.assertIsNone(snapshot(e)['fields']['silicon.repair_fuse']['value']);self.assertIsNone(r['applicability']['truth']);self.assertEqual(r['status'],'INCOMPLETE')
    def test_disabled_feature_can_decide_scope_while_retaining_unknown_fuse(self):
        r=self.result('feature-disabled-unknown-fuse');self.assertIs(r['applicability']['truth'],False);self.assertTrue(r['applicability']['unknown_nodes']);self.assertEqual(r['status'],'REVIEW_PACKET_ACCOUNTED')
    def test_primary_pass_does_not_keep_dependent_clock_premise_valid(self):
        r=self.result('interaction-conflict');self.assertEqual(r['native_result']['outcome'],'pass');self.assertTrue(r['mitigation']['effective_within_selected_model']);self.assertEqual(r['interaction']['state'],'premise_false');self.assertIn('workaround_invalidates_dependent_premise',{v['code'] for v in r['findings']})
    def test_inactive_exception_does_not_claim_power_verification(self):
        r=self.result();self.assertEqual(r['interaction']['state'],'not_enabled_in_selected_context');self.assertIn('No unpublished-erratum',r['limits'])
    def test_same_ported_guard_passes_one_context_and_fails_the_other(self):
        a=self.result('ported-guard','ordering-boundary');b=self.result('ported-guard','reset-boundary');self.assertEqual(a['implementation_observation']['workaround.guard_ticks']['value'],2);self.assertEqual(b['implementation_observation']['workaround.guard_ticks']['value'],2);self.assertEqual((a['native_result']['outcome'],b['native_result']['outcome']),('pass','fail'));self.assertFalse(b['mitigation']['guard_corresponds'])
    def test_clock_duration_is_observed_in_actual_tick_trace(self):
        for family,need in FAMILIES.items():
            e=load(self.root,family+'-affected-mitigated');self.assertEqual(len(e['native']['ticks']),need);self.assertEqual(e['native']['result']['active_ticks'],need);self.assertTrue(all(v[1]==1 for v in e['native']['ticks']))
    def test_enabled_fences_and_clock_do_not_make_short_guard_sufficient(self):
        r=self.result('too-short-guard');self.assertTrue(r['implementation_observation']['firmware.wa_ordered']['value']);self.assertTrue(r['implementation_observation']['workaround.force_clock']['value']);self.assertFalse(r['mitigation']['guard_corresponds']);self.assertEqual(r['native_result']['outcome'],'fail')
    def test_missing_current_approval_does_not_fall_back_to_captured_approval(self):
        r=self.variant('approval-missing');self.assertEqual(r['supplied_approval']['state'],'missing');self.assertEqual(r['status'],'INCOMPLETE');self.assertEqual(r['captured_sources']['request']['approval']['status'],'approved')
    def test_pending_withdrawn_and_stale_approval_are_distinct(self):
        self.assertEqual(self.variant('approval-pending')['supplied_approval']['state'],'unresolved');self.assertEqual(self.variant('approval-withdrawn')['supplied_approval']['state'],'does_not_correspond');self.assertIn('cut_ref',self.variant('approval-stale')['supplied_approval']['mismatched_fields'])
    def test_approval_binds_notice_image_mode_scope_and_intent(self):
        for key in ('notice_sha256','image_sha256','mode_ref','scope_ref','intent'):
            n,q=self.inputs();q['approval'][key]='foreign';r=review(self.root,n,q);self.assertIn(key,r['supplied_approval']['mismatched_fields']);self.assertEqual(r['status'],'REVIEW_REQUIRED')
    def test_matching_supplied_removal_record_does_not_override_affected_condition(self):
        r=self.variant('remove-affected');self.assertEqual(r['supplied_approval']['state'],'supplied_record_corresponds');self.assertIn('removal_conditions_not_established',{v['code'] for v in r['findings']});self.assertEqual(r['status'],'REVIEW_REQUIRED')
    def test_stronger_physical_all_mode_question_stays_open(self):
        r=self.variant('stronger-claim');self.assertEqual(r['status'],'INCOMPLETE');self.assertIs(r['applicability']['truth'],True);self.assertTrue(r['source_comparison']['unknowns'])
    def test_notice_version_must_match_independently_requested_source(self):
        n,q=self.inputs();n['revision']='changed';r=review(self.root,n,q);self.assertEqual(r['status'],'INAPPLICABLE_EVIDENCE');self.assertIn('notice_not_requested',{v['code'] for v in r['quarantine']})
    def test_new_sourced_notice_can_reuse_retained_model_facts(self):
        n,q=self.inputs();n['revision']='2';n['source_ref']='owned/new-notice-source';q['notice_sha256']=q['approval']['notice_sha256']=digest(n);q['approval']['source_ref']='owned/new-supplied-decision';r=review(self.root,n,q);self.assertTrue(r['notice_changed']);self.assertEqual(r['captured_sources']['notice']['revision'],'1');self.assertEqual(r['status'],'REVIEW_PACKET_ACCOUNTED')
    def test_unknown_predicate_source_is_preserved_even_with_other_findings(self):
        n,q=self.inputs();n['predicate']['basis_ref']=None;q['notice_sha256']=digest(n);r=review(self.root,n,q);self.assertIsNone(r['applicability']['truth']);self.assertIn('applicability_unresolved',{v['code'] for v in r['gaps']})
    def test_foreign_context_not_composed(self):
        n,q=self.inputs();q['binding']['identity']['configuration_ref']='foreign';r=review(self.root,n,q);self.assertEqual(r['status'],'INAPPLICABLE_EVIDENCE');self.assertIsNone(r['applicability'])
    def test_wrong_notice_profile_does_not_borrow_another_guard_budget(self):
        n,q=self.inputs();q['notice_profile']='reset-boundary';r=review(self.root,n,q);self.assertEqual(r['status'],'INAPPLICABLE_EVIDENCE');self.assertIn('foreign_notice_scope',{v['code'] for v in r['quarantine']})
    def test_stale_expected_image_binding_quarantined(self):
        n,q=self.inputs();q['binding']['sources']['firmware.txt']='0'*64;r=review(self.root,n,q);self.assertIn('stale_or_foreign_source',{v['code'] for v in r['quarantine']})
    def test_missing_expected_source_not_invented_from_observed_source(self):
        n,q=self.inputs();q['binding']['sources']['device.cpp']=None;self.assertEqual(review(self.root,n,q)['status'],'INCOMPLETE')
    def test_missing_native_packet_not_inferred_unaffected(self):
        n,q=self.inputs();q['run_ref']=None;r=review(self.root,n,q);self.assertEqual(r['status'],'INCOMPLETE');self.assertIsNone(r['applicability'])
    def test_missing_review_owner_keeps_handoff_open(self):
        n,q=self.inputs();q['owner_ref']=None;self.assertEqual(review(self.root,n,q)['status'],'INCOMPLETE')
    def test_required_model_field_cannot_be_dropped(self):
        _,q=self.inputs();del q['required_fields']['native.guard_need']
        with self.assertRaises(ValueError):validate_request(q)
    def changed(self,name,value):
        ref='ordering-boundary-affected-mitigated'
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/ref;shutil.copytree(self.root/ref,p);(p/name).write_text(value)
            with self.assertRaises(ValueError):load(t,ref)
    def test_changed_native_log_rejected(self):self.changed('native.stdout.txt','OPENTOOLS_ERRATUM_RUN_COMPLETE\n')
    def test_changed_executed_image_rejected(self):self.changed('firmware.txt','WRITE 42\nISSUE 0\n')
    def test_changed_original_context_rejected(self):self.changed('context.json','{}')
    def test_changed_captured_notice_rejected(self):self.changed('capture-notice.json','{}')
    def test_changed_captured_approval_request_rejected(self):self.changed('capture-request.json','{}')
    def test_missing_native_binary_rejected(self):
        ref='ordering-boundary-affected-mitigated'
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/ref;shutil.copytree(self.root/ref,p);(p/'device').unlink()
            with self.assertRaises(ValueError):load(t,ref)
    def test_all_actual_frames_and_snapshots_reconstruct_exactly(self):
        for i in self.collection['cases']:
            ref=i['run_ref'];e=load(self.root,ref);self.assertEqual(e,read_json(self.root/ref/'evidence.json'));self.assertEqual(snapshot(e),read_json(self.root/ref/'snapshot.json'))
    def test_review_preserves_original_source_inputs(self):
        n,q=self.inputs();old=copy.deepcopy((n,q));review(self.root,n,q);self.assertEqual((n,q),old)
    def test_markdown_preserves_failed_outcome_owner_and_limits(self):
        r=self.result('affected-unmitigated');s=markdown(r);self.assertIn('OWNED_SELECTED_DELIVERY_CHECK FAIL',s);self.assertIn('maintenance-owner',s);self.assertIn('automatic workaround application/removal',s)
    def test_markdown_escapes_supplied_text(self):
        n,q=self.inputs();q['owner_ref']='<script>x|y</script>';s=markdown(review(self.root,n,q));self.assertNotIn('<script>',s);self.assertIn('&lt;script&gt;x&#124;y',s)

if __name__=='__main__':unittest.main()
