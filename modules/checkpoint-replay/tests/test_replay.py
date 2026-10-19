import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from replay_core import check, qualify, fingerprint, read_json, validate_request

spec=importlib.util.spec_from_file_location('replay_example',ROOT/'examples/create_example.py')
example_module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(example_module)


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.c,self.q,self.p,self.control,self.restored,files=example_module.example()
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name,data in files.items():
            (self.root/name).write_bytes(data)

    def check(self):
        return check(self.c,self.q,self.p,self.root)

    def qualify(self):
        return qualify(self.c,self.q,self.p,self.control,self.restored,self.root)

    def bind(self):
        for record in (self.c,self.q):
            record['profile_sha256']=fingerprint(self.p)
        for run in (self.control,self.restored):
            run.update(request_sha256=fingerprint(self.q),checkpoint_sha256=fingerprint(self.c),profile_sha256=fingerprint(self.p))

    def test_native_like_complete_selected_horizon(self):
        self.assertEqual(self.check()['status'],'compatible_within_declared_scope')
        self.assertEqual(self.qualify()['status'],'matched_selected_observables')

    def test_explicit_root_and_current_files_required(self):
        self.assertEqual(check(self.c,self.q,self.p)['status'],'unknown_compatibility')
        (self.root/'model.bin').unlink()
        self.assertEqual(self.check()['status'],'unavailable_checkpoint')

    def test_corrupt_checkpoint(self):
        (self.root/'model.bin').write_bytes(b'truncated')
        self.assertEqual(self.check()['status'],'unavailable_checkpoint')

    def test_current_executable_not_just_declared_binary(self):
        (self.root/'sim.bin').write_bytes(b'replaced executable')
        self.assertEqual(self.check()['status'],'unavailable_checkpoint')

    def test_changed_binary_with_consistent_current_identity_is_incompatible(self):
        data=b'another executable'
        (self.root/'other.bin').write_bytes(data)
        value=hashlib.sha256(data).hexdigest()
        self.q['context']['binary_sha256']=value
        self.q['binary'].update(path='other.bin',sha256=value)
        self.assertEqual(self.check()['status'],'incompatible')

    def test_changed_consumed_prefix_image(self):
        data=b'new firmware'
        (self.root/'firmware.bin').write_bytes(data)
        value=hashlib.sha256(data).hexdigest()
        self.q['context']['prefix_inputs'][0]['sha256']=value
        self.q['prefix_files'][0]['sha256']=value
        self.assertEqual(self.check()['status'],'incompatible')

    def test_unreported_prefix_image_edit_is_unavailable(self):
        (self.root/'firmware.bin').write_bytes(b'unreported edit')
        self.assertEqual(self.check()['status'],'unavailable_checkpoint')

    def test_live_prefix_population_is_required(self):
        self.q['prefix_files']=[]
        self.assertEqual(self.check()['status'],'unknown_compatibility')

    def test_precapture_seed_is_not_runtime_override(self):
        self.q['context']['prefix_seed']=29
        self.assertEqual(self.check()['status'],'incompatible')

    def test_configuration_and_capture_point_are_exact(self):
        self.q['context']['configuration']['assertions']=False
        self.assertEqual(self.check()['status'],'incompatible')
        self.q['context']['configuration']['assertions']=True
        self.q['context']['capture_point']['step']=5
        self.assertEqual(self.check()['status'],'incompatible')

    def test_model_serialization_not_process_checkpoint(self):
        self.p['mechanism']='process_checkpoint'
        self.bind()
        self.assertEqual(self.check()['status'],'incompatible')

    def test_edited_profile_without_rebinding_is_unknown(self):
        self.p['boundary_ref']='different scope'
        self.assertEqual(self.check()['status'],'unknown_compatibility')

    def test_missing_rng_or_queue_is_rejected(self):
        for name in ('rng','queue'):
            item=next(v for v in self.c['state_inventory'] if v['id']==name)
            item['status']='missing'
            self.assertEqual(self.check()['status'],'incompatible')
            item['status']='captured'

    def test_unknown_or_incomplete_state_population(self):
        self.c['state_inventory'].pop()
        self.assertEqual(self.check()['status'],'unknown_compatibility')
        self.c['state_inventory_complete']['complete']=None
        self.assertEqual(self.check()['status'],'unknown_compatibility')

    def test_not_used_state_needs_profile_basis(self):
        self.c['state_inventory'][0]['status']='not_used'
        self.assertEqual(self.check()['status'],'incompatible')
        self.p['state'][0]['requirement']='not_used'
        self.bind()
        self.assertEqual(self.check()['status'],'compatible_within_declared_scope')
        self.p['state'][0]['evidence_ref']=None
        self.bind()
        self.assertEqual(self.check()['status'],'unknown_compatibility')

    def test_capture_and_restore_evidence_both_required(self):
        self.c['state_inventory'][0]['restore_ref']=None
        self.assertEqual(self.check()['status'],'unknown_compatibility')

    def test_failed_or_partial_capture(self):
        self.c['capture']['exit_code']=1
        self.assertEqual(self.check()['status'],'incompatible')
        self.c['capture'].update(exit_code=0,complete=False)
        self.assertEqual(self.check()['status'],'incompatible')

    def test_known_mismatch_preserves_unknown_state(self):
        self.q['context']['prefix_seed']=29
        self.c['state_inventory_complete']['complete']=None
        report=self.check()
        self.assertEqual(report['status'],'incompatible')
        self.assertTrue(report['unknowns'])

    def test_unknown_context_is_not_asserted_difference(self):
        self.q['context']['binary_sha256']=None
        report=self.check()
        self.assertEqual(report['status'],'unknown_compatibility')
        self.assertFalse(report['incompatibilities'])

    def test_missing_artifact_digest_is_unknown(self):
        self.c['artifacts'][0]['sha256']=None
        self.assertEqual(self.check()['status'],'unknown_compatibility')

    def test_artifact_escape_paths_rejected(self):
        for path in ('../outside','/outside','C:/outside','a\\b','a//b','a/./b'):
            self.c['artifacts'][0]['path']=path
            with self.subTest(path=path),self.assertRaises(ValueError):
                self.check()

    def test_symlink_checkpoint_is_unavailable(self):
        (self.root/'target.bin').write_bytes((self.root/'model.bin').read_bytes())
        (self.root/'model.bin').unlink()
        try:
            (self.root/'model.bin').symlink_to(self.root/'target.bin')
        except OSError:
            self.skipTest('symlink privilege unavailable')
        self.assertEqual(self.check()['status'],'unavailable_checkpoint')

    def test_missing_step_is_incomplete_evidence_not_behavioral_divergence(self):
        self.restored['samples'].pop(0)
        report=self.qualify()
        self.assertEqual(report['status'],'not_qualified')
        self.assertFalse(report['differences'])

    def test_missing_channel_is_unknown_not_divergence(self):
        self.restored['samples'][0]['values'].pop('rng')
        self.assertEqual(self.qualify()['status'],'not_qualified')
        self.assertFalse(self.qualify()['differences'])

    def test_reordered_and_duplicated_samples_cannot_qualify(self):
        original=copy.deepcopy(self.restored['samples'])
        self.restored['samples'].reverse()
        self.assertEqual(self.qualify()['status'],'not_qualified')
        self.restored['samples']=original+[copy.deepcopy(original[0])]
        self.assertEqual(self.qualify()['status'],'not_qualified')

    def test_passing_checker_does_not_prove_rng_replay(self):
        self.restored['samples'][0]['values']['rng']=999
        report=self.qualify()
        self.assertEqual(report['status'],'diverged')
        self.assertTrue(any(v['path']=='step/5/rng' for v in report['differences']))
        self.assertEqual(self.restored['completion']['exit_code'],0)

    def test_pending_transaction_order_is_observed(self):
        for run in (self.control,self.restored):
            run['samples'][0]['values']['queue']=[[1,7],[2,9]]
        self.restored['samples'][0]['values']['queue'].reverse()
        self.assertEqual(self.qualify()['status'],'diverged')

    def test_unknown_observable_not_silently_equal(self):
        for run in (self.control,self.restored):
            run['samples'][0]['values']['rng']=None
        self.assertEqual(self.qualify()['status'],'not_qualified')

    def test_shortened_or_foreign_horizon_is_not_qualified(self):
        self.restored['horizon']['end_step']=5
        self.assertEqual(self.qualify()['status'],'not_qualified')

    def test_foreign_binding_does_not_become_divergence_proof(self):
        self.restored['request_sha256']='a'*64
        self.restored['samples'][0]['values']['rng']=999
        report=self.qualify()
        self.assertEqual(report['status'],'not_qualified')
        self.assertTrue(report['differences'])

    def test_two_labels_cannot_reuse_one_execution_identity(self):
        self.restored['run_ref']=self.control['run_ref']
        self.assertEqual(self.qualify()['status'],'not_qualified')

    def test_exploratory_branch_is_not_faithful_replay(self):
        self.q['intent']='exploratory'
        self.q['continuation']['forced_signal']='a=1'
        self.bind()
        self.assertEqual(self.qualify()['status'],'not_qualified')

    def test_failed_execution_cannot_qualify_even_when_observations_match(self):
        self.restored['completion']['exit_code']=1
        self.assertEqual(self.qualify()['status'],'not_qualified')

    def test_known_observed_difference_survives_failed_execution(self):
        self.restored['completion']['exit_code']=1
        self.restored['samples'][0]['values']['rng']=999
        report=self.qualify()
        self.assertEqual(report['status'],'diverged')
        self.assertTrue(report['unknowns'])

    def test_capture_boundary_is_qualified(self):
        self.restored['start']['values']['rng']=999
        self.assertEqual(self.qualify()['status'],'diverged')

    def test_inconsistent_terminal_observation_is_unqualified(self):
        self.restored['end']['values']['rng']=999
        self.assertEqual(self.qualify()['status'],'not_qualified')

    def test_schema_rejects_bool_steps_and_unknown_fields(self):
        self.q['horizon']['start_step']=True
        with self.assertRaises(ValueError):
            validate_request(self.q)
        self.q['horizon']['start_step']=4
        self.q['typo']='unrecognized'
        with self.assertRaises(ValueError):
            validate_request(self.q)

    def test_duplicate_json_keys_and_nonfinite_values_rejected(self):
        for content in ('{"a":1,"a":2}','{"a":NaN}'):
            (self.root/'bad.json').write_text(content)
            with self.assertRaises(ValueError):
                read_json(self.root/'bad.json')

    def test_cli_exit_codes_new_outputs_and_input_preservation(self):
        names=('checkpoint','request','profile','control','restored')
        for name,value in zip(names,(self.c,self.q,self.p,self.control,self.restored)):
            (self.root/(name+'.json')).write_text(json.dumps(value))
        command=[sys.executable,str(ROOT/'checkpoint_replay.py'),'qualify']+[str(self.root/(name+'.json')) for name in names]
        command+=['--artifact-root',str(self.root)]
        self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)
        self.assertEqual(subprocess.run(command+['--json-out',str(self.root/'model.bin')],capture_output=True).returncode,3)
        self.assertEqual(subprocess.run(command[:-2],capture_output=True).returncode,2)
        self.restored['samples'][0]['values']['rng']=999
        (self.root/'restored.json').write_text(json.dumps(self.restored))
        self.assertEqual(subprocess.run(command,capture_output=True).returncode,1)


class NativeRecipeTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('OPENTOOLS_CHECKPOINT_NATIVE'),'set OPENTOOLS_CHECKPOINT_NATIVE to Verilator 5.020 executable')
    def test_actual_save_restore_external_state_and_rejections(self):
        with tempfile.TemporaryDirectory(prefix='opentools-replay-test-') as folder:
            out=Path(folder)/'case'
            result=subprocess.run([sys.executable,str(ROOT/'examples/verilator/run_example.py'),
                  '--verilator',os.environ['OPENTOOLS_CHECKPOINT_NATIVE'],'--verilator-root',os.environ['VERILATOR_ROOT'],
                  '--directory',str(out),'--negative-controls','--overhead-pairs','2'],capture_output=True,text=True,timeout=180)
            self.assertEqual(result.returncode,0,result.stderr)
            summary=read_json(out/'summary.json')
            self.assertEqual(summary['status'],'matched_selected_observables')
            self.assertEqual(summary['negative_controls']['missing_rng']['native_checker_exit'],0)
            self.assertEqual(summary['negative_controls']['missing_rng']['gate'],'incompatible')
            self.assertFalse(summary['negative_controls']['changed_binary']['native_restore_executed'])
            self.assertFalse(summary['negative_controls']['changed_prefix']['native_restore_executed'])
            self.assertNotEqual(summary['negative_controls']['failed_restore']['native_exit'],0)
            self.assertIsNone(summary['native_phase_observations']['restart']['rng_captured'])
            sampling=read_json(out/'sampling-cost.json')['pairs']
            self.assertEqual(len(sampling),2)
            self.assertTrue(all(row['every_step']['stdout_bytes']>row['boundary_only']['stdout_bytes'] for row in sampling))
            control=read_json(out/'control.json')
            restored=read_json(out/'restored.json')
            self.assertEqual(control['samples'],restored['samples'])
            self.assertEqual(restored['start']['values']['time'],132)
            self.assertTrue(restored['start']['values']['pending'])
            # Independent integer reference of the complete emitted suffix.
            memory=[0]*16
            pending=[]
            rng=17
            checksum=0
            firmware=(out/'prefix.bin').read_bytes()
            samples={row['step']:row['values'] for row in restored['samples']}
            for n in range(1,193):
                rng=(rng*1664525+1013904223)&0xffffffff
                address=n-1 if n<=16 else (rng>>24)&15
                data=firmware[address] if n<=16 else (rng>>16)&255
                pending.append([n,n+1,memory[address]])
                if n>1:
                    previous=pending.pop(0)
                    checksum=(checksum*131+previous[2]+previous[0])&0xffffffffffffffff
                if n<=16 or rng&1:
                    memory[address]=data
                if n>64:
                    values=samples[n]
                    self.assertEqual(values['rng'],rng)
                    self.assertEqual(values['time'],2*(n+2))
                    self.assertEqual(values['dut_memory'],memory)
                    self.assertEqual(values['reference_memory'],memory)
                    self.assertEqual(values['pending'],pending)
                    self.assertEqual(values['data_out'],previous[2])
                    self.assertEqual(values['checker_digest'],format(checksum,'016x'))
                    self.assertEqual(values['failures'],0)


if __name__=='__main__':
    unittest.main()
