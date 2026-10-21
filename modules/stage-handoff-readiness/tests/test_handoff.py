import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

MODULE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(MODULE));sys.path.insert(0,str(MODULE/'examples'))
from handoff_core import digest,exit_code,read_json,review
from image_capture import capture
from create_example import records,save
from reference_model import CODE,CASES

def kinds(report,field='findings'):return {v['kind'] for v in report[field]}
def bind(values):
    inventory,journal,policy=values;journal['inventory_sha256']=policy['inventory_sha256']=digest(inventory);policy['journal_sha256']=digest(journal)
def transfer(journal):return next(e for e in journal['events'] if e['kind']=='handoff')
def elf_fixture():
    code=bytes.fromhex('6a5a58488907f4');data=bytearray(4096+len(code));data[:16]=b'\x7fELF\x02\x01\x01'+bytes(9)
    struct.pack_into('<HHIQQQIHHHHHH',data,16,2,62,1,CODE,64,0,0,64,56,1,0,0,0)
    struct.pack_into('<IIQQQQQQ',data,64,1,5,4096,CODE,CODE,len(code),len(code),4096);data[4096:]=code
    return data

class HandoffTests(unittest.TestCase):
    def test_ordered_handoff_and_alternate_stage_have_real_distinct_contracts(self):
        first=records('rom-ready');second=records('firmware-valid')
        for values in (first,second):self.assertEqual(exit_code(review(*values)),0)
        self.assertNotEqual(first[2]['image_sha256'],second[2]['image_sha256']);self.assertNotEqual(first[2]['stack_region'],second[2]['stack_region'])
        self.assertEqual(review(*second)['observed_result'],165)

    def test_image_fits_but_first_stack_access_fails_before_readiness(self):
        result=review(*records('rom-early'));self.assertEqual(exit_code(result),1)
        self.assertNotIn('entry_outside_executable_segment',kinds(result));self.assertFalse(result['first_stack_access']['successful'])
        self.assertIn('handoff_prerequisite_not_met',kinds(result));self.assertIn('successor_result_unknown',kinds(result,'gaps'))

    def test_later_readiness_does_not_repair_boundary_or_failed_access(self):
        values=records('rom-ready-late');self.assertTrue(values[1]['events'][-1]['value'])
        result=review(*values);self.assertEqual(exit_code(result),1)
        self.assertFalse(next(o for o in result['obligations'] if o['id']=='stack-alpha-ready')['at_handoff'])

    def test_wrong_loaded_image_can_execute_successfully_but_fail_receiver_contract(self):
        result=review(*records('firmware-wrong-image'));self.assertEqual(exit_code(result),1)
        self.assertEqual(result['observed_result'],90);self.assertTrue(result['first_stack_access']['successful'])
        self.assertTrue({'required_image_mismatch','successor_result_mismatch'}<=kinds(result))

    def test_ready_intended_stack_does_not_cover_wrong_initial_stack(self):
        result=review(*records('firmware-wrong-stack'));self.assertEqual(exit_code(result),1)
        self.assertTrue(all(o['status']=='met' for o in result['obligations']))
        self.assertTrue({'initial_stack_pointer_mismatch','stack_access_outside_required_region','observed_successor_access_failure'}<=kinds(result))

    def test_unmapped_entry_not_inferred_as_stack_failure(self):
        result=review(*records('wrong-entry'));self.assertIn('entry_outside_executable_segment',kinds(result))
        self.assertNotIn('observed_successor_access_failure',kinds(result));self.assertIsNone(result['first_stack_access'])

    def test_missing_snapshot_cannot_borrow_prior_or_future_good_fact(self):
        values=records('rom-ready');del transfer(values[1])['state']['stack-alpha-ready'];bind(values)
        result=review(*values);self.assertEqual(exit_code(result),2);self.assertIn('handoff_prerequisite_unknown',kinds(result,'gaps'))

    def test_explicit_false_state_retains_finding_when_capture_is_partial(self):
        values=records('rom-early');values[1]['events_complete']=False;bind(values)
        result=review(*values);self.assertEqual(exit_code(result),1);self.assertIn('event_capture_incomplete',kinds(result,'gaps'))

    def test_unknown_state_does_not_become_false_obligation(self):
        values=records('rom-ready');transfer(values[1])['state']['stack-alpha-ready']=None;bind(values)
        result=review(*values);self.assertEqual(exit_code(result),2);self.assertNotIn('handoff_prerequisite_not_met',kinds(result))

    def test_foreign_mode_or_inventory_binding_supplies_no_interpretation(self):
        inventory,_,policy=records('firmware-valid');_,journal,_=records('rom-ready')
        result=review(inventory,journal,policy);self.assertEqual(exit_code(result),2)
        self.assertFalse(result['obligations']);self.assertIsNone(result['first_stack_access'])

    def test_stale_source_revision_and_journal_digest_remain_gaps(self):
        for variant in ('source','journal'):
            values=records('rom-ready')
            if variant=='source':values[2]['source_revision_ref']='previous-source'
            else:values[2]['journal_sha256']='0'*64
            result=review(*values);self.assertEqual(exit_code(result),2)

    def test_required_clock_or_reset_state_is_independent(self):
        for key in ('clock-ready','reset-asserted'):
            values=records('rom-ready');values[2]['requirements'][key]=not values[2]['requirements'][key]
            result=review(*values);self.assertEqual(exit_code(result),1);self.assertIn('handoff_prerequisite_not_met',kinds(result))

    def test_complete_events_challenge_disagreeing_boundary_snapshot(self):
        values=records('rom-early');transfer(values[1])['state']['stack-alpha-ready']=True;bind(values)
        result=review(*values);self.assertIn('snapshot_event_disagreement',kinds(result));self.assertIn('observed_successor_access_failure',kinds(result))

    def test_unknown_access_outcome_is_not_a_success_or_known_failure(self):
        values=records('rom-ready');next(e for e in values[1]['events'] if e['kind']=='access')['successful']=None;bind(values)
        result=review(*values);self.assertEqual(exit_code(result),2);self.assertNotIn('observed_successor_access_failure',kinds(result))

    def test_missing_first_stack_history_is_not_evidence_of_no_first_use(self):
        values=records('rom-ready');values[1]['events']=[e for e in values[1]['events'] if e.get('purpose')!='stack'];bind(values)
        result=review(*values);self.assertEqual(exit_code(result),2);self.assertIn('first_stack_access_not_observed',kinds(result,'gaps'))

    def test_actual_failure_is_preserved_when_result_is_unknown(self):
        result=review(*records('firmware-early'));self.assertIn('observed_successor_access_failure',kinds(result))
        self.assertIn('successor_result_unknown',kinds(result,'gaps'));self.assertEqual(exit_code(result),1)

    def test_load_identity_and_image_metadata_must_agree_with_handoff(self):
        for target in ('load','image'):
            values=records('rom-ready')
            if target=='load':next(e for e in values[1]['events'] if e['kind']=='image_load')['image_sha256']='0'*64
            else:values[0]['image']['sha256']='0'*64
            bind(values);result=review(*values);self.assertEqual(exit_code(result),1)
            self.assertIn('handoff_loaded_image_disagreement' if target=='load' else 'actual_image_metadata_disagreement',kinds(result))

    def test_missing_load_or_result_remains_incomplete(self):
        for kind in ('image_load','result'):
            values=records('rom-ready');values[1]['events']=[e for e in values[1]['events'] if e['kind']!=kind];bind(values)
            self.assertEqual(exit_code(review(*values)),2)

    def test_stack_boundary_sp_and_alignment_apply_to_actual_access(self):
        values=records('rom-ready');sp=transfer(values[1])['initial_sp'];self.assertEqual(sp,values[2]['stack_region']['start']+values[2]['stack_region']['size'])
        transfer(values[1])['initial_sp']=sp-1;bind(values);self.assertIn('initial_stack_outside_contract',kinds(review(*values)))

    def test_typed_native_records_are_not_bound_to_example_actor_or_addresses(self):
        values=records('rom-ready');inventory,journal,policy=values;delta=1<<40
        policy['successor_ref']='stage-B';policy['initial_sp']+=delta;policy['entry']+=delta;policy['stack_region']['start']+=delta
        inventory['image']['entry']+=delta
        for segment in inventory['image']['segments']:segment['start']+=delta
        for event in journal['events']:
            if 'actor_ref' in event:event['actor_ref']='stage-B'
            if event['kind']=='handoff':event['successor_ref']='stage-B';event['entry']+=delta;event['initial_sp']+=delta
            if event['kind']=='access':event['address']+=delta
        inventory['source_kind']='reviewed-company-export';inventory['method_ref']='caller-qualified-export';bind(values)
        self.assertEqual(exit_code(review(*values)),0)

    def test_foreign_actor_supplies_no_successor_result_credit(self):
        values=records('rom-ready')
        for event in values[1]['events']:
            if event['kind'] in ('access','result'):event['actor_ref']='other-stage'
        bind(values);result=review(*values);self.assertEqual(exit_code(result),2);self.assertIsNone(result['observed_result'])

    def test_post_handoff_image_reload_needs_another_scope(self):
        values=records('rom-ready');values[1]['events'].append({'seq':100,'kind':'image_load','image_sha256':'0'*64,'evidence_ref':'later-reload'});bind(values)
        self.assertIn('image_reload_after_handoff',kinds(review(*values),'gaps'))

    def test_empty_requirements_duplicate_handoffs_and_boolean_addresses_invalid(self):
        for variant in ('empty','duplicate','bool','overflow'):
            values=records('rom-ready')
            if variant=='empty':values[2]['requirements']={}
            elif variant=='duplicate':values[1]['events'].append(dict(transfer(values[1]),seq=100))
            elif variant=='bool':transfer(values[1])['entry']=True
            else:values[2]['stack_region']={'start':(1<<64)-1,'size':2}
            bind(values)
            with self.assertRaises(ValueError):review(*values)

    def test_elf_capture_records_actual_file_identity_and_executable_load(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'receiver.elf';data=elf_fixture();path.write_bytes(data);image=capture(path)
            self.assertEqual(image['sha256'],hashlib.sha256(data).hexdigest());self.assertEqual(image['entry'],CODE)
            self.assertEqual(image['segments'][0]['permissions'],['R','X']);data[-1]=0x90;path.write_bytes(data)
            self.assertNotEqual(capture(path)['sha256'],image['sha256'])

    def test_elf_foreign_arch_dynamic_truncation_and_nonidentity_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'bad.elf'
            for variant in ('arch','dynamic','offset','identity','entry','short'):
                data=elf_fixture()
                if variant=='arch':struct.pack_into('<H',data,18,183)
                elif variant=='dynamic':struct.pack_into('<I',data,64,2)
                elif variant=='offset':struct.pack_into('<Q',data,72,len(data)+1)
                elif variant=='identity':struct.pack_into('<Q',data,88,CODE+4096)
                elif variant=='entry':struct.pack_into('<Q',data,24,CODE+4096)
                else:data=data[:64]
                path.write_bytes(data)
                with self.assertRaises(ValueError):capture(path)

    def test_cli_no_overwrite_strict_json_and_evidence_kind(self):
        values=records('rom-ready');self.assertEqual(values[0]['source_kind'],'reference-fixture')
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            for key,value in zip(('inventory','journal','policy'),values):save(folder/(key+'.json'),value)
            command=[sys.executable,str(MODULE/'handoff_review.py')]+[str(folder/(key+'.json')) for key in ('inventory','journal','policy')]
            result=subprocess.run(command,capture_output=True,text=True);self.assertEqual(result.returncode,0)
            before=(folder/'inventory.json').read_bytes();refused=subprocess.run(command+['--output',str(folder/'inventory.json')],capture_output=True,text=True)
            self.assertEqual(refused.returncode,3);self.assertEqual((folder/'inventory.json').read_bytes(),before)
            for raw in ('{"x":1,"x":2}','{"x":NaN}'):
                (folder/'bad.json').write_text(raw,encoding='utf-8')
                with self.assertRaises(ValueError):read_json(folder/'bad.json')

    @unittest.skipUnless(sys.platform=='linux' and os.environ.get('OPENTOOLS_HANDOFF_NATIVE')=='1','Native instruction-emulation tools not configured')
    def test_native_actual_elf_instructions_and_first_stack_failures(self):
        from run_native import run
        with tempfile.TemporaryDirectory() as directory:
            result=run(Path(directory)/'proof');self.assertEqual(len(result['cases']),8)
            self.assertEqual(sum(c['completed'] for c in result['cases']),3);self.assertEqual(sum(c['accesses'] for c in result['cases']),13)
            self.assertEqual(sum(c['fault']=='unready-stack-protection' for c in result['cases']),4)
            self.assertEqual(sum(c['status']=='within_observed_contract' for c in result['cases']),2)

if __name__=='__main__':unittest.main()
