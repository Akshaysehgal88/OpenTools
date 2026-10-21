"""Synthetic logic controls plus optional actual retained native evidence tests."""
import copy,json,os
from pathlib import Path
import shutil,subprocess,sys,tempfile,unittest
from unittest.mock import patch
PROFILE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(PROFILE),str(PROFILE/'examples')]
from native_capture import capture,contained,file_hash,journal,revalidate,xml_ports
from observation_core import EXPECTED,exit_code,markdown,review
from create_example import capture_context,intent_for
from reference_model import expected
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

class LogicTests(unittest.TestCase):
    def setUp(self):
        ctx=capture_context('synthetic-never-executed','stream');ctx['scope_basis_ref']='synthetic:logic-only-not-native'
        def edge(tick,mode=0,reset=0,rv=0,rr=1,ri=7,rd=8,sv=0,sr=1,si=7,sd=8):
            return dict(zip(('tick','reset','mode','enabled','req_valid','req_ready','req_id','req_data','rsp_valid','rsp_ready','rsp_id','rsp_data','clock'),(tick,reset,mode,1,rv,rr,ri,rd,sv,sr,si,sd,0)))
        self.edge=edge
        self.e={'format':'opentools.checker-observation-evidence.v1','context':ctx,'source_sha256':{p:'0'*64 for p in ('top.sv','checker.hpp','ports.hpp','main.cpp')},'ports':{},
                'edges':[edge(0,reset=1),edge(1,rv=1),edge(2,sv=1),edge(3,mode=1,rv=1,ri=8,rd=9),edge(4,mode=1,sv=1,si=8,sd=9)],
                'checks':[{'tick':2,'id':7,'expected':8,'observed':8,'ok':1},{'tick':4,'id':8,'expected':9,'observed':9,'ok':1}],
                'native':{'status':'PASS','counts':{'stimulus':2,'accepted':2,'completed':2,'checked':2,'failures':0},'version':'SYNTHETIC, NOT NATIVE'},'provenance':{'synthetic':True}}
        self.i=intent_for('synthetic-never-executed','stream',self.e['source_sha256'])
    def check(self):
        with patch('observation_core.revalidate'):return review(self.i,self.e)
    def test_valid_observation(self):self.assertEqual(exit_code(self.check()),0)
    def test_native_failure_can_have_valid_observation(self):
        self.e['checks'][1].update(expected=10,ok=0);self.e['native']['status']='FAIL'
        r=self.check();self.assertEqual(exit_code(r),0);self.assertEqual(r['native']['status'],'FAIL')
    def test_missing_required_check(self):
        self.e['checks'].pop();self.assertEqual(exit_code(self.check()),1)
    def test_wrong_ids_with_same_count(self):
        self.e['checks'][1]['id']=99;self.assertEqual(exit_code(self.check()),1)
    def test_stimulus_check_is_not_completion(self):
        self.e['checks'][0]['tick']=1;self.assertEqual(exit_code(self.check()),1)
    def test_duplicate_check_is_not_extra_exposure(self):
        self.e['checks'].append(copy.deepcopy(self.e['checks'][0]));r=self.check();self.assertEqual(exit_code(r),1)
        self.assertEqual(next(v['known_value'] for v in r['accounting']['summary']['objectives'] if v['id']=='checked'),2)
    def test_observed_payload_must_match_native_event(self):
        self.e['checks'][0]['observed']=99;self.assertEqual(exit_code(self.check()),1)
    def test_enabled_false_even_with_action_is_finding(self):
        self.e['edges'][4]['enabled']=0;self.assertEqual(exit_code(self.check()),1)
    def test_whole_required_interval_disabled(self):
        self.e['checks'].pop();self.e['edges'][4]['enabled']=0;self.assertEqual(exit_code(self.check()),1)
    def test_narrow_scope_keeps_other_mode_failures_separate(self):
        self.e['checks'].pop();self.e['edges'][4]['enabled']=0;self.i['required_modes']=[0]
        self.assertEqual(exit_code(self.check()),0)
    def test_missing_required_mode_is_gap(self):
        self.e['edges']=self.e['edges'][:3];self.e['checks']=self.e['checks'][:1];self.assertEqual(exit_code(self.check()),2)
    def test_outstanding_is_gap_not_functional_failure(self):
        self.e['edges'].pop();self.e['checks'].pop();r=self.check();self.assertEqual(exit_code(r),2);self.assertIn('outstanding',' '.join(r['gaps']))
    def test_reset_cancellation_is_retained(self):
        self.e['edges'].insert(2,self.edge(2,reset=1));self.e['edges'][3]['rsp_valid']=0;self.e['checks'].pop(0)
        for t,row in enumerate(self.e['edges']):row['tick']=t
        self.e['checks'][0]['tick']=5;self.i['required_modes']=[1];r=self.check()
        self.assertEqual(exit_code(r),0);self.assertEqual(len(r['events']['cancelled']),1)
    def test_foreign_completion_after_reset(self):
        self.e['edges'][1]['reset']=1;self.assertEqual(exit_code(self.check()),1)
    def test_outstanding_id_collision(self):
        self.e['edges'][2].update(req_valid=1,req_id=7,rsp_valid=0);self.e['checks'].pop(0);self.assertEqual(exit_code(self.check()),1)
    def test_id_reuse_after_completion_is_distinct_event(self):
        self.e['edges'][3]['req_id']=7;self.e['edges'][4]['rsp_id']=7;self.e['checks'][1]['id']=7;r=self.check()
        self.assertEqual(exit_code(r),0);self.assertEqual([c['accepted_sequence'] for c in r['events']['completed']],[0,1])
    def test_parent_accounting_counts_real_populations(self):
        r=self.check();self.assertEqual({v['id']:v['known_value'] for v in r['accounting']['summary']['objectives']},{'stimulus':2,'accepted':2,'completed':2,'checked':2})
        self.assertIn('Timestamp unknown',r['accounting']['limits'])
    def test_changed_mode_scope_changes_measurement_basis(self):
        before=self.check()['accounting']['contract']['objectives'][0]['basis_ref'];self.i['required_modes']=[0]
        self.assertNotEqual(before,self.check()['accounting']['contract']['objectives'][0]['basis_ref'])
    def test_foreign_configuration_source_checker_clock_and_reset_quarantine(self):
        for key in ('run_ref','configuration_ref','model_ref','checker_ref','clock_ref','reset_ref','source_sha256','port_map'):
            old=copy.deepcopy(self.i['expected'][key]);self.i['expected'][key]='different'
            r=self.check();self.assertEqual(exit_code(r),1);self.assertIsNone(r['native']);self.i['expected'][key]=old
    def test_unknown_expected_scope_is_gap(self):
        self.i['expected']['clock_ref']=None;self.assertEqual(exit_code(self.check()),2)
    def test_missing_instrumentation_scope_or_oracle_blocks_qualification(self):
        for key in ('instrumentation_review_ref','scope_basis_ref','oracle_ref','dependency_basis_ref'):
            old=self.e['context'][key];self.e['context'][key]=None;r=self.check();self.assertEqual(exit_code(r),2)
            self.assertEqual(r['accounting']['summary']['objectives'][0]['known_value'],0);self.e['context'][key]=old
    def test_missing_independent_owner_and_basis(self):
        self.i['owner_ref']=None;self.i['basis_ref']=None;self.assertEqual(exit_code(self.check()),2)
    def test_unknown_required_modes(self):
        self.i['required_modes']=None;self.assertEqual(exit_code(self.check()),2)
    def test_invalid_modes(self):
        for modes in ([True],[0,0],[],[1,0],[2]):
            self.i['required_modes']=modes
            with self.assertRaises(ValueError):self.check()
    def test_missing_native_artifact_is_gap(self):
        with patch('observation_core.revalidate',side_effect=OSError('missing ELF')):self.assertEqual(exit_code(review(self.i,self.e)),2)
    def test_markdown_escapes(self):
        self.i['claim']='<untrusted>|';self.assertIn('&lt;untrusted&gt;&#124;',markdown(self.check()))

class ReaderTests(unittest.TestCase):
    def test_relative_path_contract(self):
        for p in ('../outside','/tmp/outside','C:/outside','a\\b','a/./b'):
            with self.subTest(path=p),self.assertRaises(ValueError):contained('.',p)
    def test_malformed_xml_is_value_error(self):
        with self.assertRaises(ValueError):xml_ports('<broken',{})
    def test_entities_not_loaded(self):
        with self.assertRaises(ValueError):xml_ports('<!DOCTYPE a><verilator_xml/>',{})

@unittest.skipUnless(os.environ.get('OPENTOOLS_OBSERVATION_EXAMPLE'),'Set OPENTOOLS_OBSERVATION_EXAMPLE to retained native example output')
class NativeTests(unittest.TestCase):
    def setUp(self):self.native=Path(os.environ['OPENTOOLS_OBSERVATION_EXAMPLE'])
    def copy(self,name):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);p=Path(t.name)/'case';shutil.copytree(self.native/name,p);return p
    def test_actual_native_matrix_and_independent_model(self):
        summary=load(self.native/'summary.json');collection=load(self.native/'collection.json');self.assertEqual(summary['native_runs'],22)
        for row in collection['cases']:
            p=self.native/row['case'];e=load(p/'evidence.json');revalidate(e,p);ref=expected(row['family'],row['policy'],row['scenario'],row['fault'])
            self.assertEqual(e['edges'],ref['edges']);self.assertEqual(e['checks'],ref['checks']);self.assertEqual(e['native']['counts'],ref['counts'])
            self.assertEqual(review(load(p/'intent.json'),e,p),load(p/'report.json'))
    def test_same_binary_and_gating_counterexample(self):
        names=('stream-good-clean','stream-good-fault','stream-gated-clean','stream-gated-fault');self.assertEqual(len({file_hash(self.native/n/'run/Vtop') for n in names}),1)
        good=load(self.native/'stream-good-fault/evidence.json');bad=load(self.native/'stream-gated-fault/evidence.json')
        self.assertEqual(good['native']['counts']['completed'],bad['native']['counts']['completed']);self.assertEqual(good['native']['status'],'FAIL');self.assertEqual(bad['native']['status'],'PASS')
        self.assertTrue(any(e['mode']==1 and not e['enabled'] and e['rsp_valid'] and e['rsp_ready'] for e in bad['edges']))
    def test_equal_counts_wrong_id_still_rejected(self):
        e=load(self.native/'mailbox-wrong-id/evidence.json');r=load(self.native/'mailbox-wrong-id/report.json')
        self.assertEqual(e['native']['counts']['completed'],e['native']['counts']['checked']);self.assertEqual(exit_code(r),1)
    def test_actual_reset_cancels_outstanding(self):
        r=load(self.native/'stream-reset/report.json');self.assertEqual(exit_code(r),0);self.assertEqual(len(r['events']['cancelled']),1)
    def test_changed_source_binary_or_missing_journal(self):
        for filename in ('checker.hpp','Vtop','run.stdout.txt'):
            p=self.copy('stream-good-clean');e=load(p/'evidence.json');(p/'run'/filename).write_bytes(b'changed')
            with self.subTest(file=filename):self.assertEqual(exit_code(review(load(p/'intent.json'),e,p)),2)
    def test_forged_normalized_records_cannot_replace_native(self):
        p=self.copy('stream-gated-clean');e=load(p/'evidence.json');e['checks'].append({'tick':17,'id':8,'expected':0,'observed':0,'ok':1})
        with self.assertRaises(ValueError):revalidate(e,p)
    def test_truncated_or_aggregate_only_journal_rejected(self):
        p=self.copy('stream-good-clean');ctx=load(p/'capture-context.json')
        for content in ('FINAL 22 11 11 11 0\n','EDGE 0 1 0\n'):
            (p/'run/run.stdout.txt').write_text(content)
            with self.assertRaises(ValueError):capture(p,'run',ctx)
    def test_wrong_clock_port_map_or_reset_context(self):
        p=self.copy('mailbox-good-clean');ctx=load(p/'capture-context.json');ctx['reset_active']=1
        with self.assertRaises(ValueError):capture(p,'run',ctx)
        ctx=load(p/'capture-context.json');ctx['clock_ref']='top.other_clock'
        with self.assertRaises(ValueError):capture(p,'run',ctx)
    def test_native_unsupported_clock_and_malformed_xml(self):
        p=self.copy('stream-good-clean');ctx=load(p/'capture-context.json');path=p/'run/model.xml';original=path.read_text()
        self.assertIn('edgeType="POS"',original);path.write_text(original.replace('edgeType="POS"','edgeType="NEG"'))
        with self.assertRaises(ValueError):capture(p,'run',ctx)
        path.write_text('<truncated')
        with self.assertRaises(ValueError):capture(p,'run',ctx)
    def test_contradictory_native_counts_and_comparison_action(self):
        p=self.copy('stream-good-fault');ctx=load(p/'capture-context.json');path=p/'run/run.stdout.txt';original=path.read_text()
        path.write_text(original.replace('FINAL 22 11 11 11 4','FINAL 22 11 11 11 0'))
        with self.assertRaises(ValueError):capture(p,'run',ctx)
        lines=original.splitlines();index=next(i for i,v in enumerate(lines) if v.startswith('CHECK ') and v.endswith(' 0'));lines[index]=lines[index][:-1]+'1';path.write_text('\n'.join(lines)+'\n')
        with self.assertRaises(ValueError):capture(p,'run',ctx)
    def test_cli_data_only_and_existing_output_preserved(self):
        p=self.copy('stream-good-fault');output=p/'fresh.json';args=[sys.executable,str(PROFILE/'observation_check.py'),'capture',str(p),'run',str(p/'capture-context.json'),'--output',str(output)]
        r=subprocess.run(args,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(load(output),load(p/'evidence.json'));before=output.read_bytes()
        r=subprocess.run(args,capture_output=True,text=True);self.assertEqual(r.returncode,3);self.assertEqual(output.read_bytes(),before)
        command=p/'run/run.command.json';command.write_text(json.dumps(['NEVER_EXECUTE_CAPTURE',str(p/'marker')]))
        ctx=load(p/'capture-context.json');capture(p,'run',ctx);self.assertFalse((p/'marker').exists())

if __name__=='__main__':unittest.main()
