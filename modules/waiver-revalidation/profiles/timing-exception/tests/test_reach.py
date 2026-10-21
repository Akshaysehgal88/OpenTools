"""Native saved-data controls and adversarial intent/correspondence checks."""
import copy,json,os,shutil,sys,tempfile,unittest
from pathlib import Path
PROFILE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROFILE));sys.path.insert(0,str(PROFILE/'examples'))
from reach_common import config,digest,read_json,save
from native_reach import capture,read_native
from reach_core import drift,inspect,markdown,snapshot,validate_contract
from fixture import context,rename_map

class Inputs(unittest.TestCase):
    def test_tcl_injection_rejected(self):
        c=context('shift-window','baseline');c['setup']['to_pattern']='capture*;exec bad'
        with self.assertRaises(ValueError):config(c)
    def test_unknown_case_stays_unset(self):
        value=config(context('clock-boundary','unknown-mode'))
        self.assertIn('set phase_cases {reset_n 1}',value);self.assertIn('independent_mode',value)
    def test_duplicate_json_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.json';p.write_text('{"scope":1,"scope":2}')
            with self.assertRaises(ValueError):read_json(p)
    def test_save_never_overwrites(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.json';save(p,{'original':True})
            with self.assertRaises(FileExistsError):save(p,{})
            self.assertEqual(read_json(p),{'original':True})
    def test_nonfinite_clock_rejected(self):
        c=context('shift-window','baseline');c['setup']['clocks'][0]['period_ns']=float('nan')
        with self.assertRaises(ValueError):config(c)
    def test_partial_native_export_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'native.jsonl';p.write_text('["HEADER","opentools.sta-exception-native.v1","x"]\n')
            with self.assertRaises(ValueError):read_native(p)

class NativePopulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value=os.environ.get('OPENTOOLS_STA_EXCEPTION_EXAMPLES')
        if not value:raise unittest.SkipTest('Set OPENTOOLS_STA_EXCEPTION_EXAMPLES to actual run_native.py output')
        cls.root=Path(value);cls.manifest=read_json(cls.root/'collection.json')
        if cls.manifest['native_OpenROAD_runs']!=14:raise ValueError('Complete 14-run native corpus required')
    def inputs(self,family='shift-window',case='baseline'):
        folder=self.root/(family+'-'+case);return read_json(folder/'contract.json'),read_json(folder/'evidence.json'),folder
    def review(self,family='shift-window',case='baseline'):
        c,e,p=self.inputs(family,case);return inspect(c,e,p)
    def compare(self,family,case,mapping=None):
        bc,be,bp=self.inputs(family);cc,ce,cp=self.inputs(family,case);return drift(bc,be,bp,cc,ce,cp,mapping)
    def test_both_native_contexts_baseline(self):
        for family in ('shift-window','clock-boundary'):
            r=self.review(family);self.assertEqual(r['status'],'BOUNDED_REACH_ACCOUNTED');self.assertEqual(r['counts']['before_setup_pairs'],1);self.assertEqual(r['counts']['after_setup_pairs'],0)
    def test_wildcard_expansion_masks_required_state(self):
        for family in ('shift-window','clock-boundary'):
            r=self.compare(family,'expanded');self.assertEqual(r['status'],'review_required');self.assertEqual(r['current']['counts']['masked_setup_pairs'],2)
            self.assertIn('population_expanded',{x['code'] for x in r['audit']['waivers'][0]['issues']});self.assertIn('required_setup_pair_masked',{x['code'] for x in r['current']['findings']})
    def test_reviewed_rename_preserves_meaning(self):
        for family in ('shift-window','clock-boundary'):
            r=self.compare(family,'renamed',rename_map(family));self.assertEqual(r['status'],'unchanged_within_scope');self.assertEqual(r['audit']['waivers'][0]['added'],[])
    def test_unmapped_rename_remains_review(self):
        r=self.compare('shift-window','renamed');self.assertEqual(r['status'],'review_required');self.assertEqual(len(r['audit']['waivers'][0]['added']),1);self.assertEqual(len(r['audit']['waivers'][0]['removed']),1)
    def test_same_count_wrong_role_not_hidden_by_mapping(self):
        for family in ('shift-window','clock-boundary'):
            r=self.compare(family,'retarget',rename_map(family,'retarget'));self.assertEqual(r['status'],'review_required');self.assertEqual(r['current']['counts']['masked_setup_pairs'],1)
            self.assertIn('finding_meaning_changed',{i['code'] for i in r['audit']['waivers'][0]['issues']});self.assertIn('masked_pair_outside_rationale',{i['code'] for i in r['current']['findings']})
    def test_mode_change_same_population_invalidates_premise(self):
        for family in ('shift-window','clock-boundary'):
            r=self.compare(family,'wrong-mode');self.assertEqual(r['status'],'review_required');self.assertEqual(r['current']['counts']['masked_setup_pairs'],1)
            self.assertIn('premise_does_not_hold',{i['code'] for i in r['audit']['waivers'][0]['issues']})
    def test_native_clock_boundary_becomes_synchronous(self):
        a=self.review('clock-boundary');b=self.review('clock-boundary','wrong-mode')
        self.assertEqual((a['paths'][0]['source_clock'],a['paths'][0]['destination_clock']),('launch_root','capture_root'));self.assertEqual((b['paths'][0]['source_clock'],b['paths'][0]['destination_clock']),('launch_root','launch_root'))
        self.assertIn('clock_premise_changed',{f['code'] for f in b['findings']})
    def test_unknown_mode_not_assumed_independent(self):
        for family in ('shift-window','clock-boundary'):
            r=self.review(family,'unknown-mode');self.assertEqual(r['status'],'INCOMPLETE');self.assertIn('missing_mode_premise',{f['code'] for f in r['gaps']})
        self.assertIsNone(self.review('clock-boundary','unknown-mode')['paths'][0]['destination_clock'])
    def test_untraced_matching_results_stay_unknown(self):
        for family in ('shift-window','clock-boundary'):
            c,e,p=self.inputs(family);uc,ue,up=self.inputs(family,'untraced');self.assertEqual(e['native']['phases'],ue['native']['phases']);self.assertEqual(e['native']['selectors'],ue['native']['selectors'])
            r=inspect(uc,ue,up);self.assertEqual(r['status'],'INCOMPLETE');self.assertFalse(r['population_complete'])
    def test_query_constructors_are_not_applied_exceptions(self):
        for item in self.manifest['cases']:
            n=read_json(self.root/item['run_ref']/'evidence.json')['native']
            if item['case']=='untraced':self.assertEqual(n['trace']['constructor_count'],0)
            else:self.assertEqual(n['trace']['application_count'],1);self.assertGreater(n['trace']['constructor_count'],2);self.assertEqual(len(n['applications']),1)
    def test_missing_path_intent_keeps_actual_population(self):
        c,e,p=self.inputs(case='expanded');c['intent']=[x for x in c['intent'] if x['destination_role']!='functional_state'];r=inspect(c,e,p)
        self.assertFalse(r['population_complete']);self.assertEqual(r['counts']['masked_setup_pairs'],2);self.assertIn('path_missing_independent_intent',{i['code'] for i in r['gaps']})
        s,_=snapshot(c,e,r);self.assertEqual(len(s['waivers'][0]['findings']),2)
    def test_stale_source_quarantines(self):
        c,e,p=self.inputs();c['expected']['sources']['design.v']='0'*64;r=inspect(c,e,p);self.assertEqual(r['status'],'QUARANTINED');self.assertEqual(r['paths'],[])
    def test_foreign_configuration_quarantines(self):
        c,e,p=self.inputs();c['expected']['configuration_ref']='foreign/config';r=inspect(c,e,p);self.assertEqual(r['status'],'QUARANTINED')
    def test_missing_original_fingerprint_is_gap(self):
        c,e,p=self.inputs();c['expected']['command_sha256']=None;r=inspect(c,e,p);self.assertEqual(r['status'],'INCOMPLETE')
    def test_missing_rationale_not_filled(self):
        c,e,p=self.inputs();c['exception']['rationale_ref']=None;r=inspect(c,e,p);self.assertEqual(r['status'],'INCOMPLETE')
    def test_edited_evidence_rejected(self):
        c,e,p=self.inputs();e['native']['phases']['after']['paths']=e['native']['phases']['before']['paths']
        with self.assertRaises(ValueError):inspect(c,e,p)
    def test_changed_original_artifact_rejected(self):
        c,e,p=self.inputs()
        with tempfile.TemporaryDirectory() as t:
            q=Path(t)/'run';shutil.copytree(p,q);(q/'consumed.sdc').write_text('# altered\n')
            with self.assertRaises(ValueError):inspect(c,e,q)
    def test_changed_native_producer_rejected(self):
        c,e,p=self.inputs()
        with tempfile.TemporaryDirectory() as t:
            q=Path(t)/'run';shutil.copytree(p,q);(q/'loader.tcl').write_text('# changed\n')
            with self.assertRaises(ValueError):capture(q,e['context'])
    def test_changed_original_intent_source_rejected(self):
        c,e,p=self.inputs()
        with tempfile.TemporaryDirectory() as t:
            q=Path(t)/'run';shutil.copytree(p,q);(q/'requirements.json').write_text('{}\n')
            with self.assertRaises(ValueError):inspect(c,e,q)
    def test_many_to_one_map_cannot_hide_expansion(self):
        bc,be,bp=self.inputs(case='expanded');cc,ce,cp=self.inputs(case='renamed');m=rename_map('shift-window');m['mappings'].append({**m['mappings'][0],'from':'launch/Q->capture_func/D'})
        with self.assertRaises(ValueError):drift(bc,be,bp,cc,ce,cp,m)
    def test_contract_cannot_erase_known_suppression(self):
        c,e,p=self.inputs(case='expanded');c['intent'][0]['timing_required']=False;c['intent'][1]['timing_required']=False;c['intent'][1]['destination_role']='shift_state';r=inspect(c,e,p)
        self.assertEqual(r['status'],'INCOMPLETE');self.assertEqual(r['counts']['masked_setup_pairs'],2);self.assertIn('intent_changed_after_capture',{f['code'] for f in r['gaps']})
    def test_missing_intent_field_rejected(self):
        c,_,_=self.inputs();del c['intent'][0]['timing_required']
        with self.assertRaises(ValueError):validate_contract(c)
    def test_markdown_carries_findings_and_limits(self):
        value=markdown(self.compare('clock-boundary','expanded'));self.assertIn('required_setup_pair_masked',value);self.assertIn('launch/Q-&gt;',value);self.assertIn('Not all structural paths',value)
    def test_markdown_escapes_supplied_intent(self):
        c,e,p=self.inputs();c['intent'][0]['source_clock']='<script>unsafe</script>';value=markdown(inspect(c,e,p));self.assertNotIn('<script>',value);self.assertIn('&lt;script&gt;',value)
    def test_all_raw_runs_reconstruct_exactly(self):
        for item in self.manifest['cases']:
            c,e,p=self.inputs(item['family'],item['case']);self.assertEqual(digest(capture(p,e['context'])),digest(e))

if __name__=='__main__':unittest.main()
