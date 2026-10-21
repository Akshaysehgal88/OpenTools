"""Original native static evidence, independent DC reference and scope controls."""
import copy,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
MODULE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(MODULE),str(MODULE/'examples')]
from supply_common import config,parse,read_json,sha
from supply_core import binding,review
from supply_review import evaluate,load
from native_supply import read_native
from create_example import policy
from reference_model import check
class SupplyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value=os.environ.get('OPENTOOLS_SUPPLY_NATIVE')
        if not value:raise unittest.SkipTest('Set OPENTOOLS_SUPPLY_NATIVE to retained output from examples/run_native.py')
        cls.root=Path(value).resolve();cls.collection=read_json(cls.root/'collection.json');cls.e={r['run_ref']:load(cls.root,r['run_ref']) for r in cls.collection['cases']}
    def triple(self,scenario='base',family='series'):
        p=policy(self.root,family,scenario);e=copy.deepcopy(self.e[p['selected_ref']]);return e,p['request'],p['selected_binding']
    def cloned(self):
        tmp=tempfile.TemporaryDirectory(prefix='opentools-supply-test-');self.addCleanup(tmp.cleanup);root=Path(tmp.name);ref='series-base';shutil.copytree(self.root/ref,root/ref);return root,ref
    def test_01_native_voltages_match_independent_DC_solution(self):
        total=0
        for row in self.collection['cases']:total+=check(self.e[row['run_ref']],self.root,row['family'],row['case'])['compared_instance_points']
        self.assertEqual(total,25)
    def test_02_all_saved_review_selections_reproduce(self):
        for row in read_json(self.root/'review-collection.json'):
            p=read_json(self.root/'reviews'/(row['name']+'.policy.json'));self.assertEqual(evaluate(self.root,p),read_json(self.root/'reviews'/(row['name']+'.report.json')))
    def test_03_changed_loading_preserves_original_numeric_result(self):
        r=review(*self.triple('old-loads'));self.assertEqual(r['exit_code'],1);self.assertEqual(r['original_native_status']['analysis']['tcl_catch'],0);self.assertEqual(r['original_voltage_points'],self.e['series-base']['reports']['voltage.csv'])
    def test_04_source_relocation_and_voltage_require_new_basis(self):
        r=review(*self.triple('old-source'));self.assertEqual(r['exit_code'],1);self.assertIn('setup',[f['field'] for f in r['findings']])
    def test_05_same_corner_label_and_voltage_bytes_do_not_prove_same_point(self):
        for family in ('series','branch'):
            base=self.e[family+'-base'];new=self.e[family+'-corner-change'];self.assertEqual(base['native_corner'],new['native_corner']);self.assertEqual(base['reports']['voltage.csv'],new['reports']['voltage.csv'])
            self.assertNotEqual(base['native']['point'],new['native']['point']);self.assertEqual(review(*self.triple('old-corner',family))['exit_code'],1)
    def test_06_matching_retained_result_needs_no_new_run(self):
        r=evaluate(self.root,policy(self.root,'branch','old-loads'));self.assertEqual(r['next_actions'][0],{'action':'use_matching_retained_static_result','run_ref':'branch-loads'});self.assertEqual(r['cached_review']['exit_code'],0)
    def test_07_cut_preserves_logical_names_but_native_physical_check_fails(self):
        old=self.e['series-base'];cut=self.e['series-connectivity-cut'];self.assertEqual(old['native']['iterms'],cut['native']['iterms']);self.assertNotEqual(old['native']['shapes'],cut['native']['shapes'])
        r=review(*self.triple('exact-cut'));self.assertEqual(r['exit_code'],1);self.assertIsNone(r['original_voltage_points']);self.assertEqual(r['original_native_status']['analysis']['native_result'],'PSM-0069')
    def test_08_static_concurrency_is_not_dynamic_wake(self):
        r=review(*self.triple('dynamic'));self.assertEqual(r['exit_code'],2);self.assertIsNotNone(r['original_voltage_points']);self.assertEqual({g['claim'] for g in r['gaps']},{'dynamic_IR','wake_sequence'})
    def test_09_foreign_artifact_binding(self):
        e,q,b=self.triple();b['tool_sha256']='0'*64;r=review(e,q,b);self.assertEqual(r['exit_code'],2);self.assertEqual(r['fields'],[])
    def test_10_foreign_request_scope(self):
        e,q,b=self.triple();q['scope_ref']='other';r=review(e,q,b);self.assertEqual(r['exit_code'],2);self.assertEqual(r['fields'],[])
    def test_11_missing_observed_state_basis(self):
        e,q,_=self.triple();e['context']['state_basis_ref']=None;r=review(e,q,binding(e));self.assertEqual(r['exit_code'],2)
    def test_12_missing_required_activity_basis(self):
        e,q,b=self.triple();q['basis']['activity_basis_ref']=None;self.assertEqual(review(e,q,b)['exit_code'],2)
    def test_13_unknown_required_point_not_filled_from_name(self):
        e,q,b=self.triple();q['fields']['point']=None;self.assertEqual(review(e,q,b)['exit_code'],2)
    def test_14_absent_native_operating_point_remains_unknown(self):
        e,q,b=self.triple();e['native']['point']=None;self.assertEqual(review(e,q,b)['exit_code'],2)
    def test_15_unspecified_claim_strength_stays_open(self):
        e,q,b=self.triple();del q['required_claims']['EM_lifetime'];self.assertEqual(review(e,q,b)['exit_code'],2)
    def test_16_EM_lifetime_is_not_established(self):
        e,q,b=self.triple();q['required_claims']['EM_lifetime']=True;self.assertEqual(review(e,q,b)['exit_code'],2)
    def test_17_cannot_drop_a_required_static_field(self):
        e,q,b=self.triple();del q['fields']['source/design.def']
        with self.assertRaises(ValueError):review(e,q,b)
    def test_18_missing_voltage_artifact_is_unknown_not_hardware_failure(self):
        root,ref=self.cloned();b=binding(self.e[ref]);(root/ref/'voltage.csv').unlink();r=review(load(root,ref),read_json(root/ref/'request.json'),b)
        self.assertEqual(r['exit_code'],2);self.assertEqual(r['findings'],[]);self.assertEqual(r['original_native_status']['analysis']['tcl_catch'],0)
    def test_19_changed_SPICE_artifact_is_not_recaptured_as_original(self):
        root,ref=self.cloned();b=binding(self.e[ref]);(root/ref/'network.sp').write_text('changed');r=review(load(root,ref),read_json(root/ref/'request.json'),b);self.assertEqual(r['exit_code'],2);self.assertIsNone(r['resolved_native_currents'])
    def test_20_changed_consumed_source_rejected(self):
        root,ref=self.cloned();(root/ref/'design.def').write_text('changed')
        with self.assertRaisesRegex(ValueError,'Consumed source changed'):load(root,ref)
    def test_21_changed_native_topology_rejected(self):
        root,ref=self.cloned();(root/ref/'native.odb').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Native artifact changed'):load(root,ref)
    def test_22_prospective_request_does_not_require_another_IR_run(self):
        root,ref=self.cloned();p=policy(self.root,'series','old-loads');p.update(cached_ref=None,cached_binding=None);self.assertEqual(evaluate(root,p)['exit_code'],1)
    def test_23_incomplete_scenario_inventory(self):
        e,q,b=self.triple();q['inputs_complete']=False;self.assertEqual(review(e,q,b)['exit_code'],2)
    def test_24_native_source_population_is_retained_and_checked(self):
        e,q,b=self.triple();e['reports']['network.sp']['sources']['extra']={'node':'extra','value':1.0};self.assertEqual(review(e,q,b)['exit_code'],2)
    def test_25_native_current_population_cannot_hide_missing_load(self):
        e,q,b=self.triple();e['reports']['network.sp']['sinks'].pop('I1');self.assertEqual(review(e,q,b)['exit_code'],2)
    def test_26_original_current_to_power_mapping_is_checked(self):
        e,q,b=self.triple();e['reports']['network.sp']['sinks']['I0']['value']+=0.1;self.assertEqual(review(e,q,b)['exit_code'],2)
    def test_27_missing_native_load_location(self):
        e,q,b=self.triple();e['native']['iterms']['load0/VDD']['position_known']=False;self.assertEqual(review(e,q,b)['exit_code'],2)
    def test_28_duplicate_and_nonfinite_JSON_rejected(self):
        for v in ('{"x":1,"x":2}','{"x":NaN}'):
            with self.assertRaises(ValueError):parse(v)
    def test_29_setup_cannot_inject_commands(self):
        e,_,_=self.triple();e['context']['setup']['net']='VDD;exec something'
        with self.assertRaises(ValueError):config(e['context'])
    def test_30_no_overwrite_on_CLI(self):
        root,ref=self.cloned();out=root/'existing';out.write_text('retained');p=subprocess.run([sys.executable,str(MODULE/'supply_review.py'),'capture',str(root),ref,'--output',str(out)],capture_output=True,text=True);self.assertEqual(p.returncode,3);self.assertEqual(out.read_text(),'retained')
    def test_31_actual_CLI_matches_review(self):
        path=self.root/'reviews/branch-old-corner.policy.json';p=subprocess.run([sys.executable,str(MODULE/'supply_review.py'),'review',str(self.root),str(path)],capture_output=True,text=True);self.assertEqual(p.returncode,1,p.stderr);self.assertEqual(json.loads(p.stdout),read_json(self.root/'reviews/branch-old-corner.report.json'))
    def test_32_truncated_native_supply_rejected(self):
        root,ref=self.cloned();p=root/ref/'native.jsonl';p.write_text('\n'.join(p.read_text().splitlines()[:-1]))
        with self.assertRaisesRegex(ValueError,'Incomplete native supply'):read_native(p)
if __name__=='__main__':unittest.main()
