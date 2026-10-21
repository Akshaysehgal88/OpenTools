"""Original-denominator and native-identity scenario coverage controls."""
import copy,os,shutil,sys,tempfile,unittest
from pathlib import Path
PROFILE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(PROFILE),str(PROFILE/'examples')]
from scenario_common import config,digest,read_json,save
from native_scenario import capture,load,snapshot
from scenario_core import markdown,review,validate_plan
from fixture import context,FAMILIES

class Inputs(unittest.TestCase):
    def test_native_name_injection_rejected(self):
        c=context('wake-sequence','wake','low_voltage');c['setup']['operating_condition']='qualified;exec bad'
        with self.assertRaises(ValueError):config(c)
    def test_case_unknown_not_forced_to_zero(self):
        c=context('capture-window','capture','nominal','unknown-mode');s=config(c);self.assertIn('set phase_cases {power_ok 1 reset_n 1}',s);self.assertIn('set inspected_cases {mode_select power_ok reset_n}',s)
    def test_nonfinite_period_rejected(self):
        c=context('wake-sequence','wake','low_voltage');c['setup']['period_ns']=float('nan')
        with self.assertRaises(ValueError):config(c)
    def test_duplicate_json_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.json';p.write_text('{"mode":1,"mode":2}')
            with self.assertRaises(ValueError):read_json(p)
    def test_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.json';save(p,{'original':True})
            with self.assertRaises(FileExistsError):save(p,{})
            self.assertEqual(read_json(p),{'original':True})

class NativeScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value=os.environ.get('OPENTOOLS_STA_SCENARIO_NATIVE')
        if not value:raise unittest.SkipTest('Set OPENTOOLS_STA_SCENARIO_NATIVE to actual run_native.py output')
        cls.root=Path(value);cls.collection=read_json(cls.root/'collection.json')
        if cls.collection['native_OpenROAD_runs']!=18:raise ValueError('Complete actual18-run native corpus required')
    def inputs(self,family='wake-sequence',variant='complete'):
        req=self.root/'requirements';p=read_json(req/(family+('.timing-failure-plan.json' if variant=='timing-failure' else '.plan.json')));c=read_json(req/(family+'.'+variant+'.corpus.json'));return p,c
    def review(self,family='wake-sequence',variant='complete'):
        p,c=self.inputs(family,variant);return review(self.root,p,c)
    def test_both_contexts_complete_and_one_explicit_nonapplicable(self):
        for family in FAMILIES:
            r=self.review(family);self.assertEqual(r['status'],'DECLARED_SCENARIOS_ACCOUNTED');self.assertEqual(r['counts']['covered_obligations'],3);self.assertEqual(r['counts']['source_declared_nonapplicable'],1)
    def test_unchanged_run_count_can_omit_new_mode(self):
        for family in FAMILIES:
            a=self.review(family);b=self.review(family,'omitted');self.assertEqual(a['counts']['selected_runs'],b['counts']['selected_runs']);self.assertEqual(b['counts']['selected_runs'],3);self.assertEqual(b['counts']['covered_obligations'],2)
            self.assertTrue(all(x['native_outcome']=='pass' for x in b['native_runs']));self.assertIn('required_scenario_missing',{f['code'] for f in b['findings']})
    def test_corner_label_cannot_substitute_for_actual_library_PVT(self):
        for family in FAMILIES:
            r=self.review(family,'wrong-library');self.assertEqual(r['counts']['covered_obligations'],2);self.assertIn('selected_scenario_inapplicable',{f['code'] for f in r['findings']})
            row=next(o for o in r['obligations'] if o['candidate_audits'] and o['candidate_audits'][0]['status']=='inapplicable');self.assertIn('Claim-relevant field differs: library.pvt',row['candidate_audits'][0]['mismatches']);self.assertIn('Claim-relevant field differs: library.source_sha256',row['candidate_audits'][0]['mismatches'])
    def test_native_mode_case_must_match_original_requirement(self):
        for family in FAMILIES:
            r=self.review(family,'wrong-mode');self.assertEqual(r['status'],'SCENARIO_REVIEW_REQUIRED');self.assertEqual(r['counts']['covered_obligations'],2)
            self.assertTrue(any('Claim-relevant field differs: native.cases' in a['mismatches'] for o in r['obligations'] for a in o['candidate_audits']))
    def test_unknown_mode_case_retains_unresolved_scope(self):
        for family in FAMILIES:
            r=self.review(family,'unknown-mode');self.assertEqual(r['status'],'INCOMPLETE');self.assertEqual(r['counts']['covered_obligations'],2);self.assertIn('scenario_evidence_unresolved',{f['code'] for f in r['gaps']})
    def test_native_timing_failure_is_present_evidence_not_missing_scenario(self):
        for family in FAMILIES:
            r=self.review(family,'timing-failure');self.assertEqual(r['counts']['covered_obligations'],3);self.assertIn('observed_selected_setup_violation',{f['code'] for f in r['findings']});self.assertNotIn('required_scenario_missing',{f['code'] for f in r['findings']});self.assertTrue(any(x['native_outcome']=='fail' for x in r['native_runs']))
    def test_valid_exclusion_does_not_schedule_cartesian_combinations(self):
        p,c=self.inputs();before=copy.deepcopy(c);r=review(self.root,p,c);self.assertEqual(c,before);self.assertEqual(len(c['runs']),3);self.assertEqual(len(p['obligations']),4);self.assertEqual(r['counts']['source_declared_nonapplicable'],1)
    def test_missing_exclusion_basis_cannot_close_denominator(self):
        p,c=self.inputs();p['obligations'][-1]['exclusion_ref']=None;r=review(self.root,p,c);self.assertEqual(r['status'],'INCOMPLETE');self.assertEqual(r['counts']['source_declared_nonapplicable'],0)
    def test_unidentified_combination_cannot_be_excluded(self):
        p,c=self.inputs();p['obligations'][-1]['required_fields']['library.pvt']['value']=None;r=review(self.root,p,c);self.assertEqual(r['status'],'INCOMPLETE');self.assertIn('unresolved_exclusion_identity',{f['code'] for f in r['gaps']})
    def test_unknown_applicability_not_assumed_required_or_excluded(self):
        p,c=self.inputs();p['obligations'][-1]['applicability']=None;r=review(self.root,p,c);self.assertEqual(r['status'],'INCOMPLETE');self.assertIn('unknown_scenario_applicability',{f['code'] for f in r['gaps']})
    def test_foreign_configuration_not_admitted(self):
        p,c=self.inputs();p['configuration_ref']='foreign/config';r=review(self.root,p,c);self.assertEqual(r['counts']['admitted_runs'],0);self.assertEqual(r['counts']['covered_obligations'],0);self.assertTrue(r['quarantine'])
    def test_stale_netlist_source_cannot_support_required_scenario(self):
        p,c=self.inputs()
        for o in p['obligations']:o['required_fields']['implementation.source_sha256']['value']='0'*64
        r=review(self.root,p,c);self.assertEqual(r['counts']['covered_obligations'],0);self.assertTrue(any('implementation.source_sha256' in m for o in r['obligations'] for a in o['candidate_audits'] for m in a['mismatches']))
    def test_different_RC_request_cannot_reuse_unannotated_model(self):
        p,c=self.inputs()
        for o in p['obligations']:o['required_fields']['rc.view']['value']='extracted_post_route'
        r=review(self.root,p,c);self.assertEqual(r['counts']['covered_obligations'],0)
    def test_power_state_request_not_inferred_from_library_voltage(self):
        p,c=self.inputs();p['obligations'][2]['required_fields']['power.state']['value']='retention_off';r=review(self.root,p,c);self.assertEqual(r['counts']['covered_obligations'],2)
    def test_required_field_source_missing_stays_unknown(self):
        p,c=self.inputs();p['obligations'][2]['required_fields']['clock.definition']['evidence_ref']=None;r=review(self.root,p,c);self.assertEqual(r['status'],'INCOMPLETE');self.assertEqual(r['counts']['covered_obligations'],2)
    def test_required_identity_field_cannot_be_dropped(self):
        p,_=self.inputs();del p['obligations'][0]['required_fields']['library.source_sha256']
        with self.assertRaises(ValueError):validate_plan(p)
    def test_duplicate_obligation_ids_rejected(self):
        p,_=self.inputs();p['obligations'][1]['id']=p['obligations'][0]['id']
        with self.assertRaises(ValueError):validate_plan(p)
    def test_duplicate_run_alias_not_additional_evidence(self):
        p,c=self.inputs();c['runs'].append(c['runs'][0])
        with self.assertRaises(ValueError):review(self.root,p,c)
    def test_added_stronger_field_remains_unresolved(self):
        p,c=self.inputs();p['obligations'][2]['required_fields']['hold.complete']={'value':True,'evidence_ref':'original/stronger-request'};r=review(self.root,p,c);self.assertEqual(r['status'],'INCOMPLETE');self.assertEqual(r['counts']['covered_obligations'],2)
    def test_missing_plan_owner_keeps_handoff_open(self):
        p,c=self.inputs();p['owner_ref']=None;r=review(self.root,p,c);self.assertEqual(r['status'],'INCOMPLETE')
    def test_changed_native_artifact_rejected(self):
        _,c=self.inputs();ref=c['runs'][0]
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/ref;shutil.copytree(self.root/ref,p);(p/'native.jsonl').write_text('[]\n')
            with self.assertRaises(ValueError):load(t,ref)
    def test_changed_consumed_library_rejected(self):
        _,c=self.inputs();ref=c['runs'][0]
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/ref;shutil.copytree(self.root/ref,p);(p/'cells.lib').write_text('# changed\n')
            with self.assertRaises(ValueError):load(t,ref)
    def test_changed_original_context_rejected(self):
        _,c=self.inputs();ref=c['runs'][0]
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/ref;shutil.copytree(self.root/ref,p);ctx=read_json(p/'context.json');ctx['scenario']['power_state']='foreign';(p/'context.json').write_text(__import__('json').dumps(ctx))
            with self.assertRaises(ValueError):load(t,ref)
    def test_all_raw_native_runs_reconstruct_exactly(self):
        for item in self.collection['cases']:
            e=load(self.root,item['run_ref']);self.assertEqual(e,read_json(self.root/item['run_ref']/'evidence.json'));self.assertEqual(snapshot(e),read_json(self.root/item['run_ref']/'snapshot.json'))
    def test_markdown_retains_owner_native_failure_and_limits(self):
        value=markdown(self.review('capture-window','timing-failure'));self.assertIn('scenario-review-owner',value);self.assertIn('SELECTED_MAX_SETUP_REPRESENTATIVE FAIL',value);self.assertIn('observed_selected_setup_violation',value);self.assertIn('STA signoff',value)
    def test_markdown_escapes_untrusted_role_text(self):
        p,c=self.inputs();p['owner_ref']='<script>unsafe</script>';value=markdown(review(self.root,p,c));self.assertNotIn('<script>',value);self.assertIn('&lt;script&gt;',value)

if __name__=='__main__':unittest.main()
