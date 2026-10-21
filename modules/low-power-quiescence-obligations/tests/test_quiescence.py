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
from quiescence_core import digest, exit_code, read_json, review
from create_example import example


def bind(inventory, journal, policy):
    journal["inventory_sha256"] = digest(inventory);policy["inventory_sha256"] = digest(inventory);policy["journal_sha256"] = digest(journal)


class QuiescenceTests(unittest.TestCase):
    def test_local_idle_does_not_drain_external_response_or_credit(self):
        for case in ("power-local-only", "clock-local-only"):
            report = review(*example(case))
            self.assertEqual(exit_code(report), 1)
            witness = next(f for f in report["findings"] if f["kind"] == "owner_not_quiescent_in_protected_interval" and f["milestone"] == "drain_ack")
            self.assertEqual(witness["owner"], "remote-work");self.assertEqual(witness["seq"], 3)

    def test_system_owner_drains_are_valid_for_power_and_clock_profiles(self):
        for case in ("power-system-drain", "clock-system-drain"):
            report = review(*example(case))
            self.assertEqual(exit_code(report), 0)
            self.assertEqual(len(report["milestones"]), 3 if case.startswith("power") else 2)

    def test_missing_isolation_is_a_prerequisite_failure_not_busy_owner(self):
        report = review(*example("power-no-isolation"))
        self.assertEqual(exit_code(report), 1)
        self.assertEqual({f["kind"] for f in report["findings"]}, {"milestone_prerequisite_not_met"})
        self.assertEqual({f["control"] for f in report["findings"]}, {"isolation_active"})

    def test_late_work_after_zero_at_ack_is_detected_throughout_interval(self):
        inventory, journal, policy = example("power-late-admission")
        ack = next(s for s in journal["samples"] if s["controls"]["drain_ack"])
        self.assertEqual(ack["seq"], 7);self.assertEqual(ack["counts"], {"local-work": 0, "remote-work": 0})
        witness = next(f for f in review(inventory, journal, policy)["findings"] if f["milestone"] == "drain_ack")
        self.assertEqual(witness["owner"], "local-work");self.assertEqual(witness["seq"], 8)

    def test_required_owner_roster_survives_omitted_observed_owner(self):
        inventory, journal, policy = example("power-local-only")
        inventory["owners"] = inventory["owners"][:1]
        for sample in journal["samples"]: sample["counts"].pop("remote-work")
        bind(inventory, journal, policy);report = review(inventory, journal, policy)
        self.assertEqual(exit_code(report), 2)
        self.assertIn({"kind": "required_owner_absent", "owner": "remote-work"}, report["gaps"])

    def test_units_and_counting_basis_are_not_silently_equated(self):
        for key in ("unit", "counting_basis_ref"):
            inventory, journal, policy = example("clock-system-drain")
            inventory["owners"][1][key] = "different"
            bind(inventory, journal, policy)
            report = review(inventory, journal, policy)
            self.assertEqual(exit_code(report), 2)
            self.assertIn("owner_count_basis_mismatch", [g["kind"] for g in report["gaps"]])

    def test_unknown_owner_count_in_protected_interval_is_a_gap(self):
        inventory, journal, policy = example("power-system-drain")
        journal["samples"][-1]["counts"]["remote-work"] = None
        bind(inventory, journal, policy)
        self.assertEqual(exit_code(review(inventory, journal, policy)), 2)

    def test_known_busy_owner_survives_partial_coverage(self):
        inventory, journal, policy = example("power-local-only");journal["inputs_complete"] = False
        bind(inventory, journal, policy);report = review(inventory, journal, policy)
        self.assertEqual(exit_code(report), 1);self.assertTrue(report["gaps"])
        self.assertTrue(any(f["owner"] == "remote-work" for f in report["findings"] if "owner" in f))

    def test_prerequisite_false_and_unknown_remain_distinct(self):
        for value, code in ((False, 1), (None, 2)):
            inventory, journal, policy = example("power-system-drain")
            journal["samples"][-1]["controls"]["isolation_active"] = value
            bind(inventory, journal, policy)
            self.assertEqual(exit_code(review(inventory, journal, policy)), code)

    def test_missing_required_milestone_only_reviewed_in_closed_complete_window(self):
        for closed, code in ((True, 1), (False, 2)):
            inventory, journal, policy = example("power-system-drain")
            journal["samples"] = journal["samples"][:5];journal["window_closed"] = closed
            bind(inventory, journal, policy)
            self.assertEqual(exit_code(review(inventory, journal, policy)), code)

    def test_unknown_milestone_state_is_not_a_confirmed_cut(self):
        inventory, journal, policy = example("clock-system-drain")
        journal["samples"][-1]["controls"]["clock_available"] = None
        bind(inventory, journal, policy)
        self.assertEqual(exit_code(review(inventory, journal, policy)), 2)

    def test_abort_or_reentry_requires_broader_transition_scope(self):
        inventory, journal, policy = example("clock-system-drain")
        journal["samples"][-1]["controls"]["clock_available"] = True
        bind(inventory, journal, policy);report = review(inventory, journal, policy)
        self.assertEqual(exit_code(report), 2)
        self.assertIn("transition_reentry_unreviewed", [g["kind"] for g in report["gaps"]])

    def test_unreviewed_owner_in_inventory_or_unused_required_owner_cannot_pass(self):
        for variant in ("unreviewed", "unused"):
            inventory, journal, policy = example("clock-system-drain")
            if variant == "unreviewed":
                policy["required_owners"] = policy["required_owners"][:1]
            for check in policy["checks"]: check["owners"] = ["local-work"]
            self.assertEqual(exit_code(review(inventory, journal, policy)), 2)

    def test_foreign_scope_stale_bindings_or_wrong_window_prevent_comparison(self):
        for variant in ("scope", "inventory", "journal", "window"):
            inventory, journal, policy = example()
            if variant == "scope": journal["scope"]["mode"] = "scan"
            if variant == "inventory": journal["inventory_sha256"] = "0" * 64
            if variant == "journal": policy["journal_sha256"] = "0" * 64
            if variant == "window": policy["window_ref"] = "later-window"
            report = review(inventory, journal, policy)
            self.assertEqual(exit_code(report), 2);self.assertFalse(report["milestones"])

    def test_isolation_unknown_scope_and_missing_prefix_never_pass(self):
        for variant in ("isolation", "prefix"):
            inventory, journal, policy = example("clock-system-drain")
            if variant == "isolation": journal["transition_isolated"] = None
            if variant == "prefix": journal["samples"][0]["controls"]["transition_requested"] = True
            bind(inventory, journal, policy)
            self.assertEqual(exit_code(review(inventory, journal, policy)), 2)

    def test_invalid_count_types_sequence_and_duplicate_policy_are_rejected(self):
        for variant in ("boolean", "negative", "sequence", "duplicate", "equals"):
            inventory, journal, policy = example()
            if variant == "boolean": journal["samples"][0]["counts"]["local-work"] = False
            if variant == "negative": journal["samples"][0]["counts"]["local-work"] = -1
            if variant == "sequence": journal["samples"].reverse()
            if variant == "duplicate": policy["checks"].append(copy.deepcopy(policy["checks"][0]))
            if variant == "equals": policy["checks"][0]["predicates"][0]["equals"] = 1
            bind(inventory, journal, policy)
            with self.assertRaises(ValueError): review(inventory, journal, policy)

    def test_cli_refuses_overwrite_and_duplicate_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for name, record in zip(("inventory", "journal", "policy"), example("power-system-drain")):
                (folder / (name + ".json")).write_text(json.dumps(record), encoding="utf-8")
            command = [sys.executable, str(MODULE / "quiescence_review.py"), "review"] + [str(folder / (n + ".json")) for n in ("inventory", "journal", "policy")]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(command + ["--json-out", str(folder / "journal.json")], capture_output=True).returncode, 3)
            (folder / "duplicate.json").write_text('{"x":1,"x":2}', encoding="utf-8")
            with self.assertRaises(ValueError): read_json(folder / "duplicate.json")

    @unittest.skipUnless(os.environ.get("OPENTOOLS_VERILATOR") and os.environ.get("OPENTOOLS_VERILATOR_ROOT"), "Native Linux simulation tools not configured")
    def test_native_owner_handoff_drain_isolation_and_late_admission(self):
        from run_native import run
        with tempfile.TemporaryDirectory() as temporary:
            result = run(Path(temporary) / "native", os.environ["OPENTOOLS_VERILATOR"], os.environ["OPENTOOLS_VERILATOR_ROOT"])
            self.assertEqual([r["returned"] for r in result["cases"]], [0, 1, 0, 1, 1, 1])
            self.assertEqual([r["accepted"] for r in result["cases"]], [1, 1, 1, 1, 1, 2])


if __name__ == "__main__": unittest.main()
