"""Native timing object, lineage, mode and consumer-coverage controls."""
import copy,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
PROFILE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(PROFILE),str(PROFILE/'examples')]
from lineage_common import config,parse,read_json
from lineage_core import binding,review
from sta_review import evaluate,load
from native_lineage import read_native
from create_example import policy
from reference_model import check
class LineageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value=os.environ.get('OPENTOOLS_STA_LINEAGE_NATIVE')
        if not value:raise unittest.SkipTest('Set OPENTOOLS_STA_LINEAGE_NATIVE to retained examples/run_native.py output')
        cls.root=Path(value).resolve();cls.collection=read_json(cls.root/'collection.json');cls.e={r['run_ref']:load(cls.root,r['run_ref']) for r in cls.collection['cases']}
    def triple(self,case='complete',family='boot-divider'):
        p=policy(self.root,family+'-'+case);return copy.deepcopy(self.e[p['run_ref']]),p['contract'],p['binding']
    def cloned(self):
        t=tempfile.TemporaryDirectory(prefix='opentools-sta-test-');self.addCleanup(t.cleanup);root=Path(t.name);ref='boot-divider-complete';shutil.copytree(self.root/ref,root/ref);return root,ref
    def test_01_independent_period_route_and_creation_tables(self):
        totals=0
        for row in self.collection['cases']:totals+=check(self.e[row['run_ref']],row['family'],row['case'])['clock_endpoint_associations_compared']
        self.assertEqual(totals,59)
    def test_02_all_native_review_records_reproduce(self):
        for row in read_json(self.root/'review-collection.json'):
            path=self.root/'reviews'/(row['run_ref']+'.policy.json');self.assertEqual(evaluate(self.root,read_json(path)),read_json(self.root/'reviews'/(row['run_ref']+'.report.json')))
    def test_03_root_present_but_required_consumers_uncovered(self):
        r=review(*self.triple('missing-generated'));self.assertEqual(r['exit_code'],1)
        self.assertIn('root',r['original_native_objects']['clocks']);self.assertEqual([e['pin'] for e in r['endpoint_review'] if not e['native_clocks']],['launch/CK','capture/CK'])
    def test_04_wrong_mode_with_all_clocks_still_requires_review(self):
        r=review(*self.triple('wrong-mode'));self.assertEqual(r['exit_code'],1);self.assertEqual(len(r['original_native_objects']['clocks']),2);self.assertTrue(r['original_native_objects']['path_count'])
    def test_05_wrong_ratio_preserves_native_lineage_and_period(self):
        r=review(*self.triple('wrong-divide','wake-divider'));self.assertEqual(r['exit_code'],1);self.assertEqual(r['original_native_objects']['clocks']['divide_four']['period_ns'],96.0)
        self.assertIn('resolved_native_lineage_differs',[f['kind'] for f in r['findings']])
    def test_06_reference_source_is_not_definition_target(self):
        e,_,_=self.triple(family='wake-divider');event=e['native']['generated_events'][-1];self.assertEqual(event['reference_source'],'divider0/Q');self.assertEqual(event['targets'],['divider1/Q']);self.assertEqual(event['master'],'divide_two')
    def test_07_ideal_state_is_not_propagated(self):
        r=review(*self.triple('ideal'));self.assertEqual(r['exit_code'],1);self.assertTrue(all(c['is_propagated']==0 for c in r['original_native_objects']['clocks'].values()))
    def test_08_gate_off_keeps_definitions_but_loses_consumers(self):
        r=review(*self.triple('gate-off'));self.assertEqual(r['exit_code'],1);self.assertEqual(r['original_native_objects']['path_count'],0);self.assertEqual(len(r['original_native_objects']['clocks']),2)
    def test_09_unknown_case_retains_ambiguity(self):
        r=review(*self.triple('unknown-case'));self.assertEqual(r['exit_code'],1);self.assertTrue(r['gaps']);self.assertEqual(r['original_native_objects']['cases']['boot_sel'],'X')
    def test_10_untraced_lineage_not_filled_from_contract(self):
        r=review(*self.triple('untraced'));self.assertEqual(r['exit_code'],2);self.assertEqual(r['original_native_objects']['generated_events'],[])
    def test_11_automatic_master_is_not_a_captured_explicit_master(self):
        r=review(*self.triple('auto-master'));self.assertEqual(r['exit_code'],2);self.assertIsNone(r['original_native_objects']['generated_events'][0]['master'])
    def test_12_foreign_artifact_binding_holds_attribution(self):
        e,c,b=self.triple();b['tool_sha256']='0'*64;r=review(e,c,b);self.assertEqual(r['exit_code'],2);self.assertEqual(r['clock_review'],[])
    def test_13_foreign_mode_scope(self):
        e,c,b=self.triple();c['identity']['mode_ref']='other';self.assertEqual(review(e,c,b)['exit_code'],2)
    def test_14_missing_power_basis(self):
        e,c,_=self.triple();e['context']['power_basis_ref']=None;self.assertEqual(review(e,c,binding(e))['exit_code'],2)
    def test_15_missing_required_reset_basis(self):
        e,c,b=self.triple();c['basis']['reset_basis_ref']=None;self.assertEqual(review(e,c,b)['exit_code'],2)
    def test_16_stronger_waveform_safety_claim_stays_open(self):
        e,c,b=self.triple();c['required_claims']['waveform_safety']=True;r=review(e,c,b);self.assertEqual(r['exit_code'],2);self.assertTrue(all(v['waveform_valid'] for v in r['original_native_objects']['clocks'].values()))
    def test_17_unspecified_claim_strength(self):
        e,c,b=self.triple();del c['required_claims']['timing_signoff'];self.assertEqual(review(e,c,b)['exit_code'],2)
    def test_18_cannot_drop_consumer_from_contract(self):
        e,c,b=self.triple();del c['clock_pin_requirements']['capture/CK'];r=review(e,c,b);self.assertEqual(r['exit_code'],1);self.assertIn('native_consumer_missing_from_contract',[f['kind'] for f in r['findings']])
    def test_19_incomplete_inventory(self):
        e,c,b=self.triple();c['inputs_complete']=False;self.assertEqual(review(e,c,b)['exit_code'],2)
    def test_20_duplicate_generation_events_ambiguous(self):
        e,c,b=self.triple();e['native']['generated_events'].append(copy.deepcopy(e['native']['generated_events'][0]));self.assertEqual(review(e,c,b)['exit_code'],2)
    def test_21_changed_clock_object_not_reused(self):
        e,c,b=self.triple();e['native']['generated_events'][0]['current_object_matches']=0;self.assertEqual(review(e,c,b)['exit_code'],2)
    def test_22_nondividing_generation_requires_another_profile(self):
        e,c,b=self.triple();e['native']['generated_events'][0]['native_edges']='1 2 3';self.assertEqual(review(e,c,b)['exit_code'],2)
    def test_23_changed_consumed_source_rejected(self):
        root,ref=self.cloned();(root/ref/'design.v').write_text('changed')
        with self.assertRaisesRegex(ValueError,'Consumed source changed'):load(root,ref)
    def test_24_changed_native_report_rejected(self):
        root,ref=self.cloned();(root/ref/'native.jsonl').write_text('changed')
        with self.assertRaisesRegex(ValueError,'Native artifact changed'):load(root,ref)
    def test_25_missing_original_clock_export_rejected(self):
        root,ref=self.cloned();(root/ref/'native.jsonl').unlink()
        with self.assertRaisesRegex(ValueError,'Missing/linked'):load(root,ref)
    def test_26_truncated_native_report(self):
        root,ref=self.cloned();p=root/ref/'native.jsonl';p.write_text('\n'.join(p.read_text().splitlines()[:-1]))
        with self.assertRaisesRegex(ValueError,'Incomplete native export'):read_native(p)
    def test_27_duplicate_or_nonfinite_JSON(self):
        for s in ('{"x":1,"x":2}','{"x":NaN}'):
            with self.assertRaises(ValueError):parse(s)
    def test_28_setup_cannot_inject_commands(self):
        e,_,_=self.triple();e['context']['setup']['root']['port']='clk;exec unexpected'
        with self.assertRaises(ValueError):config(e['context'])
    def test_29_no_overwrite(self):
        root,ref=self.cloned();out=root/'existing';out.write_text('retained');p=subprocess.run([sys.executable,str(PROFILE/'sta_review.py'),'capture',str(root),ref,'--output',str(out)],capture_output=True,text=True);self.assertEqual(p.returncode,3);self.assertEqual(out.read_text(),'retained')
    def test_30_actual_CLI_matches_review(self):
        path=self.root/'reviews/wake-divider-wrong-mode.policy.json';p=subprocess.run([sys.executable,str(PROFILE/'sta_review.py'),'review',str(self.root),str(path)],capture_output=True,text=True);self.assertEqual(p.returncode,1,p.stderr);self.assertEqual(json.loads(p.stdout),read_json(self.root/'reviews/wake-divider-wrong-mode.report.json'))
    def test_31_unrelated_creation_lifecycle_is_unknown(self):
        e,c,b=self.triple();ev=copy.deepcopy(e['native']['generated_events'][0]);ev['name']='deleted';e['native']['generated_events'].append(ev);self.assertEqual(review(e,c,b)['exit_code'],2)
    def test_32_unknown_required_lineage_is_not_assumed(self):
        e,c,b=self.triple();c['clocks']['half_rate']['lineage']=None;self.assertEqual(review(e,c,b)['exit_code'],2)
if __name__=='__main__':unittest.main()
