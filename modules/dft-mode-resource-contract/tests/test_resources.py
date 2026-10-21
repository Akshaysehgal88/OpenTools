import copy,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(HERE),str(HERE/'examples')]
from dft_common import contained,read_json
from native_capture import behavior,capture,resources,revalidate,xml_bindings
from resource_core import contract,review
from reference_model import check_collection

class ProtocolTests(unittest.TestCase):
    def test_duplicate_json_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(ValueError):read_json(p)
    def test_nonfinite_json_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text('{"a":NaN}')
            with self.assertRaises(ValueError):read_json(p)
    def test_path_boundary(self):
        for p in ('../x','x/../y','x\\y','/absolute','C:/file','./x','x//y'):
            with self.subTest(p=p),self.assertRaises(ValueError):contained(HERE,p)
    def test_empty_resource_line_rejected(self):
        with self.assertRaises(ValueError):resources('FORMAT opentools.openroad-dft-resources.v1\n\nOPENTOOLS_NATIVE_RESOURCE_EXPORT_COMPLETE')
    def test_unknown_and_duplicate_cases(self):
        prefix='FORMAT opentools.openroad-dft-resources.v1\n';end='OPENTOOLS_NATIVE_RESOURCE_EXPORT_COMPLETE'
        r=resources(prefix+'CASE shift reset X\n'+end);self.assertEqual(r['cases']['shift']['reset'],'X')
        with self.assertRaises(ValueError):resources(prefix+'CASE shift reset X\nCASE shift reset 0\n'+end)
    def test_behavior_cannot_rewrite_failure(self):
        s='CONFIG 1 1 0 1 1 0 1 1 0\nSTEP 1 shift 1 0 1 0 1 1 1 0 0 0 1 0 0\nNATIVE_RESULT 1 1 0'
        with self.assertRaises(ValueError):behavior(s,1)

@unittest.skipUnless(os.environ.get('OPENTOOLS_DFT_RESOURCE_EXAMPLE'),'Set OPENTOOLS_DFT_RESOURCE_EXAMPLE to a generated native collection')
class NativeEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(os.environ['OPENTOOLS_DFT_RESOURCE_EXAMPLE']).resolve();cls.base=cls.root/'register-bank-supported-mask';cls.c=read_json(cls.base/'contract.json');cls.e=read_json(cls.base/'evidence.json')
    def checked(self,c=None,e=None):return review(c or self.c,e or self.e,self.root)
    def test_full_native_matrix_and_independent_reference(self):
        s=check_collection(self.root);self.assertEqual(s['totals'],{'steps':312,'checks':456,'failures':103})
        manifest=read_json(self.root/'collection.json');counts={}
        for case in manifest['cases']:
            with self.subTest(case=case['case']):
                folder=self.root/case['case'];r=review(read_json(folder/'contract.json'),read_json(folder/'evidence.json'),self.root)
                self.assertEqual(r,read_json(folder/'review.json'));counts[r['status']]=counts.get(r['status'],0)+1
        self.assertEqual(counts,{'BOUNDED_RESOURCES_SUPPORTED':4,'RESOURCE_MISMATCH':18,'INCOMPLETE':2})
    def test_source_identity_precedes_attribution(self):
        c=copy.deepcopy(self.c);c['expected']['sources']['top.sv']='0'*64;r=self.checked(c)
        self.assertEqual(r['status'],'QUARANTINED');self.assertEqual(r['findings'],[])
    def test_foreign_mode(self):
        c=copy.deepcopy(self.c);c['expected']['mode_ref']='different-mode';self.assertEqual(self.checked(c)['status'],'QUARANTINED')
    def test_missing_independent_identity(self):
        c=copy.deepcopy(self.c);c['expected']['mode_sdc_sha256']=None;self.assertEqual(self.checked(c)['status'],'INCOMPLETE')
    def test_missing_requirement_basis(self):
        c=copy.deepcopy(self.c);c['policy_basis_ref']=None;self.assertEqual(self.checked(c)['status'],'INCOMPLETE')
    def test_period_is_independently_required(self):
        c=copy.deepcopy(self.c);c['clock_period']=12;self.assertIn('clock_period_mismatch',{f['code'] for f in self.checked(c)['findings']})
    def test_native_unknown_not_promoted(self):
        c=copy.deepcopy(self.c);c['require_propagated_reset']=True;r=self.checked(c);self.assertEqual(r['status'],'INCOMPLETE');self.assertEqual(len([g for g in r['gaps'] if g['code']=='unresolved_propagated_reset']),3)
    def test_cannot_accept_debug_instead_of_manufacturing(self):
        c=copy.deepcopy(self.c);c['phases']['shift']['manufacturing']=0
        with self.assertRaises(ValueError):contract(c)
    def test_cannot_weaken_scan_enable_or_reset(self):
        for k in ('reset_level','scan_enable'):
            c=copy.deepcopy(self.c);c['phases']['shift'][k]=0
            with self.subTest(k=k),self.assertRaises(ValueError):contract(c)
    def test_full_chain_samples_survive_low_declared_minimum(self):
        c=copy.deepcopy(self.c);c['phases']['shift']['min_steps']=1;r=self.checked(c)
        self.assertEqual(r['phases'][0]['minimum'],4)
    def test_native_fail_preserved(self):
        folder=self.root/'register-bank-reset-clamp';r=review(read_json(folder/'contract.json'),read_json(folder/'evidence.json'),self.root)
        self.assertEqual(r['native_status'],'FAIL');self.assertIn('native_behavior_failure',{f['code'] for f in r['findings']})
    def test_denial_pass_does_not_accept_test_mode(self):
        folder=self.root/'register-bank-debug-is-not-manufacturing';r=review(read_json(folder/'contract.json'),read_json(folder/'evidence.json'),self.root)
        self.assertEqual((r['native_status'],r['status']),('PASS','RESOURCE_MISMATCH'));self.assertIn('ineffective_shift_witness',{g['code'] for g in r['gaps']})
    def test_constraint_disagreement_despite_behavior_pass(self):
        folder=self.root/'register-bank-constraint-reset-asserted';r=review(read_json(folder/'contract.json'),read_json(folder/'evidence.json'),self.root)
        self.assertEqual(r['native_status'],'PASS');self.assertIn('constraint_behavior_disagreement',{f['code'] for f in r['findings']})
    def test_normalized_mutation_rejected(self):
        e=copy.deepcopy(self.e);e['steps'][0]['raw_state']^=1
        with self.assertRaises(ValueError):revalidate(e,self.root)
    def test_changed_original_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            relative=next(iter(self.e['provenance']['integrity_files']));p=Path(d)/relative;p.parent.mkdir(parents=True);p.write_text('changed original bytes')
            with self.assertRaisesRegex(ValueError,'Changed native artifact'):revalidate(self.e,Path(d))
    def test_same_width_wrong_signal_role_rejected(self):
        ctx=copy.deepcopy(self.e['context']);m=ctx['role_map'];m['reset_level'],m['scan_enable']=m['scan_enable'],m['reset_level']
        xml=(self.base/'run/model.xml').read_text(encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Observed role does not bind'):xml_bindings(xml,ctx,4)
    def test_missing_original_rejected(self):
        with tempfile.TemporaryDirectory() as d,self.assertRaises((ValueError,OSError)):revalidate(self.e,Path(d))
    def test_duplicate_scan_member_rejected(self):
        c=copy.deepcopy(self.c);c['expected']['chain']['instances'][1]=c['expected']['chain']['instances'][0]
        with self.assertRaises(ValueError):contract(c)
    def test_distinct_and_exclusive_cli_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report';p.write_text('preserve');r=subprocess.run([sys.executable,str(HERE/'dft_resources.py'),'review',str(self.root),str(self.base/'contract.json'),str(self.base/'evidence.json'),'--json-out',str(p),'--markdown-out',str(p)],capture_output=True,text=True)
            self.assertEqual(r.returncode,3);self.assertEqual(p.read_text(),'preserve')
    def test_cli_captures_failure_without_execution(self):
        folder=self.root/'register-bank-reset-clamp'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'e.json';r=subprocess.run([sys.executable,str(HERE/'dft_resources.py'),'capture',str(self.root),'register-bank-reset-clamp/run',str(folder/'context.json'),'--output',str(p)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(read_json(p)['native']['status'],'FAIL')
if __name__=='__main__':unittest.main()
