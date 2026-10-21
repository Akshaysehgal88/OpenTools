import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PROFILE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROFILE));sys.path.insert(0,str(PROFILE/'examples'))
from handoff_core import review
from native_repair import capture
from repair_common import contained,exit_code,read_json,sha
from reference_model import compare

NATIVE=os.environ.get('OPENTOOLS_REPAIR_NATIVE')
def kinds(report,key='findings'):return {i['kind'] for i in report[key]}

@unittest.skipUnless(NATIVE,'Set OPENTOOLS_REPAIR_NATIVE to a retained example collection')
class HandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(NATIVE);cls.records={}
        collection=read_json(cls.root/'collection.json')
        for c in collection['cases']:
            folder=cls.root/c['case'];e=capture(folder/'run',read_json(folder/'context.json'))
            cls.records[c['case']]=(e,read_json(folder/'receiving-policy.json'),read_json(folder/'run/plan.json'))
    def pair(self,case='good',family='word-bank'):
        return copy.deepcopy(self.records[family+'-'+case][:2])
    def test_all_native_transactions_against_independent_array_replay(self):
        for e,p,plan in self.records.values():compare(e,plan)
    def test_valid_repair_no_repair_and_denied_probe_transfer(self):
        for family in ('word-bank','row-bank'):
            for case in ('good','no-repair','early-release-denied'):
                report=review(*self.pair(case,family));self.assertEqual(exit_code(report),0)
                self.assertTrue(report['handoffs'][0]['admitted'])
    def test_all_seeded_fault_controls_have_known_findings(self):
        for name,(e,p,_) in self.records.items():
            if not name.endswith(('-good','-no-repair','-early-release-denied')):
                self.assertEqual(exit_code(review(e,p)),1,name)
    def test_passing_native_test_can_cover_wrong_physical_rows(self):
        e,p=self.pair('test-target-mismatch');r=review(e,p)
        self.assertEqual(e['native_result']['status'],'PASS')
        self.assertIn('handoff_prerequisites_not_met',kinds(r));self.assertFalse(r['handoffs'][0]['admitted'])
        self.assertTrue(r['handoffs'][0]['missing_test_physical_words'])
    def test_ecc_valid_data_does_not_prove_logical_mapping(self):
        e,p=self.pair('mapping-mismatch');rows=[r for r in e['events'] if r['operation']==7 and not r['error']]
        self.assertTrue(rows);r=review(e,p)
        self.assertIn('consumer_physical_view_mismatch',kinds(r));self.assertIn('required_readback_mismatch',kinds(r))
    def test_loaded_no_repair_is_distinct_from_missing_load(self):
        e,p=self.pair('no-repair');load=next(r for r in e['events'] if r['operation']==3)
        self.assertEqual((load['repair_loaded'],load['repair_active']),(1,0));self.assertEqual(exit_code(review(e,p)),0)
    def test_late_mapping_epoch_does_not_inherit_old_initialization(self):
        r=review(*self.pair('repair-load-late'))
        self.assertIn('initialization_not_admitted',kinds(r));self.assertIn('old_read_before_current_epoch_initialization',kinds(r))
    def test_ready_flags_do_not_replace_current_ecc(self):
        e,p=self.pair('stale-ecc');self.assertTrue(any(row['initialized']==15 for row in e['events']))
        r=review(e,p);self.assertIn('consumer_uncorrectable_word',kinds(r));self.assertIn('initialization_not_admitted',kinds(r))
    def test_ecc_enable_is_required_at_release_and_consumption(self):
        r=review(*self.pair('ecc-disabled'));self.assertIn('consumer_ecc_disabled',kinds(r));self.assertFalse(r['handoffs'][0]['admitted'])
    def test_partial_full_and_zero_mask_semantics(self):
        e,p=self.pair();self.assertEqual(exit_code(review(e,p)),0)
        e,p=self.pair('byte-lane-reversal');self.assertIn('byte_write_semantics_mismatch',kinds(review(e,p)))
        zero=next(r for r in e['events'] if r['event_ref']=='zero-write')
        self.assertEqual((zero['internal_read'],zero['committed'],zero['error']),(0,0,0))
    def test_test_port_is_revoked_at_functional_handoff(self):
        r=review(*self.pair('test-owner-leak'));self.assertIn('test_port_access_after_handoff',kinds(r));self.assertIn('required_readback_mismatch',kinds(r))
    def test_full_write_does_not_claim_old_ecc_status(self):
        e,p=self.pair();row=next(r for r in e['events'] if r['event_ref']=='full-write');row['uncorrectable']=1
        self.assertIn('unexpected_old_read_status',kinds(review(e,p)))
    def test_invalid_payload_cannot_be_loaded_as_valid_mapping(self):
        r=review(*self.pair('invalid-repair'));self.assertIn('repair_payload_mismatch',kinds(r));self.assertFalse(r['handoffs'][0]['admitted'])
    def test_missing_source_or_owner_keeps_review_open(self):
        e,p=self.pair();e['context']['macro_view_ref']=None;p['owner_ref']=None
        r=review(e,p);self.assertEqual(exit_code(r),2);self.assertIn('missing_source_basis',kinds(r,'gaps'))
    def test_independent_roster_cannot_be_replaced_by_observed_events(self):
        e,p=self.pair();p['required_accesses'].append(dict(event_ref='new-consumer-read',operation=7,word=0,expected_data=0))
        r=review(e,p);self.assertEqual(exit_code(r),2);self.assertIn('required_access_missing',kinds(r,'gaps'))
    def test_foreign_or_stale_scope_is_quarantined(self):
        for field in ('memory_ref','init_epoch_ref','configuration_ref','transition_ref'):
            e,p=self.pair();p['identity'][field]='foreign/'+field;r=review(e,p)
            self.assertEqual(exit_code(r),2);self.assertFalse(r['handoffs']);self.assertIn('scope_not_admitted',kinds(r,'gaps'))
    def test_wrong_source_plan_command_or_binary_keeps_receiving_basis_open(self):
        for field in ('source_sha256','plan_sha256','run_command_sha256','binary_sha256'):
            e,p=self.pair();p[field]={} if field=='source_sha256' else '0'*64
            r=review(e,p);self.assertEqual(exit_code(r),2);self.assertFalse(r['accesses'])
    def test_known_native_failure_remains_when_receiving_basis_is_unknown(self):
        e,p=self.pair('mapping-mismatch');p['identity']['design_ref']='other'
        r=review(e,p);self.assertEqual(exit_code(r),1);self.assertIn('native_assertions_failed',kinds(r));self.assertFalse(r['accesses'])
    def test_geometry_and_unsupported_repair_format_are_explicit(self):
        e,p=self.pair();p['geometry']['physical_words']+=1
        self.assertIn('geometry_mismatch',kinds(review(e,p)))
        e,p=self.pair();p['repair']['bad_lsb']=5
        with self.assertRaises(ValueError):review(e,p)
    def test_selected_native_role_map_must_resolve_actual_xml(self):
        folder=self.root/'row-bank-good';context=read_json(folder/'context.json');context['role_map']['reset']='reset'
        with self.assertRaises(ValueError):capture(folder/'run',context)
    def test_native_terminal_counter_or_payload_tampering_is_invalid(self):
        source=self.root/'word-bank-good/run'
        for filename,change in [('run.stdout.txt',lambda s:s.replace('NATIVE_RESULT 28 52 0','NATIVE_RESULT 28 52 1')),
                                ('plan.json',lambda s:s.replace('"actual_payload": 2120','"actual_payload": 2121').replace('"repair_input": 2120','"repair_input": 2121'))]:
            with tempfile.TemporaryDirectory() as temp:
                shutil.copytree(source,Path(temp)/'run');folder=Path(temp)/'run';path=folder/filename
                original=path.read_text();changed=change(original);self.assertNotEqual(original,changed);path.write_text(changed)
                with self.assertRaises(ValueError):capture(folder,read_json(source.parent/'context.json'))
    def test_missing_native_artifact_is_invalid_not_clean(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):contained(temp,'../run.stdout.txt')
            with self.assertRaises(ValueError):capture(temp,self.pair()[0]['context'])
    def test_cli_recaptures_native_bytes_and_preserves_failure_exit(self):
        for case,code in [('good',0),('mapping-mismatch',1)]:
            folder=self.root/('word-bank-'+case)
            p=subprocess.run([sys.executable,str(PROFILE/'handoff.py'),'review',str(folder/'run'),str(folder/'context.json'),str(folder/'receiving-policy.json')],capture_output=True,text=True)
            self.assertEqual(p.returncode,code,p.stderr);self.assertEqual(json.loads(p.stdout)['native_result']['status'],'PASS' if code==0 else 'FAIL')

if __name__=='__main__':unittest.main()
