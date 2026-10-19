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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reuse_core import compare, fingerprint, read_json, validate_record
from verilator_evidence import inspect_manifest

spec = importlib.util.spec_from_file_location('reuse_example', ROOT/'examples/create_example.py')
example_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example_module)


class ReuseTests(unittest.TestCase):
    def setUp(self):
        self.a, self.b, self.p, artifact = example_module.example()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'sim.bin').write_bytes(artifact)

    def check(self):
        return compare(self.a, self.b, self.p, self.root)

    def test_seed_only_with_verified_artifact(self):
        report = self.check()
        self.assertEqual(report['status'], 'eligible_within_declared_scope')
        self.assertEqual(report['runtime_differences'][0]['name'], 'seed')
        self.assertEqual(report['build_key_sha256']['baseline'], report['build_key_sha256']['requested'])
        self.assertEqual(report['result_reuse'], 'not_established')

    def test_artifact_must_be_checked(self):
        self.assertEqual(compare(self.a, self.b, self.p)['status'], 'unknown_eligibility')

    def test_artifact_corruption(self):
        (self.root/'sim.bin').write_bytes(b'wrong')
        self.assertEqual(self.check()['status'], 'artifact_unavailable')

    def test_missing_artifact(self):
        (self.root/'sim.bin').unlink()
        self.assertEqual(self.check()['artifacts'][0]['status'], 'missing_or_unsafe')

    def test_original_artifact_digest_unknown(self):
        self.a['build']['artifacts'][0]['sha256'] = None
        self.assertEqual(self.check()['status'], 'unknown_eligibility')

    def test_traversal_rejected(self):
        for path in ('../secret', '/secret', 'C:/secret', 'a/../secret', 'a\\secret', 'a//b'):
            self.a['build']['artifacts'][0]['path'] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.check()

    def test_symlink_not_read(self):
        target = self.root/'target'
        target.write_bytes((self.root/'sim.bin').read_bytes())
        (self.root/'sim.bin').unlink()
        try:
            (self.root/'sim.bin').symlink_to(target)
        except OSError:
            self.skipTest('symlink privilege unavailable')
        self.assertEqual(self.check()['artifacts'][0]['status'], 'missing_or_unsafe')

    def test_source_include_generated_linked_input_changes(self):
        for role in ('source', 'include', 'generated', 'linked-model', 'nested-filelist'):
            with self.subTest(role=role):
                self.a['basis']['dependencies'][0]['role'] = role
                self.b['basis']['dependencies'][0]['role'] = role
                self.b['basis']['dependencies'][0]['sha256'] = 'a'*64
                self.assertEqual(self.check()['status'], 'rebuild_required')

    def test_unknown_hash_is_not_known_difference(self):
        self.b['basis']['dependencies'][0]['sha256'] = None
        self.assertEqual(self.check()['status'], 'unknown_eligibility')
        self.assertFalse(self.check()['build_differences'])

    def test_dependency_and_command_order_preserved(self):
        second = copy.deepcopy(self.a['basis']['dependencies'][0])
        second['path'] = 'second.sv'
        self.a['basis']['dependencies'].append(second)
        self.b['basis']['dependencies'] = list(reversed(self.a['basis']['dependencies']))
        self.assertEqual(self.check()['status'], 'rebuild_required')
        self.b['basis']['dependencies'] = copy.deepcopy(self.a['basis']['dependencies'])
        self.b['basis']['commands'][0]['argv'].reverse()
        self.assertEqual(self.check()['status'], 'rebuild_required')

    def test_search_order_and_environment_not_normalized(self):
        for key in ('configuration', 'environment'):
            saved = copy.deepcopy(self.b['basis'][key])
            self.b['basis'][key]['search_order'] = ['earlier', '.']
            self.assertEqual(self.check()['status'], 'rebuild_required')
            self.b['basis'][key] = saved

    def test_trace_build_change(self):
        self.b['basis']['options'][1]['value'] = True
        self.assertEqual(self.check()['status'], 'rebuild_required')

    def test_seed_can_be_build_consumed(self):
        self.p['rules'][0]['phase'] = 'build'
        for record in (self.a, self.b):
            record['profile_sha256'] = fingerprint(self.p)
        self.assertEqual(self.check()['status'], 'rebuild_required')

    def test_unclassified_option_unknown(self):
        self.b['basis']['options'].append({'name': 'firmware', 'value': 'image.bin', 'evidence_ref': 'run'})
        self.assertEqual(self.check()['status'], 'unknown_eligibility')

    def test_profile_change_requires_new_binding(self):
        self.p['rules'][1]['phase'] = 'runtime'
        self.assertEqual(self.check()['status'], 'unknown_eligibility')

    def test_unsourced_phase_does_not_hide_build_changes(self):
        self.p['rules'][0]['evidence_ref'] = None
        for record in (self.a, self.b):
            record['profile_sha256'] = fingerprint(self.p)
        self.assertEqual(self.check()['status'], 'unknown_eligibility')

    def test_every_coverage_obligation_gates_eligibility(self):
        for key in self.b['coverage']:
            with self.subTest(key=key):
                saved = self.b['coverage'][key]
                self.b['coverage'][key] = {'complete': None, 'evidence_ref': None}
                self.assertEqual(self.check()['status'], 'unknown_eligibility')
                self.b['coverage'][key] = saved

    def test_posthoc_hashes_not_consumed_capture(self):
        self.a['capture']['consumed_bytes']['complete'] = False
        self.assertEqual(self.check()['status'], 'unknown_eligibility')

    def test_request_must_be_resolved_not_old_deps_rehashed(self):
        self.b['capture']['request_resolved']['complete'] = None
        self.assertEqual(self.check()['status'], 'unknown_eligibility')

    def test_incomplete_or_failed_build(self):
        for complete, code in ((False, 0), (True, 1), (None, None)):
            self.a['build'].update(complete=complete, exit_code=code)
            self.assertEqual(self.check()['status'], 'unknown_eligibility')

    def test_distinct_run_and_result_identities(self):
        self.b['result_ref'] = self.a['result_ref']
        self.assertEqual(self.check()['status'], 'unknown_eligibility')

    def test_known_rebuild_does_not_erase_unknowns(self):
        self.b['basis']['options'][1]['value'] = True
        self.a['capture']['consumed_bytes']['complete'] = None
        report = self.check()
        self.assertEqual(report['status'], 'rebuild_required')
        self.assertTrue(report['unknowns'])

    def test_evidence_location_change_is_not_build_change(self):
        self.b['basis']['dependencies'][0]['evidence_ref'] = 'relocated evidence'
        self.assertEqual(self.check()['status'], 'eligible_within_declared_scope')

    def test_malformed_records_rejected(self):
        for field, value in (('profile_sha256', 'invalid'), ('extra', 'typo')):
            record = copy.deepcopy(self.a)
            record[field] = value
            with self.assertRaises(ValueError):
                validate_record(record)

    def test_duplicate_options_and_json_keys_rejected(self):
        self.b['basis']['options'].append(copy.deepcopy(self.b['basis']['options'][0]))
        with self.assertRaises(ValueError):
            self.check()
        path = self.root/'dup.json'
        path.write_text('{"a":1,"a":2}')
        with self.assertRaises(ValueError):
            read_json(path)

    def test_cli_codes_and_output_preservation(self):
        for name, value in [('a', self.a), ('b', self.b), ('p', self.p)]:
            (self.root/(name+'.json')).write_text(json.dumps(value))
        command = [sys.executable, str(ROOT/'build_reuse.py'), 'compare', str(self.root/'a.json'),
                   str(self.root/'b.json'), str(self.root/'p.json'), '--artifact-root', str(self.root)]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.assertEqual(subprocess.run(command + ['--json-out', str(self.root/'sim.bin')], capture_output=True).returncode, 3)
        self.assertEqual(subprocess.run(command[:-2], capture_output=True).returncode, 2)
        self.b['basis']['options'][1]['value'] = True
        (self.root/'b.json').write_text(json.dumps(self.b))
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)


class NativeReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'Vtop__verFiles.dat'
        self.content = '# DESCRIPTION: Verilator output: Timestamp data for --skip-identical.  Delete at will.\nC "--cc -f outer.f"\nS 1 2 3 4 5 6 "outer.f"\nT 1 2 3 4 5 6 "obj_dir/Vtop.h"\n'
        self.path.write_text(self.content)

    def test_inventory_does_not_promote_timestamps_to_hashes(self):
        report = inspect_manifest(self.path, '5.020')
        self.assertEqual(report['sources'][0]['path'], 'outer.f')
        self.assertEqual(report['consumed_content_hashes'], 'not_present')
        self.assertEqual(report['dependency_closure'], 'not_established')
        self.assertEqual(report['source_file_sha256'], hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_unknown_native_profile_rejected(self):
        with self.assertRaises(ValueError):
            inspect_manifest(self.path, '5.052')

    def test_unsupported_or_duplicate_native_records_rejected(self):
        for extra in ('S 1 2 3 4 5 6 "outer.f"\n', 'future-record\n', 'C "again"\n'):
            self.path.write_text(self.content + extra)
            with self.assertRaises(ValueError):
                inspect_manifest(self.path, '5.020')

    @unittest.skipUnless(os.environ.get('OPENTOOLS_REUSE_NATIVE'), 'set OPENTOOLS_REUSE_NATIVE to Verilator 5.020 binary')
    def test_actual_native_nested_filelist_and_generated_include(self):
        binary = Path(os.environ['OPENTOOLS_REUSE_NATIVE']).resolve()
        library = Path(os.environ['VERILATOR_ROOT']).resolve()
        work = Path(self.temp.name)
        (work/'verilator').symlink_to(binary)
        (work/'lib').symlink_to(library, target_is_directory=True)
        (work/'inc').mkdir()
        for name, content in {'outer.f':'-f inner.f\n', 'inner.f':'+incdir+inc\ntop.sv\n',
                              'inc/generated.svh':'`define W 8\n',
                              'top.sv':'`include "generated.svh"\nmodule top(input logic [`W-1:0] a, output logic [`W-1:0] y); assign y=a; endmodule\n'}.items():
            (work/name).write_text(content)
        env = dict(os.environ, VERILATOR_ROOT=str(work/'lib'))
        version = subprocess.run([str(work/'verilator'), '--version'], env=env, capture_output=True, text=True, check=True).stdout
        self.assertIn('Verilator 5.020', version)
        subprocess.run([str(work/'verilator'), '--cc', '--MMD', '--top-module', 'top', '-f', 'outer.f'],
                       cwd=work, env=env, capture_output=True, check=True)
        report = inspect_manifest(work/'obj_dir/Vtop__verFiles.dat', '5.020')
        paths = {s['path'] for s in report['sources']}
        self.assertTrue({'outer.f', 'inner.f', 'inc/generated.svh', 'top.sv'} <= paths)
        self.assertEqual(report['dependency_closure'], 'not_established')


if __name__ == '__main__':
    unittest.main()
