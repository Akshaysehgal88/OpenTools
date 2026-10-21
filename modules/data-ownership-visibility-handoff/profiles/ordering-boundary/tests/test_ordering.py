import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROFILE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROFILE));sys.path.insert(0,str(PROFILE/'examples'))
from ordering_core import digest,exit_code,program_digest,read_json,review
from create_example import example,save
from reference_model import enumerate_outcomes,trace


def bind(contract,evidence,claim,program=True):
    evidence['contract_sha256']=digest(contract);claim['contract_sha256']=digest(contract)
    if program:
        if evidence['model_result'] is not None:evidence['model_result']['program_sha256']=program_digest(contract)
        for row in evidence['observations']:row['program_sha256']=program_digest(contract)
    claim['evidence_sha256']=digest(evidence)


def kinds(report,field='findings'):return {f['kind'] for f in report[field]}


class OrderingTests(unittest.TestCase):
    def test_ram_and_mmio_are_different_successor_domains(self):
        ram=review(*example('ram-ww'));io=review(*example('mmio-ww'))
        self.assertEqual(exit_code(ram),0);self.assertFalse(ram['model_permits_stale'])
        self.assertEqual(exit_code(io),1);self.assertTrue(io['model_permits_stale']);self.assertFalse(io['control_covers_boundary'])

    def test_domain_specific_and_full_controls_gate_actual_publication(self):
        for case in ('ram-ww','mmio-wo','mmio-full'):
            report=review(*example(case));self.assertEqual(exit_code(report),0);self.assertTrue(report['control_covers_boundary'])
            self.assertFalse(report['model_permits_stale'] or report['observed_stale_runs'])
            rows=trace(case,3);attempt=next(r for r in rows if r['command']==5)
            self.assertFalse(attempt['step_enabled']);self.assertFalse(attempt['publication_visible'])

    def test_wrong_predecessor_does_not_order_normal_payload_write(self):
        report=review(*example('mmio-wrong-predecessor'))
        self.assertFalse(report['control_covers_boundary']);self.assertTrue(report['model_permits_stale']);self.assertEqual(exit_code(report),1)

    def test_early_or_late_control_is_not_retroactive(self):
        for case in ('mmio-early-control','mmio-late-control'):
            report=review(*example(case));self.assertFalse(report['control_covers_boundary']);self.assertTrue(report['model_permits_stale'])

    def test_favorable_single_observation_does_not_forbid_unobserved_stale(self):
        report=review(*example('ram-selected-good'))
        self.assertFalse(report['observed_stale_runs']);self.assertEqual(len(report['observations']),1)
        self.assertTrue(report['model_permits_stale']);self.assertIn('selected_model_permits_stale',kinds(report))

    def test_actual_early_read_is_not_replaced_by_final_memory(self):
        rows=trace('mmio-ww',3);self.assertEqual(rows[-1]['payload_memory'],1);self.assertEqual(rows[-1]['rpayload'],0)
        report=review(*example('mmio-ww'));self.assertIn('observed_stale_owned_implementation',kinds(report))
        self.assertEqual(report['model_witness'],['publication-commit','observe','payload-commit'])

    def test_model_output_and_observation_kinds_are_kept_separate(self):
        contract,evidence,claim=example('mmio-wo');self.assertEqual(evidence['observations'][0]['kind'],'owned-reference-fixture')
        self.assertNotEqual(evidence['model_result']['kind'],evidence['observations'][0]['kind'])
        self.assertEqual(exit_code(review(contract,evidence,claim)),0)

    def test_ram_evidence_cannot_be_rebound_to_mmio_by_matching_values(self):
        contract,_,claim=example('mmio-wo');_,evidence,_=example('ram-ww')
        report=review(contract,evidence,claim);self.assertEqual(exit_code(report),2);self.assertFalse(report['observations'])

    def test_source_model_or_program_revision_mismatch_is_a_gap(self):
        for variant in ('model','program','observation'):
            contract,evidence,claim=example('mmio-wo')
            if variant=='model':evidence['model_result']['model_revision_ref']='old-source'
            elif variant=='program':evidence['model_result']['program_sha256']='0'*64
            else:evidence['observations'][0]['program_sha256']='0'*64
            bind(contract,evidence,claim,False);report=review(contract,evidence,claim)
            self.assertEqual(exit_code(report),2);self.assertTrue(report['gaps'])

    def test_isa_hardware_and_atomicity_claims_are_not_qualified_by_owned_pattern(self):
        for variant in ('isa','hardware','atomicity'):
            contract,evidence,claim=example('mmio-wo')
            claim['property' if variant=='atomicity' else 'strength']=variant
            report=review(contract,evidence,claim);self.assertEqual(exit_code(report),2)
            self.assertIn('atomicity_not_qualified' if variant=='atomicity' else 'claim_strength_not_qualified',kinds(report,'gaps'))

    def test_missing_model_result_is_not_replaced_by_clean_observations(self):
        contract,evidence,claim=example('mmio-wo');evidence['model_result']=None;bind(contract,evidence,claim)
        report=review(contract,evidence,claim);self.assertEqual(exit_code(report),2);self.assertIsNone(report['model_permits_stale'])

    def test_observed_counterexample_survives_missing_model_result(self):
        contract,evidence,claim=example('mmio-ww');evidence['model_result']=None;bind(contract,evidence,claim)
        report=review(contract,evidence,claim);self.assertEqual(exit_code(report),1);self.assertTrue(report['gaps'])
        self.assertIn('observed_stale_owned_implementation',kinds(report))

    def test_partial_good_model_result_cannot_prove_outcome_forbidden(self):
        contract,evidence,claim=example('ram-selected-good');analysis=evidence['model_result']
        analysis['complete']=False;analysis['witnesses']=analysis['witnesses'][:1];analysis['outcomes']=[{'flag':1,'payload':1}]
        bind(contract,evidence,claim);report=review(contract,evidence,claim)
        self.assertEqual(exit_code(report),2);self.assertIsNone(report['model_permits_stale']);self.assertNotIn('observation_outside_supplied_model',kinds(report))

    def test_partial_stale_witness_is_positive_evidence_but_not_exhaustive(self):
        contract,evidence,claim=example('ram-selected-good');analysis=evidence['model_result']
        analysis['complete']=False;analysis['witnesses']=[w for w in analysis['witnesses'] if w['flag']==1 and w['payload']==0];analysis['outcomes']=[{'flag':1,'payload':0}]
        bind(contract,evidence,claim);report=review(contract,evidence,claim)
        self.assertEqual(exit_code(report),1);self.assertTrue(report['gaps']);self.assertTrue(report['model_permits_stale'])
        self.assertNotIn('observation_outside_supplied_model',kinds(report))

    def test_complete_label_cannot_hide_a_missing_stale_schedule(self):
        contract,evidence,claim=example('ram-selected-good');analysis=evidence['model_result']
        analysis['witnesses']=[w for w in analysis['witnesses'] if not(w['flag']==1 and w['payload']==0)]
        analysis['outcomes']=[o for o in analysis['outcomes'] if not(o['flag']==1 and o['payload']==0)]
        bind(contract,evidence,claim);report=review(contract,evidence,claim)
        self.assertEqual(exit_code(report),2);self.assertIn('model_enumeration_coverage_incomplete',kinds(report,'gaps'));self.assertIsNone(report['model_permits_stale'])

    def test_illegal_order_or_wrong_witness_outcome_is_not_an_admitted_counterexample(self):
        for variant in ('order','outcome'):
            contract,evidence,claim=example('mmio-wo');analysis=evidence['model_result']
            if variant=='order':analysis['witnesses'].append({'order':['publication-commit','observe','payload-commit'],'flag':1,'payload':0,'evidence_ref':'invalid-assertion'})
            else:analysis['witnesses'][0]['payload']=0
            bind(contract,evidence,claim);report=review(contract,evidence,claim)
            self.assertEqual(exit_code(report),1);self.assertNotEqual(report['model_permits_stale'],True)
            self.assertIn('model_witness_conflicts_with_control' if variant=='order' else 'model_witness_outcome_mismatch',kinds(report))

    def test_expected_domains_paths_or_observer_contract_cannot_silently_change(self):
        for variant in ('domain','path','observer'):
            contract,evidence,claim=example('mmio-wo')
            if variant=='domain':claim['required_domains']['publication']='W'
            elif variant=='path':claim['required_attributes']['publication']['path_ref']='unrelated-ram-path'
            else:claim['observer_contract_ref']='speculative-observer'
            report=review(contract,evidence,claim);self.assertEqual(exit_code(report),2);self.assertTrue(report['gaps'])

    def test_unknown_masks_attributes_observer_and_read_remain_unknown(self):
        for variant in ('mask','attribute','observer','read','schedule'):
            contract,evidence,claim=example('mmio-wo')
            if variant=='mask':next(s for s in contract['program'] if s['kind']=='ordering_control')['successors']=None
            elif variant=='attribute':contract['attributes']['publication']['shareability_ref']=None
            elif variant=='observer':contract['observer_ordered']=None
            elif variant=='read':evidence['observations'][0]['payload']=None
            else:evidence['observations'][0]['all_steps_enabled']=None
            bind(contract,evidence,claim);report=review(contract,evidence,claim);self.assertEqual(exit_code(report),2,report);self.assertTrue(report['gaps'])

    def test_foreign_observation_method_does_not_become_hardware_proof(self):
        contract,evidence,claim=example('mmio-wo');evidence['observations'][0]['kind']='hardware-trace';bind(contract,evidence,claim)
        self.assertEqual(exit_code(review(contract,evidence,claim)),2)

    def test_valid_model_can_be_reviewed_without_native_observations(self):
        contract,evidence,claim=example('mmio-wo');evidence['observations']=[];bind(contract,evidence,claim)
        report=review(contract,evidence,claim);self.assertEqual(exit_code(report),0);self.assertFalse(report['observations'])

    def test_unknown_or_unsupported_model_cannot_gain_support_from_its_name(self):
        contract,evidence,claim=example('mmio-wo');contract['model_ref']=claim['model_ref']='RVWMO-unqualified';contract['model_kind']='isa'
        evidence['model_result']['model_ref']=contract['model_ref'];bind(contract,evidence,claim)
        report=review(contract,evidence,claim);self.assertEqual(exit_code(report),2);self.assertIn('model_profile_unqualified',kinds(report,'gaps'))

    def test_nonfinite_duplicate_boolean_integer_and_bad_mask_are_invalid(self):
        for variant in ('flag','mask','duplicate','complete'):
            contract,evidence,claim=example('mmio-wo')
            if variant=='flag':evidence['observations'][0]['flag']=True
            elif variant=='mask':next(s for s in contract['program'] if s['kind']=='ordering_control')['predecessors']=['X']
            elif variant=='duplicate':contract['program'][1]['id']=contract['program'][0]['id']
            else:evidence['model_result']['complete']=1
            bind(contract,evidence,claim)
            with self.assertRaises(ValueError):review(contract,evidence,claim)

    def test_cli_json_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            for key,value in zip(('contract','evidence','claim'),example('mmio-wo')):save(folder/(key+'.json'),value)
            command=[sys.executable,str(PROFILE/'ordering_review.py')]+[str(folder/(key+'.json')) for key in ('contract','evidence','claim')]
            result=subprocess.run(command,capture_output=True,text=True);self.assertEqual(result.returncode,0);self.assertEqual(json.loads(result.stdout)['status'],'within_selected_owned_model')
            before=(folder/'contract.json').read_bytes();refused=subprocess.run(command+['--output',str(folder/'contract.json')],capture_output=True,text=True)
            self.assertEqual(refused.returncode,3);self.assertEqual((folder/'contract.json').read_bytes(),before)
            for raw in ('{"x":1,"x":2}','{"x":NaN}'):
                (folder/'bad.json').write_text(raw,encoding='utf-8')
                with self.assertRaises(ValueError):read_json(folder/'bad.json')

    @unittest.skipUnless(os.environ.get('OPENTOOLS_VERILATOR') and os.environ.get('OPENTOOLS_VERILATOR_ROOT'),'Native tools not configured')
    def test_native_domains_schedules_and_captured_consumer_results(self):
        from run_native import run
        with tempfile.TemporaryDirectory() as temporary:
            result=run(Path(temporary)/'proof',os.environ['OPENTOOLS_VERILATOR'],os.environ['OPENTOOLS_VERILATOR_ROOT'])
            self.assertEqual(sum(c['runs'] for c in result['cases']),55);self.assertEqual(sum(c['native_rows'] for c in result['cases']),372)
            self.assertEqual(sum(c['observed_stale'] for c in result['cases']),6)
            self.assertTrue(result['cases'][-1]['model_allows_stale']);self.assertFalse(result['cases'][-1]['observed_stale'])


if __name__=='__main__':unittest.main()
