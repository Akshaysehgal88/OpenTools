import copy,json,os
from pathlib import Path
import shutil,subprocess,sys,tempfile,unittest
PROFILE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROFILE));sys.path.insert(0,str(PROFILE/'examples'))
from fault_common import exit_code,file,read_json
from fault_core import compare
from native_fault import capture
from create_example import binding
from reference_model import check

NATIVE=os.environ.get('OPENTOOLS_FAULT_NATIVE')
def kinds(r,key='findings'):return {v['kind'] for v in r[key]}

@unittest.skipUnless(NATIVE,'Set OPENTOOLS_FAULT_NATIVE to a retained example collection')
class FaultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(NATIVE);cls.records={}
        for row in read_json(cls.root/'collection.json')['cases']:
            folder=cls.root/row['case'];cls.records[row['case']]=(capture(folder/'run',read_json(folder/'context.json')),read_json(folder/'policy.json'))
    def pair(self,case='same',family='select-network'):
        current,policy=self.records[family+'-'+case];baseline=self.records[family+'-baseline'][0]
        return copy.deepcopy((baseline,current,policy))
    def test_all_actual_responses_and_collapse_maps_match_independent_equations(self):
        for e,p in self.records.values():check(e)
    def test_unchanged_complete_scope_in_two_logic_contexts(self):
        for family in ('select-network','qualifier-network'):
            r=compare(*self.pair(family=family));self.assertEqual(exit_code(r),0);self.assertFalse(r['newly_detected_faults'])
    def test_denominator_only_increase_keeps_original_faults_and_detected_count(self):
        for family in ('select-network','qualifier-network'):
            a,b,p=self.pair('denominator-only',family);r=compare(a,b,p)
            self.assertIn('reported_ratio_increased_without_new_detection',kinds(r));self.assertEqual(len(r['original_faults']),len(a['faults']));self.assertFalse(r['newly_detected_faults']);self.assertGreater(r['reported_delta_percent'],0)
    def test_excluded_faults_keep_native_classification(self):
        a,b,p=self.pair('denominator-only');r=compare(a,b,p)
        self.assertEqual(r['current']['native_classes'],r['baseline']['native_classes']);self.assertTrue(all(f['current']['classification']=='UD' for f in r['original_faults'] if f['current']['excluded']))
    def test_approved_exclusion_is_measurement_change_without_alleging_more_detection(self):
        r=compare(*self.pair('valid-exclusion'));self.assertIn('reported_denominator_changed',kinds(r));self.assertFalse(r['gaps']);self.assertFalse(r['newly_detected_faults'])
    def test_missing_exclusion_rationale_remains_an_open_basis(self):
        r=compare(*self.pair('denominator-only'));self.assertIn('exclusion_basis_unestablished',kinds(r,'gaps'));self.assertEqual(exit_code(r),1)
    def test_new_selected_pattern_detections_are_distinguished_from_denominator_changes(self):
        for family in ('select-network','qualifier-network'):
            r=compare(*self.pair('more-patterns',family));self.assertEqual(len(r['newly_detected_faults']),5);self.assertNotIn('reported_ratio_increased_without_new_detection',kinds(r));self.assertFalse(r['exclusion_changes'])
    def test_untestable_is_only_the_declared_finite_legal_input_space(self):
        a,b,p=self.pair('mode-change');r=compare(a,b,p);self.assertFalse(r['same_detection_scope']);self.assertIn('detection_scope_changed',kinds(r,'gaps'));self.assertIsNone(r['reported_delta_percent']);self.assertIn('native_collapse_map_changed',kinds(r))
    def test_unlike_metric_definitions_are_not_normalized(self):
        r=compare(*self.pair('metric-change'));self.assertFalse(r['same_measurement_definition']);self.assertIsNone(r['reported_delta_percent']);self.assertIn('native_measurement_definition_changed',kinds(r))
    def test_collapsed_fraction_preserves_original_population_and_mapping(self):
        a,b,p=self.pair('collapsed-score');r=compare(a,b,p)
        self.assertEqual((len(b['faults']),len(b['groups'])),(10,7));self.assertEqual(len(r['original_faults']),10);self.assertIsNone(r['reported_delta_percent']);self.assertFalse(r['same_measurement_definition'])
    def test_aborted_faults_are_not_normalized_to_undetected_or_untestable(self):
        a,b,p=self.pair('aborted');r=compare(a,b,p);self.assertTrue(any(f['classification']=='AB' for f in b['faults']));self.assertIn('classification_unresolved',kinds(r,'gaps'));self.assertEqual(r['current']['native_classes']['UT'],0)
    def test_unknown_native_class_stays_unknown_even_with_a_numeric_report(self):
        a,b,p=self.pair('unknown-class');r=compare(a,b,p);self.assertEqual(b['faults'][0]['classification'],'UNKNOWN');self.assertIn('classification_unresolved',kinds(r,'gaps'));self.assertNotIn('reported_ratio_increased_without_new_detection',kinds(r))
    def test_same_unknown_population_is_incomplete_not_a_clean_change(self):
        a,b,p=self.pair('unknown-class');p['baseline']=binding(b);r=compare(b,b,p);self.assertEqual(exit_code(r),2)
    def test_unknown_resolution_is_not_claimed_as_new_pattern_detection(self):
        a,b,p=self.pair('unknown-class');original=a;p['baseline']=binding(b);p['current']=binding(original);r=compare(b,original,p);self.assertIn(0,r['resolved_classifications']);self.assertFalse(r['newly_detected_faults'])
    def test_missing_model_or_owner_basis_keeps_stable_comparison_open(self):
        a,b,p=self.pair();b['context']['model_basis_ref']=None;p['owner_ref']=None
        r=compare(a,b,p);self.assertEqual(exit_code(r),2);self.assertIn('missing_native_basis',kinds(r,'gaps'))
    def test_stale_or_foreign_run_bindings_cannot_support_progress(self):
        for k in ('run_ref','configuration_ref','objective_ref','fault_model_ref'):
            a,b,p=self.pair();p['current']['identity'][k]='foreign';r=compare(a,b,p);self.assertEqual(exit_code(r),2);self.assertFalse(r['original_faults'])
    def test_source_plan_command_and_binary_bindings_are_independent(self):
        for k in ('source_sha256','plan_sha256','run_command_sha256','binary_sha256'):
            a,b,p=self.pair();p['current'][k]={} if k=='source_sha256' else '0'*64
            self.assertEqual(exit_code(compare(a,b,p)),2)
    def test_required_original_population_cannot_be_replaced_by_selected_rows(self):
        a,b,p=self.pair();p['required_original_faults']=p['required_original_faults'][:-1]
        self.assertIn('faults_outside_original_roster',kinds(compare(a,b,p)))
    def test_partial_normalized_population_is_not_treated_as_removed_faults(self):
        a,b,p=self.pair();b['faults'].pop();r=compare(a,b,p);self.assertIn('required_faults_missing',kinds(r,'gaps'))
    def test_native_role_binding_must_resolve_actual_parameterized_unit(self):
        folder=self.root/'qualifier-network-same';ctx=read_json(folder/'context.json');ctx['role_map']['observed']='observed'
        with self.assertRaises((ValueError,KeyError)):capture(folder/'run',ctx)
    def test_truncated_native_export_or_changed_collapse_map_is_invalid(self):
        source=self.root/'select-network-same/run'
        for name,change in [('run.stdout.txt',lambda s:s.rsplit('NATIVE_CHECKS',1)[0]),('run.stdout.txt',lambda s:s.replace('GROUP 4 2','GROUP 4 3'))]:
            with tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp)/'run';shutil.copytree(source,folder);p=folder/name;old=p.read_text();new=change(old);self.assertNotEqual(old,new);p.write_text(new)
                with self.assertRaises((ValueError,StopIteration)):capture(folder,read_json(source.parent/'context.json'))
    def test_compile_plan_and_original_source_are_bound(self):
        source=self.root/'select-network-same/run'
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'run';shutil.copytree(source,folder);p=folder/'plan.json';x=read_json(p);x['excluded']=1;p.write_text(json.dumps(x))
            with self.assertRaises(ValueError):capture(folder,read_json(source.parent/'context.json'))
    def test_input_json_does_not_accept_duplicate_or_nonfinite_values(self):
        for value in ('{"x":1,"x":2}','{"x":NaN}'):
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'input.json';p.write_text(value)
                with self.assertRaises(ValueError):read_json(p)
    def test_cli_preserves_own_native_metric_and_review_status(self):
        for case,code in [('same',0),('denominator-only',1)]:
            a=self.root/'select-network-baseline';b=self.root/('select-network-'+case)
            p=subprocess.run([sys.executable,str(PROFILE/'fault_audit.py'),'compare',str(a/'run'),str(a/'context.json'),str(b/'run'),str(b/'context.json'),str(b/'policy.json')],capture_output=True,text=True)
            self.assertEqual(p.returncode,code,p.stderr);self.assertEqual(json.loads(p.stdout)['current']['measurement']['denominator'],10 if code==0 else 8)

if __name__=='__main__':unittest.main()
