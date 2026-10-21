"""Native geometry/reference evidence and physical-review boundary controls."""
import copy,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
MODULE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(MODULE),str(MODULE/'examples')]
from physical_common import config,digest,folder,parse,read_json
from physical_review import load
from physical_core import binding,metric,review
from native_region import read_native
from create_example import policy
from reference_model import check

class PhysicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value=os.environ.get('OPENTOOLS_PHYSICAL_NATIVE')
        if not value:raise unittest.SkipTest('Set OPENTOOLS_PHYSICAL_NATIVE to output from examples/run_native.py')
        cls.root=Path(value).resolve();cls.collection=read_json(cls.root/'collection.json');cls.e={r['run_ref']:load(cls.root,r['run_ref']) for r in cls.collection['cases']}
    def pair(self,case='preserving-control',family='horizontal-access'):
        return copy.deepcopy((self.e[family+'-baseline'],self.e[family+'-'+case],policy(self.root,family,case)))
    def cloned(self):
        tmp=tempfile.TemporaryDirectory(prefix='opentools-physical-test-');self.addCleanup(tmp.cleanup);root=Path(tmp.name);ref='horizontal-access-baseline';shutil.copytree(self.root/ref,root/ref);return root,ref
    def test_01_native_facts_match_independent_geometry_tables(self):
        total=0
        for row in self.collection['cases']:total+=check(self.e[row['run_ref']],row['family'],row['case'])['pin_positions_compared']
        self.assertEqual(total,180)
    def test_02_all_original_review_records_reproduce(self):
        for row in read_json(self.root/'review-collection.json'):
            p=read_json(self.root/'reviews'/(row['name']+'.policy.json'));r=review(self.e[p['before']],self.e[p['after']],p)
            self.assertEqual(r,read_json(self.root/'reviews'/(row['name']+'.report.json')))
    def test_03_native_pass_does_not_authorize_dropped_protection(self):
        r=review(*self.pair('drop-and-intrude'));self.assertEqual(r['native_placement']['after']['return_code'],0)
        self.assertEqual({f['kind'] for f in r['findings']},{'required_region_protection_removed','candidate_intrudes_required_region'})
        self.assertLess(r['metric']['reported_delta_dbu'],0);self.assertEqual(r['experiment']['qualification'],'comparable_for_selected_geometry')
    def test_04_native_failure_preserved_when_constraint_remains(self):
        r=review(*self.pair('keep-and-intrude'));self.assertEqual(r['native_placement']['after'],{'return_code':1,'native_message':'DPL-0033'})
        self.assertIn('candidate_native_placement_check_failed',[f['kind'] for f in r['findings']])
    def test_05_preserving_control_touches_edge_without_intrusion(self):
        r=review(*self.pair());self.assertEqual(r['exit_code'],0);self.assertEqual(r['metric']['reported_delta_dbu'],-4000)
        self.assertEqual(r['region_review']['after_intruding_instances'],[])
    def test_06_unchanged_evidence_needs_no_new_action(self):
        r=review(*self.pair('unchanged'));self.assertEqual(r['exit_code'],0);self.assertEqual(r['metric']['reported_delta_dbu'],0);self.assertEqual(r['next_actions'],[])
    def test_07_foreign_artifact_binding_quarantines_attribution(self):
        a,b,p=self.pair();p['after_binding']['database_sha256']='0'*64;r=review(a,b,p);self.assertEqual(r['exit_code'],2);self.assertEqual(r['changed_instances'],[]);self.assertIsNone(r['metric'])
    def test_08_foreign_configuration(self):
        a,b,p=self.pair();b['context']['configuration_ref']='other';p['after_binding']=binding(b);r=review(a,b,p);self.assertEqual(r['exit_code'],2);self.assertIsNone(r['metric'])
    def test_09_missing_object_correspondence(self):
        a,b,p=self.pair();p['correspondence_ref']=None;r=review(a,b,p);self.assertEqual(r['exit_code'],2);self.assertEqual(r['changed_instances'],[])
    def test_10_missing_relationship_basis(self):
        a,b,p=self.pair();b['context']['performance_basis_ref']=None;r=review(a,b,p);self.assertEqual(r['exit_code'],2);self.assertIn('missing_relationship_basis',[g['kind'] for g in r['gaps']])
    def test_11_missing_original_region_rationale(self):
        a,b,p=self.pair();p['region']['rationale_ref']=None;self.assertEqual(review(a,b,p)['exit_code'],2)
    def test_12_unspecified_required_claim_strength(self):
        a,b,p=self.pair();del p['required_claims']['throughput_latency'];self.assertEqual(review(a,b,p)['exit_code'],2)
    def test_13_stronger_claim_not_established_by_smaller_geometry(self):
        a,b,p=self.pair();p['required_claims']['congestion_improvement']=True;r=review(a,b,p)
        self.assertEqual(r['exit_code'],2);self.assertEqual(r['metric']['reported_delta_dbu'],-4000)
    def test_14_source_requirement_restore_changes_favorable_derived_record(self):
        a,b,p=self.pair('drop-and-intrude');p['region'].update(require_hard_blockage=False,require_clear_instances=False);self.assertEqual(review(a,b,p)['exit_code'],0)
        intent=read_json(self.root/'horizontal-access-intent.json');p['region'].update(require_hard_blockage=intent['required_hard_blockage'],require_clear_instances=intent['required_clear_region']);self.assertEqual(review(a,b,p)['exit_code'],1)
    def test_15_incomplete_obligation_inventory(self):
        a,b,p=self.pair();p['inputs_complete']=False;self.assertEqual(review(a,b,p)['exit_code'],2)
    def test_16_missing_native_report_rejected(self):
        root,ref=self.cloned();(root/ref/'native.jsonl').unlink()
        with self.assertRaisesRegex(ValueError,'Missing/linked'):load(root,ref)
    def test_17_changed_consumed_source_cannot_be_recaptured(self):
        root,ref=self.cloned();(root/ref/'design.v').write_text('module top;endmodule')
        with self.assertRaisesRegex(ValueError,'Consumed source changed'):load(root,ref)
    def test_18_changed_native_artifact_rejected(self):
        root,ref=self.cloned();(root/ref/'native.odb').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Native artifact changed'):load(root,ref)
    def test_19_truncated_native_export(self):
        root,ref=self.cloned();file=root/ref/'native.jsonl';file.write_text('\n'.join(file.read_text().splitlines()[:-1]))
        with self.assertRaisesRegex(ValueError,'Incomplete native export'):read_native(file)
    def test_20_duplicate_native_pin_rejected(self):
        root,ref=self.cloned();file=root/ref/'native.jsonl';lines=file.read_text().splitlines();lines.insert(-1,next(s for s in lines if s.startswith('["PIN"')));file.write_text('\n'.join(lines))
        with self.assertRaisesRegex(ValueError,'duplicate native pin'):read_native(file)
    def test_21_evidence_path_cannot_escape_root(self):
        with self.assertRaises(ValueError):folder(self.root,'../foreign')
    def test_22_duplicate_keys_and_nonfinite_records_rejected(self):
        for value in ('{"x":1,"x":2}','{"x":NaN}'):
            with self.assertRaises(ValueError):parse(value)
    def test_23_cli_no_overwrite(self):
        root,ref=self.cloned();out=root/'existing.json';out.write_text('retained')
        p=subprocess.run([sys.executable,str(MODULE/'physical_review.py'),'capture',str(root),ref,'--output',str(out)],capture_output=True,text=True)
        self.assertEqual(p.returncode,3);self.assertEqual(out.read_text(),'retained')
    def test_24_changed_native_phase_is_a_comparison_gap(self):
        a,b,p=self.pair();b['native']['cases']['test_mode']='0';r=review(a,b,p)
        self.assertEqual(r['exit_code'],2);self.assertEqual(r['experiment']['qualification'],'unqualified_reported_difference')
    def test_25_other_cell_move_is_not_part_of_one_intervention(self):
        a,b,p=self.pair();b['native']['instances']['gate']['box']=[5000,2000,6000,3000];r=review(a,b,p)
        self.assertEqual(r['exit_code'],1);self.assertIn('unplanned_placement_change',[f['kind'] for f in r['findings']]);self.assertEqual(r['experiment']['qualification'],'unqualified_reported_difference')
    def test_26_unrelated_constraint_change_requires_its_own_basis(self):
        a,b,p=self.pair();a['native']['blockages'].append({'box':[30000,30000,31000,31000],'soft':False});r=review(a,b,p)
        self.assertEqual(r['exit_code'],2);self.assertEqual(r['experiment']['qualification'],'unqualified_reported_difference')
    def test_27_master_change_is_outside_translation_profile(self):
        a,b,p=self.pair();b['native']['instances']['buffer']['master']='other';r=review(a,b,p);self.assertEqual(r['exit_code'],2)
        self.assertIn('change_outside_translation_profile',[g['kind'] for g in r['gaps']])
    def test_28_boundary_terminal_geometry_remains_unknown(self):
        _,b,_=self.pair();b['native']['net_bterms']=['boundary'];self.assertIn('boundary_terminal_geometry_not_qualified',metric(b)['geometry_gaps'])
    def test_29_missing_pin_position_is_not_zero_distance(self):
        _,b,_=self.pair();b['native']['pins']['buffer/Y']['position_known']=False;self.assertIn('selected_pin_position_unknown',metric(b)['geometry_gaps'])
    def test_30_absent_selected_path_stays_open(self):
        a,b,p=self.pair();b['native'].update(paths=[],path_count=0);self.assertEqual(review(a,b,p)['exit_code'],2)
    def test_31_stale_original_endpoint_selection(self):
        a,b,p=self.pair();p['selection']['endpoint_names']=['other/D'];r=review(a,b,p);self.assertEqual(r['exit_code'],2);self.assertIsNone(r['metric'])
    def test_32_setup_cannot_inject_native_commands(self):
        a,_,_=self.pair();a['context']['setup']['top']='top;exec unexpected'
        with self.assertRaises(ValueError):config(a['context'])
    def test_33_actual_cli_matches_review(self):
        path=self.root/'reviews/vertical-boundary-drop-and-intrude.policy.json';p=subprocess.run([sys.executable,str(MODULE/'physical_review.py'),'review',str(self.root),str(path)],capture_output=True,text=True)
        self.assertEqual(p.returncode,1,p.stderr);self.assertEqual(json.loads(p.stdout),read_json(self.root/'reviews/vertical-boundary-drop-and-intrude.report.json'))

if __name__=='__main__':unittest.main()
