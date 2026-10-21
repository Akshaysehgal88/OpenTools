import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(MODULE));sys.path.insert(0,str(MODULE/'examples'))
from progress_core import cycles,digest,exit_code,read_json,review
from create_example import CASES,example,save
from episode_model import INITIAL,config,explore,transition


def bind(model,journal,policy):
    journal['model_sha256']=digest(model);policy['model_sha256']=digest(model);policy['journal_sha256']=digest(journal)


def kinds(report,field='gaps'):return {item['kind'] for item in report[field]}


class ProgressTests(unittest.TestCase):
    def test_opposite_orders_have_reachable_conditional_blocking_for_both_profiles(self):
        for case in ('coherence-opposite','accelerator-opposite'):
            report=review(*example(case));self.assertEqual(exit_code(report),1)
            self.assertEqual(len(report['candidate_cycles']),1);self.assertEqual(report['blocking_witnesses'][0]['seq'],2)
            self.assertEqual(len(report['blocking_witnesses']),11);self.assertFalse(report['gaps'])

    def test_alternate_channel_release_order_and_common_order_complete(self):
        for case in ('coherence-escape','coherence-release-before-wait','accelerator-ordered'):
            report=review(*example(case));self.assertEqual(exit_code(report),0)
            self.assertFalse(report['candidate_cycles'] or report['blocking_witnesses'])

    def test_static_cycle_does_not_mean_observed_blocking(self):
        report=review(*example('coherence-serialized'))
        self.assertTrue(report['candidate_cycles']);self.assertFalse(report['blocking_witnesses'] or report['findings'])
        self.assertEqual(exit_code(report),1) # candidate review only

    def test_enabled_escape_left_unscheduled_is_not_closed_blocking(self):
        report=review(*example('coherence-starved-escape'))
        self.assertFalse(report['candidate_cycles'] or report['blocking_witnesses'])
        self.assertTrue(report['observations'][-1]['enabled_progress']['snoop-owner'])
        self.assertFalse(report['observations'][-1]['no_enabled_internal_progress'])
        self.assertEqual(kinds(report,'findings'),{'completion_not_seen_by_window_end'})
        self.assertFalse(report['fair_scheduling_premise'])

    def test_external_reclaim_prevents_closed_cycle_blocking(self):
        report=review(*example('coherence-external-reclaim'))
        self.assertTrue(report['candidate_cycles']);self.assertFalse(report['blocking_witnesses'])
        snapshot=report['observations'][2];self.assertTrue(snapshot['no_enabled_internal_progress']);self.assertTrue(snapshot['external_enabled'])
        self.assertFalse(report['findings'] or report['gaps'])

    def test_unknown_environment_cannot_qualify_a_flat_trace(self):
        report=review(*example('coherence-open-environment'))
        self.assertTrue(report['observations'][-1]['no_enabled_internal_progress']);self.assertFalse(report['blocking_witnesses'])
        self.assertIn('premise_unknown',kinds(report));self.assertIn('blocking_observation_unqualified',kinds(report))

    def test_independent_search_replays_every_blocking_witness_and_safe_controls(self):
        for cfg,expected_states in (((0,False),13),((1,False),14),((2,False),17),((3,False),12),((0,True),19)):
            result=explore(cfg);self.assertEqual(result['states'],expected_states)
            self.assertEqual(len(result['blocked']),1 if cfg==(0,False) else 0)
            for witness in result['blocked']:
                state=INITIAL
                for action in witness['actions']:state=transition(state,cfg,action)
                self.assertEqual(list(state),witness['state'])
            for state in result['reachable_states']:self.assertEqual(state[2]&state[3],0)
            self.assertTrue(result['completed'])

    def test_available_capacity_breaks_actual_wait_even_with_static_scc(self):
        model,journal,policy=example('coherence-opposite')
        for resource in model['resources']:resource['capacity']=2
        for sample in journal['samples']:
            for actor in sample['actors']:
                if actor['pending']:actor['advance_enabled']=True
        policy['require_completion_at_end']=False;bind(model,journal,policy);report=review(model,journal,policy)
        self.assertTrue(report['candidate_cycles']);self.assertFalse(report['blocking_witnesses']);self.assertFalse(report['gaps'])

    def test_occupancy_and_enabled_mismatch_cannot_certify_blocking(self):
        for variant in ('capacity','enabled'):
            model,journal,policy=example('coherence-opposite')
            if variant=='capacity':model['resources'][0]['capacity']=2
            else:journal['samples'][2]['actors'][0]['advance_enabled']=True
            bind(model,journal,policy);report=review(model,journal,policy)
            self.assertIn('advance_enable_mismatch',kinds(report,'findings'))
            self.assertFalse(any(w['seq']==2 for w in report['blocking_witnesses']))

    def test_impossible_double_ownership_is_not_a_blocking_witness(self):
        model,journal,policy=example('coherence-opposite')
        journal['samples'][2]['actors'][1]['held']['response-slot']=1
        bind(model,journal,policy);report=review(model,journal,policy)
        self.assertIn('occupancy_exceeds_capacity',kinds(report,'findings'));self.assertFalse(any(w['seq']==2 for w in report['blocking_witnesses']))

    def test_unknown_active_guard_or_retention_is_a_gap(self):
        for key in ('active','retains_until_acquire'):
            model,journal,policy=example('coherence-opposite');model['waits'][0][key]=None
            bind(model,journal,policy);report=review(model,journal,policy)
            self.assertFalse(report['blocking_witnesses']);self.assertIn('wait_premise_unknown',kinds(report))
            self.assertIn('observed_wait_not_in_active_contract',kinds(report))

    def test_false_guard_cannot_hide_an_observed_retained_wait(self):
        model,journal,policy=example('coherence-opposite');model['waits'][0]['active']=False
        bind(model,journal,policy);report=review(model,journal,policy)
        self.assertFalse(report['candidate_cycles']);self.assertIn('observed_wait_not_in_active_contract',kinds(report));self.assertFalse(report['blocking_witnesses'])

    def test_missing_release_paths_or_autonomous_timer_premise_prevents_qualification(self):
        for key in ('closed_resource_census','release_paths_complete','autonomous_updates_absent'):
            model,journal,policy=example('coherence-opposite');model['premises'][key]=False
            bind(model,journal,policy);report=review(model,journal,policy)
            self.assertFalse(report['blocking_witnesses']);self.assertIn('closed_model_premise_not_satisfied',kinds(report))

    def test_missing_actor_resource_or_wrong_unit_cannot_shrink_independent_roster(self):
        for variant in ('actor','resource','unit','role'):
            model,journal,policy=example('coherence-escape')
            if variant=='actor':model['actors'].pop()
            elif variant=='resource':model['resources'].pop()
            elif variant=='unit':model['resources'][0]['unit']='byte'
            else:model['actors'][0]['role_ref']='unrelated'
            bind(model,journal,policy);report=review(model,journal,policy)
            self.assertTrue({'required_definition_absent','required_definition_mismatch'}&kinds(report))
            self.assertFalse(report['blocking_witnesses'])

    def test_unknown_counts_flags_or_missing_observed_owner_prevent_snapshot_claim(self):
        for variant in ('count','flag','owner','capacity'):
            model,journal,policy=example('coherence-opposite')
            if variant=='count':journal['samples'][2]['actors'][0]['held']['response-slot']=None
            elif variant=='flag':journal['samples'][2]['actors'][0]['release_enabled']=None
            elif variant=='owner':journal['samples'][2]['actors'].pop()
            else:model['resources'][0]['capacity']=None
            bind(model,journal,policy);report=review(model,journal,policy)
            self.assertFalse(any(w['seq']==2 for w in report['blocking_witnesses']));self.assertTrue(report['gaps'])

    def test_missing_external_enable_observation_is_not_false(self):
        model,journal,policy=example('coherence-external-reclaim');journal['samples'][2]['external_enabled']={}
        bind(model,journal,policy);report=review(model,journal,policy)
        self.assertIn('external_enable_unknown',kinds(report));self.assertFalse(report['blocking_witnesses'])

    def test_foreign_class_mode_episode_or_stale_hash_cannot_supply_witness(self):
        for variant in ('traffic_class_ref','mode','episode_ref','hash','window'):
            model,journal,policy=example('coherence-opposite');journal=copy.deepcopy(journal)
            if variant in ('traffic_class_ref','mode','episode_ref'):journal['scope'][variant]='foreign'
            elif variant=='hash':journal['model_sha256']='0'*64
            else:policy['window_ref']='another-window'
            report=review(model,journal,policy);self.assertEqual(exit_code(report),2);self.assertFalse(report['observations'] or report['blocking_witnesses'])

    def test_missing_prefix_sample_or_unqualified_reachability_stays_visible(self):
        for variant in ('sample','prefix','basis','complete','open'):
            model,journal,policy=example('coherence-opposite')
            if variant=='sample':journal['samples'].pop(0)
            elif variant=='prefix':journal['reachable_prefix_confirmed']=None
            elif variant=='basis':journal['reachability_basis_ref']=None
            elif variant=='complete':journal['observations_complete']=False
            else:journal['window_closed']=False
            bind(model,journal,policy);report=review(model,journal,policy)
            self.assertFalse(report['blocking_witnesses']);self.assertTrue(report['gaps'])

    def test_known_deadline_finding_retains_other_gaps(self):
        model,journal,policy=example('coherence-starved-escape');journal['reachable_prefix_confirmed']=None
        bind(model,journal,policy);report=review(model,journal,policy)
        self.assertEqual(exit_code(report),1);self.assertTrue(report['gaps']);self.assertIn('completion_not_seen_by_window_end',kinds(report,'findings'))

    def test_self_wait_is_candidate_but_acyclic_graph_is_not(self):
        self.assertEqual(cycles({'one':{'one'}}),[['one']]);self.assertEqual(cycles({'one':{'two'},'two':set()}),[])

    def test_invalid_types_duplicate_identity_and_sequence_rejected(self):
        for variant in ('count','flag','duplicate','order','capacity'):
            model,journal,policy=example('coherence-escape')
            if variant=='count':journal['samples'][0]['actors'][0]['held']['response-slot']=-1
            elif variant=='flag':journal['samples'][0]['actors'][0]['pending']=1
            elif variant=='duplicate':model['resources'][1]['id']=model['resources'][0]['id']
            elif variant=='order':journal['samples'][-1]['seq']=0
            else:model['resources'][0]['capacity']=0
            bind(model,journal,policy)
            with self.assertRaises(ValueError):review(model,journal,policy)

    def test_cli_output_is_new_file_only_and_json_is_strict(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            for key,value in zip(('model','journal','policy'),example('coherence-escape')):save(folder/(key+'.json'),value)
            command=[sys.executable,str(MODULE/'progress_review.py')]+[str(folder/(key+'.json')) for key in ('model','journal','policy')]
            result=subprocess.run(command,capture_output=True,text=True);self.assertEqual(result.returncode,0);self.assertEqual(json.loads(result.stdout)['status'],'within_observed_contract')
            before=(folder/'model.json').read_bytes();refused=subprocess.run(command+['--output',str(folder/'model.json')],capture_output=True,text=True)
            self.assertEqual(refused.returncode,3);self.assertEqual((folder/'model.json').read_bytes(),before)
            for raw in ('{"x":0,"x":1}','{"x":NaN}'):
                (folder/'bad.json').write_text(raw,encoding='utf-8')
                with self.assertRaises(ValueError):read_json(folder/'bad.json')

    @unittest.skipUnless(os.environ.get('OPENTOOLS_VERILATOR') and os.environ.get('OPENTOOLS_VERILATOR_ROOT'),'Native tools not configured')
    def test_native_reachable_episode_and_exhaustive_oracle(self):
        from run_native import run
        with tempfile.TemporaryDirectory() as temporary:
            result=run(Path(temporary)/'proof',os.environ['OPENTOOLS_VERILATOR'],os.environ['OPENTOOLS_VERILATOR_ROOT'])
            self.assertEqual(sum(c['native_rows'] for c in result['cases']),117)
            self.assertEqual(sum(c['reachable_model_blocking_states']>0 for c in result['cases']),4)
            self.assertEqual(sum(bool(c['blocking_witness_samples']) for c in result['reviews']),2)


if __name__=='__main__':unittest.main()
