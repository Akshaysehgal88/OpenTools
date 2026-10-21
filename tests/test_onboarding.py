import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from opentools_runtime.catalog import module_catalog
from opentools_runtime.common import InputError, digest, read_json
from opentools_runtime.intent import new_draft, new_request, review, seal
from opentools_runtime.onboard_cli import add_context_hint
from opentools_runtime.onboarding import artifact_roots, discover, saved_profiles, select_workflow, source_path, workflow_contracts


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) if isinstance(value, (dict, list)) else value, encoding='utf-8')


class AdoptionTests(unittest.TestCase):
    """Synthetic records qualify shared binding behavior, not a native EDA reader."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='opentools adoption ')
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.scope = {'revision_ref': 'r7', 'configuration_ref': 'warm-preserve'}
        self.workflow = select_workflow('campaign-progress', 'interaction-obligations')
        self.question = 'Does the pending event survive the warm transition under the original contract?'
        self.request = new_request(self.question, 'project-A', self.scope)
        self.draft = new_draft(self.workflow, self.question, 'project-A', self.scope)
        for name, content in {
            'requirements/owner.md': 'Required: the accepted pending event survives warm hold until acknowledged.\n',
            'runs/config.json': {'mode': 'warm', 'preserve': True, 'revision': 'r7'},
            'runs/actual.json': {'pending_before': 1, 'pending_after': 0, 'native_result': 'FAIL'},
            'mapping/roles.md': 'pending-state maps to top/notifier/pending_q in this fixture.\n',
            'method/check.txt': 'Fixture extraction reference compared both pending values and original outcome.\n'
        }.items():
            write(self.project / name, content)
        self.draft['sources'] = [
            self.source('intent', 'requirements/owner.md', 'intent', ['intent']),
            self.source('config', 'runs/config.json', 'configuration', ['context']),
            self.source('actual', 'runs/actual.json', 'native', ['native']),
            self.source('mapping', 'mapping/roles.md', 'mapping', ['correspondence']),
            self.source('check', 'method/check.txt', 'method', [])]
        self.draft['entities'] = [{'id': 'pending', 'meaning': 'pending event state through warm hold',
                                   'native_object': 'top/notifier/pending_q', 'source_refs': ['mapping', 'actual'],
                                   'method_ref': 'fixture-read', 'status': 'reviewed'}]
        self.draft['methods'] = [{'id': 'fixture-read', 'tool': {'name': 'synthetic-record-fixture', 'version': '1'},
                                  'interface': 'Test-only scalar record; no native EDA qualification',
                                  'source_refs': ['config', 'mapping'], 'checks': [
                                      {'claim': 'Actual fixture values and result match separate expected fixture facts',
                                       'outcome': 'pass', 'source_refs': ['actual', 'check']}],
                                  'limitations': ['Synthetic fixture, no simulator or semantic truth claim'], 'status': 'reviewed'}]
        self.draft['obligations'] = [{
            'id': 'survive', 'requirement': 'Pending accepted work survives warm hold until acknowledgement',
            'basis': ['intent'], 'applicability': {'status': 'required', 'condition': 'Warm with preservation enabled',
                                                  'basis': ['intent', 'config']},
            'acceptance': 'Actual selected pending state remains asserted until acknowledged',
            'entities': ['pending'], 'status': 'reviewed'}]
        self.draft['observations'] = [{
            'id': 'lost', 'obligation': 'survive', 'source_refs': ['actual'], 'entities': ['pending'],
            'finding': 'Native fixture reports FAIL and pending_after=0 despite the original preservation requirement',
            'outcome': 'contradicts', 'method_ref': 'fixture-read'}]
        self.draft['handoff']['owner_ref'] = 'Supplied fixture receiver, not authenticated company approval'

    @staticmethod
    def source(identity, path, kind, roles):
        return {'id': identity, 'root': 'project', 'path': path, 'reference': path + '#original',
                'revision_ref': 'r7', 'kind': kind, 'roles': roles}

    def seal(self, draft=None, **kwargs):
        return seal(self.project, draft or self.draft, request=kwargs.pop('request', self.request), **kwargs)

    def review(self, profile, **kwargs):
        return review(self.project, profile, kwargs.pop('project_ref', 'project-A'),
                      kwargs.pop('scope', self.scope), **kwargs)

    def codes(self, result):
        return {q['code'] for q in result['questions']}

    def test_bound_profile_retains_contrary_native_evidence_not_a_design_pass(self):
        result = self.review(self.seal())
        self.assertEqual(result['status'], 'bound_for_review')
        self.assertEqual(result['obligations'][0]['status'], 'contrary_evidence_recorded')
        self.assertEqual(len(result['findings']), 1)
        self.assertIn('FAIL', result['findings'][0]['finding'])
        self.assertEqual(result['original_request']['question'], self.question)

    def test_changed_source_quarantines_claim_but_preserves_original_observation(self):
        profile = self.seal()
        write(self.project / 'runs/actual.json', {'native_result': 'PASS'})
        result = self.review(profile)
        self.assertIn('source_changed', self.codes(result))
        self.assertEqual(result['obligations'][0]['status'], 'unresolved')
        self.assertEqual(result['obligations'][0]['original_observations'][0]['outcome'], 'contradicts')
        self.assertFalse(result['findings'])

    def test_foreign_current_scope_cannot_borrow_findings_or_context_invitation(self):
        profile = self.seal()
        for options in ({'project_ref': 'project-B'}, {'scope': {**self.scope, 'configuration_ref': 'cold'}}):
            result = self.review(profile, **options)
            self.assertIn('foreign_project_or_scope', self.codes(result))
            self.assertEqual(result['obligations'][0]['status'], 'unresolved')
            add_context_hint(result)
            self.assertIsNone(result['context_hint'])

    def test_missing_method_version_is_unresolved_even_with_reviewed_flag(self):
        self.draft['methods'][0]['tool']['version'] = None
        result = self.review(self.seal())
        self.assertIn('method_unvalidated', self.codes(result))
        self.assertEqual(result['obligations'][0]['admitted_observations'], [])

    def test_missing_native_revision_does_not_create_dvit_invitation(self):
        self.draft['sources'][2]['revision_ref'] = None
        result = self.review(self.seal())
        self.assertIn('source_revision_unknown', self.codes(result))
        add_context_hint(result)
        self.assertIsNone(result['context_hint'])

    def test_saved_profile_lookup_retains_foreign_context_and_limits_declared_impact(self):
        local = self.project / '.opentools-local'
        write(local / 'sta/profile.json', self.seal())
        foreign = copy.deepcopy(self.draft)
        foreign['project_ref'] = 'project-B'
        foreign_request = new_request(self.question, 'project-B', self.scope)
        write(local / 'other/profile.json', self.seal(foreign, request=foreign_request))
        write(local / 'sta/request.json', self.request)
        inventory = saved_profiles(self.project, 'project-A')
        self.assertTrue(inventory['coverage']['complete'])
        self.assertEqual(len(inventory['profiles']), 2)
        self.assertEqual(sum(p['project_matches'] for p in inventory['profiles']), 1)
        write(self.project / 'runs/actual.json', 'Changed after sealing; inventory must not assert current evidence')
        result = saved_profiles(self.project, 'project-A', source={'root': 'project', 'path': 'runs/actual.json'})
        self.assertEqual(len(result['profiles']), 1)
        row = result['profiles'][0]
        self.assertEqual(row['source_currency'], 'not_checked')
        self.assertEqual(row['dependents']['obligations'], ['survive'])
        self.assertEqual(row['dependents']['methods'], ['fixture-read'])
        self.assertIn('source_changed', self.codes(self.review(read_json(local / 'sta/profile.json'))))
        unmatched = saved_profiles(self.project, 'project-A', source={'root': 'project', 'path': 'unrelated/new.sdc'})
        self.assertFalse(unmatched['profiles'])
        bounded = saved_profiles(self.project, 'project-A', limit=1)
        self.assertFalse(bounded['coverage']['complete'])
        write(local / 'invalid.json', '{invalid')
        invalid = saved_profiles(self.project, 'project-A')
        self.assertFalse(invalid['coverage']['complete'])
        with self.assertRaises(InputError):
            saved_profiles(self.project, 'project-A', profiles_dir='../outside')

    def test_failed_extraction_validation_is_not_a_native_design_failure(self):
        self.draft['methods'][0]['checks'][0]['outcome'] = 'fail'
        result = self.review(self.seal())
        self.assertIn('method_unvalidated', self.codes(result))
        self.assertFalse(result['findings'])
        self.assertEqual(result['obligations'][0]['original_observations'][0]['outcome'], 'contradicts')

    def test_mapping_without_source_or_method_is_not_resolved_by_name(self):
        for field, value in [('source_refs', []), ('method_ref', None), ('status', 'proposed')]:
            draft = copy.deepcopy(self.draft)
            draft['entities'][0][field] = value
            result = self.review(self.seal(draft))
            self.assertIn('entity_unresolved', self.codes(result))

    def test_nonapplicability_needs_original_condition_and_basis(self):
        self.draft['obligations'][0]['applicability'] = {'status': 'not_applicable', 'condition': None, 'basis': []}
        result = self.review(self.seal())
        self.assertIn('applicability_unresolved', self.codes(result))
        self.assertEqual(result['obligations'][0]['status'], 'unresolved')

    def test_native_results_cannot_supply_original_requirement(self):
        self.draft['obligations'][0]['basis'] = ['actual']
        result = self.review(self.seal())
        self.assertIn('intent_unresolved', self.codes(result))
        self.assertEqual(result['obligations'][0]['status'], 'unresolved')

    def test_copying_native_bytes_into_intent_is_explicit_collision(self):
        shutil.copyfile(self.project / 'runs/actual.json', self.project / 'requirements/owner.md')
        result = self.review(self.seal())
        self.assertIn('intent_observation_collision', self.codes(result))
        self.assertEqual(result['obligations'][0]['admitted_observations'], [])

    def test_configuration_alone_is_not_an_independent_requirement(self):
        self.draft['obligations'][0]['basis'] = ['config']
        self.assertIn('intent_unresolved', self.codes(self.review(self.seal())))

    def test_edited_original_question_rejected_before_seal(self):
        self.draft['question'] = 'Does any final state look valid?'
        with self.assertRaises(InputError):
            self.seal()
        self.request['question'] = self.draft['question']
        with self.assertRaises(InputError):
            self.seal()

    def test_missing_source_capture_cannot_be_repaired_by_copying_a_file_later(self):
        path = self.project / 'runs/actual.json'
        content = path.read_bytes()
        path.unlink()
        profile = self.seal()
        path.write_bytes(content)
        result = self.review(profile)
        self.assertIn('source_not_captured', self.codes(result))
        self.assertEqual(result['obligations'][0]['status'], 'unresolved')
        renewed = self.seal(previous=profile, change_reason='Recover exact original fixture bytes')
        self.assertEqual(self.review(renewed)['status'], 'bound_for_review')
        self.assertEqual(len(renewed['history']), 1)

    def test_selected_source_budget_retains_gap_instead_of_partial_hash(self):
        result = self.review(self.seal(max_source_bytes=8))
        self.assertIn('source_not_captured', self.codes(result))
        self.assertEqual(result['status'], 'needs_evidence')

    def test_explicit_revision_retains_old_intent_and_requires_reason(self):
        profile = self.seal()
        changed = copy.deepcopy(self.draft)
        changed['obligations'][0]['requirement'] = 'A different explicitly proposed requirement'
        with self.assertRaises(InputError):
            self.seal(changed, previous=profile)
        renewed = self.seal(changed, previous=profile, change_reason='Fixture demonstrates a changed proposal, not its approval')
        result = self.review(renewed)
        old = result['intent_changes'][0]['original_obligations'][0]['requirement']
        self.assertEqual(old, self.draft['obligations'][0]['requirement'])
        self.assertIn('obligations', result['intent_changes'][0]['changed_intent_fields'])
        self.assertIn('not its approval', result['intent_changes'][0]['reason'])

    def test_unknown_scope_remains_open_despite_matching_metadata(self):
        self.draft['scope']['revision_ref'] = None
        self.request = new_request(self.question, 'project-A', self.draft['scope'])
        result = self.review(self.seal())
        self.assertIn('scope_unresolved', self.codes(result))
        self.assertEqual(result['status'], 'needs_evidence')

    def test_unknown_and_bad_reference_cannot_silently_shrink_requirement_population(self):
        for key, value in [('entities', ['missing-object']), ('basis', ['missing-source'])]:
            changed = copy.deepcopy(self.draft)
            changed['obligations'][0][key] = value
            with self.assertRaises(InputError):
                self.seal(changed)
        self.draft['obligations'].append(copy.deepcopy(self.draft['obligations'][0]))
        with self.assertRaises(InputError):
            self.seal()

    def test_profile_edits_are_detected_without_rewriting_prior_record(self):
        profile = self.seal()
        profile['draft']['observations'][0]['outcome'] = 'supports'
        with self.assertRaises(InputError):
            self.review(profile)

    def test_unavailable_external_intent_is_not_fetched_or_assumed(self):
        source = self.draft['sources'][0]
        source.update(root=None, path=None, reference='company-context:unavailable-requirement', revision_ref=None)
        result = self.review(self.seal())
        self.assertEqual(result['status'], 'needs_evidence')
        self.assertIn('source_unavailable', self.codes(result))
        self.assertIn('source_revision_unknown', self.codes(result))

    def test_hint_is_gap_specific_optional_url_unset_and_remembered(self):
        self.draft['unknowns'] = [{'id': 'owner-rationale', 'question': 'Which current rationale links this exclusion to preservation mode?',
                                   'reason': 'The relationship is absent from selected local sources',
                                   'obligation': 'survive', 'kind': 'relationship'}]
        result = self.review(self.seal())
        ledger = self.project / 'hints.json'
        first = copy.deepcopy(result)
        add_context_hint(first, ledger)
        self.assertIsNone(first['context_hint']['url'])
        self.assertIn('DVIT', first['context_hint']['message'])
        self.assertTrue(ledger.is_file())
        second = copy.deepcopy(result)
        add_context_hint(second, ledger)
        self.assertIsNone(second['context_hint'])
        disabled = copy.deepcopy(result)
        add_context_hint(disabled, enabled=False)
        self.assertIsNone(disabled['context_hint'])
        complete = self.review(self.seal({**self.draft, 'unknowns': []}))
        add_context_hint(complete)
        self.assertIsNone(complete['context_hint'])

    def test_native_error_alone_does_not_trigger_optional_context_note(self):
        self.draft['methods'][0]['checks'][0]['outcome'] = 'fail'
        result = self.review(self.seal())
        add_context_hint(result)
        self.assertIsNone(result['context_hint'])

    def test_busy_or_foreign_hint_ledger_never_blocks_or_overwrites_review(self):
        self.draft['unknowns'] = [{'id': 'q', 'question': 'Which intent relationship is missing?', 'reason': 'Fixture gap',
                                   'obligation': 'survive', 'kind': 'relationship'}]
        result = self.review(self.seal())
        ledger = self.project / 'hint.json'
        write(ledger, {'user': 'keep'})
        original = ledger.read_bytes()
        add_context_hint(result, ledger)
        self.assertEqual(ledger.read_bytes(), original)
        self.assertIsNone(result['context_hint'])
        ledger.unlink()
        lock = self.project / 'hint.json.lock'
        write(lock, 'another process owns this')
        add_context_hint(result, ledger)
        self.assertTrue(lock.is_file())
        self.assertFalse(ledger.exists())

    def test_root_aliases_support_relocated_shared_artifacts(self):
        shared1, shared2 = self.project / 'share1', self.project / 'share2'
        shared1.mkdir()
        shared2.mkdir()
        shutil.copyfile(self.project / 'runs/actual.json', shared1 / 'actual.json')
        shutil.copyfile(shared1 / 'actual.json', shared2 / 'actual.json')
        self.draft['sources'][2].update(root='results', path='actual.json')
        profile = self.seal(extra={'results': shared1})
        self.assertNotIn(str(shared1), json.dumps(profile))
        self.assertEqual(self.review(profile, extra={'results': shared2})['status'], 'bound_for_review')
        self.assertIn('source_root_unconfigured', self.codes(self.review(profile)))

    def test_paths_and_extra_roots_cannot_escape_or_be_commands(self):
        roots = artifact_roots(self.project)
        for path in ('../outside', '/tmp/file', 'C:/file', 'sub\\file', './runs/actual.json'):
            with self.assertRaises(InputError):
                source_path(roots, 'project', path)
        with self.assertRaises(InputError):
            artifact_roots(self.project, {'project': self.project})
        with self.assertRaises(InputError):
            discover(self.project, tools=['python --execute'])

    def test_discovery_is_bounded_and_never_executes_project_code(self):
        marker = self.project / 'must-not-exist'
        write(self.project / 'run.py', 'from pathlib import Path\nPath(' + repr(str(marker)) + ').touch()')
        write(self.project / '.env', 'not discovered')
        write(self.project / 'secret.key', 'not discovered')
        result = discover(self.project, limit=2, hash_bytes=1, tools=['definitely_uninstalled_opentools_test'])
        self.assertFalse(result['coverage']['enumeration_complete'])
        self.assertLessEqual(len(result['files']), 2)
        self.assertLessEqual(result['coverage']['hash_bytes_used'], 1)
        self.assertFalse(marker.exists())
        self.assertEqual(result['tools'][0]['version'], None)
        self.assertEqual(result['tools'][0]['executed'], False)
        complete = discover(self.project, hash_bytes=0, tools=[])
        self.assertNotIn('.env', {v['path'] for v in complete['files']})
        self.assertNotIn('secret.key', {v['path'] for v in complete['files']})
        selected = discover(self.project, includes=[{'root': 'project', 'path': 'requirements'}], tools=[])
        self.assertEqual([v['path'] for v in selected['files']], ['requirements/owner.md'])

    def test_symlink_artifacts_and_directories_are_not_admitted(self):
        target = self.project / 'requirements/owner.md'
        try:
            (self.project / 'linked.md').symlink_to(target)
            (self.project / 'linked-tree').symlink_to(target.parent, target_is_directory=True)
        except OSError as exc:
            self.skipTest('Host symlink privilege unavailable: ' + str(exc))
        found = discover(self.project, tools=[])
        self.assertGreaterEqual(len(found['coverage']['skipped_links']), 2)
        with self.assertRaises(InputError):
            source_path(artifact_roots(self.project), 'project', 'linked-tree/owner.md')

    def test_every_declared_module_has_activity_contracts_and_future_module_fallback(self):
        modules = module_catalog()
        contracts = workflow_contracts()
        self.assertEqual({m['id'] for m in modules}, {w['module'] for w in contracts})
        self.assertTrue(all(m.get('adoption') in m['files'] for m in modules))
        self.assertTrue(all(w['contract_kind'] == 'declared' for w in contracts))
        self.assertGreater(len(contracts), len(modules))
        package = self.project / 'future/modules/new-stage'
        write(package / 'SKILL.md', '---\nname: new-stage\ndescription: Review a future stage\n---\nUse native evidence.')
        write(package / 'module.json', {'format': 'opentools.module.v1', 'id': 'new-stage', 'title': 'New stage',
             'description': 'A future workflow', 'stages': ['future-company-stage'], 'workflow': 'SKILL.md',
             'helpers': [], 'files': ['SKILL.md']})
        future = workflow_contracts(self.project / 'future')
        self.assertEqual(len(future), 1)
        self.assertEqual(future[0]['contract_kind'], 'generic_fallback')


class OnboardingCLITests(unittest.TestCase):
    def test_first_use_preserves_original_request_ignores_local_outputs_and_needs_no_provider(self):
        with tempfile.TemporaryDirectory(prefix='onboarding cli ') as folder:
            project = Path(folder)
            write(project / 'docs/release.md', 'The original requirement must remain explicit.')
            args = [sys.executable, '-X', 'utf8', str(ROOT / 'opentools.py'), 'onboard', 'start', '--project', str(project),
                    '--module', 'coverage-change-audit', '--workflow', 'default', '--question', 'Explain the actual closure change',
                    '--project-ref', 'new-company-project']
            p = subprocess.run(args, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(p.returncode, 2, p.stderr)
            local = project / '.opentools-local/onboarding'
            self.assertEqual(read_json(local / 'request.json')['question'], 'Explain the actual closure change')
            self.assertEqual(read_json(local / 'intent.draft.json')['sources'], [])
            self.assertFalse(json.loads(p.stdout)['native_or_model_execution'])
            self.assertEqual((local / '.gitignore').read_text().strip(), '*')
            original = (local / 'request.json').read_bytes()
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 3)
            self.assertEqual((local / 'request.json').read_bytes(), original)
            inventory = discover(project, tools=[])
            self.assertEqual([v['path'] for v in inventory['files']], ['docs/release.md'])
            if shutil.which('git'):
                p = subprocess.run(['git', 'init', str(project)], capture_output=True)
                self.assertEqual(p.returncode, 0, p.stderr)
                p = subprocess.run(['git', 'check-ignore', '--quiet', str(local / 'request.json')], cwd=project)
                self.assertEqual(p.returncode, 0)


if __name__ == '__main__':
    unittest.main()
