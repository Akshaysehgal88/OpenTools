"""Local project discovery and per-activity adoption contracts; no EDA execution."""
import os
from pathlib import Path, PurePosixPath
import re
import shutil

from .catalog import ROOT, module_catalog
from .common import digest, file_hash, relative_file, require, shape, text

SKIP_DIRS = {'.git', '.hg', '.svn', '.local', '.opentools-local', '.agents', '.claude',
             '.opentools', '.venv', 'venv', '__pycache__', 'node_modules'}
CATEGORIES = {
    '.sv': 'hdl-source', '.v': 'hdl-source', '.vhd': 'hdl-source', '.vhdl': 'hdl-source',
    '.sdc': 'timing-constraints', '.tcl': 'native-tool-script', '.lib': 'timing-library',
    '.lef': 'physical-library', '.def': 'physical-design', '.odb': 'physical-database',
    '.spef': 'parasitics', '.sdf': 'timing-annotation', '.upf': 'power-intent',
    '.ucdb': 'coverage-database', '.vdb': 'coverage-database', '.ucis': 'coverage-interchange',
    '.xml': 'structured-export', '.json': 'structured-record', '.yaml': 'structured-record',
    '.yml': 'structured-record', '.csv': 'table', '.rpt': 'native-report', '.log': 'run-log',
    '.vcd': 'waveform', '.fst': 'waveform', '.sby': 'formal-task', '.md': 'document',
    '.rst': 'document', '.txt': 'text-artifact', '.pdf': 'document', '.f': 'file-list',
    '.c': 'software-source', '.h': 'software-source', '.cpp': 'software-source',
    '.sh': 'runner-script', '.ps1': 'runner-script', '.mk': 'build-script'}
TOOL_NAMES = ('verilator', 'yosys', 'sby', 'openroad', 'sta', 'iverilog', 'vvp',
              'vcs', 'xrun', 'vsim', 'pt_shell', 'tempus', 'innovus', 'icc2_shell',
              'tessent', 'genus', 'dc_shell')


def portable_path(value):
    require(text(value) and len(value) <= 4096, 'A project-relative path is required')
    p = PurePosixPath(value)
    require('\\' not in value and ':' not in value and not p.is_absolute()
            and '..' not in p.parts and p.as_posix() == value and value != '.',
            'Use a normalized relative path inside a named artifact root')
    return p


def artifact_roots(project, extra=None):
    project = Path(project).resolve()
    require(project.is_dir(), 'Engineering project directory must exist')
    result = {'project': project}
    for alias, path in (extra or {}).items():
        require(alias != 'project' and re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', alias),
                'Artifact roots need distinct lowercase aliases; project is reserved')
        original = Path(path)
        require(original.is_dir() and not original.is_symlink(), 'Artifact root must be an existing directory')
        result[alias] = original.resolve()
    return result


def source_path(roots, alias, value):
    require(alias in roots, 'Artifact root is not configured: ' + str(alias))
    rel = portable_path(value)
    base = roots[alias]
    current = base
    for part in rel.parts:
        current = current / part
        require(not current.is_symlink(), 'Selected artifact traverses a symbolic link')
    resolved = current.resolve()
    require(base in resolved.parents, 'Selected artifact escapes its root')
    return current


def workflow_contracts(root=ROOT, module=None):
    """Discover contracts from installed manifests; older/custom modules get a fallback."""
    from .common import read_json
    result = []
    for module in module_catalog(root, module_id=module):
        base = Path(root) / 'modules' / module['id']
        if module.get('adoption'):
            record = read_json(relative_file(base, module['adoption']))
            shape(record, {'format', 'module', 'workflows'})
            require(record['format'] == 'opentools.adoption-contract.v1' and record['module'] == module['id'],
                    'Adoption contract must name its module')
            require(isinstance(record['workflows'], list) and record['workflows'], 'Adoption workflows required')
            entries = record['workflows']
        else:
            entries = [{'id': 'default', 'title': module['title'], 'entry': module['workflow'],
                        'stage': ', '.join(module['stages']), 'decision': module['description'],
                        'intent_questions': ['What original engineering requirement must this evidence answer?',
                                             'Which configuration, native entities and applicability sources define this stage?'],
                        'evidence_roles': [{'id': 'intent', 'meaning': 'Independent requirement and applicability source', 'required': True},
                                           {'id': 'native', 'meaning': 'Original native observations for the selected question', 'required': True}],
                        'revalidate_when': ['Requirements, native sources, configuration or mappings change'],
                        'references': [module['workflow']]}]
        seen = set()
        for workflow in entries:
            shape(workflow, {'id', 'title', 'entry', 'stage', 'decision', 'intent_questions',
                             'evidence_roles', 'revalidate_when', 'references'})
            require(text(workflow['id']) and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', workflow['id'])
                    and workflow['id'] not in seen, 'Distinct workflow identity required')
            seen.add(workflow['id'])
            for key in ('title', 'stage', 'decision'):
                require(text(workflow[key]), 'Workflow ' + key + ' required')
            require(workflow['entry'] in module['files'], 'Adoption entry must be declared package content')
            relative_file(base, workflow['entry'])
            for key in ('intent_questions', 'revalidate_when', 'references'):
                require(isinstance(workflow[key], list) and workflow[key] and all(text(v) for v in workflow[key]),
                        'Workflow ' + key + ' required')
            for name in workflow['references']:
                require(name in module['files'], 'Adoption reference must be declared package content')
                relative_file(base, name)
            roles = workflow['evidence_roles']
            require(isinstance(roles, list) and roles, 'Evidence roles required')
            role_ids = set()
            for role in roles:
                shape(role, {'id', 'meaning', 'required'})
                require(text(role['id']) and role['id'] not in role_ids and text(role['meaning'])
                        and type(role['required']) is bool, 'Distinct evidence role and explicit requirement needed')
                role_ids.add(role['id'])
            # Definition and referenced workflow bytes invalidate stale local setup.
            entry_hashes = {name: file_hash(base / name) for name in set(workflow['references']) | {workflow['entry']}}
            result.append({'module': module['id'], **workflow, 'contract_sha256': digest({'definition': workflow, 'references': entry_hashes}),
                           'contract_kind': 'declared' if module.get('adoption') else 'generic_fallback'})
    return result


def select_workflow(module, workflow=None, root=ROOT):
    entries = workflow_contracts(root, module=module)
    require(entries, 'No installed workflow for module: ' + str(module))
    if workflow is None:
        require(len(entries) == 1, 'Select an activity with --workflow: ' + ', '.join(v['id'] for v in entries))
        return entries[0]
    found = [v for v in entries if v['id'] == workflow]
    require(len(found) == 1, 'Unknown activity in the selected module: ' + str(workflow))
    return found[0]


def discover(project, extra=None, includes=None, limit=2000, hash_bytes=1024 * 1024, tools=TOOL_NAMES):
    require(type(limit) is int and 1 <= limit <= 100000, 'File limit must be 1..100000')
    require(type(hash_bytes) is int and 0 <= hash_bytes <= 16 * 1024 * 1024, 'Discovery hash budget must be 0..16MiB')
    roots = artifact_roots(project, extra)
    selections = includes or [{'root': alias, 'path': None} for alias in roots]
    require(isinstance(selections, list) and selections, 'Select at least one artifact tree')
    records, gaps, skipped, seen, remaining = [], [], [], set(), hash_bytes
    directories = 0
    for selected in selections:
        shape(selected, {'root', 'path'})
        alias = selected['root']
        require(alias in roots, 'Unknown selected root')
        start = roots[alias] if selected['path'] is None else source_path(roots, alias, selected['path'])
        require(start.is_dir() or start.is_file(), 'Selected tree or artifact does not exist')
        def onerror(error):
            gaps.append({'kind': 'unreadable_tree', 'root': alias, 'path': str(Path(error.filename).relative_to(roots[alias])) if error.filename else None})
        walk = os.walk(start, followlinks=False, onerror=onerror) if start.is_dir() else [(start.parent, [], [start.name])]
        for directory, children, names in walk:
            directories += 1
            if directories > limit * 4:
                gaps.append({'kind': 'directory_limit', 'limit': limit * 4})
                break
            directory = Path(directory)
            children[:] = sorted(name for name in children if name not in SKIP_DIRS)
            for name in list(children):
                if (directory / name).is_symlink():
                    skipped.append({'root': alias, 'path': (directory / name).relative_to(roots[alias]).as_posix(), 'reason': 'symlink_directory'})
                    children.remove(name)
            for name in sorted(names):
                path = directory / name
                rel = path.relative_to(roots[alias]).as_posix()
                key = (alias, rel)
                if key in seen:
                    continue
                seen.add(key)
                if len(records) >= limit:
                    gaps.append({'kind': 'file_limit', 'limit': limit})
                    break
                if path.is_symlink():
                    skipped.append({'root': alias, 'path': rel, 'reason': 'symlink_file'})
                    continue
                # Dotfiles and likely credentials have no default discovery role.
                if name.startswith('.') or name.lower().endswith(('.pem', '.key', '.p12', '.pfx')):
                    continue
                try:
                    stat = path.stat()
                    if not path.is_file():
                        continue
                    category = CATEGORIES.get(path.suffix.lower(), 'unclassified')
                    if name in ('Makefile', 'CMakeLists.txt'):
                        category = 'build-script'
                    value = {'root': alias, 'path': rel, 'category_candidate': category, 'bytes': stat.st_size, 'sha256': None}
                    if stat.st_size <= remaining:
                        value['sha256'] = file_hash(path)
                        remaining -= stat.st_size
                    records.append(value)
                except OSError:
                    gaps.append({'kind': 'unreadable_artifact', 'root': alias, 'path': rel})
            if gaps and gaps[-1]['kind'] in ('file_limit', 'directory_limit'):
                break
        if gaps and gaps[-1]['kind'] in ('file_limit', 'directory_limit'):
            break
    require(isinstance(tools, (tuple, list)) and all(text(name) and re.fullmatch(r'[A-Za-z0-9_.-]+', name) for name in tools),
            'Use simple executable lookup names, not commands')
    return {'format': 'opentools.environment-inventory.v1',
            'roots': {alias: str(path) for alias, path in roots.items()}, 'files': records,
            'tools': [{'name': name, 'path': shutil.which(name), 'version': None, 'executed': False} for name in tools],
            'coverage': {'selected_trees': selections, 'enumeration_complete': not gaps,
                         'hash_bytes_used': hash_bytes - remaining, 'gaps': gaps, 'skipped_links': skipped},
            'limits': 'Filename categories and PATH lookups are candidates. No file content is interpreted, no native command or project script executes, and this does not establish dependency completeness, tool version, license availability or engineering semantics.'}


def saved_profiles(project, project_ref, profiles_dir='.opentools-local', module=None, limit=500, source=None):
    """Find saved intent and declared dependents without reading engineering sources."""
    from .common import InputError, read_json
    from .intent import PROFILE_FORMAT, check_profile, validate_draft
    require(text(project_ref), 'Supply the current project identity')
    require(type(limit) is int and 1 <= limit <= 10000, 'Profile scan limit must be 1..10000')
    roots = artifact_roots(project)
    start = source_path(roots, 'project', profiles_dir)
    require(start.is_dir(), 'Selected project-local profile directory must exist')
    if source is not None:
        shape(source, {'root', 'path'})
        require(text(source['root']), 'Source needs its declared root alias')
        portable_path(source['path'])
    entries, gaps, visited, bytes_read, directories = [], [], 0, 0, 0
    contracts = {}
    def scan_error(error):
        gaps.append({'kind': 'unreadable_tree', 'path': str(error.filename)})
    for directory, children, names in os.walk(start, followlinks=False, onerror=scan_error):
        directories += 1
        if directories > limit * 4:
            gaps.append({'kind': 'directory_limit'}); break
        base = Path(directory)
        for name in list(children):
            if (base / name).is_symlink():
                gaps.append({'kind': 'linked_tree_skipped', 'path': (base / name).relative_to(roots['project']).as_posix()})
                children.remove(name)
        children.sort()
        for name in sorted(names):
            if not name.endswith('.json'):
                continue
            path = base / name
            relative = path.relative_to(roots['project']).as_posix()
            visited += 1
            if visited > limit:
                gaps.append({'kind': 'file_limit'}); break
            try:
                require(not path.is_symlink() and path.is_file(), 'Linked/nonregular profile skipped')
                size = path.stat().st_size
                require(size <= 4 * 1024 * 1024 and bytes_read + size <= 16 * 1024 * 1024,
                        'Profile scan byte limit exceeded')
                bytes_read += size
                record = read_json(path)
                if not isinstance(record, dict) or record.get('format') != PROFILE_FORMAT:
                    continue
                check_profile(record)
                draft = record['draft']
                identity = (draft['workflow']['module'], draft['workflow']['id'])
                if module and identity[0] != module:
                    continue
                if identity not in contracts:
                    contracts[identity] = select_workflow(*identity)
                contract = contracts[identity]
                validate_draft(draft, contract)
                matching = draft['project_ref'] == project_ref
                item = {'path': relative, 'profile_id': record['profile_id'], 'project_ref': draft['project_ref'],
                        'project_matches': matching, 'scope': draft['scope'], 'workflow': draft['workflow'],
                        'contract_current': draft['workflow']['contract_sha256'] == contract['contract_sha256'],
                        'question': draft['question'], 'obligations': draft['obligations'],
                        'source_bindings': record['source_bindings'], 'source_currency': 'not_checked'}
                if source is not None:
                    # A shared mount path alone cannot establish another project's relationship.
                    selected = {s['id'] for s in draft['sources'] if matching
                                and s['root'] == source['root'] and s['path'] == source['path']}
                    if not selected:
                        continue
                    methods = {m['id'] for m in draft['methods'] if selected.intersection(m['source_refs'])
                               or any(selected.intersection(c['source_refs']) for c in m['checks'])}
                    entities = {e['id'] for e in draft['entities'] if selected.intersection(e['source_refs'])
                                or e['method_ref'] in methods}
                    observations = [o for o in draft['observations'] if selected.intersection(o['source_refs'])
                                    or entities.intersection(o['entities']) or o['method_ref'] in methods]
                    observed = {o['obligation'] for o in observations}
                    obligations = [o['id'] for o in draft['obligations'] if o['id'] in observed
                                   or selected.intersection(o['basis'] + o['applicability']['basis'])
                                   or entities.intersection(o['entities'])]
                    item['dependents'] = {'sources': sorted(selected), 'methods': sorted(methods),
                                          'entities': sorted(entities), 'observations': [o['id'] for o in observations],
                                          'obligations': obligations}
                entries.append(item)
            except (InputError, OSError, ValueError, TypeError, KeyError) as exc:
                gaps.append({'kind': 'unreadable_or_invalid_record', 'path': relative, 'reason': str(exc)})
        if visited > limit:
            break
    return {'format': 'opentools.saved-profiles.v1', 'project_ref': project_ref, 'source': source,
            'profiles': entries, 'coverage': {'complete': not gaps, 'json_files_examined': min(visited, limit),
                                             'bytes_read': bytes_read, 'gaps': gaps},
            'limits': 'Saved declarations only. Recheck current scope, workflow, source bytes and method validity before reuse. Dependents follow only explicit source/method/entity/observation references in matching-project profiles; this is not a complete design dependency graph or proof of functional impact.'}
