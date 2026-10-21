import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE));sys.path.insert(0, str(MODULE / "examples"))
from event_core import digest, exit_code, read_json, review
from create_example import example


def bind(topology, journal, policy):
    journal["topology_sha256"] = digest(topology);policy["topology_sha256"] = digest(topology);policy["journal_sha256"] = digest(journal)


class EventTests(unittest.TestCase):
    def test_wake_capture_before_source_clear_is_a_real_order_obligation(self):
        report = review(*example("clear-before-wake"))
        self.assertEqual(exit_code(report), 1)
        self.assertIn({"kind": "required_stage_not_observed_in_window", "stage": "wake_retained"}, report["findings"])
        self.assertTrue(any(f["kind"] == "required_stage_order_not_observed" and f["after"] == "source_cleared" for f in report["findings"]))

    def test_retention_before_service_and_held_source_across_gating_are_controls(self):
        for case in ("retain-before-service", "held-irq-required"):
            self.assertEqual(exit_code(review(*example(case))), 0)

    def test_wake_is_not_interrupt_delivery(self):
        report = review(*example("pulse-irq-required"))
        states = {s["stage"]: s["state"] for s in report["stage_observations"]}
        self.assertEqual(states["wake_requested"], "observed")
        self.assertEqual(states["interrupt_delivered"], "not_observed_in_window")
        self.assertEqual(exit_code(report), 1)

    def test_wake_only_intent_does_not_require_an_unrequested_interrupt(self):
        report = review(*example("wake-only"))
        self.assertEqual(exit_code(report), 0)
        self.assertIn("not_observed_in_window", [s["state"] for s in report["stage_observations"]])

    def test_service_acknowledgement_is_not_source_clear(self):
        report = review(*example("service-without-source-clear"))
        states = {s["stage"]: s["state"] for s in report["stage_observations"]}
        self.assertEqual(states["serviced"], "observed")
        self.assertEqual(states["source_cleared"], "not_observed_in_window")
        self.assertEqual(report["findings"], [{"kind": "required_stage_not_observed_in_window", "stage": "source_cleared"}])

    def test_unestablished_isolation_or_prefix_never_passes(self):
        for variant in ("isolation", "prefix", "multiple"):
            topology, journal, policy = example("retain-before-service")
            if variant == "isolation": journal["event_isolated"] = False
            if variant == "prefix": journal["samples"][0]["wake_pending_state"] = True
            if variant == "multiple": journal["samples"][1]["stages"]["asserted"] = True
            bind(topology, journal, policy)
            self.assertEqual(exit_code(review(topology, journal, policy)), 2, variant)

    def test_partial_or_open_window_does_not_prove_a_missing_stage(self):
        for key in ("inputs_complete", "window_closed"):
            topology, journal, policy = example("pulse-irq-required")
            journal[key] = False;bind(topology, journal, policy)
            report = review(topology, journal, policy)
            self.assertEqual(exit_code(report), 2)
            self.assertFalse(report["findings"])

    def test_known_order_failure_survives_unknown_stage_sample(self):
        topology, journal, policy = example("clear-before-wake")
        journal["samples"][-1]["stages"]["wake_requested"] = None;bind(topology, journal, policy)
        report = review(topology, journal, policy)
        self.assertEqual(exit_code(report), 1);self.assertTrue(report["gaps"])
        self.assertTrue(any(f["kind"] == "required_stage_order_not_observed" for f in report["findings"]))

    def test_stage_availability_false_and_unknown_differ(self):
        for value, code in ((False, 1), (None, 2)):
            topology, journal, policy = example("retain-before-service")
            sample = next(s for s in journal["samples"] if s["stages"]["interrupt_delivered"])
            sample["controls"]["route_selected"] = value;bind(topology, journal, policy)
            self.assertEqual(exit_code(review(topology, journal, policy)), code)

    def test_missing_predecessor_observation_is_not_invented(self):
        topology, journal, policy = example("retain-before-service")
        next(s for s in journal["samples"] if s["stages"]["interrupt_retained"])["stages"]["interrupt_retained"] = None
        bind(topology, journal, policy);report = review(topology, journal, policy)
        self.assertEqual(exit_code(report), 2)
        self.assertTrue(any(g["kind"] == "stage_order_unresolved" for g in report["gaps"]))

    def test_event_stage_before_selected_assertion_is_a_finding(self):
        topology, journal, policy = example("retain-before-service")
        journal["samples"][1]["stages"]["interrupt_retained"] = True;bind(topology, journal, policy)
        self.assertIn("stage_precedes_selected_assertion", [f["kind"] for f in review(topology, journal, policy)["findings"]])

    def test_foreign_scope_stale_topology_or_wrong_window_prevents_review(self):
        for variant in ("scope", "topology", "journal", "window"):
            topology, journal, policy = example()
            if variant == "scope": journal["scope"]["event_ref"] = "another-event"
            if variant == "topology": journal["topology_sha256"] = "0" * 64
            if variant == "journal": policy["journal_sha256"] = "0" * 64
            if variant == "window": policy["window_ref"] = "later-window"
            report = review(topology, journal, policy)
            self.assertEqual(exit_code(report), 2);self.assertFalse(report["stage_observations"])

    def test_unreviewed_stage_order_or_availability_remains_a_gap(self):
        for key in ("orders", "stage_prerequisites"):
            topology, journal, policy = example("retain-before-service");policy[key] = []
            self.assertEqual(exit_code(review(topology, journal, policy)), 2)

    def test_invalid_order_types_and_duplicate_obligations(self):
        for variant in ("sequence", "boolean", "duplicate", "stages"):
            topology, journal, policy = example()
            if variant == "sequence": journal["samples"].reverse()
            if variant == "boolean": journal["samples"][0]["stages"]["asserted"] = 0
            if variant == "duplicate": policy["required_stages"].append(copy.deepcopy(policy["required_stages"][0]))
            if variant == "stages": journal["samples"][0]["stages"].pop("wake_requested")
            bind(topology, journal, policy)
            with self.assertRaises(ValueError): review(topology, journal, policy)

    def test_cli_refuses_input_overwrite_and_duplicate_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for name, record in zip(("topology", "journal", "policy"), example("retain-before-service")):
                (folder / (name + ".json")).write_text(json.dumps(record), encoding="utf-8")
            command = [sys.executable, str(MODULE / "event_review.py"), "review"] + [str(folder / (n + ".json")) for n in ("topology", "journal", "policy")]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(command + ["--json-out", str(folder / "journal.json")], capture_output=True).returncode, 3)
            (folder / "duplicate.json").write_text('{"x":1,"x":2}', encoding="utf-8")
            with self.assertRaises(ValueError): read_json(folder / "duplicate.json")

    @unittest.skipUnless(os.environ.get("OPENTOOLS_VERILATOR") and os.environ.get("OPENTOOLS_VERILATOR_ROOT"), "Native Linux simulation tools not configured")
    def test_native_routes_service_source_clear_and_independent_reference(self):
        from run_native import run
        with tempfile.TemporaryDirectory() as temporary:
            result = run(Path(temporary) / "native", os.environ["OPENTOOLS_VERILATOR"], os.environ["OPENTOOLS_VERILATOR_ROOT"])
            self.assertEqual(len(result["cases"]), 6)
            self.assertEqual([r["counts"]["wake_requests"] for r in result["cases"]], [0, 1, 1, 1, 1, 1])
            self.assertEqual([r["counts"]["deliveries"] for r in result["cases"]], [1, 1, 0, 1, 0, 1])


if __name__ == "__main__": unittest.main()
