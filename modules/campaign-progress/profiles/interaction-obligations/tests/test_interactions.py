"""Synthetic review logic controls and optional actual retained-native qualification."""
import copy,json,os
from pathlib import Path
import shutil,subprocess,sys,tempfile,unittest
from unittest.mock import patch
PROFILE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(PROFILE),str(PROFILE/'examples')]
from interaction_core import exit_code,markdown,review
from saved_native import capture,contained,file_hash,journal,revalidate,xml_ports
from create_example import context_for,plan_for
from reference_model import expected
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.row={'case':'synthetic-never-executed','family':'interrupt','selection':['portfolio','good','warm','on'],'source_sha256':{p:'0'*64 for p in ('top.sv','ports.hpp','main.cpp')},'command_sha256':'0'*64}
        self.plan=plan_for('synthetic-no-native-proof',[self.row]);self.e={'format':'opentools.interaction-native-evidence.v1','context':context_for(self.row),'sources':self.row['source_sha256'],
             'native':{'status':'PASS','command_sha256':'0'*64,'version':'SYNTHETIC LOGIC FIXTURE, NOT EXECUTED'},'provenance':{'synthetic':True}}
        self.update_trace();self.corpus={'format':'opentools.interaction-evidence-corpus.v1','complete':True,'evidence_ref':'synthetic:record-only','runs':[{'path':'native.json','sha256':'0'*64}]};self.bind()
    def update_trace(self,scenario='portfolio',variant='good',mode='warm',checker='on'):
        ref=expected('interrupt',[scenario,variant,mode,checker]);self.e.update(frames=ref['frames'],checks=ref['checks']);self.e['native']['status']='FAIL' if ref['counts']['failures'] else 'PASS'
    def bind(self):
        p=self.root/'native.json';p.write_text(json.dumps(self.e),encoding='utf-8');self.corpus['runs'][0]['sha256']=file_hash(p)
    def check(self):
        self.bind()
        # Native provenance is mocked only in pure logic tests. Real parent accounting and receipt-file hashing remain active.
        with patch('interaction_core.revalidate'):return review(self.plan,self.corpus,self.root)
    def test_all_three_obligations_supported(self):
        r=self.check();self.assertEqual(exit_code(r),0);self.assertEqual([v['status'] for v in r['obligations']],['observed_pass']*3)
    def test_separate_features_do_not_supply_combination_evidence(self):
        self.update_trace('separate');r=self.check();self.assertEqual(exit_code(r),2);self.assertTrue(all(not v['witnesses'] for v in r['obligations']))
    def test_one_combination_does_not_close_other_two(self):
        self.update_trace('arrive');r=self.check();self.assertEqual(exit_code(r),2);self.assertEqual(r['obligations'][0]['status'],'observed_pass')
    def test_actual_checker_failure_retained_per_window(self):
        self.update_trace(variant='bug');r=self.check();self.assertEqual(exit_code(r),1);self.assertTrue(all(v['status']=='observed_failure' for v in r['obligations']))
    def test_checker_off_is_not_pass(self):
        self.update_trace(variant='bug',checker='off');self.assertEqual(exit_code(self.check()),1)
    def test_missing_checker_action_is_gap(self):
        self.e['checks']=[c for c in self.e['checks'] if (c['tick'],c['id'])!=(3,'state_model')];self.assertEqual(exit_code(self.check()),2)
    def test_checker_observation_must_match_native_point(self):
        c=next(c for c in self.e['checks'] if c['tick']==3 and c['id']=='state_model');c['observed']^=1;c['expected']=c['observed'];self.assertEqual(exit_code(self.check()),1)
    def test_short_window_is_incomplete(self):
        self.update_trace('short');self.assertEqual(exit_code(self.check()),2)
    def test_initialization_reset_interrupts_observation_span(self):
        self.e['frames'][4]['reset']=1;r=self.check();self.assertEqual(exit_code(r),2);self.assertIn('reset interrupts',' '.join(r['gaps']))
    def test_source_bound_risk_relationship_cannot_be_stale(self):
        self.plan['obligations'][0]['relationship']['design_source_sha256']='1'*64;r=self.check();self.assertEqual(exit_code(r),1);self.assertEqual(r['obligations'][0]['status'],'unresolved')
    def test_foreign_risk_configuration(self):
        self.plan['obligations'][0]['relationship']['configuration_ref']='other';self.assertEqual(exit_code(self.check()),1)
    def test_missing_relationship(self):
        self.plan['obligations'][0]['relationship']['resource_ref']=None;self.assertEqual(exit_code(self.check()),2)
    def test_missing_definition_owner_and_checker_link(self):
        for field in ('definition_ref','owner_ref'):
            old=self.plan['obligations'][0][field];self.plan['obligations'][0][field]=None;self.assertEqual(exit_code(self.check()),2);self.plan['obligations'][0][field]=old
        self.plan['obligations'][0]['checkers'][0]['basis_ref']=None;self.assertEqual(exit_code(self.check()),2)
    def test_unknown_applicability_does_not_exclude_obligation(self):
        self.plan['obligations'][0]['applicability']['status']='unknown';self.assertEqual(exit_code(self.check()),2)
    def test_missing_applicability_review(self):
        self.plan['obligations'][0]['applicability']['reviewer_ref']=None;self.assertEqual(exit_code(self.check()),2)
    def test_nonapplicability_conflicts_with_known_fact(self):
        a=self.plan['obligations'][0]['applicability'];a.update(status='not_applicable',facts={'retain':0});self.assertEqual(exit_code(self.check()),1)
    def test_nonapplicability_requires_explicit_fact(self):
        a=self.plan['obligations'][0]['applicability'];a.update(status='not_applicable',facts={});self.assertEqual(exit_code(self.check()),2)
    def test_all_nonapplicable_roster_is_not_closure(self):
        for o in self.plan['obligations']:o['applicability'].update(status='not_applicable',facts={'retain':1})
        self.assertEqual(exit_code(self.check()),2)
    def test_native_mode_fact_conflicts_with_requested_scope(self):
        self.plan['scope_facts']['retain']['value']=0;self.assertEqual(exit_code(self.check()),1)
    def test_missing_scope_fact_source(self):
        self.plan['scope_facts']['retain']['basis_ref']=None;self.assertEqual(exit_code(self.check()),2)
    def test_foreign_original_run_identity_and_model(self):
        for field in ('run_ref','configuration_ref','model_ref','sources','command_sha256','clock_ref'):
            before=copy.deepcopy(self.plan['runs'][0][field]);self.plan['runs'][0][field]='foreign';r=self.check();self.assertEqual(exit_code(r),1);self.assertTrue(all(v['quarantined'] for v in r['native_runs']));self.plan['runs'][0][field]=before
    def test_missing_original_run_fact(self):
        self.plan['runs'][0]['sources']=None;self.assertEqual(exit_code(self.check()),2)
    def test_original_source_review_and_oracle_are_required(self):
        self.e['context']['instrumentation_review_ref']=None;self.assertEqual(exit_code(self.check()),2)
    def test_incomplete_population_or_corpus_stays_open(self):
        self.plan['population_complete']=False;self.assertEqual(exit_code(self.check()),2);self.plan['population_complete']=True;self.corpus['complete']=False;self.assertEqual(exit_code(self.check()),2)
    def test_missing_or_stale_receipt_is_gap(self):
        self.bind();self.corpus['runs'][0]['sha256']='f'*64
        with patch('interaction_core.revalidate'):self.assertEqual(exit_code(review(self.plan,self.corpus,self.root)),2)
        (self.root/'native.json').unlink()
        with patch('interaction_core.revalidate'):self.assertEqual(exit_code(review(self.plan,self.corpus,self.root)),2)
    def test_duplicate_obligation_and_invalid_trigger_reject(self):
        self.plan['obligations'].append(copy.deepcopy(self.plan['obligations'][0]))
        with self.assertRaises(ValueError):self.check()
        self.plan['obligations'].pop();self.plan['obligations'][0]['trigger'][0]['equals']=True
        with self.assertRaises(ValueError):self.check()
    def test_parent_named_goal_accounting_used_without_extra_combinations(self):
        r=self.check();o=r['accounting']['summary']['objectives'][0];self.assertEqual(o['known_value'],3);self.assertEqual(o['target'],3);self.assertEqual(len(r['accounting']['contract']['objectives'][0]['target']['population_ids']),3)
    def test_passing_witness_does_not_erase_selected_counterexample(self):
        bad=copy.deepcopy(self.e);ref=expected('interrupt',['portfolio','bug','warm','on']);bad.update(frames=ref['frames'],checks=ref['checks']);bad['context']['run_ref']='synthetic:second-run';bad['native']['status']='FAIL'
        p=self.root/'second.json';p.write_text(json.dumps(bad));self.corpus['runs'].append({'path':'second.json','sha256':file_hash(p)})
        expectation=copy.deepcopy(self.plan['runs'][0]);expectation['run_ref']='synthetic:second-run';self.plan['runs'].append(expectation)
        r=self.check();self.assertEqual(exit_code(r),1);self.assertEqual(r['accounting']['summary']['objectives'][0]['known_value'],0)
        self.assertTrue(all(any(w['status']=='pass' for w in o['witnesses']) and any(w['status']=='failure' for w in o['witnesses']) for o in r['obligations']))
    def test_markdown_escapes_untrusted_text(self):
        self.plan['claim']='<injected>|';self.assertIn('&lt;injected&gt;&#124;',markdown(self.check()))

class ReaderTests(unittest.TestCase):
    def test_paths_cannot_escape(self):
        for name in ('../x','/tmp/x','C:/x','a\\b','a/./b'):
            with self.subTest(name=name),self.assertRaises(ValueError):contained('.',name)
    def test_entities_and_bad_xml_rejected(self):
        for xml in ('<!DOCTYPE a><verilator_xml/>','<truncated'):
            with self.subTest(xml=xml),self.assertRaises(ValueError):xml_ports(xml,{})
    def test_truncated_aggregate_only_and_postterminal_records(self):
        for data in ('RESULT 0 0 0\n','FRAME 0 0 0\n','RESULT 0 0 0\nFRAME 0\n'):
            with self.subTest(data=data),self.assertRaises(ValueError):journal(data)

@unittest.skipUnless(os.environ.get('OPENTOOLS_INTERACTION_EXAMPLE'),'Set OPENTOOLS_INTERACTION_EXAMPLE to retained native example output')
class NativeTests(unittest.TestCase):
    def setUp(self):self.native=Path(os.environ['OPENTOOLS_INTERACTION_EXAMPLE'])
    def copy(self,name):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);p=Path(temp.name)/'case';shutil.copytree(self.native/name,p);return p
    def test_all_native_traces_and_independent_reference(self):
        s=load(self.native/'summary.json');collection=load(self.native/'collection.json');self.assertEqual((s['native_runs'],s['review_packets']),(26,30));total=0
        for row in collection['cases']:
            p=self.native/row['case'];e=load(p/'native.json');revalidate(e,p);ref=expected(row['family'],row['selection']);self.assertEqual(e['frames'],ref['frames']);self.assertEqual(e['checks'],ref['checks']);self.assertEqual(e['native']['counts'],ref['counts']);total+=len(e['frames'])
        self.assertEqual(total,778)
    def test_all_native_review_packets_and_joined_existing_runs(self):
        for row in load(self.native/'summary.json')['cases']:
            p=self.native/row['case'];r=review(load(p/'plan.json'),load(p/'corpus.json'),p);self.assertEqual(r,load(p/'report.json'));self.assertEqual(exit_code(r),row['exit'])
    def test_separate_features_pass_but_combined_witness_fails_same_binary(self):
        for family in ('interrupt','maintenance'):
            a=load(self.native/(family+'-separate-bug')/'native.json');b=load(self.native/(family+'-arrive-bug')/'native.json');self.assertEqual(a['native']['status'],'PASS');self.assertEqual(b['native']['status'],'FAIL')
            self.assertEqual(file_hash(self.native/(family+'-separate-bug')/'run/Vtop'),file_hash(self.native/(family+'-arrive-bug')/'run/Vtop'))
    def test_valid_nonapplicable_mode_keeps_third_obligation(self):
        r=load(self.native/'interrupt-cold-valid/report.json');self.assertEqual(exit_code(r),0);self.assertEqual([o['status'] for o in r['obligations']],['reviewed_not_applicable','reviewed_not_applicable','observed_pass']);self.assertEqual(r['accounting']['summary']['objectives'][0]['target'],1)
    def test_changed_or_missing_original_files_quarantine(self):
        for filename in ('top.sv','Vtop','run.stdout.txt'):
            p=self.copy('interrupt-portfolio-good');(p/'run'/filename).write_bytes(b'changed')
            with self.subTest(filename=filename):self.assertEqual(exit_code(review(load(p/'plan.json'),load(p/'corpus.json'),p)),2)
    def test_forged_receipt_cannot_replace_native(self):
        p=self.copy('interrupt-portfolio-bug');e=load(p/'native.json');e['checks'][0]['expected']^=1
        with self.assertRaises(ValueError):revalidate(e,p)
    def test_bad_native_clock_and_missing_action_result(self):
        p=self.copy('maintenance-portfolio-good');ctx=load(p/'capture-context.json');path=p/'run/model.xml';path.write_text(path.read_text().replace('edgeType="POS"','edgeType="NEG"'))
        with self.assertRaises(ValueError):capture(p,'run',ctx)
        p=self.copy('interrupt-portfolio-good');ctx=load(p/'capture-context.json');path=p/'run/run.stdout.txt';path.write_text('\n'.join(path.read_text().splitlines()[:-1]))
        with self.assertRaises(ValueError):capture(p,'run',ctx)
    def test_cli_data_only_and_preserves_existing_output(self):
        p=self.copy('interrupt-arrive-bug');out=p/'new.json';args=[sys.executable,str(PROFILE/'interaction_check.py'),'capture',str(p),'run',str(p/'capture-context.json'),'--output',str(out)]
        r=subprocess.run(args,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(load(out),load(p/'native.json'));self.assertEqual(json.loads(r.stdout)['receipt_sha256'],file_hash(out));before=out.read_bytes();r=subprocess.run(args,capture_output=True,text=True);self.assertEqual(r.returncode,3);self.assertEqual(out.read_bytes(),before)
        (p/'run/run.command.json').write_text(json.dumps(['NEVER_EXECUTE_CAPTURE',str(p/'marker')]));capture(p,'run',load(p/'capture-context.json'));self.assertFalse((p/'marker').exists())

if __name__=='__main__':unittest.main()
