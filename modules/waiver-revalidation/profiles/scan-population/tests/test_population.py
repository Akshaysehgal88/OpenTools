import copy,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
PROFILE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(PROFILE),str(PROFILE/'examples')]
from scan_common import read_json,relative
from native_inventory import capture,inventory,revalidate
from population_core import contract,documents,drift,review
from reference_inventory import check_collection

class RecordTests(unittest.TestCase):
    def test_duplicate_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'duplicate.json';p.write_text('{"state":1,"state":2}')
            with self.assertRaises(ValueError):read_json(p)
    def test_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text('{"period":NaN}')
            with self.assertRaises(ValueError):read_json(p)
    def test_relative_paths(self):
        for path in ('../x','x/../y','x//y','/absolute','C:/x','x\\y','./x'):
            with self.subTest(path=path),self.assertRaises(ValueError):relative(PROFILE,path)
    def test_duplicate_native_state(self):
        with self.assertRaises(ValueError):inventory('FORMAT opentools.openroad-scan-inventory.v1 PRE\nSEQ ff0\nSEQ ff0\nOPENTOOLS_NATIVE_INVENTORY_COMPLETE','PRE')
    def test_native_census_cannot_omit_a_cell(self):
        with self.assertRaises(ValueError):inventory('FORMAT opentools.openroad-scan-inventory.v1 PRE\nSEQ ff0\nCELL ff0 DFFR_CELL\nCELL ff1 DFFR_CELL\nOPENTOOLS_NATIVE_INVENTORY_COMPLETE','PRE')

@unittest.skipUnless(os.environ.get('OPENTOOLS_SCAN_POPULATION_EXAMPLE'),'Set OPENTOOLS_SCAN_POPULATION_EXAMPLE to a generated native collection')
class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(os.environ['OPENTOOLS_SCAN_POPULATION_EXAMPLE']).resolve();cls.base=cls.root/'control-bank-complete';cls.c=read_json(cls.base/'contract.json');cls.e=read_json(cls.base/'evidence.json')
    def packet(self,case):
        f=self.root/case;return read_json(f/'contract.json'),read_json(f/'evidence.json')
    def test_all_native_insertions_and_reference(self):
        reference=check_collection(self.root);self.assertEqual(reference['totals'],{'native_runs':16,'sequential_states':96,'scan_members':86,'unscanned':10,'chains':24,'functional_pin_checks':384})
        counts={}
        for row in read_json(self.root/'collection.json')['cases']:
            c,e=self.packet(row['case']);r=review(c,e,self.root);self.assertEqual(r,read_json(self.root/row['case']/'review.json'));counts[r['status']]=counts.get(r['status'],0)+1
        self.assertEqual(counts,{'BOUNDED_POPULATION_ACCOUNTED':4,'MEMBERSHIP_REVIEW_REQUIRED':6,'INCOMPLETE':6})
    def test_native_completion_does_not_hide_omission(self):
        c,e=self.packet('control-bank-missing-required');r=review(c,e,self.root);self.assertEqual((r['native_status'],r['status']),('COMPLETE','MEMBERSHIP_REVIEW_REQUIRED'));self.assertIn('required_state_unscanned',{f['code'] for f in r['findings']})
    def test_valid_exclusion_stays_visible(self):
        c,e=self.packet('control-bank-allowed-exclusion');r=review(c,e,self.root);self.assertEqual(r['status'],'BOUNDED_POPULATION_ACCOUNTED');self.assertEqual((r['counts']['native_unscanned'],r['counts']['admitted_exclusions']),(1,1));self.assertFalse(r['states'][0]['scan_member']);self.assertTrue(r['states'][0]['exclusion_admitted'])
    def test_obsolete_role_and_native_clock_premise(self):
        c,e=self.packet('mixed-bank-obsolete-role');r=review(c,e,self.root);f=next(f for f in r['findings'] if f['code']=='exclusion_premise_false');self.assertIn('required_clock',f['detail']);self.assertIn('required_role',f['detail'])
    def test_missing_rationale_not_invented(self):
        c,e=self.packet('control-bank-missing-rationale');r=review(c,e,self.root);self.assertEqual(r['status'],'INCOMPLETE');self.assertEqual(r['counts']['admitted_exclusions'],0)
    def test_stale_exclusion_cannot_exempt(self):
        c,e=self.packet('control-bank-stale-exclusion');r=review(c,e,self.root);self.assertEqual(r['status'],'INCOMPLETE');self.assertIn('stale_or_foreign_exclusion_scope',{g['code'] for g in r['gaps']})
    def test_complete_declaration_cannot_hide_roster_omission(self):
        c,e=self.packet('control-bank-partial-roster');self.assertTrue(e['population']['complete']);r=review(c,e,self.root);self.assertEqual(r['status'],'INCOMPLETE');self.assertIn('native_state_missing_from_required_source',{g['code'] for g in r['gaps']})
    def test_clock_group_checked_even_with_all_members(self):
        c,e=self.packet('mixed-bank-wrong-clock-group');r=review(c,e,self.root);self.assertEqual(r['counts']['scan_members'],8);self.assertIn('clock_group_mismatch',{f['code'] for f in r['findings']})
    def test_foreign_scope_quarantined_before_attribution(self):
        c,e=self.packet('control-bank-missing-required');c['expected']['scope']='foreign';r=review(c,e,self.root);self.assertEqual(r['status'],'QUARANTINED');self.assertEqual(r['findings'],[])
    def test_stale_source_quarantined(self):
        c=copy.deepcopy(self.c);c['expected']['sources']['seed.v']='0'*64;self.assertEqual(review(c,self.e,self.root)['status'],'QUARANTINED')
    def test_missing_independent_source_identity(self):
        c=copy.deepcopy(self.c);c['expected']['sources']['population.json']=None;self.assertEqual(review(c,self.e,self.root)['status'],'INCOMPLETE')
    def test_unknown_receiving_owner(self):
        c=copy.deepcopy(self.c);c['owner_ref']=None;self.assertEqual(review(c,self.e,self.root)['status'],'INCOMPLETE')
    def test_power_mapping_basis_not_silently_closed(self):
        ctx=copy.deepcopy(self.e['context']);ctx['power_basis_ref']=None;e=capture(self.root,'control-bank-complete/run',ctx);r=review(self.c,e,self.root);self.assertEqual(r['status'],'INCOMPLETE')
    def test_mismatches_survive_missing_owner(self):
        c,e=self.packet('control-bank-missing-required');c['owner_ref']=None;r=review(c,e,self.root);self.assertEqual(r['status'],'MEMBERSHIP_REVIEW_REQUIRED');self.assertTrue(r['gaps'])
    def test_duplicate_required_native_mapping(self):
        e=copy.deepcopy(self.e);e['population']['states'][1]['instance']='ff0'
        with self.assertRaises(ValueError):documents(e)
    def test_duplicate_exclusion_target(self):
        c,e=self.packet('control-bank-allowed-exclusion');x=copy.deepcopy(e['exclusions']['records'][0]);x['id']='another';e['exclusions']['records'].append(x)
        with self.assertRaises(ValueError):documents(e)
    def test_booleans_are_not_integer_flags(self):
        e=copy.deepcopy(self.e);e['population']['states'][0]['scan_required']=1
        with self.assertRaises(ValueError):documents(e)
    def test_normalized_membership_cannot_be_rewritten(self):
        e=copy.deepcopy(self.e);e['membership']['members'].pop()
        with self.assertRaises(ValueError):revalidate(e,self.root)
    def test_changed_original_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            name=next(iter(self.e['provenance']['integrity_files']));p=Path(d)/name;p.parent.mkdir(parents=True);p.write_text('changed')
            with self.assertRaisesRegex(ValueError,'Changed original artifact'):revalidate(self.e,Path(d))
    def test_missing_original_artifact(self):
        with tempfile.TemporaryDirectory() as d,self.assertRaises((ValueError,OSError)):revalidate(self.e,Path(d))
    def test_parent_comparator_tracks_changed_premises(self):
        _,a=self.packet('mixed-bank-allowed-exclusion');_,b=self.packet('mixed-bank-obsolete-role');r=drift(a,b,self.root);self.assertEqual(r,read_json(self.root/'mixed-bank-exclusion-drift.json'));self.assertEqual(r['status'],'review_required');self.assertTrue(any(f['code']=='premise_does_not_hold' for w in r['audit']['waivers'] for f in w['issues']))
    def test_unchanged_exclusion_control(self):
        _,e=self.packet('control-bank-allowed-exclusion');r=drift(e,e,self.root);self.assertEqual(r['status'],'unchanged_within_scope')
    def test_historical_comparison_keeps_missing_basis(self):
        _,e=self.packet('control-bank-missing-rationale');r=drift(e,e,self.root);self.assertEqual(r['status'],'incomplete');self.assertEqual(len(r['basis_gaps']),2)
    def test_no_synthetic_empty_waiver(self):
        with self.assertRaises(ValueError):drift(self.e,self.e,self.root)
    def test_cli_outputs_are_distinct_new_files(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'existing';p.write_text('keep');r=subprocess.run([sys.executable,str(PROFILE/'scan_population.py'),'review',str(self.root),str(self.base/'contract.json'),str(self.base/'evidence.json'),'--json-out',str(p),'--markdown-out',str(p)],capture_output=True,text=True)
            self.assertEqual(r.returncode,3);self.assertEqual(p.read_text(),'keep')
    def test_cli_capture_complete_native_omission(self):
        folder=self.root/'control-bank-missing-required'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'capture.json';r=subprocess.run([sys.executable,str(PROFILE/'scan_population.py'),'capture',str(self.root),'control-bank-missing-required/run',str(folder/'context.json'),'--output',str(p)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(read_json(p)['membership']['unscanned'],['ff0'])
if __name__=='__main__':unittest.main()
