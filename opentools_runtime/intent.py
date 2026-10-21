"""Bind a reusable AI-authored intent profile to actual local sources and methods."""
from pathlib import Path

from .common import digest, file_hash, require, shape, text
from .onboarding import artifact_roots, portable_path, select_workflow, source_path

DRAFT_FORMAT = 'opentools.intent-draft.v1'
PROFILE_FORMAT = 'opentools.adoption-profile.v1'
REVIEW_LIMIT = ('Binding and declared traceability only. Recorded AI judgments, native meanings, '
                'applicability, owners and validation claims require source review. This is not '
                'design acceptance, source authentication or a universal EDA adapter.')


def new_request(question, project_ref=None, scope=None):
    require(text(question), 'Original engineering question required')
    value = {'format': 'opentools.intent-request.v1', 'question': question,
             'project_ref': project_ref, 'scope': scope or {}}
    return {'request_id': digest(value), **value}


def check_request(request):
    shape(request, {'format', 'request_id', 'question', 'project_ref', 'scope'})
    require(request['format'] == 'opentools.intent-request.v1' and text(request['question'])
            and isinstance(request['scope'], dict), 'Original request required')
    optional_text(request['project_ref'], 'original project identity')
    require(request['request_id'] == digest({k: v for k, v in request.items() if k != 'request_id'}),
            'Original request changed after capture')


def new_draft(workflow, question, project_ref=None, scope=None):
    require(text(question), 'Start with the actual engineering question')
    return {'format': DRAFT_FORMAT, 'project_ref': project_ref, 'scope': scope or {},
            'workflow': {k: workflow[k] for k in ('module', 'id', 'contract_sha256')},
            'question': question, 'sources': [], 'obligations': [], 'entities': [],
            'methods': [], 'observations': [], 'unknowns': [],
            'handoff': {'owner_ref': None, 'decision_ref': None}}


def records(value, name, maximum=1000):
    require(isinstance(value, list) and len(value) <= maximum, 'Bounded ' + name + ' list required')
    ids = set()
    for record in value:
        require(isinstance(record, dict) and text(record.get('id')) and len(record['id']) <= 256
                and record['id'] not in ids, 'Distinct ' + name + ' IDs required')
        ids.add(record['id'])
    return ids


def references(value, known, label):
    require(isinstance(value, list) and len(value) == len(set(value))
            and all(text(v) and v in known for v in value), 'Unknown or repeated ' + label + ' reference')


def optional_text(value, label):
    require(value is None or text(value), 'Use text or null for ' + label)


def validate_draft(draft, workflow):
    shape(draft, {'format', 'project_ref', 'scope', 'workflow', 'question', 'sources', 'obligations',
                  'entities', 'methods', 'observations', 'unknowns', 'handoff'})
    require(draft['format'] == DRAFT_FORMAT and text(draft['question']), 'Original question required')
    optional_text(draft['project_ref'], 'project identity')
    require(isinstance(draft['scope'], dict), 'Explicit scope object required')
    shape(draft['workflow'], {'module', 'id', 'contract_sha256'})
    require(all(draft['workflow'][k] == workflow[k] for k in ('module', 'id')), 'Draft selects another activity')
    require(text(draft['workflow']['contract_sha256']), 'Bind the selected workflow contract')
    sources = records(draft['sources'], 'source')
    obligations = records(draft['obligations'], 'obligation')
    entities = records(draft['entities'], 'entity')
    methods = records(draft['methods'], 'method')
    records(draft['observations'], 'observation')
    records(draft['unknowns'], 'unknown')
    roles = {r['id'] for r in workflow['evidence_roles']}
    for s in draft['sources']:
        shape(s, {'id', 'root', 'path', 'reference', 'revision_ref', 'kind', 'roles'})
        require(s['kind'] in ('intent', 'native', 'configuration', 'mapping', 'method', 'decision', 'other'), 'Source kind required')
        optional_text(s['reference'], 'source reference')
        optional_text(s['revision_ref'], 'source revision')
        require((s['root'] is None) == (s['path'] is None), 'Local source needs both root and path')
        if s['path'] is not None:
            require(text(s['root']), 'Named source root required')
            portable_path(s['path'])
        else:
            require(text(s['reference']), 'Unavailable/nonlocal source needs its actual reference')
        references(s['roles'], roles, 'evidence role')
    for o in draft['obligations']:
        shape(o, {'id', 'requirement', 'basis', 'applicability', 'acceptance', 'entities', 'status'})
        require(text(o['requirement']) and o['status'] in ('proposed', 'reviewed', 'unknown'), 'Requirement and review state required')
        references(o['basis'], sources, 'intent source')
        references(o['entities'], entities, 'entity')
        optional_text(o['acceptance'], 'acceptance criterion')
        shape(o['applicability'], {'status', 'condition', 'basis'})
        a = o['applicability']
        require(a['status'] in ('required', 'not_applicable', 'unknown'), 'Keep explicit applicability')
        optional_text(a['condition'], 'applicability condition')
        references(a['basis'], sources, 'applicability source')
    for entity in draft['entities']:
        shape(entity, {'id', 'meaning', 'native_object', 'source_refs', 'method_ref', 'status'})
        require(text(entity['meaning']) and entity['status'] in ('proposed', 'reviewed', 'unknown'), 'Entity meaning/review state required')
        optional_text(entity['native_object'], 'resolved native object')
        references(entity['source_refs'], sources, 'entity source')
        require(entity['method_ref'] is None or entity['method_ref'] in methods, 'Unknown entity method')
    for method in draft['methods']:
        shape(method, {'id', 'tool', 'interface', 'source_refs', 'checks', 'limitations', 'status'})
        shape(method['tool'], {'name', 'version'})
        require(text(method['tool']['name']) and text(method['interface']), 'Actual tool/interface required')
        optional_text(method['tool']['version'], 'tool version')
        references(method['source_refs'], sources, 'method source')
        require(method['status'] in ('proposed', 'reviewed', 'unknown'), 'Method review state required')
        require(isinstance(method['limitations'], list) and all(text(v) for v in method['limitations']), 'Method limits required')
        require(isinstance(method['checks'], list) and len(method['checks']) <= 100, 'Bounded validation checks required')
        for check in method['checks']:
            shape(check, {'claim', 'outcome', 'source_refs'})
            require(text(check['claim']) and check['outcome'] in ('pass', 'fail', 'unknown'), 'Preserve validation outcome')
            references(check['source_refs'], sources, 'validation source')
    for observation in draft['observations']:
        shape(observation, {'id', 'obligation', 'source_refs', 'entities', 'finding', 'outcome', 'method_ref'})
        require(observation['obligation'] in obligations and text(observation['finding'])
                and observation['outcome'] in ('supports', 'contradicts', 'unknown'), 'Observation needs its original obligation and interpretation')
        references(observation['source_refs'], sources, 'observation source')
        references(observation['entities'], entities, 'observation entity')
        require(observation['method_ref'] is None or observation['method_ref'] in methods, 'Unknown observation method')
    for unknown in draft['unknowns']:
        shape(unknown, {'id', 'question', 'reason', 'obligation', 'kind'})
        require(text(unknown['question']) and text(unknown['reason'])
                and unknown['kind'] in ('intent', 'mapping', 'native', 'relationship', 'authority'), 'Focused unresolved question required')
        require(unknown['obligation'] is None or unknown['obligation'] in obligations, 'Unknown unresolved obligation')
    shape(draft['handoff'], {'owner_ref', 'decision_ref'})
    for k, v in draft['handoff'].items():
        optional_text(v, k)


def check_profile(profile):
    shape(profile, {'format', 'profile_id', 'request', 'draft', 'source_bindings', 'history'})
    require(profile['format'] == PROFILE_FORMAT and isinstance(profile['source_bindings'], list)
            and isinstance(profile['history'], list) and len(profile['history']) <= 100, 'Invalid adoption profile')
    require(profile['profile_id'] == digest({k: v for k, v in profile.items() if k != 'profile_id'}),
            'Profile changed after sealing; preserve it and seal an explicit revision')
    require(isinstance(profile['draft'], dict), 'Profile draft required')
    check_request(profile['request'])


def seal(project, draft, extra=None, previous=None, change_reason=None, root=None, max_source_bytes=512 * 1024 * 1024, request=None):
    kwargs = {} if root is None else {'root': root}
    workflow = select_workflow(draft['workflow']['module'], draft['workflow']['id'], **kwargs)
    validate_draft(draft, workflow)
    require(request is not None, 'Supply the separately captured original engineering request')
    check_request(request)
    require(draft['question'] == request['question'], 'Draft question differs from the original request; capture a separately authorized changed question')
    require(request['project_ref'] is None or request['project_ref'] == draft['project_ref'], 'Original project identity changed')
    for key, value in request['scope'].items():
        require(value is None or draft['scope'].get(key) == value, 'Original requested scope changed: ' + key)
    require(draft['workflow']['contract_sha256'] == workflow['contract_sha256'], 'Workflow changed; review the current contract before sealing')
    require(type(max_source_bytes) is int and max_source_bytes > 0, 'Positive selected-source byte budget required')
    roots = artifact_roots(project, extra)
    bindings = []
    for source in draft['sources']:
        item = {'id': source['id'], 'state': 'unavailable', 'sha256': None, 'bytes': None}
        if source['path'] is not None:
            if source['root'] not in roots:
                item['state'] = 'root_unconfigured'
            else:
                path = source_path(roots, source['root'], source['path'])
                if not path.is_file():
                    item['state'] = 'missing'
                else:
                    item['bytes'] = path.stat().st_size
                    if item['bytes'] > max_source_bytes:
                        item['state'] = 'over_budget'
                    else:
                        before = path.stat()
                        item['sha256'] = file_hash(path)
                        after = path.stat()
                        require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
                                'Selected source changed while binding')
                        item['state'] = 'captured'
        bindings.append(item)
    history = []
    if previous is not None:
        check_profile(previous)
        require(text(change_reason), 'A revised profile needs its explicit change reason')
        old = previous['draft']
        require(old['workflow']['module'] == draft['workflow']['module']
                and old['workflow']['id'] == draft['workflow']['id'], 'Revision must retain the workflow identity')
        require(old['project_ref'] == draft['project_ref'], 'Another project needs a separate profile')
        history = previous['history'] + [{'profile_id': previous['profile_id'], 'reason': change_reason,
                                         'original_request': previous['request'],
                                         'original_draft': old, 'original_source_bindings': previous['source_bindings']}]
        require(len(history) <= 100, 'Retain long review history in a separate archive')
    value = {'format': PROFILE_FORMAT, 'request': request, 'draft': draft, 'source_bindings': bindings, 'history': history}
    return {'profile_id': digest(value), **value}


def review(project, profile, project_ref, scope, extra=None, root=None):
    check_profile(profile)
    draft = profile['draft']
    kwargs = {} if root is None else {'root': root}
    workflow = select_workflow(draft['workflow']['module'], draft['workflow']['id'], **kwargs)
    validate_draft(draft, workflow)
    require(text(project_ref) and isinstance(scope, dict), 'Supply current project identity and scope independently of saved setup')
    roots = artifact_roots(project, extra)
    questions, differences, source_states, findings = [], [], [], []
    def gap(code, question, reason, kind='intent', obligation=None):
        key = digest({'code': code, 'question': question, 'obligation': obligation})
        if not any(q['id'] == key for q in questions):
            questions.append({'id': key, 'code': code, 'question': question, 'reason': reason,
                              'kind': kind, 'obligation': obligation})
    context_ok = project_ref == draft['project_ref'] and scope == draft['scope']
    if not context_ok:
        gap('foreign_project_or_scope', 'Which retained profile belongs to this current project, revision and configuration?',
            'Saved profile identities differ from the explicitly supplied current scope.', 'mapping')
    if not draft['scope'] or any(value is None for value in draft['scope'].values()):
        gap('scope_unresolved', 'Which revision, configuration and operating conditions define the requested review?',
            'Resolve scope from original project sources rather than a successful result.', 'mapping')
    if workflow['contract_sha256'] != draft['workflow']['contract_sha256']:
        gap('workflow_changed', 'Which changed workflow requirements and native support need revalidation?',
            'The current activity definition or referenced instructions changed.', 'mapping')
    source_ids = {s['id'] for s in draft['sources']}
    require(len(profile['source_bindings']) == len(source_ids) and {b.get('id') for b in profile['source_bindings']} == source_ids,
            'Every declared source needs exactly one sealed binding')
    bound = {b['id']: b for b in profile['source_bindings']}
    source_by_id = {s['id']: s for s in draft['sources']}
    current = set()
    for s in draft['sources']:
        b = bound[s['id']]
        shape(b, {'id', 'state', 'sha256', 'bytes'})
        status = b['state']
        if s['path'] is not None and s['root'] in roots:
            path = source_path(roots, s['root'], s['path'])
            if b['state'] != 'captured':
                status = 'not_captured'
            elif not path.is_file():
                status = 'missing'
            elif path.stat().st_size != b['bytes'] or file_hash(path) != b['sha256']:
                status = 'changed'
            else:
                status = 'current'
                current.add(s['id'])
        elif s['path'] is not None:
            status = 'root_unconfigured'
        source_states.append({'id': s['id'], 'state': status, 'kind': s['kind'], 'roles': s['roles'],
                              'reference': s['reference'], 'revision_ref': s['revision_ref']})
        if status != 'current':
            gap('source_' + status, 'Where is the original applicable source for ' + s['id'] + '?',
                'Retained reference: ' + str(s['reference']) + '; original binding is preserved.',
                'relationship' if s['kind'] in ('intent', 'mapping') else 'native')
        if s['revision_ref'] is None:
            gap('source_revision_unknown', 'Which revision does ' + s['id'] + ' represent?',
                'File bytes do not establish the source revision.',
                'relationship' if s['kind'] in ('intent', 'configuration', 'mapping', 'decision') else 'native')
    for role in workflow['evidence_roles']:
        if role['required'] and not any(role['id'] in s['roles'] for s in draft['sources']):
            gap('missing_evidence_role', 'Which source supplies ' + role['meaning'] + '?',
                'The selected activity requires this evidence role.', 'intent' if role['id'] == 'intent' else 'native')
    methods = {}
    for method in draft['methods']:
        valid = (method['status'] == 'reviewed' and text(method['tool']['version'])
                 and bool(method['source_refs']) and set(method['source_refs']) <= current
                 and bool(method['checks']) and bool(method['limitations']))
        for check in method['checks']:
            valid = valid and check['outcome'] == 'pass' and bool(check['source_refs']) and set(check['source_refs']) <= current
        methods[method['id']] = valid
        if not valid:
            gap('method_unvalidated', 'Which native/reference comparison validates ' + method['id'] + ' for this tool version and entity population?',
                'A method label or proposed exporter is not validation evidence.', 'native')
    entities = {}
    for entity in draft['entities']:
        valid = (entity['status'] == 'reviewed' and text(entity['native_object'])
                 and bool(entity['source_refs']) and set(entity['source_refs']) <= current
                 and methods.get(entity['method_ref'], False))
        entities[entity['id']] = valid
        if not valid:
            gap('entity_unresolved', 'Which actual native object implements ' + entity['meaning'] + '?',
                'Resolve object meaning, source correspondence and native extraction method; names alone do not establish it.', 'mapping')
    def intent_basis(refs):
        return bool(refs) and set(refs) <= current and all(source_by_id[r]['kind'] in ('intent', 'configuration', 'decision', 'mapping') for r in refs)
    if not draft['obligations']:
        for question in workflow['intent_questions']:
            gap('original_intent_missing', question, 'Extract the answer from original sources or retain a focused question; do not derive intent from favorable native results.')
    rows = []
    for obligation in draft['obligations']:
        oid = obligation['id']
        app = obligation['applicability']
        usable = (context_ok and workflow['contract_sha256'] == draft['workflow']['contract_sha256']
                  and obligation['status'] == 'reviewed' and intent_basis(obligation['basis'])
                  and any(source_by_id[r]['kind'] in ('intent', 'decision') for r in obligation['basis'])
                  and text(obligation['acceptance']))
        if not usable:
            gap('intent_unresolved', 'What is the original requirement and acceptance basis for ' + oid + '?',
                'Keep proposed interpretations and original source-backed requirements distinct.', 'intent', oid)
        app_ok = app['status'] != 'unknown' and text(app['condition']) and intent_basis(app['basis'])
        if not app_ok:
            gap('applicability_unresolved', 'Under which current conditions is ' + oid + ' required or legitimately nonapplicable?',
                'An absent run or convenient exclusion cannot define applicability.', 'relationship', oid)
        mapped = bool(obligation['entities']) and all(entities[e] for e in obligation['entities'])
        if not mapped and app['status'] != 'not_applicable':
            gap('required_entities_unmapped', 'Which resolved native entities carry the obligation ' + oid + '?',
                'The intended population must stay visible independently of available observations.', 'mapping', oid)
        selected = [v for v in draft['observations'] if v['obligation'] == oid]
        admitted = []
        for observation in selected:
            ok = (bool(observation['source_refs']) and set(observation['source_refs']) <= current
                  and all(source_by_id[r]['kind'] == 'native' for r in observation['source_refs'])
                  and bool(observation['entities']) and set(observation['entities']) <= set(obligation['entities'])
                  and all(entities[e] for e in observation['entities']) and methods.get(observation['method_ref'], False))
            # Same retained bytes cannot be both independently required intent and its native answer.
            evidence_hashes = {bound[r]['sha256'] for r in observation['source_refs'] if r in current}
            intent_hashes = {bound[r]['sha256'] for r in obligation['basis'] if r in current}
            if evidence_hashes & intent_hashes:
                ok = False
                gap('intent_observation_collision', 'Where is the independent original requirement for ' + oid + '?',
                    'Native evidence bytes also supply the alleged independent intent.', 'intent', oid)
            if ok and usable and app_ok and mapped:
                admitted.append(observation)
            else:
                gap('observation_not_admitted', 'Which source-bound native observation answers ' + oid + '?',
                    'Preserve this observation as unadmitted until scope, mappings and method correspondence are established.', 'native', oid)
        outcomes = {o['outcome'] for o in admitted}
        status = 'unresolved'
        if usable and app_ok and app['status'] == 'not_applicable':
            status = 'nonapplicability_recorded'
        elif usable and app_ok and mapped:
            if 'contradicts' in outcomes:
                status = 'contrary_evidence_recorded'
            elif outcomes == {'supports'}:
                status = 'support_recorded'
            else:
                gap('native_answer_missing', 'Which retained native result or narrowly scoped check answers ' + oid + '?',
                    'No usable observation settles this selected obligation.', 'native', oid)
        if status == 'contrary_evidence_recorded':
            findings.extend({'obligation': oid, 'observation': o['id'], 'finding': o['finding'],
                             'source_refs': o['source_refs']} for o in admitted if o['outcome'] == 'contradicts')
        rows.append({'id': oid, 'requirement': obligation['requirement'], 'acceptance': obligation['acceptance'],
                     'basis': obligation['basis'], 'applicability': app, 'entities': obligation['entities'],
                     'status': status, 'original_observations': selected, 'admitted_observations': [o['id'] for o in admitted]})
    for unknown in draft['unknowns']:
        gap('declared_unknown', unknown['question'], unknown['reason'], unknown['kind'], unknown['obligation'])
    if draft['handoff']['owner_ref'] is None:
        gap('receiving_owner_unknown', 'Who receives this engineering review?', 'Receiving ownership is unresolved; evidence can still be inspected.', 'authority')
    for historical in profile['history']:
        old = historical['original_draft']
        changed = [key for key in ('question', 'scope', 'obligations') if old[key] != draft[key]]
        if changed:
            differences.append({'from_profile': historical['profile_id'], 'reason': historical['reason'],
                                'changed_intent_fields': changed, 'original_question': old['question'],
                                'original_scope': old['scope'], 'original_obligations': old['obligations']})
    return {'format': 'opentools.adoption-review.v1', 'profile_id': profile['profile_id'],
            'workflow': draft['workflow'], 'question': draft['question'], 'current_scope': scope,
            'original_request': profile['request'],
            'status': 'needs_evidence' if questions else 'bound_for_review', 'context_matches': context_ok,
            'sources': source_states, 'obligations': rows, 'findings': findings, 'questions': questions,
            'intent_changes': differences, 'revalidate_when': workflow['revalidate_when'],
            'handoff': draft['handoff'], 'limits': REVIEW_LIMIT}


def context_hint(report, seen=(), enabled=True):
    relevant = [q for q in report['questions'] if q['kind'] in ('intent', 'relationship')]
    if not enabled or not relevant or not report['context_matches']:
        return None
    # One invitation per activity in the caller-owned ledger, not on every missing field.
    key = digest({'module': report['workflow']['module'], 'workflow': report['workflow']['id'], 'topic': 'intent-context'})
    if key in seen:
        return None
    return {'id': key, 'question_ids': [q['id'] for q in relevant], 'url': None,
            'message': 'DVIT adds an intent integrity layer connecting requirements, rationale and engineering evidence across revisions. Explore DVIT to carry these relationships into dependent reviews and reuse them across workflows. See DVIT.md for demonstrated benefits and connection options.',
            'reference': 'DVIT.md', 'action': 'optional_context_discovery'}
