"""Saved native evidence, independent ledger and reuse/unknown controls."""
import copy,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(HERE),str(HERE/'examples')]
from eco_common import read_json
from eco_core import changes,load,review
from native_eco import capture,projection,xml_binding
from create_example import SCENARIOS,policy
from reference_model import check

class EcoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value=os.environ.get('OPENTOOLS_ECO_NATIVE')
        if not value:raise unittest.SkipTest('Set OPENTOOLS_ECO_NATIVE to output from examples/run_native.py')
        cls.root=Path(value).resolve();cls.collection=read_json(cls.root/'collection.json')

    def p(self,scenario='unchanged-cached',family='test-control'):return policy(self.root,family,scenario)
    def cloned(self,scenario='unchanged-cached'):
        tmp=tempfile.TemporaryDirectory(prefix='opentools-eco-test-');self.addCleanup(tmp.cleanup);root=Path(tmp.name)
        p=self.p(scenario)
        for ref in {p['before'],p['after']}:shutil.copytree(self.root/ref,root/ref)
        return root,p
    def write(self,path,value):path.write_text(json.dumps(value),encoding='utf-8')

    def test_01_native_independent_ledger(self):
        total=0
        for row in self.collection['cases']:
            run=self.root/row['case'];e=capture(run,read_json(run/'context.json'));total+=check(e,row['family'],row['selection'])['numeric_values_compared']
        self.assertEqual(total,1600)
    def test_02_all_review_selections(self):
        expected=(0,1,1,1,0,1,0,1,2,2)
        for family in ('test-control','wake-control'):
            for scenario,code in zip(SCENARIOS,expected):
                with self.subTest(family=family,scenario=scenario):self.assertEqual(review(self.root,self.p(scenario,family))['exit_code'],code)
    def test_03_identical_counts_distinct_dependencies(self):
        a=review(self.root,self.p('data-old'));b=review(self.root,self.p('control-old'))
        self.assertEqual(a['native_counts'],b['native_counts']);self.assertEqual(len(a['changed_objects']),1);self.assertEqual(len(b['changed_objects']),1)
        self.assertTrue(a['reports'][1]['conditional_reuse_eligible']);self.assertFalse(b['reports'][1]['conditional_reuse_eligible'])
    def test_04_original_pass_retained_when_stale(self):
        r=review(self.root,self.p('control-old'))
        self.assertTrue(all(x['applicability']['native_result']['outcome']=='pass' and x['applicability']['status']=='inapplicable' for x in r['reports']))
    def test_05_current_failure_retained(self):
        r=review(self.root,self.p('control-cached'))
        self.assertTrue(all(x['applicability']['native_result']['outcome']=='fail' for x in r['reports']))
        self.assertEqual({x['action'] for x in r['next_actions']},{'correct_proposal_or_required_condition_then_revalidate'})
    def test_06_existing_current_result_resolves_only_stale_report(self):
        r=review(self.root,self.p('data-old'))
        self.assertEqual(r['next_actions'],[{'report':'sta','action':'use_matching_retained_current_result','run_ref':'test-control-data-eco'}])
        self.assertEqual(review(self.root,self.p('data-cached'))['exit_code'],0)
    def test_07_phase_changes_without_object_delta(self):
        r=review(self.root,self.p('phase-old'));self.assertEqual(r['changed_objects'],[]);self.assertEqual(len(r['findings']),2)
        self.assertTrue(all(x['current_cached_applicability']['native_result']['outcome']=='pass' for x in r['reports']))
    def test_08_missing_correspondence(self):
        r=review(self.root,self.p('missing-correspondence'));self.assertEqual(r['exit_code'],2);self.assertEqual(r['reports'],[])
    def test_09_foreign_configuration(self):
        r=review(self.root,self.p('foreign-binding'));self.assertEqual(r['exit_code'],2);self.assertEqual(r['reports'],[])
    def test_10_stale_native_graph_binding(self):
        p=self.p();p['after_binding']['graph_sha256']='0'*64;r=review(self.root,p);self.assertEqual(r['exit_code'],2);self.assertEqual(r['reports'],[])
    def test_11_selected_roles_bound(self):
        p=self.p();p['after_binding']['selection']['cells']['gate']='other';self.assertEqual(review(self.root,p)['exit_code'],2)
    def test_12_no_implicit_reuse_approval(self):
        r=review(self.root,self.p('data-no-approval'));self.assertEqual(len(r['findings']),2);self.assertTrue(all(x['reuse_rule'] is None for x in r['reports']))
    def test_13_foreign_reuse_approval(self):
        p=self.p('data-cached');p['reports']['clock']['reviewed_reuse']['after_run_ref']='foreign';r=review(self.root,p)
        self.assertEqual(r['exit_code'],1);self.assertIsNone(r['reports'][1]['reuse_rule']);self.assertTrue(r['gaps'])
    def test_14_missing_relationship_basis(self):
        root,p=self.cloned();file=root/p['after']/'context.json';ctx=read_json(file);ctx['functional_intent_ref']=None;self.write(file,ctx)
        r=review(root,p);self.assertEqual(r['exit_code'],2);self.assertIn('missing_relationship_basis',[x['kind'] for x in r['gaps']])
    def test_15_broader_required_claim_stays_open(self):
        p=self.p();p['required_claims']['complete_equivalence']=True;r=review(self.root,p);self.assertEqual(r['exit_code'],2)
        self.assertTrue(all(x['applicability']['status']=='directly_applicable_within_scope' for x in r['reports']))
    def test_16_cannot_drop_required_report(self):
        p=self.p();del p['reports']['sta']
        with self.assertRaises(ValueError):review(self.root,p)
    def test_17_missing_raw_report_is_unknown(self):
        root,p=self.cloned('unchanged-old');(root/p['before']/'sta.txt').unlink();r=review(root,p)
        self.assertEqual(r['exit_code'],2);self.assertEqual(r['reports'][0]['applicability']['native_result']['outcome'],'pass')
        self.assertEqual(r['reports'][0]['applicability']['result_integrity']['status'],'missing')
    def test_18_changed_raw_report_is_unknown(self):
        root,p=self.cloned('unchanged-old');(root/p['before']/'clock.stdout.txt').write_text('changed bytes\n');r=review(root,p)
        self.assertEqual(r['exit_code'],2);self.assertEqual(r['reports'][1]['applicability']['result_integrity']['status'],'changed')
    def test_19_snapshot_reconstructed_only_from_original_bytes(self):
        root,p=self.cloned();(root/p['after']/'sta.snapshot.json').unlink();self.assertEqual(review(root,p)['exit_code'],0)
    def test_20_missing_record_and_raw_locates_existing_current_result(self):
        root,p=self.cloned('unchanged-old')
        for name in ('sta.snapshot.json','sta.txt'):(root/p['before']/name).unlink()
        r=review(root,p);self.assertEqual(r['exit_code'],2);self.assertIsNone(r['reports'][0]['applicability'])
        self.assertEqual(r['next_actions'][0]['action'],'use_matching_retained_current_result')
    def test_21_changed_source_not_recaptured_as_original(self):
        root,p=self.cloned();(root/p['after']/'design.v').write_text('module top;endmodule')
        with self.assertRaisesRegex(ValueError,'Consumed source changed'):review(root,p)
    def test_22_original_executable_binding(self):
        root,p=self.cloned();(root/p['after']/'Vtop').write_bytes(b'not original')
        with self.assertRaisesRegex(ValueError,'executable binding'):review(root,p)
    def test_23_model_profile_cannot_be_relabelled(self):
        root,p=self.cloned();file=root/p['after']/'models.sv';file.write_text(file.read_text()+'\n// different\n')
        with self.assertRaises(ValueError):review(root,p)
    def test_24_missing_native_graph(self):
        root,p=self.cloned();(root/p['after']/'graph.txt').unlink()
        with self.assertRaisesRegex(ValueError,'Missing native file'):review(root,p)
    def test_25_physical_change_needs_other_evidence(self):
        e,_=load(self.root,'test-control-before');after=copy.deepcopy(e);after['graph']['placement']['gate']['location']=[10,20]
        self.assertIn('physical_change_outside_endpoint_rewire_profile',changes(e,after)[1])
    def test_26_unknown_instance_correspondence(self):
        e,_=load(self.root,'test-control-before');after=copy.deepcopy(e);after['graph']['cells']['new']='ECO_BUF'
        self.assertIn('native_instance_correspondence_or_master_changed',changes(e,after)[1])
    def test_27_stateful_clock_dependency_not_waived(self):
        e,_=load(self.root,'test-control-before');e['graph']['pins']['gate/B']['net']='q0'
        self.assertIn('stateful_clock_dependency',projection(e,'clock')['unqualified_dependencies'])
    def test_28_combinational_cycle_not_waived(self):
        e,_=load(self.root,'test-control-before');e['graph']['pins']['allow/A']['net']='qualified_enable'
        self.assertIn('combinational_cycle',projection(e,'clock')['unqualified_dependencies'])
    def test_29_receiver_clock_transfer_must_be_observed(self):
        e,_=load(self.root,'test-control-before');e['graph']['pins']['capture/CK']['net']='other'
        self.assertIn('receiver_clock_transfer_not_observed',projection(e,'clock')['unqualified_dependencies'])
    def test_30_unqualified_top_behavior_rejected(self):
        root,p=self.cloned();run=root/p['before'];e,_=load(root,p['before']);file=run/'logical.xml'
        source=file.read_text();at=source.index('topModule="1"');end=source.index('</module>',at);file.write_text(source[:end]+'<always/>'+source[end:])
        with self.assertRaisesRegex(ValueError,'Top-level behavior'):xml_binding(file,e['graph'],e['context'])
    def test_31_logical_native_connectivity_must_match(self):
        e,_=load(self.root,'test-control-before');e['graph']['pins']['gate/B']['net']='db'
        with self.assertRaisesRegex(ValueError,'connectivity mismatch'):xml_binding(self.root/'test-control-before/logical.xml',e['graph'],e['context'])
    def test_32_missing_independent_required_phase(self):
        p=self.p();p['required_phase']['clock']=None;r=review(self.root,p);self.assertEqual(r['exit_code'],2)
    def test_33_original_snapshot_cannot_change_outcome(self):
        root,p=self.cloned();file=root/p['after']/'sta.snapshot.json';r=read_json(file);r['result']['outcome']='fail';self.write(file,r)
        with self.assertRaisesRegex(ValueError,'snapshot differs'):review(root,p)
    def test_34_cli_matches_saved_review(self):
        file=self.root/'reviews/test-control-data-cached.policy.json';p=subprocess.run([sys.executable,str(HERE/'eco_review.py'),'review',str(self.root),str(file)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout),review(self.root,read_json(file)))

if __name__=='__main__':unittest.main()
