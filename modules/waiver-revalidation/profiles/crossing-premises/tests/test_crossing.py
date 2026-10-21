import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROFILE=Path(__file__).resolve().parents[1]
MODULE=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(PROFILE));sys.path.insert(0,str(PROFILE/'examples'));sys.path.insert(0,str(MODULE))
from crossing_capture import capture
from create_example import example,policy
from waiver_core import compare,digest


class CrossingTests(unittest.TestCase):
    def test_stable_and_ordered_controls_reuse_existing_waiver_comparison(self):
        baseline=example('stable')[2]
        for case in ('stable','ordered-reset'):
            report=compare(baseline,example(case)[2],policy())
            self.assertEqual(report['status'],'unchanged_within_scope')

    def test_live_update_invalidates_stability_premise_without_new_population(self):
        baseline=example('stable')[2];current=example('live-update')[2]
        evidence=current['crossing_premise_capture']
        self.assertFalse(evidence['stable_in_window']);self.assertTrue(evidence['source_ready_before_destination'])
        report=compare(baseline,current,policy())
        self.assertEqual(report['status'],'review_required')
        self.assertFalse(report['waivers'][0]['added'])

    def test_early_destination_activity_invalidates_readiness_not_data_stability(self):
        current=example('early-reset')[2];evidence=current['crossing_premise_capture']
        self.assertTrue(evidence['stable_in_window']);self.assertFalse(evidence['source_ready_before_destination'])
        self.assertEqual(evidence['reset_witnesses'][0]['seq'],1)

    def test_update_returning_to_original_value_still_has_witness(self):
        population,journal,_=example('live-update')
        journal['events'][6]['source_value']=3;journal['events'][7]['source_value']=3
        captured=capture(population,journal)['crossing_premise_capture']
        self.assertFalse(captured['stable_in_window'])
        self.assertEqual(len(captured['stability_witnesses']),2)

    def test_update_after_closed_window_does_not_invalidate_its_stability(self):
        population,journal,_=example('stable')
        event=copy.deepcopy(journal['events'][-1]);event.update(seq=8,time_tick=8,source_value=7)
        journal['events'].append(event)
        self.assertTrue(capture(population,journal)['crossing_premise_capture']['stable_in_window'])

    def test_partial_coverage_or_unknown_sample_remains_incomplete(self):
        for variant in ('coverage','value','readiness','window','prefix','suffix','sample'):
            population,journal,_=example('stable')
            if variant=='coverage':journal['inputs_complete']=False
            if variant=='value':journal['events'][5]['source_value']=None
            if variant=='readiness':journal['events'][4]['source_ready']=None
            if variant=='window':journal['events'][4]['window']=None
            if variant=='prefix':journal['events']=journal['events'][4:]
            if variant=='suffix':journal['events'].pop()
            if variant=='sample':
                for event in journal['events']:event['destination_sample']=False
            current=capture(population,journal)
            report=compare(example('stable')[2],current,policy())
            self.assertEqual(report['status'],'incomplete',variant)
            self.assertTrue(current['crossing_premise_capture']['gaps'])

    def test_unknown_window_boundary_does_not_invent_a_change_inside_window(self):
        population,journal,_=example('stable')
        journal['events'][5].update(window=None,source_value=7)
        journal['events'][6].update(window=False,source_value=7)
        journal['events'][7].update(window=False,source_value=7)
        evidence=capture(population,journal)['crossing_premise_capture']
        self.assertIsNone(evidence['stable_in_window'])
        self.assertFalse(evidence['stability_witnesses'])

    def test_known_false_premise_survives_incomplete_coverage(self):
        population,journal,_=example('live-update');journal['inputs_complete']=False
        current=capture(population,journal);report=compare(example('stable')[2],current,policy())
        self.assertEqual(report['status'],'incomplete');self.assertTrue(report['review_required'])
        self.assertFalse(current['crossing_premise_capture']['stable_in_window'])

    def test_foreign_stale_run_or_crossing_mapping_is_rejected(self):
        for variant in ('digest','scope','mode','run','mapping'):
            population,journal,_=example()
            if variant=='digest':journal['population_sha256']='0'*64
            if variant=='scope':journal['scope']='another-project'
            if variant=='mode':journal['configuration_ref']='scan'
            if variant=='run':journal['run_id']='another-run'
            if variant=='mapping':journal['crossing']['source_clock']='other-clock'
            with self.assertRaises(ValueError):capture(population,journal)

    def test_invalid_order_scalar_type_or_duplicate_source_premise(self):
        for variant in ('order','boolean','duplicate'):
            population,journal,_=example()
            if variant=='order':journal['events'].reverse()
            if variant=='boolean':journal['events'][4]['source_value']=True
            if variant=='duplicate':
                population['configuration']['crossing:cfg-exception:cfg-bus:stable_in_window']=True
                journal['population_sha256']=digest(population)
            with self.assertRaises(ValueError):capture(population,journal)

    def test_unmapped_waiver_or_endpoint_not_inferred_from_name(self):
        population,journal,_=example()
        journal['finding_id']='other'
        with self.assertRaises(ValueError):capture(population,journal)

    def test_original_structural_population_and_native_capture_are_preserved(self):
        population,journal,_=example()
        population['capture']={'profile':'existing-exporter','top':'cfg-top','population_basis':'native-finding-identity'}
        journal['population_sha256']=digest(population);original=copy.deepcopy(population)
        current=capture(population,journal)
        self.assertEqual(population,original)
        self.assertEqual(current['capture'],original['capture'])
        self.assertEqual(current['waivers'],original['waivers'])
        self.assertEqual(current['tool']['name'],'owned-synthetic-crossing-report')

    def test_destination_sample_without_known_activity_cannot_pass(self):
        population,journal,_=example();journal['events'][4]['destination_active']=False
        self.assertTrue(capture(population,journal)['crossing_premise_capture']['gaps'])

    def test_cli_refuses_overwrite_and_captures_false_premise(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);population,journal,_=example('live-update')
            for name,record in (('population',population),('journal',journal)):
                (folder/(name+'.json')).write_text(json.dumps(record),encoding='utf-8')
            command=[sys.executable,str(PROFILE/'crossing_capture.py'),str(folder/'population.json'),str(folder/'journal.json'),'--out']
            self.assertEqual(subprocess.run(command+[str(folder/'snapshot.json')],capture_output=True).returncode,1)
            self.assertEqual(subprocess.run(command+[str(folder/'population.json')],capture_output=True).returncode,3)

    @unittest.skipUnless(os.environ.get('OPENTOOLS_VERILATOR') and os.environ.get('OPENTOOLS_VERILATOR_ROOT'),'Native Linux simulation tools not configured')
    def test_native_configuration_update_and_reset_readiness(self):
        from run_native import run
        with tempfile.TemporaryDirectory() as temp:
            result=run(Path(temp)/'native',os.environ['OPENTOOLS_VERILATOR'],os.environ['OPENTOOLS_VERILATOR_ROOT'])
            self.assertEqual(len(result['cases']),4)
            self.assertEqual([r['stable_in_window'] for r in result['cases']],[True,False,True,True])
            self.assertEqual([r['source_ready_before_destination'] for r in result['cases']],[True,True,True,False])


if __name__=='__main__':unittest.main()
