import copy,json,os
from pathlib import Path
import shutil,subprocess,sys,tempfile,unittest
MODULE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(MODULE));sys.path.insert(0,str(MODULE/'examples'))
from macro_common import exit_code,parse,read_json
from native_views import capture
from view_core import review
from reference_model import check
NATIVE=os.environ.get('OPENTOOLS_MACRO_NATIVE')
def kinds(r,key='findings'):return {f['kind'] for f in r[key]}

@unittest.skipUnless(NATIVE,'Set OPENTOOLS_MACRO_NATIVE to a retained example collection')
class ViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(NATIVE);cls.records={}
        for row in read_json(cls.root/'collection.json')['cases']:
            folder=cls.root/row['case'];e=capture(folder,read_json(folder/'context.json'));cls.records[row['case']]=(e,read_json(folder/'policy.json'),row)
    def pair(self,case='good',family='storage'):return copy.deepcopy(self.records[family+'-'+case][:2])
    def test_all_native_object_fields_match_independent_tables(self):
        for e,p,row in self.records.values():check(e,row['family'],row['selection'])
    def test_valid_view_set_and_supported_mirror_in_two_macro_classes(self):
        for family in ('storage','clock-control'):
            for case in ('good','valid-mirror'):self.assertEqual(exit_code(review(*self.pair(case,family))),0)
    def test_all_seeded_view_mismatches_are_retained(self):
        for e,p,row in self.records.values():
            if row['selection'] not in ('good','valid-mirror'):self.assertEqual(exit_code(review(e,p)),1)
    def test_power_connection_is_not_established_by_power_pin_name(self):
        r=review(*self.pair('wrong-supply'));self.assertIn('instance_pin_connection_mismatch',kinds(r))
    def test_same_physical_database_does_not_establish_same_timing_voltage(self):
        good,_=self.pair();bad,p=self.pair('voltage-change')
        self.assertEqual(good['file_sha256']['native.odb'],bad['file_sha256']['native.odb'])
        self.assertNotEqual(good['file_sha256']['macro.lib'],bad['file_sha256']['macro.lib'])
        self.assertIn('selected_characterization_point_mismatch',kinds(review(bad,p)))
    def test_physical_repair_direction_must_match_logical_and_timing_views(self):
        r=review(*self.pair('wrong-direction'));self.assertIn('physical_pin_role_mismatch',kinds(r))
    def test_orientation_requires_both_intent_and_native_symmetry(self):
        e,p=self.pair('wrong-orientation');p['allowed_orientations'].append('R90');r=review(e,p)
        self.assertNotIn('orientation_outside_contract',kinds(r));self.assertIn('orientation_not_supported_by_master_symmetry',kinds(r))
    def test_access_is_the_declared_window_not_a_blanket_pin_obs_rule(self):
        r=review(*self.pair('blocked-window'));self.assertIn('selected_access_window_obstructed',kinds(r))
        self.assertEqual(exit_code(review(*self.pair())),0)
    def test_touching_window_boundary_is_not_positive_area_overlap(self):
        e,p=self.pair();e['native']['obstructions']=[{'layer':'metal1','box':[250,1350,300,1550]}]
        self.assertNotIn('selected_access_window_obstructed',kinds(review(e,p)))
    def test_wrong_selected_timing_endpoints_are_not_hidden_by_pin_compatibility(self):
        r=review(*self.pair('arc-change'));self.assertIn('required_timing_endpoints_missing',kinds(r))
    def test_footprint_is_compared_with_database_units(self):
        r=review(*self.pair('footprint-change'));self.assertIn('macro_geometry_mismatch',kinds(r))
    def test_instance_wiring_is_compared_with_original_logical_correspondence(self):
        r=review(*self.pair('wrong-connection'));self.assertIn('instance_pin_connection_mismatch',kinds(r))
    def test_internal_liberty_state_ports_are_preserved_without_becoming_physical_pins(self):
        e,p=self.pair();self.assertEqual(e['native']['timing_library']['pins']['IQ']['direction'],'internal')
        self.assertNotIn('unreviewed_pin_population',kinds(review(e,p),'gaps'))
    def test_missing_revision_or_supply_basis_keeps_intake_open(self):
        e,p=self.pair();e['context']['revision_basis_ref']=None;e['context']['supply_basis_ref']=None
        r=review(e,p);self.assertEqual(exit_code(r),2);self.assertIn('missing_view_basis',kinds(r,'gaps'))
    def test_foreign_or_stale_scope_cannot_grant_view_acceptance(self):
        for k in ('revision_ref','corner_ref','configuration_ref','macro_ref'):
            e,p=self.pair();p['identity'][k]='foreign';r=review(e,p);self.assertEqual(exit_code(r),2);self.assertFalse(r['pins'])
    def test_selected_object_binding_is_independent_of_shared_file_digest(self):
        e,p=self.pair();p['selection']['logical_instance']='another_instance';r=review(e,p)
        self.assertEqual(exit_code(r),2);self.assertFalse(r['pins'])
    def test_sources_database_export_and_commands_have_independent_bindings(self):
        for key in ('source_sha256','database_sha256','native_export_sha256','logical_xml_sha256','native_command_sha256','logical_command_sha256'):
            e,p=self.pair();p[key]={} if key=='source_sha256' else '0'*64;self.assertEqual(exit_code(review(e,p)),2)
    def test_unreviewed_pin_population_is_not_silently_dropped(self):
        e,p=self.pair();p['pin_map']=[v for v in p['pin_map'] if v['physical']!='TEST_EN'];r=review(e,p)
        self.assertEqual(exit_code(r),2);self.assertIn('unreviewed_pin_population',kinds(r,'gaps'))
    def test_geometry_does_not_replace_required_signal_correspondence(self):
        e,p=self.pair();p['pin_map'][0]['width']=2
        self.assertIn('logical_width_mismatch',kinds(review(e,p)))
    def test_unsupported_requested_claims_remain_open(self):
        for claim in ('timing_polarity','liberty_pg_associations','memory_behavior','clock_waveform_safety','DRC_LVS'):
            e,p=self.pair();p['required_claims'][claim]=True;r=review(e,p);self.assertEqual(exit_code(r),2);self.assertIn('requested_claim_unqualified',kinds(r,'gaps'))
    def test_unspecified_claim_strength_is_not_assumed_false(self):
        e,p=self.pair();p['required_claims'].pop('DRC_LVS');self.assertEqual(exit_code(review(e,p)),2)
    def test_known_violation_is_preserved_with_missing_evidence(self):
        e,p=self.pair('wrong-supply');p['owner_ref']=None;r=review(e,p)
        self.assertEqual(exit_code(r),1);self.assertIn('missing_intake_basis',kinds(r,'gaps'))
    def test_boolean_evidence_references_are_invalid(self):
        e,p=self.pair();p['access_windows'][0]['source_ref']=True
        with self.assertRaises(ValueError):review(e,p)
    def test_unknown_loader_cannot_be_treated_as_the_qualified_batch(self):
        e,p=self.pair();e['qualified_batch_loader']=False;r=review(e,p);self.assertEqual(exit_code(r),2);self.assertFalse(r['pins'])
    def test_truncated_or_tampered_native_database_and_export_are_invalid(self):
        original=self.root/'storage-good'
        for name in ('native.jsonl','native.odb'):
            with tempfile.TemporaryDirectory() as temp:
                folder=Path(temp)/'run';shutil.copytree(original,folder);path=folder/name
                if name.endswith('jsonl'):path.write_text(path.read_text().replace('["END"]',''))
                else:
                    with path.open('ab') as f:f.write(b'changed')
                with self.assertRaises(ValueError):capture(folder,read_json(folder/'context.json'))
    def test_duplicate_nonfinite_and_bad_input_shapes_are_rejected(self):
        for source in ('{"x":1,"x":2}','{"x":NaN}'):
            with self.assertRaises(ValueError):parse(source)
    def test_cli_recaptures_original_native_views_and_preserves_finding_exit(self):
        for case,code in [('good',0),('wrong-supply',1)]:
            folder=self.root/('storage-'+case);p=subprocess.run([sys.executable,str(MODULE/'view_review.py'),'review',str(folder),str(folder/'context.json'),str(folder/'policy.json')],capture_output=True,text=True)
            self.assertEqual(p.returncode,code,p.stderr);self.assertEqual(json.loads(p.stdout)['native_result']['logical_elaboration'],'PASS')

if __name__=='__main__':unittest.main()
