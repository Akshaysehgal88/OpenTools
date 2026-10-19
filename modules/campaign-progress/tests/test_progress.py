import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from progress_core import review,range_union,fingerprint,read_json,markdown
spec=importlib.util.spec_from_file_location('campaign_example',ROOT/'examples/create_example.py')
example=importlib.util.module_from_spec(spec);spec.loader.exec_module(example)


class ProgressTests(unittest.TestCase):
    def setUp(self):self.c,self.a,self.b=example.example()
    def check(self):return review(self.c,self.a,self.b)
    def current(self,report,key):return next(v for v in report['after']['objectives'] if v['id']==key)
    def delta(self,report,key):return next(v for v in report['objective_changes'] if v['id']==key)

    def test_plateau_does_not_complete_stress_or_required_population(self):
        value=self.check()
        self.assertEqual(value['status'],'recorded_progress')
        self.assertEqual(self.delta(value,'coverage')['newly_attained_goal_ids'],[])
        self.assertEqual(self.delta(value,'stress')['known_value_delta'],64)
        self.assertEqual(self.current(value,'stress')['remaining'],64)
        self.assertEqual(value['after']['remaining_required_run_refs'],['c'])
        self.assertFalse(value['all_recorded_targets_attained'])
        self.assertEqual(value['release_completeness'],'not_established')

    def test_current_cumulative_total_is_not_before_plus_after(self):
        self.assertEqual(self.current(self.check(),'stress')['known_value'],128)

    def test_repeated_event_ranges_count_once(self):
        self.b['runs'][1]['measurements'][1]['data']['ranges'][0]['space_ref']='synthetic:events:a'
        value=self.check()
        self.assertEqual(self.current(value,'stress')['known_value'],64)
        self.assertEqual(self.delta(value,'stress')['known_value_delta'],0)
        self.assertTrue(value['after']['warnings'])

    def test_overlap_union_and_empty_ranges(self):
        values=[{'space_ref':'x','start':0,'stop':10},{'space_ref':'x','start':5,'stop':15},{'space_ref':'y','start':0,'stop':2}]
        self.assertEqual(range_union(values),(17,True))
        self.assertEqual(range_union([{'space_ref':'x','start':1,'stop':1}]),(0,False))

    def test_long_wall_or_many_seeds_do_not_create_effective_exposure(self):
        for snapshot in (self.a,self.b):
            for run in snapshot['runs']:
                if run['state']=='passed':
                    run['measurements'][1]['data']['ranges']=[]
                    run['resources']=[{'metric':'wall','value':'1000000','unit':'s','definition_ref':'synthetic:process wall','basis':'measured','evidence_ref':'synthetic:timer'}]
        value=self.check()
        self.assertEqual(self.current(value,'stress')['known_value'],0)
        self.assertFalse(self.current(value,'stress')['recorded_target_attained'])

    def test_missing_effective_counter_is_unknown_not_zero_progress(self):
        self.b['runs'][1]['measurements'].pop()
        value=self.check()
        self.assertEqual(value['status'],'needs_context')
        self.assertEqual(self.current(value,'stress')['known_value'],64)
        self.assertIsNone(self.delta(value,'stress')['known_value_delta'])

    def test_changed_coverage_denominator_does_not_imply_new_hits(self):
        measurement=self.b['runs'][1]['measurements'][0]
        measurement['data']['population_ids']=['bin0','bin1','bin2']
        value=self.check()
        self.assertEqual(value['status'],'needs_context')
        self.assertIsNone(self.delta(value,'coverage')['newly_attained_goal_ids'])
        self.assertEqual(self.current(value,'coverage')['remaining'],['bin3'])

    def test_same_bin_names_with_changed_definition_are_not_comparable(self):
        self.b['runs'][1]['measurements'][0]['basis_ref']='synthetic:changed goal thresholds'
        self.assertIsNone(self.delta(self.check(),'coverage')['known_value_delta'])

    def test_changed_configuration_is_not_pooled(self):
        self.b['runs'][1]['configuration_ref']='synthetic:config-B'
        value=self.check()
        self.assertEqual(value['status'],'review_required')
        self.assertEqual(self.current(value,'stress')['known_value'],64)
        self.assertIsNone(self.delta(value,'stress')['known_value_delta'])
        self.assertEqual(value['after']['runs'][1]['configuration_ref'],'synthetic:config-B')

    def test_changed_model_is_not_pooled(self):
        self.b['runs'][1]['model_ref']='other-model'
        self.assertEqual(self.current(self.check(),'stress')['known_value'],64)

    def test_failed_prefix_is_retained_but_not_counted_without_policy(self):
        self.b['runs'][1].update(state='failed',native_state='CHECKER_FAIL')
        value=self.check()
        self.assertEqual(value['status'],'execution_findings')
        self.assertEqual(self.current(value,'stress')['known_value'],64)
        self.assertTrue(value['after']['runs'][1]['measurements'])

    def test_explicit_policy_can_count_qualified_failed_prefix_without_passing_run(self):
        self.c['objectives'][2]['eligible_states'].append('failed')
        self.b['runs'][1].update(state='failed',native_state='CHECKER_FAIL')
        value=self.check()
        self.assertEqual(self.current(value,'stress')['known_value'],128)
        self.assertIn('b',value['after']['remaining_required_run_refs'])

    def test_aborted_queued_and_unknown_states_remain_distinct(self):
        self.b['runs'][1].update(state='aborted',native_state='KILLED')
        self.b['runs'][2].update(state='queued',native_state='WAITING')
        value=self.check();self.assertEqual(value['after']['state_counts']['aborted'],1)
        self.assertEqual(value['after']['state_counts']['queued'],1)
        self.b['runs'][2].update(state='unknown',native_state='NO_STATE_EXPORT')
        self.assertEqual(self.check()['after']['state_counts']['unknown'],1)

    def test_queue_entry_cannot_claim_executed_effective_measurements(self):
        self.b['runs'][1].update(state='queued',native_state='WAITING')
        self.assertEqual(self.check()['status'],'review_required')

    def test_missing_run_is_not_a_pass_or_assumed_not_run(self):
        self.b['runs'].pop();self.b['complete']=False
        value=self.check()
        self.assertIn('c',value['after']['remaining_required_run_refs'])
        self.assertEqual(value['after']['required_population'][-1]['state'],'record_absent')
        self.assertEqual(value['status'],'needs_context')

    def test_falsely_complete_export_does_not_erase_known_measurements(self):
        self.b['runs'].pop()
        value=self.check()
        self.assertEqual(value['status'],'review_required')
        self.assertEqual(self.current(value,'stress')['known_value'],128)

    def test_disappearing_cumulative_extra_execution_stays_visible(self):
        extra=copy.deepcopy(self.a['runs'][0]);extra['run_ref']='extra';self.a['runs'].append(extra)
        value=self.check()
        self.assertEqual(value['removed_run_refs'],['extra'])
        self.assertIsNone(self.delta(value,'stress')['known_value_delta'])

    def test_terminal_execution_cannot_be_replaced_by_passing_retry(self):
        self.a['runs'][0].update(state='failed',native_state='CHECKER_FAIL')
        value=self.check()
        self.assertEqual(value['changed_terminal_run_refs'],['a'])
        self.assertEqual(value['status'],'review_required')

    def test_zero_exposure_target_is_a_declared_zero_not_statistical_assurance(self):
        self.c['objectives'][2]['target']['value']=0
        self.assertTrue(self.current(self.check(),'stress')['recorded_target_attained'])
        self.assertEqual(self.check()['release_completeness'],'not_established')

    def test_empty_population_and_missing_policy_do_not_establish_completion(self):
        self.c['population_complete']=None;self.c['policy']['evidence_ref']=None
        self.assertEqual(self.check()['status'],'needs_context')
        self.assertFalse(self.check()['all_recorded_targets_attained'])

    def test_manual_statistical_objective_requires_separate_qualified_method(self):
        self.c['objectives'].append({'id':'reliability','kind':'manual','description':'Rare event assurance','basis_ref':'synthetic:unqualified model',
            'policy_ref':'synthetic:required model review','eligible_states':[],'target':'Justified statistical model and effective exposure.'})
        value=self.check()
        self.assertEqual(value['status'],'needs_context')
        self.assertIsNone(self.current(value,'reliability')['known_value'])

    def test_no_timestamps_means_no_comparable_review_interval(self):
        self.b['captured_at']=None
        self.assertIsNone(self.delta(self.check(),'stress')['known_value_delta'])

    def test_reversed_interval_requires_review(self):
        self.b['captured_at']=self.a['captured_at']
        self.assertEqual(self.check()['status'],'review_required')

    def test_unknown_event_identity_cannot_be_counted(self):
        self.b['runs'][1]['measurements'][1]['data']['ranges'][0]['space_ref']=None
        value=self.check()
        self.assertEqual(self.current(value,'stress')['known_value'],64)
        self.assertEqual(value['status'],'needs_context')

    def test_mismatched_exposure_unit_does_not_convert_wall_to_transactions(self):
        self.b['runs'][1]['measurements'][1]['data']['unit']='seconds'
        self.assertEqual(self.current(self.check(),'stress')['known_value'],64)

    def test_resource_origin_missing_is_visible(self):
        self.b['runs'][1]['resources']=[{'metric':'cpu','value':'8','unit':'s','definition_ref':None,'basis':'measured','evidence_ref':None}]
        self.assertEqual(self.check()['status'],'needs_context')

    def test_foreign_snapshot_failures_are_retained_but_not_applied(self):
        self.b['campaign_ref']='foreign-campaign';self.b['runs'][1]['state']='failed'
        value=self.check()
        self.assertEqual(value['current_failed_or_aborted_run_refs'],[])
        self.assertEqual(value['after']['runs'][1]['state'],'failed')

    def test_inputs_are_never_mutated(self):
        before=copy.deepcopy((self.c,self.a,self.b));self.check();self.assertEqual(before,(self.c,self.a,self.b))

    def test_execution_policy_cannot_treat_failed_runs_as_passes(self):
        self.c['objectives'][0]['eligible_states']=['failed']
        with self.assertRaises(ValueError):self.check()

    def test_empty_eligible_state_policy_is_a_visible_gap(self):
        self.c['objectives'][1]['eligible_states']=[]
        self.assertEqual(self.check()['status'],'needs_context')

    def test_all_recorded_targets_still_do_not_establish_release(self):
        third=copy.deepcopy(self.b['runs'][1]);third.update(run_ref='c',evidence_ref='synthetic:c actual checker')
        third['measurements'][0]['data']['hit_ids'].append('bin3')
        third['measurements'][1]['data']['ranges'][0]['space_ref']='synthetic:events:c'
        self.b['runs'][2]=third
        value=self.check()
        self.assertTrue(value['all_recorded_targets_attained'])
        self.assertEqual(value['release_completeness'],'not_established')

    def test_favorable_shape_does_not_factcheck_a_false_effective_counter_claim(self):
        self.b['runs'][1]['measurements'][1]['data']['ranges'][0]['stop']=1000000
        value=self.check()
        self.assertEqual(value['status'],'recorded_progress')
        self.assertTrue(self.current(value,'stress')['recorded_target_attained'])

    def test_duplicate_json_and_duplicate_run_ids_reject(self):
        self.b['runs'].append(copy.deepcopy(self.b['runs'][0]))
        with self.assertRaises(ValueError):self.check()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'bad.json'
            for value in ('{"a":1,"a":2}','{"a":NaN}'):
                path.write_text(value,encoding='utf-8')
                with self.assertRaises(ValueError):read_json(path)

    def test_cli_utf8_json_markdown_and_existing_output_preservation(self):
        self.c['objectives'][0]['description']='事务 execution'
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);args=[sys.executable,str(ROOT/'campaign_progress.py'),'summarize']
            for key,value in zip(('contract','before','after'),(self.c,self.a,self.b)):
                path=out/(key+'.json');path.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8');args.append(str(path))
            report=out/'report.json';human=out/'report.md';args+=['--output',str(report),'--markdown',str(human)]
            run=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',env=dict(os.environ,PYTHONIOENCODING='ascii'))
            self.assertEqual(run.returncode,0,run.stderr)
            value=json.loads(run.stdout);self.assertEqual(value['contract']['objectives'][0]['description'],'事务 execution')
            self.assertIn('| stress | 64 | 128 | 192 | 64 |',human.read_text(encoding='utf-8'))
            prior=report.read_bytes();again=subprocess.run(args,capture_output=True)
            self.assertEqual(again.returncode,3);self.assertEqual(report.read_bytes(),prior)
            digest=subprocess.run([sys.executable,str(ROOT/'campaign_progress.py'),'digest',str(out/'contract.json')],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(json.loads(digest.stdout)['canonical_sha256'],fingerprint(self.c))


if __name__=='__main__':unittest.main()
