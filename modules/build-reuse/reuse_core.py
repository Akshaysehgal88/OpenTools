"""Advisory build compatibility over an explicitly captured, declared boundary."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

COVERAGE = ('sources', 'filelists', 'includes', 'generated', 'configuration',
            'linked_models', 'toolchain', 'environment', 'resolution', 'options', 'artifacts')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def shape(value, keys, optional=()):
    require(isinstance(value, dict) and set(keys) <= set(value)
            and set(value) <= set(keys) | set(optional), 'Invalid fields; expected ' + ', '.join(keys))


def text(value):
    return isinstance(value, str) and bool(value.strip())


def nullable(value):
    return value is None or text(value)


def digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON: ' + value)))


def fact(value):
    shape(value, ('complete', 'evidence_ref'))
    require(value['complete'] is None or type(value['complete']) is bool, 'Completeness must be boolean or null')
    require(nullable(value['evidence_ref']), 'Evidence reference must be a string or null')


def relative(path):
    require(text(path) and '\\' not in path and ':' not in path, 'Use a relative POSIX artifact path')
    parts = path.split('/')
    require(not PurePosixPath(path).is_absolute() and all(p not in ('', '.', '..') for p in parts),
            'Artifact path must stay within its root')
    return parts


def validate_profile(profile):
    shape(profile, ('format', 'id', 'rules', 'evidence_ref'))
    require(profile['format'] == 'opentools.build-profile.v1' and text(profile['id']), 'Invalid flow profile')
    require(nullable(profile['evidence_ref']) and isinstance(profile['rules'], list), 'Invalid profile basis/rules')
    names = set()
    for rule in profile['rules']:
        shape(rule, ('name', 'phase', 'evidence_ref'))
        require(text(rule['name']) and rule['name'] not in names, 'Option names must be unique')
        names.add(rule['name'])
        require(rule['phase'] in ('build', 'runtime', 'unknown') and nullable(rule['evidence_ref']), 'Invalid option phase/basis')


def validate_record(record):
    shape(record, ('format', 'record_ref', 'profile_sha256', 'basis', 'coverage', 'capture',
                   'build', 'run_ref', 'result_ref'), ('provenance',))
    canonical(record)
    require(record['format'] == 'opentools.build-record.v1', 'Unsupported build record')
    require(all(text(record[k]) for k in ('record_ref', 'run_ref', 'result_ref')), 'Record/run/result identities required')
    require(record['profile_sha256'] is None or digest(record['profile_sha256']), 'Invalid profile digest')
    shape(record['coverage'], COVERAGE)
    for value in record['coverage'].values():
        fact(value)
    shape(record['capture'], ('consumed_bytes', 'request_resolved'))
    for value in record['capture'].values():
        fact(value)
    basis = record['basis']
    shape(basis, ('commands', 'dependencies', 'configuration', 'environment', 'toolchain', 'options'))
    require(isinstance(basis['commands'], list) and basis['commands'], 'Ordered commands required')
    for command in basis['commands']:
        shape(command, ('cwd', 'argv', 'evidence_ref'))
        require(nullable(command['cwd']) and isinstance(command['argv'], list) and command['argv']
                and all(isinstance(v, str) for v in command['argv']) and nullable(command['evidence_ref']), 'Invalid argv command')
    for key in ('configuration', 'environment'):
        require(basis[key] is None or isinstance(basis[key], dict), key + ' must be an object or null')
    require(isinstance(basis['dependencies'], list) and isinstance(basis['toolchain'], list)
            and isinstance(basis['options'], list), 'Dependencies, toolchain and options must be lists')
    names = set()
    for dep in basis['dependencies']:
        shape(dep, ('path', 'role', 'sha256', 'evidence_ref'))
        require(text(dep['path']) and text(dep['role']) and dep['path'] not in names, 'Unique dependency paths and roles required')
        names.add(dep['path'])
        require((dep['sha256'] is None or digest(dep['sha256'])) and nullable(dep['evidence_ref']), 'Invalid dependency identity')
    names = set()
    for tool in basis['toolchain']:
        shape(tool, ('name', 'identity', 'evidence_ref'))
        require(text(tool['name']) and tool['name'] not in names and nullable(tool['identity'])
                and nullable(tool['evidence_ref']), 'Invalid tool identity')
        names.add(tool['name'])
    names = set()
    for option in basis['options']:
        shape(option, ('name', 'value', 'evidence_ref'))
        require(text(option['name']) and option['name'] not in names and nullable(option['evidence_ref']), 'Invalid/duplicate option')
        names.add(option['name'])
    build = record['build']
    shape(build, ('complete', 'exit_code', 'evidence_ref', 'artifacts'))
    require(build['complete'] is None or type(build['complete']) is bool, 'Build complete must be boolean or null')
    require(build['exit_code'] is None or type(build['exit_code']) is int, 'Build exit code must be integer or null')
    require(nullable(build['evidence_ref']) and isinstance(build['artifacts'], list), 'Invalid build evidence')
    names = set()
    for artifact in build['artifacts']:
        shape(artifact, ('path', 'sha256', 'evidence_ref'))
        relative(artifact['path'])
        require(artifact['path'] not in names and (artifact['sha256'] is None or digest(artifact['sha256']))
                and nullable(artifact['evidence_ref']), 'Invalid artifact identity')
        names.add(artifact['path'])


def known_differences(a, b, path='basis'):
    """Null means unknown, never an asserted mismatch against a known value."""
    if a is None or b is None:
        return []
    if type(a) is not type(b):
        return [{'path': path, 'baseline': a, 'requested': b}]
    if isinstance(a, dict):
        if set(a) != set(b):
            return [{'path': path + '/keys', 'baseline': sorted(a), 'requested': sorted(b)}]
        return [change for key in sorted(a) for change in known_differences(a[key], b[key], path + '/' + key)]
    if isinstance(a, list):
        if len(a) != len(b):
            return [{'path': path + '/length', 'baseline': len(a), 'requested': len(b)}]
        return [change for i, (x, y) in enumerate(zip(a, b)) for change in known_differences(x, y, path + '/' + str(i))]
    return [] if a == b else [{'path': path, 'baseline': a, 'requested': b}]


def contains_null(value):
    if value is None:
        return True
    if isinstance(value, dict):
        return any(contains_null(v) for v in value.values())
    return isinstance(value, list) and any(contains_null(v) for v in value)


def build_key(record, phases):
    basis = record['basis']
    return {'commands': [{'cwd': c['cwd'], 'argv': c['argv']} for c in basis['commands']],
            'dependencies': [{k: d[k] for k in ('path', 'role', 'sha256')} for d in basis['dependencies']],
            'configuration': basis['configuration'], 'environment': basis['environment'],
            'toolchain': [{k: t[k] for k in ('name', 'identity')} for t in basis['toolchain']],
            'options': {o['name']: o['value'] for o in basis['options'] if phases.get(o['name']) == 'build'}}


def compare(baseline, requested, profile, artifact_root=None):
    validate_profile(profile)
    for record in (baseline, requested):
        validate_record(record)
    unknowns = []
    bound = all(r['profile_sha256'] == fingerprint(profile) for r in (baseline, requested))
    if not bound:
        unknowns.append('Records are not both bound to the supplied phase profile')
    phases = {r['name']: r['phase'] for r in profile['rules'] if text(r['evidence_ref'])} if bound and text(profile['evidence_ref']) else {}
    if not text(profile['evidence_ref']):
        unknowns.append('No usable bound phase-classification basis')
    for label, record in (('baseline', baseline), ('requested', requested)):
        for key, value in record['coverage'].items():
            if value['complete'] is not True or not text(value['evidence_ref']):
                unknowns.append(label + ': incomplete/unsourced ' + key + ' coverage')
        capture = record['capture']['consumed_bytes' if label == 'baseline' else 'request_resolved']
        if capture['complete'] is not True or not text(capture['evidence_ref']):
            unknowns.append(label + ': original consumed bytes/resolved request not established')
        if not record['basis']['dependencies'] or not record['basis']['toolchain']:
            unknowns.append(label + ': empty dependency/toolchain inventory')
        for kind in ('commands', 'dependencies', 'toolchain', 'options'):
            for item in record['basis'][kind]:
                if not text(item['evidence_ref']):
                    unknowns.append(label + ': unsourced ' + kind + ' entry')
        for option in record['basis']['options']:
            if phases.get(option['name']) not in ('build', 'runtime'):
                unknowns.append(label + ': unclassified option ' + option['name'])
            if contains_null(option['value']):
                unknowns.append(label + ': unknown option value ' + option['name'])
    a, b = build_key(baseline, phases), build_key(requested, phases)
    if contains_null(a) or contains_null(b):
        unknowns.append('Build key contains unknown values')
    changes = known_differences(a, b)
    runtime = []
    for name in sorted(set(o['name'] for r in (baseline, requested) for o in r['basis']['options'])):
        if phases.get(name) == 'runtime':
            values = [{o['name']: o['value'] for o in r['basis']['options']} for r in (baseline, requested)]
            # Preserve absent versus present-null; neither is a permission to reuse results.
            before = {'present': name in values[0], 'value': values[0].get(name)}
            after = {'present': name in values[1], 'value': values[1].get(name)}
            if before != after:
                runtime.append({'name': name, 'baseline': before, 'requested': after})
    if baseline['run_ref'] == requested['run_ref'] or baseline['result_ref'] == requested['result_ref']:
        unknowns.append('Distinct run and result identities are required for a reuse request')
    build = baseline['build']
    if build['complete'] is not True or build['exit_code'] != 0 or not text(build['evidence_ref']):
        unknowns.append('Baseline build is not an evidenced completed successful invocation')
    if not build['artifacts']:
        unknowns.append('No baseline immutable artifacts declared')
    artifacts = []
    unavailable = False
    for item in build['artifacts']:
        observation = {'path': item['path'], 'expected_sha256': item['sha256'], 'observed_sha256': None, 'status': 'unverified'}
        if item['sha256'] is None or not text(item['evidence_ref']):
            unknowns.append('Missing original artifact hash/evidence: ' + item['path'])
        if artifact_root is None:
            unknowns.append('Artifact root not supplied for current verification: ' + item['path'])
        else:
            root = Path(artifact_root).resolve(strict=True)
            require(root.is_dir(), 'Artifact root must be an existing directory')
            path = root.joinpath(*relative(item['path']))
            # Refuse symlink components, including a final symlink to a different binary.
            cursor = root
            safe = True
            for part in relative(item['path']):
                cursor = cursor / part
                safe = safe and not cursor.is_symlink()
            safe = safe and path.resolve().is_relative_to(root)
            if not safe or not path.is_file():
                observation['status'] = 'missing_or_unsafe'
                unavailable = True
            else:
                observed = hashlib.sha256(path.read_bytes()).hexdigest()
                observation['observed_sha256'] = observed
                if item['sha256'] is None:
                    observation['status'] = 'original_hash_unknown'
                else:
                    observation['status'] = 'verified' if observed == item['sha256'] else 'mismatch'
                    unavailable = unavailable or observation['status'] == 'mismatch'
        artifacts.append(observation)
    status = 'rebuild_required' if changes else 'artifact_unavailable' if unavailable else 'unknown_eligibility' if unknowns else 'eligible_within_declared_scope'
    return {'format': 'opentools.build-comparison.v1', 'status': status,
            'records': {'baseline': baseline['record_ref'], 'requested': requested['record_ref']},
            'input_sha256': {'baseline': fingerprint(baseline), 'requested': fingerprint(requested), 'profile': fingerprint(profile)},
            'build_key_sha256': {'baseline': fingerprint(a), 'requested': fingerprint(b)},
            'build_differences': changes, 'runtime_differences': runtime, 'unknowns': list(dict.fromkeys(unknowns)),
            'artifacts': artifacts, 'result_reuse': 'not_established',
            'limits': 'Advisory correspondence within supplied closure, consumed-byte and phase evidence; no cache operation, authenticity, sufficiency or future stability proof.'}


def exit_code(report):
    return {'eligible_within_declared_scope': 0, 'rebuild_required': 1, 'artifact_unavailable': 1, 'unknown_eligibility': 2}[report['status']]


def markdown(report):
    lines = ['# Build reuse comparison', '', 'Status: ' + report['status'], '',
             'Result reuse: ' + report['result_reuse'], '']
    for key, title in (('build_differences', 'Build differences'), ('runtime_differences', 'Runtime differences'),
                       ('unknowns', 'Unknowns'), ('artifacts', 'Artifact observations')):
        lines += ['## ' + title, '', '```json', json.dumps(report[key], indent=2, ensure_ascii=False), '```', '']
    return '\n'.join(lines + [report['limits'], ''])
