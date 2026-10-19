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
from experiment_core import audit,review_result,fingerprint,read_json,validate_plan
spec=importlib.util.spec_from_file_location('experiment_example',ROOT/'examples/create_example.py')
example_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(example_module)


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.p,self.r,self.replay,self.unexecuted=example_module.example()

    def bind(self):self.r['plan_sha256']=fingerprint(self.p)

    def test_inspect_existing_route_is_not_a_new_run(self):
        report=review_result(self.p,self.r)
        self.assertEqual(report['status'],'recorded_outcome')
        self.assertFalse(report['execution']['attempted'])
        self.assertEqual(report['selected_outcome']['id'],'accepted_unfinished')

    def test_planned_run_has_no_actual_result(self):
        self.assertEqual(audit(self.replay)['status'],'structured_plan')
        self.assertEqual(review_result(self.replay,self.unexecuted)['status'],'not_executed')

    def test_unexecuted_record_cannot_claim_normal_outcome(self):
        self.unexecuted['outcome_id']='accepted_unfinished'
        self.assertEqual(review_result(self.replay,self.unexecuted)['status'],'review_required')

    def test_unknown_plan_binding_is_missing_not_foreign(self):
        self.r['plan_sha256']=None
        self.assertEqual(review_result(self.p,self.r)['status'],'needs_context')

    def test_original_plan_cannot_be_rewritten_after_result(self):
        self.p['hypotheses'][0]['statement']='A retrospective different explanation.'
        self.assertEqual(review_result(self.p,self.r)['status'],'review_required')

    def test_outcome_and_state_cannot_conflict(self):
        self.r['state']='inconclusive'
        self.assertEqual(review_result(self.p,self.r)['status'],'review_required')

    def test_missing_window_is_inconclusive_not_nonacceptance(self):
        self.r.update(state='inconclusive',outcome_id='insufficient')
        self.r['observations'][1].update(value=None,complete=False)
        self.assertEqual(review_result(self.p,self.r)['status'],'inconclusive')

    def test_normal_outcome_requires_complete_source_evidence(self):
        self.r['observations'][0]['complete']=False
        self.assertEqual(review_result(self.p,self.r)['status'],'needs_context')
        self.r['observations'][0]['complete']=True;self.r['observations'][1]['evidence_ref']=None
        self.assertEqual(review_result(self.p,self.r)['status'],'needs_context')

    def test_failed_experiment_is_retained(self):
        self.p=copy.deepcopy(self.replay);self.bind()
        self.r.update(actual_route='propose_run',state='failed',outcome_id='run_failed',observations=[])
        self.r['execution']={'attempted':True,'run_ref':'failed-attempt','exit_code':1,'evidence_ref':'native failure log'}
        self.assertEqual(review_result(self.p,self.r)['status'],'execution_failed')

    def test_failure_can_be_informative_about_a_failure_hypothesis(self):
        self.p=copy.deepcopy(self.replay)
        self.p['hypotheses'][0]['statement']='The native loader cannot load the required model library.'
        self.p['required_observations'].append({'id':'loader_error','description':'Specific load failure','scope':'native startup','attainability_ref':'native stderr'})
        outcome=next(v for v in self.p['outcomes'] if v['id']=='run_failed')
        outcome['requires']=['loader_error'];outcome['effects'][0]['assessment']='supported'
        self.bind()
        self.r.update(actual_route='propose_run',state='failed',outcome_id='run_failed')
        self.r['actual_variables']=[{'name':v['name'],'value':v['proposed'],'evidence_ref':'actual invocation'} for v in self.p['variables']]
        self.r['execution']={'attempted':True,'run_ref':'loader-attempt','exit_code':1,'evidence_ref':'native stderr'}
        self.r['observations']=[{'id':'loader_error','value':'cannot load model.so','complete':True,'evidence_ref':'native stderr'}]
        report=review_result(self.p,self.r)
        self.assertEqual(report['status'],'execution_failed')
        self.assertEqual(report['selected_outcome']['effects'][0]['assessment'],'supported')
        self.assertTrue(report['plan_review']['warnings'])

    def test_normal_result_cannot_hide_native_failure(self):
        self.r['execution'].update(attempted=True,run_ref='failed-run',exit_code=1)
        self.assertEqual(review_result(self.p,self.r)['status'],'review_required')

    def test_failed_or_diverged_controls_remain_visible(self):
        self.r.update(state='diverged',outcome_id='replay_changed')
        self.r['actual_variables'][0]['value']='different-execution'
        report=review_result(self.p,self.r)
        self.assertEqual(report['status'],'review_required')
        self.assertEqual(report['actual_variables'][0]['value'],'different-execution')

    def test_fixed_variables_cannot_change_in_the_plan(self):
        self.p['variables'][0]['proposed']='changed'
        self.assertEqual(audit(self.p)['status'],'review_required')

    def test_multiple_intended_changes_are_allowed(self):
        self.replay['variables'].append({'name':'debug visibility','role':'intended','baseline':'limited','proposed':'request signals','evidence_ref':'native build profile'})
        self.assertEqual(audit(self.replay)['status'],'structured_plan')

    def test_unknown_fixed_control_needs_context(self):
        self.p['variables'][0]['baseline']=None
        self.assertEqual(audit(self.p)['status'],'needs_context')

    def test_missing_hypothesis_basis_is_not_invented(self):
        self.replay['hypotheses'][0]['basis_ref']=None
        self.assertEqual(audit(self.replay)['status'],'needs_context')

    def test_required_observations_need_attainability_and_scope(self):
        self.replay['required_observations'][0]['attainability_ref']=None
        self.assertEqual(audit(self.replay)['status'],'needs_context')

    def test_rerun_requires_prior_search_and_cheaper_route_review(self):
        self.replay['prior_search']['performed']=False
        self.assertEqual(audit(self.replay)['status'],'needs_context')
        self.replay['prior_search']['performed']=True;self.replay['next_action']['alternatives']=[]
        self.assertEqual(audit(self.replay)['status'],'needs_context')

    def test_run_failure_and_inconclusive_decisions_are_required(self):
        self.replay['outcomes']=[v for v in self.replay['outcomes'] if v['kind']!='execution_failed']
        self.assertEqual(audit(self.replay)['status'],'needs_context')

    def test_same_seed_does_not_establish_reproduction(self):
        self.p=copy.deepcopy(self.replay);self.bind()
        self.r['actual_route']='propose_run'
        self.r['execution']={'attempted':True,'run_ref':'new-run','exit_code':0,'evidence_ref':'actual native command'}
        self.r['actual_variables']=[{'name':v['name'],'value':v['proposed'],'evidence_ref':'actual'} for v in self.p['variables']]
        self.r['correspondence']={'status':'unknown','evidence_ref':'same seed only','limits':[]}
        self.assertEqual(review_result(self.p,self.r)['status'],'needs_context')
        self.r['correspondence']['status']='diverged'
        self.assertEqual(review_result(self.p,self.r)['status'],'review_required')

    def test_scoped_correspondence_can_support_declared_replay_result(self):
        self.p=copy.deepcopy(self.replay);self.bind();self.r['actual_route']='propose_run'
        self.r['execution']={'attempted':True,'run_ref':'new-run','exit_code':0,'evidence_ref':'native completion'}
        self.r['actual_variables']=[{'name':v['name'],'value':v['proposed'],'evidence_ref':'actual'} for v in self.p['variables']]
        self.r['correspondence']={'status':'matched_selected_observables','evidence_ref':'actual bounded original/replay comparison','limits':['selected horizon only']}
        self.assertEqual(review_result(self.p,self.r)['status'],'recorded_outcome')

    def test_exploratory_result_preserves_divergent_correspondence(self):
        self.p['reproduction']['kind']='exploratory';self.bind()
        self.r['correspondence'].update(status='diverged',evidence_ref='expected branch difference')
        self.assertEqual(review_result(self.p,self.r)['status'],'recorded_outcome')

    def test_exact_repeat_is_a_notice_not_a_ban_on_replication(self):
        prior=copy.deepcopy(self.p);prior['plan_ref']='prior-plan'
        report=audit(self.p,[prior])
        self.assertEqual(report['status'],'structured_plan')
        self.assertEqual(len(report['repeated_designs']),1)

    def test_new_evidence_scope_is_not_exactly_the_same_design(self):
        prior=copy.deepcopy(self.p);prior['plan_ref']='prior';prior['observation']['evidence_ref']='different source/revision'
        self.assertFalse(audit(self.p,[prior])['repeated_designs'])

    def test_same_plan_id_different_content_is_flagged(self):
        prior=copy.deepcopy(self.p);prior['question']='different question'
        self.assertEqual(audit(self.p,[prior])['status'],'review_required')

    def test_helper_does_not_factcheck_a_false_semantic_interpretation(self):
        self.r['observations'][1]['value']={'accepted':False}
        self.assertEqual(review_result(self.p,self.r)['status'],'recorded_outcome')
        self.assertIn('no automatic semantic classification',review_result(self.p,self.r)['limits'])

    def test_invalid_references_and_duplicate_identifiers_rejected(self):
        self.p['outcomes'][0]['requires']=['missing-observation']
        with self.assertRaises(ValueError):validate_plan(self.p)
        self.p=example_module.example()[0]
        self.p['hypotheses'].append(copy.deepcopy(self.p['hypotheses'][0]))
        with self.assertRaises(ValueError):validate_plan(self.p)

    def test_duplicate_json_and_unknown_fields_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'bad.json';path.write_text('{"a":1,"a":2}')
            with self.assertRaises(ValueError):read_json(path)
        self.p['typo']='not a supported field'
        with self.assertRaises(ValueError):validate_plan(self.p)

    def test_cli_exit_codes_no_overwrite_and_input_immutability(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            for name,value in [('plan',self.p),('result',self.r),('replay',self.replay),('unexecuted',self.unexecuted)]:
                (out/(name+'.json')).write_text(json.dumps(value))
            before=(out/'plan.json').read_bytes()
            base=[sys.executable,str(ROOT/'experiment_ledger.py')]
            self.assertEqual(subprocess.run(base+['audit-plan',str(out/'plan.json')],capture_output=True).returncode,0)
            self.assertEqual(subprocess.run(base+['review-result',str(out/'replay.json'),str(out/'unexecuted.json')],capture_output=True).returncode,2)
            self.assertEqual(subprocess.run(base+['audit-plan',str(out/'plan.json'),'--output',str(out/'plan.json')],capture_output=True).returncode,3)
            self.assertEqual((out/'plan.json').read_bytes(),before)

    def test_cli_unicode_records_under_non_utf8_console(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'plan.json'
            self.p['next_action']['summary']='Inspect request 事务 and preserve its identity.'
            path.write_text(json.dumps(self.p,ensure_ascii=False),encoding='utf-8')
            result=subprocess.run([sys.executable,str(ROOT/'experiment_ledger.py'),'audit-plan',str(path)],
                capture_output=True,env=dict(os.environ,PYTHONIOENCODING='ascii'))
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('事务',result.stdout.decode('utf-8'))


if __name__=='__main__':unittest.main()
