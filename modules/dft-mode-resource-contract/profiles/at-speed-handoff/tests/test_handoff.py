import copy,os,subprocess,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(HERE),str(HERE/'examples')]
from occ_common import contained,read_json
from native_occ import capture,consumed_sdc,revalidate,resources,xml_binding
from occ_core import contract,pulse_spans,review
from reference_model import check_collection

class Records(unittest.TestCase):
    def test_duplicate_json_and_nonfinite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json'
            for value in ('{"a":1,"a":2}','{"time":NaN}'):
                p.write_text(value)
                with self.subTest(value=value),self.assertRaises(ValueError):read_json(p)
    def test_path_boundary(self):
        for value in ('../x','x/../y','C:/x','/x','x\\y','x//y','./x'):
            with self.subTest(value=value),self.assertRaises(ValueError):contained(HERE,value)
    def test_no_tcl_evaluation(self):
        with self.assertRaises(ValueError):consumed_sdc('exec touch hidden-file')
    def test_duplicate_native_cases(self):
        with self.assertRaises(ValueError):resources('FORMAT opentools.occ-sta.v1\nCASE reset X\nCASE reset 1\nOPENTOOLS_NATIVE_OCC_STA_COMPLETE')
    def test_sampled_widths_and_unclosed_pulse(self):
        f=[{'tick_ns':i,'clock':v} for i,v in enumerate((0,1,1,0,1))];self.assertEqual(pulse_spans(f,'clock'),[{'rise_ns':1,'fall_ns':3},{'rise_ns':4,'fall_ns':None}])

@unittest.skipUnless(os.environ.get('OPENTOOLS_OCC_EXAMPLE'),'Set OPENTOOLS_OCC_EXAMPLE to the generated native collection')
class Native(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(os.environ['OPENTOOLS_OCC_EXAMPLE']).resolve();cls.base=cls.root/'scan-window-capture-good';cls.c=read_json(cls.base/'contract.json');cls.e=read_json(cls.base/'evidence.json')
    def packet(self,case):
        f=self.root/case;return read_json(f/'contract.json'),read_json(f/'evidence.json')
    def test_full_native_matrix_and_independent_reference(self):
        r=check_collection(self.root);self.assertEqual(r['totals'],{'samples':7516,'checks':318,'failures':20,'pulses':80});counts={}
        for case in read_json(self.root/'collection.json')['cases']:
            c,e=self.packet(case['case']);r=review(c,e,self.root);self.assertEqual(r,read_json(self.root/case['case']/'review.json'));counts[r['status']]=counts.get(r['status'],0)+1
        self.assertEqual(counts,{'BOUNDED_RECIPE_ALIGNED':6,'ALIGNMENT_REVIEW_REQUIRED':18,'INCOMPLETE':4})
    def test_shift_exception_is_permitted_in_shift(self):
        c,e=self.packet('scan-window-shift-valid');r=review(c,e,self.root);self.assertTrue(e['sta']['consumed_sdc']['false_paths']);self.assertEqual(r['status'],'BOUNDED_RECIPE_ALIGNED')
    def test_conservative_shift_without_false_path(self):
        c,e=self.packet('scan-window-shift-conservative');r=review(c,e,self.root);self.assertEqual(r['native_selected_path_probe']['with_consumed_constraints'],1);self.assertEqual(r['status'],'BOUNDED_RECIPE_ALIGNED')
    def test_capture_exception_has_native_suppression_witness(self):
        c,e=self.packet('scan-window-capture-shift-exception');r=review(c,e,self.root);self.assertEqual((r['native_sta_status'],r['native_behavior_status']),('COMPLETE','PASS'));self.assertEqual(r['native_selected_path_probe'],{'without_selected_exception':1,'with_consumed_constraints':0});self.assertIn('native_path_suppression_witness',{f['code'] for f in r['findings']})
    def test_correct_edge_value_can_have_late_guard(self):
        c,e=self.packet('scan-window-capture-late-release');r=review(c,e,self.root);first=next(g for g in r['control_guards'] if g['tick_ns']==25);self.assertIn('scan_enable guard',first['mismatches']);frame=e['behavior']['frames'][25];self.assertEqual(frame['scan_enable'],0)
    def test_stronger_independent_guard_overrides_native_pass(self):
        c,e=self.packet('scan-window-capture-release-boundary');r=review(c,e,self.root);self.assertEqual(r['native_behavior_status'],'PASS');self.assertIn('observed_control_mismatch',{f['code'] for f in r['findings']})
    def test_native_failure_is_retained(self):
        c,e=self.packet('scan-window-capture-missing');r=review(c,e,self.root);self.assertEqual(r['native_behavior_status'],'FAIL');self.assertIn('native_behavior_failure',{f['code'] for f in r['findings']})
    def test_native_unknown_not_filled_from_passing_trace(self):
        for suffix in ('unknown-reset','unknown-se'):
            c,e=self.packet('scan-window-capture-'+suffix);r=review(c,e,self.root);self.assertEqual((r['status'],r['native_behavior_status']),('INCOMPLETE','PASS'))
    def test_actual_sta_period_compared(self):
        c,e=self.packet('test-window-capture-wrong-sta-period');r=review(c,e,self.root);self.assertIn('sta_period_mismatch',{f['code'] for f in r['findings']})
    def test_opposite_reset_and_other_period(self):
        c,e=self.packet('test-window-capture-good');r=review(c,e,self.root);self.assertEqual(c['recipe']['reset_released'],0);self.assertEqual(r['observed_pulses_ns'],[40,56]);self.assertEqual(r['status'],'BOUNDED_RECIPE_ALIGNED')
    def test_native_atpg_claim_remains_open(self):
        c=copy.deepcopy(self.c);c['recipe']['require_native_atpg']=True;r=review(c,self.e,self.root);self.assertEqual(r['status'],'INCOMPLETE');self.assertIn('native_atpg_not_qualified',{g['code'] for g in r['gaps']})
    def test_missing_owner_remains_open(self):
        c=copy.deepcopy(self.c);c['recipe']['owner_ref']=None;self.assertEqual(review(c,self.e,self.root)['status'],'INCOMPLETE')
    def test_foreign_phase_quarantined_before_attribution(self):
        c,e=self.packet('scan-window-capture-missing');c['expected']['phase']='shift';r=review(c,e,self.root);self.assertEqual(r['status'],'QUARANTINED');self.assertEqual(r['findings'],[])
    def test_stale_shared_source_quarantined(self):
        c=copy.deepcopy(self.c);c['expected']['sta_sources']['unit.v']='0'*64;self.assertEqual(review(c,self.e,self.root)['status'],'QUARANTINED')
    def test_missing_expected_source_remains_unknown(self):
        c=copy.deepcopy(self.c);c['expected']['behavior_sources']['main.cpp']=None;self.assertEqual(review(c,self.e,self.root)['status'],'INCOMPLETE')
    def test_broader_window_does_not_become_missing_pulse(self):
        c=copy.deepcopy(self.c);c['recipe']['pulse_edge_indices']=[20,21];r=review(c,self.e,self.root);self.assertIn('recipe_window_short',{g['code'] for g in r['gaps']})
    def test_matching_shift_prefix_remains_incomplete(self):
        c,e=self.packet('scan-window-shift-valid');c['recipe']['pulse_edge_indices']=list(range(20));r=review(c,e,self.root);self.assertEqual(r['status'],'INCOMPLETE');self.assertFalse(r['findings'])
    def test_guard_before_observation_start_stays_unknown(self):
        c=copy.deepcopy(self.c);c['recipe']['control_guard_ns']=30;r=review(c,self.e,self.root);self.assertEqual(r['status'],'INCOMPLETE');self.assertIn('control_history_short',{g['code'] for g in r['gaps']})
    def test_capture_cannot_be_marked_shift_exempt(self):
        c=copy.deepcopy(self.c);c['recipe']['allow_selected_false_path']=True
        with self.assertRaises(ValueError):contract(c)
    def test_nonconsecutive_loc_recipe_requires_other_profile(self):
        c=copy.deepcopy(self.c);c['recipe']['pulse_edge_indices']=[2,4]
        with self.assertRaises(ValueError):contract(c)
    def test_normalized_mutation_rejected(self):
        e=copy.deepcopy(self.e);e['behavior']['frames'][25]['scan_enable']=1
        with self.assertRaises(ValueError):revalidate(e,self.root)
    def test_changed_original_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            name=next(iter(self.e['provenance']['integrity_files']));p=Path(d)/name;p.parent.mkdir(parents=True);p.write_text('changed')
            with self.assertRaisesRegex(ValueError,'Changed original artifact'):revalidate(self.e,Path(d))
    def test_missing_original_artifact(self):
        with tempfile.TemporaryDirectory() as d,self.assertRaises((ValueError,OSError)):revalidate(self.e,Path(d))
    def test_same_width_wrong_signal_role_rejected(self):
        c=copy.deepcopy(self.e['context']);m=c['role_map'];m['reset'],m['scan_enable']=m['scan_enable'],m['reset']
        with self.assertRaises(ValueError):xml_binding((self.base/'run/model.xml').read_text(encoding='utf-8'),c)
    def test_new_distinct_cli_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'existing';p.write_text('keep');r=subprocess.run([sys.executable,str(HERE/'occ_handoff.py'),'review',str(self.root),str(self.base/'contract.json'),str(self.base/'evidence.json'),'--json-out',str(p),'--markdown-out',str(p)],capture_output=True,text=True);self.assertEqual(r.returncode,3);self.assertEqual(p.read_text(),'keep')
    def test_capture_retains_complete_native_failure(self):
        folder=self.root/'scan-window-capture-missing';row=next(v for v in read_json(self.root/'collection.json')['cases'] if v['case']==folder.name)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'native.json';r=subprocess.run([sys.executable,str(HERE/'occ_handoff.py'),'capture',str(self.root),row['behavior_workdir'],row['sta_workdir'],str(folder/'context.json'),'--output',str(p)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(read_json(p)['behavior']['status'],'FAIL')
if __name__=='__main__':unittest.main()
