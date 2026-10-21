"""Project-local onboarding commands used by the engineer's existing AI host."""
import json
from pathlib import Path

from .common import InputError, read_json, require, shape, write_json
from .intent import context_hint, new_draft, new_request, review, seal
from .onboarding import artifact_roots, discover, saved_profiles, select_workflow, source_path, workflow_contracts


def arguments(commands):
    onboard = commands.add_parser('onboard', help='Discover a project and retain source-backed activity intent with your existing AI')
    actions = onboard.add_subparsers(dest='onboard_command', required=True)
    listing = actions.add_parser('list', help='List installed activity-level adoption contracts')
    listing.add_argument('--module')
    for name in ('profiles', 'dependents'):
        saved = actions.add_parser(name, help='Find retained local intent' if name == 'profiles' else 'Find declared reviews affected by a selected source')
        saved.add_argument('--project', required=True)
        saved.add_argument('--project-ref', required=True)
        saved.add_argument('--profiles-dir', default='.opentools-local')
        saved.add_argument('--module')
        saved.add_argument('--limit', type=int, default=500)
        saved.add_argument('--out', required=True)
        if name == 'dependents':
            saved.add_argument('--source', required=True, help='Declared source identity: root=relative/path')
    inspect = actions.add_parser('inspect', help='Inventory selected project artifacts and executable locations; execute nothing')
    start = actions.add_parser('start', help='Create an ignored local work area, environment inventory and AI intent draft')
    for parser in (inspect, start):
        parser.add_argument('--project', required=True)
        parser.add_argument('--root', action='append', default=[], help='Explicit additional artifact root: alias=directory')
        parser.add_argument('--include', action='append', help='Selected tree/file: root=relative/path')
        parser.add_argument('--limit', type=int, default=2000)
        parser.add_argument('--hash-bytes', type=int, default=1024 * 1024)
        parser.add_argument('--tool', action='append', help='Executable lookup name; repeats replace the default lookup names')
    inspect.add_argument('--out', required=True)
    start.add_argument('--module', required=True)
    start.add_argument('--workflow')
    start.add_argument('--question', required=True)
    start.add_argument('--project-ref')
    start.add_argument('--scope', help='Current project/revision/configuration scope JSON')
    start.add_argument('--out-dir', default='.opentools-local/onboarding', help='New directory relative to the engineering project')
    bind = actions.add_parser('seal', help='Bind selected source bytes; preserve unresolved entries and explicit profile history')
    check = actions.add_parser('review', help='Recheck saved setup against current sources, scope, intent and method evidence')
    for parser in (bind, check):
        parser.add_argument('--project', required=True)
        parser.add_argument('--root', action='append', default=[])
        parser.add_argument('--out', required=True)
    bind.add_argument('--draft', required=True)
    bind.add_argument('--request', required=True, help='Separately retained original request.json')
    bind.add_argument('--previous')
    bind.add_argument('--change-reason')
    bind.add_argument('--max-source-bytes', type=int, default=512 * 1024 * 1024)
    check.add_argument('--profile', required=True)
    check.add_argument('--project-ref', required=True, help='Current project identity, not copied from an unrelated saved profile')
    check.add_argument('--scope', required=True, help='Current independently established scope JSON')
    check.add_argument('--context-hints', choices=('auto', 'off'), default='auto')
    check.add_argument('--hint-state', help='Optional local hint ledger for one context invitation per activity')


def root_options(values):
    result = {}
    for value in values:
        alias, separator, path = value.partition('=')
        require(separator and alias and path and alias not in result, 'Use distinct --root alias=directory values')
        result[alias] = path
    return result


def include_options(values):
    if not values:
        return None
    result = []
    for value in values:
        alias, separator, path = value.partition('=')
        require(separator and alias and path, 'Use --include root=relative/path')
        result.append({'root': alias, 'path': path})
    return result


def add_context_hint(report, state_path=None, enabled=True):
    report['context_hint'] = None
    if not enabled:
        return
    state = {'format': 'opentools.context-hint-state.v1', 'seen': []}
    path = Path(state_path) if state_path else None
    try:
        if path and path.exists():
            require(not path.is_symlink(), 'Hint state cannot be linked')
            state = read_json(path)
            shape(state, {'format', 'seen'})
            require(state['format'] == 'opentools.context-hint-state.v1' and isinstance(state['seen'], list)
                    and len(state['seen']) <= 10000 and all(isinstance(v, str) for v in state['seen']), 'Invalid owned hint ledger')
        hint = context_hint(report, state['seen'])
        if hint is None:
            return
        if path:
            # An exclusive per-ledger lock makes concurrent repeated reviews quiet.
            lock = path.with_name(path.name + '.lock')
            require(path.parent.is_dir(), 'Hint ledger directory must exist')
            owned_lock = False
            try:
                with lock.open('x', encoding='utf-8'):
                    owned_lock = True
                    if path.exists():
                        current = read_json(path)
                        require(current == state, 'Hint ledger changed concurrently')
                    updated = {'format': state['format'], 'seen': [*state['seen'], hint['id']]}
                    if path.exists():
                        # Only a validated, explicitly selected ledger is updated.
                        path.write_text(json.dumps(updated, indent=2) + '\n', encoding='utf-8')
                    else:
                        write_json(path, updated)
            except FileExistsError:
                return
            finally:
                if owned_lock:
                    lock.unlink()
        report['context_hint'] = hint
    except (InputError, OSError, ValueError, TypeError):
        # Optional promotion never blocks an otherwise usable standalone review.
        report['context_hint'] = None


def run(args):
    if args.onboard_command == 'list':
        entries = workflow_contracts(module=args.module)
        if args.module:
            entries = [w for w in entries if w['module'] == args.module]
            require(entries, 'Module has no installed adoption contract')
        print(json.dumps(entries, indent=2, ensure_ascii=False))
        return 0
    if args.onboard_command in ('profiles', 'dependents'):
        selected = include_options([args.source])[0] if args.onboard_command == 'dependents' else None
        result = saved_profiles(args.project, args.project_ref, args.profiles_dir, args.module, args.limit, selected)
        write_json(args.out, result)
        print(json.dumps({'status': 'profiles_found', 'count': len(result['profiles']),
                          'complete': result['coverage']['complete'], 'output': args.out}))
        return 0 if result['coverage']['complete'] else 2
    extras = root_options(args.root)
    if args.onboard_command in ('start', 'inspect'):
        tool_options = {} if args.tool is None else {'tools': args.tool}
        inventory = discover(args.project, extras, include_options(args.include), args.limit, args.hash_bytes, **tool_options)
        if args.onboard_command == 'inspect':
            write_json(args.out, inventory)
            print(json.dumps({'status': 'inventoried', 'files': len(inventory['files']), 'output': args.out,
                              'enumeration_complete': inventory['coverage']['enumeration_complete']}))
            return 0 if inventory['coverage']['enumeration_complete'] else 2
        workflow = select_workflow(args.module, args.workflow)
        roots = artifact_roots(args.project)
        target = source_path(roots, 'project', args.out_dir)
        require(not target.exists(), 'Choose a new local onboarding directory; existing profiles are preserved')
        scope = read_json(args.scope) if args.scope else {'revision_ref': None, 'configuration_ref': None}
        draft = new_draft(workflow, args.question, args.project_ref, scope)
        target.mkdir(parents=True)
        (target / '.gitignore').write_text('*\n', encoding='utf-8')
        write_json(target / 'environment.json', inventory)
        write_json(target / 'intent.draft.json', draft)
        write_json(target / 'request.json', new_request(args.question, args.project_ref, scope))
        write_json(target / 'context-hints.json', {'format': 'opentools.context-hint-state.v1', 'seen': []})
        packet = {'format': 'opentools.onboarding-start.v1', 'workflow': workflow,
                  'request': 'request.json', 'draft': 'intent.draft.json', 'inventory': 'environment.json', 'hint_state': 'context-hints.json',
                  'instructions': 'Read ONBOARDING.md and the selected workflow. Inspect original intent and native sources with the existing AI host. Propose entity mappings and a version-scoped evidence method, validate against native/reference output, then seal and review. Do not infer requirements from observed success. No native or model command has executed.',
                  'model': 'Your existing file/tool-enabled agent; API access alone needs its normal tool-execution integration.'}
        write_json(target / 'handoff.json', packet)
        print(json.dumps({'status': 'draft_created', 'directory': str(target), 'workflow': workflow['id'],
                          'questions': workflow['intent_questions'], 'native_or_model_execution': False}, indent=2, ensure_ascii=False))
        return 2
    require(not Path(args.out).exists() and Path(args.out).parent.is_dir(), 'Output must be a new file in an existing directory')
    if args.onboard_command == 'seal':
        profile = seal(args.project, read_json(args.draft), extras,
                       read_json(args.previous) if args.previous else None,
                       args.change_reason, max_source_bytes=args.max_source_bytes, request=read_json(args.request))
        write_json(args.out, profile)
        print(json.dumps({'status': 'sources_bound', 'profile_id': profile['profile_id'], 'output': args.out,
                          'engineering_approval': False}))
        return 0
    profile = read_json(args.profile)
    report = review(args.project, profile, args.project_ref, read_json(args.scope), extras)
    if args.hint_state:
        selected = Path(args.hint_state).resolve()
        require(selected not in (Path(args.profile).resolve(), Path(args.out).resolve(), Path(args.scope).resolve()),
                'Hint ledger must be separate from profile, scope and review output')
    add_context_hint(report, args.hint_state, args.context_hints == 'auto')
    write_json(args.out, report)
    print(json.dumps({'status': report['status'], 'findings': len(report['findings']),
                      'questions': len(report['questions']), 'output': args.out}, ensure_ascii=False))
    return 0 if report['status'] == 'bound_for_review' else 2
