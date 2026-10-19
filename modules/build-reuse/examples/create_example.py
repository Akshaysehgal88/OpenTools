"""Create a self-contained synthetic comparison, including a verifiable artifact."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reuse_core import COVERAGE, fingerprint


def example():
    profile = {'format': 'opentools.build-profile.v1', 'id': 'synthetic-runtime-seed',
               'evidence_ref': 'synthetic:runner consumes seed after launch',
               'rules': [{'name': 'seed', 'phase': 'runtime', 'evidence_ref': 'synthetic:argv parser'},
                         {'name': 'trace', 'phase': 'build', 'evidence_ref': 'synthetic:instrumentation generation'}]}
    source_hash = hashlib.sha256(b'synthetic source').hexdigest()
    artifact = b'synthetic artifact, not an executable\n'
    baseline = {'format': 'opentools.build-record.v1', 'record_ref': 'synthetic:build-A',
                'profile_sha256': fingerprint(profile),
                'basis': {'commands': [{'cwd': '/synthetic/work', 'argv': ['simulator', '--cc', 'top.sv'],
                                        'evidence_ref': 'synthetic:build argv'}],
                          'dependencies': [{'path': 'top.sv', 'role': 'source', 'sha256': source_hash,
                                            'evidence_ref': 'synthetic:consumed source capture'}],
                          'configuration': {'top': 'top', 'linked_models': [], 'search_order': ['.']},
                          'environment': {'LANG': 'C', 'PATH': '/synthetic/bin'},
                          'toolchain': [{'name': 'simulator', 'identity': 'synthetic:version-and-image',
                                         'evidence_ref': 'synthetic:toolchain capture'}],
                          'options': [{'name': 'seed', 'value': 17, 'evidence_ref': 'synthetic:run argv'},
                                      {'name': 'trace', 'value': False, 'evidence_ref': 'synthetic:build argv'}]},
                'coverage': {key: {'complete': True, 'evidence_ref': 'synthetic:bounded inventory including N/A declarations'} for key in COVERAGE},
                'capture': {key: {'complete': True, 'evidence_ref': 'synthetic:immutable source/resolution record'}
                            for key in ('consumed_bytes', 'request_resolved')},
                'build': {'complete': True, 'exit_code': 0, 'evidence_ref': 'synthetic:completed build',
                          'artifacts': [{'path': 'sim.bin', 'sha256': hashlib.sha256(artifact).hexdigest(),
                                         'evidence_ref': 'synthetic:artifact capture'}]},
                'run_ref': 'synthetic:run-17', 'result_ref': 'synthetic:result-17'}
    requested = copy.deepcopy(baseline)
    requested.update(record_ref='synthetic:request-B', run_ref='synthetic:run-29', result_ref='synthetic:result-29')
    requested['basis']['options'][0]['value'] = 29
    requested['capture']['consumed_bytes'] = {'complete': None, 'evidence_ref': None}
    requested['build'] = {'complete': None, 'exit_code': None, 'evidence_ref': None, 'artifacts': []}
    return baseline, requested, profile, artifact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    args = parser.parse_args()
    out = Path(args.directory)
    out.mkdir(parents=False, exist_ok=False)
    baseline, requested, profile, artifact = example()
    for name, data in [('baseline', baseline), ('requested', requested), ('profile', profile)]:
        (out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8', newline='\n')
    (out / 'sim.bin').write_bytes(artifact)


if __name__ == '__main__':
    main()
