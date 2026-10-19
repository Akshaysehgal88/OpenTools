import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from selection_core import plan,feedback,fingerprint,read_json
spec=importlib.util.spec_from_file_location('regression_example',ROOT/'examples/create_example.py')
example_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(example_module)


class SelectionTests(unittest.TestCase):
    def setUp(self):self.u,self.c,self.m,self.p,self.r,self.full=example_module.example()
    def rebind(self):
        self.m.update(universe_sha256=fingerprint(self.u),change_sha256=fingerprint(self.c))
        self.p['universe_sha256']=fingerprint(self.u)
    def bind_results(self,value):
        value.update(universe_sha256=fingerprint(self.u),change_sha256=fingerprint(self.c),scope_ref=self.u['scope_ref'],
            selection_sha256=fingerprint(plan(self.u,self.c,self.m,self.p)) if value['kind']=='targeted' else None)
    def select(self):return plan(self.u,self.c,self.m,self.p)
    def review(self,full=None):return feedback(self.u,self.c,self.m,self.p,self.r,full)

    def test_full_independent_denominator_and_required_omission_retained(self):
        value=self.select()
        self.assertEqual(value['selected_ids'],['soc_smoke','dma_directed','fabric_integration'])
        self.assertEqual(value['deferred_ids'],['soc_stress'])
        self.assertEqual(len(value['population']),4)
        self.assertIn('soc_stress',value['remaining_required_ids'])
        self.assertTrue(all(v['execution']=='not_executed' for v in value['population']))
        self.assertEqual(value['release_completeness'],'not_established')

    def test_selected_does_not_mean_executed(self):
        self.r['attempts']=[];self.r['complete']=False
        value=self.review()
        self.assertEqual(value['status'],'needs_context')
        self.assertEqual(value['selected_pass_ids'],[])
        self.assertEqual(len(value['remaining_required_ids']),4)

    def test_targeted_pass_keeps_omitted_required_test(self):
        value=self.review()
        self.assertEqual(value['status'],'recorded_feedback')
        self.assertEqual(value['remaining_required_ids'],['soc_stress'])
        self.assertEqual(value['release_completeness'],'not_established')

    def test_full_campaign_exposes_failure_outside_selection(self):
        value=self.review(self.full)
        self.assertEqual(value['status'],'failures_observed')
        self.assertEqual(value['failures_outside_selection'],['soc_stress'])
        self.assertEqual(value['remaining_required_ids'],['soc_stress'])

    def test_all_full_passes_do_not_assert_release(self):
        self.full['attempts'][-1]['state']='pass'
        value=self.review(self.full)
        self.assertEqual(value['remaining_required_ids'],[])
        self.assertEqual(value['release_completeness'],'not_established')

    def test_shared_package_category_broadens_independent_population(self):
        self.c['items'][0]['category']='shared';self.rebind()
        self.assertEqual(self.select()['selected_ids'],[v['id'] for v in self.u['tests']])

    def test_configuration_and_toolchain_categories_broaden(self):
        for category in ('configuration','toolchain','generator'):
            with self.subTest(category=category):
                self.c['items'][0]['category']=category;self.rebind()
                self.assertEqual(len(self.select()['selected_ids']),4)

    def test_unknown_dependency_broadens(self):
        self.m['entries']=[]
        value=self.select()
        self.assertEqual(len(value['selected_ids']),4)
        self.assertEqual(value['impact_gaps'][0]['resolution'],'all_known_tests_selected')

    def test_unknown_dependency_can_remain_explicit_gap(self):
        self.p['unknown_impact']='record_gap';self.m['entries']=[]
        value=self.select()
        self.assertEqual(value['status'],'needs_context')
        self.assertEqual(value['impact_gaps'][0]['resolution'],'unresolved')
        self.assertIn('dma_directed',value['unselected_ids'])

    def test_incomplete_change_inventory_broadens(self):
        self.c['complete']=False;self.rebind()
        self.assertEqual(len(self.select()['selected_ids']),4)

    def test_incomplete_universe_cannot_be_repaired_by_all_known_tests(self):
        self.u['complete']=False;self.rebind();self.m['entries']=[]
        value=self.select()
        self.assertEqual(len(value['selected_ids']),4)
        self.assertEqual(value['status'],'needs_context')

    def test_stale_mapping_is_not_trusted_even_if_test_names_match(self):
        self.c['revision_ref']='synthetic:rev-C';self.u['revision_ref']='synthetic:rev-C'
        self.p['universe_sha256']=fingerprint(self.u)
        value=self.select()
        self.assertEqual(value['status'],'review_required')
        self.assertEqual(len(value['selected_ids']),4)

    def test_mapping_claim_does_not_prove_semantic_adequacy(self):
        self.m['entries'][0]['test_ids']=[]
        self.assertEqual(self.select()['status'],'advisory_selection')
        self.assertNotIn('dma_directed',self.select()['selected_ids'])

    def test_renamed_test_is_not_fuzzily_mapped(self):
        self.u['tests'][1]['id']='dma_directed_v2';self.rebind()
        value=self.select()
        self.assertEqual(value['status'],'review_required')
        self.assertIn('dma_directed_v2',value['selected_ids'])
        self.assertTrue(any('renamed' in v for v in value['conflicts']))

    def test_nonexistent_policy_test_is_not_silently_dropped(self):
        self.p['mandatory_ids'].append('invented_test')
        self.assertEqual(self.select()['status'],'review_required')

    def test_missing_mapping_change_id_is_visible(self):
        self.m['entries'][0]['change_id']='other-change'
        value=self.select()
        self.assertEqual(value['status'],'review_required')
        self.assertEqual(len(value['selected_ids']),4)

    def test_mandatory_test_cannot_be_removed_through_deferral(self):
        self.p['defer_ids'].append('fabric_integration')
        value=self.select()
        self.assertIn('fabric_integration',value['selected_ids'])
        self.assertTrue(value['warnings'])

    def test_unavailable_selected_test_remains_an_obligation(self):
        self.u['tests'][1]['available']=False;self.rebind()
        value=self.select()
        self.assertEqual(value['status'],'needs_context')
        self.assertIn('dma_directed',value['selected_ids'])
        self.assertIn('dma_directed',value['unavailable_ids'])
        self.assertIn('dma_directed',value['remaining_required_ids'])

    def test_unknown_availability_remains_distinct(self):
        self.u['tests'][1]['available']=None;self.rebind()
        self.assertIn('dma_directed',self.select()['availability_unknown_ids'])

    def test_foreign_scope_broadens_but_still_requires_review(self):
        self.m['scope_ref']='other-config'
        value=self.select()
        self.assertEqual(value['status'],'review_required')
        self.assertEqual(len(value['selected_ids']),4)

    def test_source_identity_and_configuration_cannot_be_filled_by_name(self):
        self.u['tests'][1]['configuration_ref']=None;self.rebind()
        self.assertEqual(self.select()['status'],'needs_context')

    def test_empty_universe_cannot_claim_complete_selection(self):
        self.u['tests']=[];self.m['entries']=[]
        self.p.update(mandatory_ids=[],required_ids=[],defer_ids=[]);self.rebind()
        self.assertEqual(self.select()['status'],'needs_context')

    def test_targeted_results_bind_exact_selection(self):
        self.p['mandatory_ids'].append('soc_stress')
        value=self.review()
        self.assertEqual(value['status'],'review_required')
        self.assertEqual(value['selected_pass_ids'],[])

    def test_foreign_full_revision_is_retained_but_not_applied(self):
        self.full['change_sha256']='foreign-change'
        value=self.review(self.full)
        self.assertEqual(value['status'],'review_required')
        self.assertEqual(value['failures_outside_selection'],[])
        self.assertEqual(value['campaigns'][1]['attempts'][-1]['state'],'fail')

    def test_incomplete_full_population_keeps_matching_actual_failure(self):
        self.full['attempts'].pop(0)
        value=self.review(self.full)
        self.assertEqual(value['status'],'review_required')
        self.assertEqual(value['failures_outside_selection'],['soc_stress'])

    def test_error_is_not_a_hardware_failure_or_pass(self):
        self.full['attempts'][-1]['state']='error'
        value=self.review(self.full)
        self.assertEqual(value['failures_outside_selection'],[])
        self.assertEqual(value['errors_outside_selection'],['soc_stress'])
        self.assertIn('soc_stress',value['remaining_required_ids'])

    def test_retry_pass_does_not_erase_failure(self):
        extra=copy.deepcopy(self.r['attempts'][1]);extra.update(attempt_ref='retry-original-failed',state='fail')
        self.r['attempts'].insert(0,extra)
        value=self.review()
        self.assertIn('dma_directed',value['failed_ids'])
        self.assertIn('dma_directed',value['mixed_attempt_ids'])
        self.assertNotIn('dma_directed',value['selected_pass_ids'])

    def test_skipped_and_not_run_do_not_count_as_pass(self):
        for state in ('skipped','not_run'):
            with self.subTest(state=state):
                self.r['attempts'][1].update(state=state,run_ref=None)
                self.assertNotIn('dma_directed',self.review()['selected_pass_ids'])

    def test_missing_source_cannot_apply_claimed_pass(self):
        self.r['attempts'][1]['evidence_ref']=None
        value=self.review()
        self.assertEqual(value['status'],'needs_context')
        self.assertNotIn('dma_directed',value['selected_pass_ids'])

    def test_a_targeted_packet_is_not_full_comparison(self):
        self.assertEqual(self.review(self.r)['status'],'review_required')

    def test_original_inputs_never_mutated(self):
        values=copy.deepcopy((self.u,self.c,self.m,self.p,self.r,self.full))
        self.review(self.full)
        self.assertEqual(values,(self.u,self.c,self.m,self.p,self.r,self.full))

    def test_duplicate_ids_and_nonfinite_or_duplicate_json_rejected(self):
        self.u['tests'].append(copy.deepcopy(self.u['tests'][0]))
        with self.assertRaises(ValueError):self.select()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'bad.json'
            for value in ('{"a":1,"a":2}','{"value":NaN}'):
                path.write_text(value,encoding='utf-8')
                with self.assertRaises(ValueError):read_json(path)

    def test_cli_preserves_existing_report_and_utf8_console(self):
        self.u['tests'][0]['name']='事务 smoke';self.rebind()
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);args=[sys.executable,str(ROOT/'regression_select.py'),'plan']
            for key,value in zip(('universe','changes','mapping','policy'),(self.u,self.c,self.m,self.p)):
                path=out/(key+'.json');path.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8');args+=['--'+key,str(path)]
            target=out/'report.json';args+=['--output',str(target)]
            env=dict(os.environ,PYTHONIOENCODING='ascii')
            run=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',env=env)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(json.loads(run.stdout)['population'][0]['name'],'事务 smoke')
            before=target.read_bytes();again=subprocess.run(args,capture_output=True)
            self.assertEqual(again.returncode,3);self.assertEqual(target.read_bytes(),before)

    def test_cli_digest_and_review_expose_missed_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);args=[sys.executable,str(ROOT/'regression_select.py'),'review']
            for key,value in zip(('universe','changes','mapping','policy','results','full-results'),(self.u,self.c,self.m,self.p,self.r,self.full)):
                path=out/(key+'.json');path.write_text(json.dumps(value),encoding='utf-8');args+=['--'+key,str(path)]
            run=subprocess.run(args,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(run.returncode,1,run.stderr)
            self.assertEqual(json.loads(run.stdout)['failures_outside_selection'],['soc_stress'])
            digest=subprocess.run([sys.executable,str(ROOT/'regression_select.py'),'digest',str(out/'universe.json')],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(digest.returncode,0,digest.stderr)
            self.assertEqual(json.loads(digest.stdout)['canonical_sha256'],fingerprint(self.u))


if __name__=='__main__':unittest.main()
