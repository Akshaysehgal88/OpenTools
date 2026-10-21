"""Native denominator, role-change, exclusion and interface-contract controls."""
import copy,os,shutil,sys,tempfile,unittest
from pathlib import Path
MODULE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(MODULE),str(MODULE/'examples')]
from endpoint_common import config,read_json,save
from native_endpoints import capture,read_report
from endpoint_core import markdown,review,validate_contract
from fixture import FAMILIES,context

class Inputs(unittest.TestCase):
    def test_injection_in_native_name_rejected(self):
        c=context('block-interface','complete');c['setup']['clock_port']='bus_clk;exec bad'
        with self.assertRaises(ValueError):config(c)
    def test_unknown_case_remains_unset(self):
        value=config(context('block-interface','unknown-mode'));self.assertIn('set phase_cases {power_ok 1 reset_n 1}',value);self.assertIn('run_enable',value)
    def test_nonfinite_period_rejected(self):
        c=context('block-interface','complete');c['setup']['period_ns']=float('nan')
        with self.assertRaises(ValueError):config(c)
    def test_duplicate_json_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.json';p.write_text('{"role":0,"role":1}')
            with self.assertRaises(ValueError):read_json(p)
    def test_original_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.json';save(p,{'original':True})
            with self.assertRaises(FileExistsError):save(p,{})
            self.assertEqual(read_json(p),{'original':True})
    def test_report_count_mismatch_not_trimmed(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'report.txt';p.write_text('Warning: There are 2 unconstrained endpoints.\n  one\n')
            with self.assertRaises(ValueError):read_report(p)

class NativeEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value=os.environ.get('OPENTOOLS_STA_ENDPOINT_NATIVE')
        if not value:raise unittest.SkipTest('Set OPENTOOLS_STA_ENDPOINT_NATIVE to actual run_native.py output')
        cls.root=Path(value);cls.collection=read_json(cls.root/'collection.json')
        if cls.collection['native_OpenROAD_runs']!=16:raise ValueError('Complete16-run native corpus required')
    def inputs(self,family='block-interface',case='complete'):
        p=self.root/(family+'-'+case);return read_json(p/'contract.json'),read_json(p/'evidence.json'),p
    def review(self,family='block-interface',case='complete'):
        c,e,p=self.inputs(family,case);return review(c,e,p)
    def test_complete_intent_accounts_for_reported_diagnostic_and_constant(self):
        for family in FAMILIES:
            r=self.review(family);self.assertEqual(r['status'],'BOUNDED_ENDPOINT_INTENT_ACCOUNTED');self.assertEqual(r['counts']['native_endpoints'],5);self.assertEqual(r['counts']['reported_unconstrained'],2);self.assertEqual(r['counts']['admitted_exemptions'],2)
    def test_missing_functional_output_delay_is_not_blanket_exempted(self):
        for family in FAMILIES:
            r=self.review(family,'missing-output');self.assertEqual(r['status'],'ENDPOINT_REVIEW_REQUIRED');self.assertEqual(r['counts']['reported_unconstrained'],3);self.assertIn('required_endpoint_unconstrained',{f['code'] for f in r['findings']});self.assertIn('required_output_delay_missing',{f['code'] for f in r['findings']})
    def test_clock_loss_is_visible_despite_existing_output_delay(self):
        for family in FAMILIES:
            r=self.review(family,'unclocked');self.assertEqual(r['status'],'ENDPOINT_REVIEW_REQUIRED');self.assertIn('capture/D',{f['endpoint'] for f in r['findings'] if f['code']=='required_endpoint_unconstrained'});self.assertEqual(r['counts']['admitted_exemptions'],0)
    def test_reported_unclocked_objects_remain_when_paths_disappear(self):
        r=self.review('block-interface','unclocked');self.assertEqual(r['counts']['native_endpoints'],5);self.assertEqual(r['counts']['reported_unconstrained'],5);self.assertEqual(r['counts']['native_path_representatives'],1);self.assertEqual(len(r['endpoints']),5)
        a=next(x for x in r['endpoints'] if x['endpoint']=='ack');self.assertEqual(a['native']['paths'],[]);self.assertTrue(a['native']['reported_unconstrained'])
    def test_output_delay_presence_does_not_prove_contract_value(self):
        for family in FAMILIES:
            r=self.review(family,'wrong-delay');self.assertEqual(r['counts']['reported_unconstrained'],2);self.assertIn('output_delay_contract_mismatch',{f['code'] for f in r['findings']});self.assertNotIn('required_output_delay_missing',{f['code'] for f in r['findings']})
    def test_role_change_same_native_population_invalidates_old_exemption(self):
        for family in FAMILIES:
            c,e,p=self.inputs(family);cc,ee,pp=self.inputs(family,'role-changed');a=copy.deepcopy(e['native']);b=copy.deepcopy(ee['native']);a.pop('run_ref');b.pop('run_ref');self.assertEqual(a,b)
            r=review(cc,ee,pp);self.assertEqual(r['counts']['reported_unconstrained'],2);self.assertIn('required_endpoint_has_exemption',{f['code'] for f in r['findings']});self.assertIn('exemption_premise_false',{f['code'] for f in r['findings']})
    def test_fixed_role_keeps_boot_requirement_and_native_delay(self):
        for family in FAMILIES:
            r=self.review(family,'role-fixed');self.assertEqual(r['status'],'BOUNDED_ENDPOINT_INTENT_ACCOUNTED');self.assertEqual(r['counts']['reported_unconstrained'],1);self.assertEqual(r['counts']['admitted_exemptions'],1)
            x=next(x for x in r['endpoints'] if x['intent']['role']=='boot_release');self.assertTrue(x['intent']['timing_required']);self.assertEqual(x['native']['paths'][0]['margin_ns'],3.0);self.assertIsNone(x['exemption'])
    def test_simulated_constant_is_separate_from_case_or_logic_assumption(self):
        for family in FAMILIES:
            r=self.review(family);x=next(x for x in r['endpoints'] if x['intent']['role']=='static_override_zero');self.assertEqual(x['native']['simulated'],'0');self.assertEqual(x['native']['case'],'X');self.assertEqual(x['native']['logic'],'X');self.assertEqual(x['native']['paths'],[]);self.assertTrue(x['exemption_admitted'])
    def test_wrong_tie_value_does_not_pass_from_no_path(self):
        for family in FAMILIES:
            r=self.review(family,'wrong-constant');self.assertIn('constant_intent_false',{f['code'] for f in r['findings']});self.assertIn('exemption_premise_false',{f['code'] for f in r['findings']});x=next(x for x in r['endpoints'] if x['intent']['role']=='static_override_zero');self.assertEqual(x['native']['simulated'],'1');self.assertEqual(x['native']['paths'],[]);self.assertFalse(x['exemption_admitted'])
    def test_unknown_mode_keeps_exemptions_unadmitted(self):
        for family in FAMILIES:
            r=self.review(family,'unknown-mode');self.assertEqual(r['status'],'INCOMPLETE');self.assertEqual(r['counts']['admitted_exemptions'],0);self.assertIn('unknown_mode_condition',{f['code'] for f in r['gaps']})
    def test_missing_native_role_map_entry_does_not_reduce_population(self):
        c,e,p=self.inputs();c['endpoints']=[x for x in c['endpoints'] if x['endpoint']!='capture/D'];r=review(c,e,p);self.assertEqual(r['counts']['native_endpoints'],5);self.assertIn('native_endpoint_missing_intent',{f['code'] for f in r['gaps']})
    def test_missing_exemption_approval_not_inferred_from_role(self):
        c,e,p=self.inputs();c['exemptions'][0]['approval_ref']=None;r=review(c,e,p);self.assertEqual(r['status'],'INCOMPLETE');self.assertIn('missing_exemption_basis',{f['code'] for f in r['gaps']})
    def test_missing_current_role_stays_unknown(self):
        c,e,p=self.inputs();c['endpoints'][0]['role']=None;r=review(c,e,p);self.assertEqual(r['status'],'INCOMPLETE');self.assertIn('missing_endpoint_intent',{f['code'] for f in r['gaps']})
    def test_input_assumption_mismatch_retained_as_bound_setup_difference(self):
        c,e,p=self.inputs();c['input_delays']['data']=.8;r=review(c,e,p);self.assertIn('input_delay_assumption_mismatch',{f['code'] for f in r['findings']})
    def test_stale_netlist_quarantined(self):
        c,e,p=self.inputs();c['expected']['sources']['design.v']='0'*64;r=review(c,e,p);self.assertEqual(r['status'],'QUARANTINED');self.assertEqual(r['endpoints'],[])
    def test_foreign_mode_quarantined(self):
        c,e,p=self.inputs();c['expected']['mode_ref']='foreign/mode';r=review(c,e,p);self.assertEqual(r['status'],'QUARANTINED')
    def test_missing_original_command_identity_kept_open(self):
        c,e,p=self.inputs();c['expected']['command_sha256']=None;r=review(c,e,p);self.assertEqual(r['status'],'INCOMPLETE')
    def test_original_contract_edit_is_not_current_intent_proof(self):
        c,e,p=self.inputs(case='role-changed')
        for x in c['endpoints']:
            if x['role']=='boot_release':x.update(role='diagnostic_trace',timing_required=False,source_clock=None,target_clock=None,output_delay_ns=None)
        r=review(c,e,p);self.assertIn('contract_changed_after_run',{f['code'] for f in r['gaps']})
    def test_bad_evidence_cannot_remove_reported_endpoint(self):
        c,e,p=self.inputs();e['native']['reported_unconstrained']=[]
        with self.assertRaises(ValueError):review(c,e,p)
    def test_changed_original_native_report_rejected(self):
        c,e,p=self.inputs()
        with tempfile.TemporaryDirectory() as t:
            q=Path(t)/'run';shutil.copytree(p,q);(q/'unconstrained.txt').write_text('')
            with self.assertRaises(ValueError):review(c,e,q)
    def test_changed_original_contract_rejected(self):
        c,e,p=self.inputs()
        with tempfile.TemporaryDirectory() as t:
            q=Path(t)/'run';shutil.copytree(p,q);(q/'contract.json').write_text('{}\n')
            with self.assertRaises(ValueError):capture(q,e['context'])
    def test_unconstrained_infinite_slack_not_serialized_as_numeric_pass(self):
        r=self.review();x=next(x for x in r['endpoints'] if x['intent']['role']=='diagnostic_trace');self.assertEqual(x['native']['paths'][0]['slack_native_ns'],'INF');self.assertTrue(x['native']['paths'][0]['unconstrained'])
    def test_duplicate_endpoint_roles_rejected(self):
        c,_,_=self.inputs();c['endpoints'].append(copy.deepcopy(c['endpoints'][0]))
        with self.assertRaises(ValueError):validate_contract(c)
    def test_register_margin_cannot_be_relabelled_output_delay(self):
        c,_,_=self.inputs();x=next(x for x in c['endpoints'] if x['kind']=='data');x['output_delay_ns']=.01
        with self.assertRaises(ValueError):validate_contract(c)
    def test_all_original_native_runs_reconstruct_exactly(self):
        for item in self.collection['cases']:
            p=self.root/item['run_ref'];e=read_json(p/'evidence.json');self.assertEqual(capture(p,e['context']),e)
    def test_markdown_keeps_receiving_owner_and_findings(self):
        value=markdown(self.review(case='role-changed'));self.assertIn('timing-owner',value);self.assertIn('required_endpoint_has_exemption',value);self.assertIn('not automatically a hardware defect',value)
    def test_markdown_escapes_untrusted_owner(self):
        c,e,p=self.inputs();c['owner_ref']='<script>unsafe</script>';value=markdown(review(c,e,p));self.assertNotIn('<script>',value);self.assertIn('&lt;script&gt;',value)

if __name__=='__main__':unittest.main()
