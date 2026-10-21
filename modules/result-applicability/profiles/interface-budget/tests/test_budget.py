"""Native block/top budget, identity and source-preserving review controls."""
import copy,json,os,shutil,sys,tempfile,unittest
from pathlib import Path
PROFILE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(PROFILE),str(PROFILE/'examples')]
from budget_common import config,read_json,save
from budget_core import markdown,projection,review,validate_contract
from native_budget import load,snapshot
from fixture import context,FAMILIES

class Inputs(unittest.TestCase):
    def test_tcl_injection_rejected(self):
        c=context('rising-cycle','coherent','top');c['setup']['clock_name']='clk;exec bad'
        with self.assertRaises(ValueError):config(c)
    def test_nonfinite_period_rejected(self):
        c=context('rising-cycle','coherent','top');c['setup']['period_ns']=float('nan')
        with self.assertRaises(ValueError):config(c)
    def test_unknown_case_not_forced(self):
        c=context('rising-cycle','unknown-mode','top');s=config(c);self.assertIn('set phase_cases {reset_n 1}',s);self.assertIn('set inspected_cases {mode reset_n}',s)
    def test_duplicate_json_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x';p.write_text('{"edge":0,"edge":1}')
            with self.assertRaises(ValueError):read_json(p)
    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x';save(p,{'original':True})
            with self.assertRaises(FileExistsError):save(p,{})
            self.assertEqual(read_json(p),{'original':True})

class NativeBudget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value=os.environ.get('OPENTOOLS_INTERFACE_BUDGET_NATIVE')
        if not value:raise unittest.SkipTest('Set OPENTOOLS_INTERFACE_BUDGET_NATIVE to the actual run_native.py corpus')
        cls.root=Path(value);cls.collection=read_json(cls.root/'collection.json')
        if cls.collection['native_OpenROAD_runs']!=42:raise ValueError('Complete actual42-view corpus required')
    def contract(self,case='coherent',family='rising-cycle'):return read_json(self.root/'packets'/(family+'-'+case+'.json'))
    def run_review(self,case='coherent',family='rising-cycle'):return review(self.root,self.contract(case,family))
    def test_both_reference_contexts_agree(self):
        for f in FAMILIES:
            r=self.run_review(family=f);self.assertEqual(r['status'],'BOUNDED_INTERFACE_AGREEMENT');self.assertTrue(r['projection']['complete']);self.assertTrue(all(r['relationships'].values()))
    def test_individually_passing_blocks_can_fail_integration(self):
        for f in FAMILIES:
            r=self.run_review('permissive',f);self.assertEqual([r['native_views'][v]['native_result']['outcome'] for v in ('upstream','downstream','top')],['pass','pass','fail']);self.assertIn('handoff_budget_disagrees',{x['code'] for x in r['findings']});self.assertAlmostEqual(r['native_views']['top']['path']['slack_ns'],-.14)
    def test_agreement_does_not_erase_timing_debt(self):
        for f in FAMILIES:
            r=self.run_review('coherent-slow',f);self.assertTrue(r['relationships']['handoff_deadline_matches_downstream_assumption']);self.assertEqual(r['counts']['native_failed_views'],3);self.assertIn('observed_selected_timing_failure',{x['code'] for x in r['findings']})
    def test_native_load_not_inferred_from_unchanged_slack(self):
        r=self.run_review('wrong-load');self.assertTrue(all(v['native_result']['outcome']=='pass' for v in r['native_views'].values()));self.assertFalse(r['relationships']['upstream_load_matches_top']);self.assertIn('external_load_not_projected',{x['code'] for x in r['findings']})
    def test_same_period_wrong_reference_edge_rejected(self):
        for f in FAMILIES:
            r=self.run_review('wrong-reference',f);self.assertFalse(r['relationships']['capture_requirement_matches_top']);self.assertIn('capture_reference_not_projected',{x['code'] for x in r['findings']})
    def test_library_label_does_not_establish_common_model(self):
        r=self.run_review('wrong-model');self.assertFalse(r['relationships']['native_model_and_projection_admitted']);self.assertIn('cross_view_composition_unestablished',{x['code'] for x in r['gaps']});self.assertIn('Claim-relevant field differs: library.source_sha256',r['native_views']['upstream']['audit']['mismatches'])
    def test_unknown_mode_remains_unresolved(self):
        r=self.run_review('unknown-mode');self.assertEqual(r['status'],'INCOMPLETE');self.assertIsNone(load(self.root,'rising-cycle-unknown-mode-top')['native']['cases']['mode']);self.assertFalse(r['relationships']['native_model_and_projection_admitted'])
    def test_rewriting_expected_models_cannot_authorize_cross_view_pooling(self):
        c=self.contract('wrong-model');e=load(self.root,c['views']['upstream']['run_ref']);c['views']['upstream']['required_fields']['library.source_sha256']['value']=e['source_sha256']['cells.lib'];r=review(self.root,c);self.assertFalse(r['relationships']['actual_common_model']);self.assertFalse(r['relationships']['native_model_and_projection_admitted']);self.assertIn('native_cross_view_model_mismatch',{x['code'] for x in r['findings']})
    def test_half_cycle_uses_edge_time_not_period(self):
        r=self.run_review(family='opposite-edge');p=r['native_views']['top']['path'];self.assertEqual(p['target_time_ns'],1.0);self.assertEqual(p['target_phase_ns'],1.0);self.assertEqual(r['native_views']['top']['context']['setup']['period_ns'],2.0);self.assertEqual(r['native_views']['top']['report']['target_edge']['transition'],'fall')
    def test_missing_view_keeps_composition_open(self):
        c=self.contract();c['views']['top']['run_ref']=None;r=review(self.root,c);self.assertEqual(r['status'],'INCOMPLETE');self.assertIn('missing_native_view',{x['code'] for x in r['gaps']})
    def test_foreign_scope_quarantined(self):
        c=self.contract();c['scope_ref']='foreign/interface';r=review(self.root,c);self.assertEqual(r['counts']['admitted_identity_views'],0);self.assertTrue(r['quarantine'])
    def test_stale_expected_source_quarantined(self):
        c=self.contract();c['views']['upstream']['sources']['design.v']='0'*64;r=review(self.root,c);self.assertIn('stale_or_foreign_source',{x['code'] for x in r['quarantine']})
    def test_foreign_invocation_quarantined(self):
        c=self.contract();c['views']['top']['command_sha256']='0'*64;r=review(self.root,c);self.assertIn('foreign_native_command',{x['code'] for x in r['quarantine']})
    def test_missing_original_owner_not_closed(self):
        c=self.contract();c['owner_ref']=None;r=review(self.root,c);self.assertEqual(r['status'],'INCOMPLETE')
    def test_missing_clock_mapping_prevents_composition(self):
        c=self.contract();c['clock_mapping_ref']=None;r=review(self.root,c);self.assertFalse(r['relationships']['native_model_and_projection_admitted'])
    def test_changed_allocation_cannot_rewrite_original_run(self):
        c=self.contract();c['handoff_deadline_ns']=.9;r=review(self.root,c);self.assertIn('contract_changed_after_execution',{x['code'] for x in r['gaps']});self.assertIn('original_handoff_allocation_not_met',{x['code'] for x in r['findings']})
    def test_stronger_hold_claim_remains_unknown(self):
        c=self.contract();c['views']['top']['required_fields']['hold.all_paths']={'value':True,'evidence_ref':'original/stronger-request'};r=review(self.root,c);self.assertEqual(r['status'],'INCOMPLETE');self.assertIn('Missing observed or requested evidence: hold.all_paths',r['native_views']['top']['audit']['unknowns'])
    def test_required_model_field_cannot_be_removed(self):
        c=self.contract();del c['views']['upstream']['required_fields']['library.source_sha256']
        with self.assertRaises(ValueError):validate_contract(c)
    def test_shared_projected_cell_rejected(self):
        c=self.contract();c['maps']['downstream']['d0']='a0'
        with self.assertRaises(ValueError):validate_contract(c)
    def test_complete_native_cones_not_just_endpoints(self):
        c=self.contract();es={v:load(self.root,b['run_ref']) for v,b in c['views'].items()};es['top']['native']['pins']['a1/A']['net']='payload';p=projection(c,es);self.assertFalse(p['complete']);self.assertIn('block_connectivity_not_projected',{x['code'] for x in p['issues']})
    def test_extra_top_cell_prevents_complete_projection(self):
        c=self.contract();es={v:load(self.root,b['run_ref']) for v,b in c['views'].items()};es['top']['native']['cells']['unmapped']='ECO_BUF';p=projection(c,es);self.assertFalse(p['complete'])
    def test_disconnected_boundary_is_not_projected(self):
        c=self.contract();es={v:load(self.root,b['run_ref']) for v,b in c['views'].items()};es['top']['native']['pins']['b0/A']['net']='foreign';p=projection(c,es);self.assertFalse(p['boundary_connected'])
    def changed(self,name,value):
        ref='rising-cycle-coherent-upstream'
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/ref;shutil.copytree(self.root/ref,p);(p/name).write_text(value)
            with self.assertRaises(ValueError):load(t,ref)
    def test_changed_native_artifact_rejected(self):self.changed('native.jsonl','[]\n')
    def test_changed_consumed_library_rejected(self):self.changed('cells.lib','changed\n')
    def test_changed_original_context_rejected(self):self.changed('context.json','{}')
    def test_changed_completion_log_rejected(self):self.changed('stdout.txt','no marker')
    def test_missing_original_report_rejected(self):
        ref='rising-cycle-coherent-top'
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/ref;shutil.copytree(self.root/ref,p);(p/'path.txt').unlink()
            with self.assertRaises(ValueError):load(t,ref)
    def test_all_native_frames_reconstruct_exactly(self):
        for item in self.collection['cases']:
            ref=item['run_ref'];e=load(self.root,ref);self.assertEqual(e,read_json(self.root/ref/'evidence.json'));self.assertEqual(snapshot(e),read_json(self.root/ref/'snapshot.json'))
    def test_markdown_preserves_failure_owner_limits(self):
        s=markdown(self.run_review('permissive'));self.assertIn('budget-owner',s);self.assertIn('SELECTED_MAX_SETUP FAIL',s);self.assertIn('do not establish all-path timing, functional equivalence',s)
    def test_markdown_escapes_untrusted_text(self):
        c=self.contract();c['owner_ref']='<script>bad|owner</script>';s=markdown(review(self.root,c));self.assertNotIn('<script>',s);self.assertIn('&lt;script&gt;bad&#124;owner',s)
    def test_review_does_not_mutate_original_contract(self):
        c=self.contract('permissive');before=copy.deepcopy(c);review(self.root,c);self.assertEqual(c,before)

if __name__=='__main__':unittest.main()
