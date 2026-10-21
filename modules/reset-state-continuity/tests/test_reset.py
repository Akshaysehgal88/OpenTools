import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(MODULE / "examples"))
from reset_core import digest, exit_code, read_json, review
from create_example import example


def bind(inventory, journal, policy):
    journal["inventory_sha256"] = digest(inventory)
    policy["inventory_sha256"] = digest(inventory)
    policy["journal_sha256"] = digest(journal)


class ResetTests(unittest.TestCase):
    def test_partial_reset_exposes_surviving_pending_work_and_actual_orphan(self):
        result = review(*example())
        self.assertEqual(exit_code(result), 1)
        self.assertEqual([f["kind"] for f in result["findings"]], ["producer_survives_cleared_consumer", "unexpected_post_release_effect"])
        self.assertEqual(result["state_by_owner"][0]["released"], 1)

    def test_coordinated_reset_and_drain_are_valid_distinct_controls(self):
        for case in ("warm-reset-both", "warm-drain"):
            self.assertEqual(exit_code(review(*example(case))), 0)

    def test_retained_event_needs_explicit_replay_contract(self):
        self.assertEqual(exit_code(review(*example("watchdog-fresh-start"))), 1)
        valid = review(*example("watchdog-replay"))
        self.assertEqual(exit_code(valid), 0)
        self.assertEqual(valid["continuity"][0]["status"], "replay_permitted_by_supplied_policy")

    def test_state_clear_preservation_and_reset_scope_are_separate(self):
        for variant in ("clear", "preserve", "reset"):
            inventory, journal, policy = example("warm-drain")
            if variant == "clear": journal["phases"][1]["values"]["consumer_id"] = 5
            if variant == "preserve": journal["phases"][1]["values"]["producer_id"] = 0
            if variant == "reset": journal["phases"][1]["reset_active"]["consumer-reset"] = False
            bind(inventory, journal, policy)
            kinds = [f["kind"] for f in review(inventory, journal, policy)["findings"]]
            self.assertIn({"clear":"required_state_clear_missing","preserve":"required_state_preservation_missing","reset":"reset_application_mismatch"}[variant], kinds)

    def test_unknown_state_owner_sample_or_reset_cannot_pass(self):
        for variant in ("owner", "sample", "reset", "phase", "policy", "quiet", "replay"):
            inventory, journal, policy = example("warm-drain")
            if variant == "owner": inventory["states"][0]["owner_ref"] = None
            if variant == "sample": journal["phases"][2]["values"]["producer_pending"] = None
            if variant == "reset": journal["phases"][1]["reset_active"]["producer-reset"] = None
            if variant == "phase": journal["phases"].pop()
            if variant == "policy": policy["state_expectations"].pop()
            if variant == "quiet": journal["phases"][1]["hardware_quiet"] = False
            if variant == "replay": policy["continuity"][0]["allow_replay"] = None
            bind(inventory, journal, policy)
            self.assertEqual(exit_code(review(inventory, journal, policy)), 2, variant)

    def test_release_prerequisite_false_and_unknown_have_different_results(self):
        for value, code in ((False,1),(None,2)):
            inventory, journal, policy = example("watchdog-replay")
            journal["phases"][2]["prerequisites"]["replay_ready"] = value
            bind(inventory, journal, policy)
            self.assertEqual(exit_code(review(inventory, journal, policy)), code)

    def test_unknowns_do_not_hide_known_native_orphan(self):
        inventory, journal, policy = example()
        journal["phases"][2]["values"]["producer_pending"] = None
        bind(inventory, journal, policy)
        result = review(inventory, journal, policy)
        self.assertEqual(exit_code(result), 1)
        self.assertTrue(result["gaps"])
        self.assertIn("unexpected_post_release_effect", [f["kind"] for f in result["findings"]])

    def test_retained_context_identity_is_checked_when_both_owners_survive(self):
        inventory, journal, policy = example("warm-drain")
        journal["phases"][2]["values"].update(producer_pending=1,consumer_context=1,producer_id=5,consumer_id=4)
        bind(inventory, journal, policy)
        self.assertIn("retained_identity_mismatch", [f["kind"] for f in review(inventory, journal, policy)["findings"]])

    def test_stale_foreign_or_basis_mismatch_prevents_comparison(self):
        for variant in ("scope", "inventory", "journal", "basis"):
            inventory, journal, policy = example()
            if variant == "scope": journal["scope"]["reset_event_ref"] = "power-on"
            if variant == "inventory": journal["inventory_sha256"] = "0"*64
            if variant == "journal": policy["journal_sha256"] = "0"*64
            if variant == "basis": policy["basis_ref"] = "other"
            result = review(inventory, journal, policy)
            self.assertEqual(exit_code(result), 2)
            self.assertFalse(result["state_by_owner"])

    def test_partial_evidence_remains_visible_on_otherwise_valid_control(self):
        inventory, journal, policy = example("warm-drain")
        journal["inputs_complete"] = False
        bind(inventory, journal, policy)
        self.assertEqual(exit_code(review(inventory, journal, policy)), 2)

    def test_missing_continuity_release_or_post_intent_does_not_pass(self):
        for section in ("continuity", "release_requires", "post_expectations"):
            inventory, journal, policy = example("warm-drain")
            policy[section] = []
            self.assertEqual(exit_code(review(inventory, journal, policy)), 2)

    def test_invalid_population_or_value_types_are_rejected(self):
        for variant in ("duplicate", "boolean", "phase", "policy"):
            inventory, journal, policy = example()
            if variant == "duplicate": inventory["states"].append(copy.deepcopy(inventory["states"][0]))
            if variant == "boolean": journal["phases"][0]["values"]["producer_pending"] = True
            if variant == "phase": journal["phases"].reverse()
            if variant == "policy": policy["state_expectations"].append(copy.deepcopy(policy["state_expectations"][0]))
            bind(inventory, journal, policy)
            with self.assertRaises(ValueError): review(inventory, journal, policy)

    def test_cli_and_duplicate_json_do_not_overwrite_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for name, value in zip(("inventory", "journal", "policy"), example("warm-drain")):
                (folder / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")
            command = [sys.executable,str(MODULE / "reset_review.py"),"review"] + [str(folder / (n + ".json")) for n in ("inventory","journal","policy")]
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)
            self.assertEqual(subprocess.run(command+["--json-out",str(folder / "inventory.json")],capture_output=True).returncode,3)
            (folder / "duplicate.json").write_text('{"x":1,"x":2}',encoding="utf-8")
            with self.assertRaises(ValueError): read_json(folder / "duplicate.json")

    @unittest.skipUnless(os.environ.get("OPENTOOLS_VERILATOR") and os.environ.get("OPENTOOLS_VERILATOR_ROOT"), "Native Linux simulation tools not configured")
    def test_native_partial_coordinated_drain_and_event_replay_controls(self):
        from run_native import run
        with tempfile.TemporaryDirectory() as temp:
            result = run(Path(temp) / "native",os.environ["OPENTOOLS_VERILATOR"],os.environ["OPENTOOLS_VERILATOR_ROOT"])
            self.assertEqual([r["post_orphan"] for r in result["cases"]],[1,0,0,1,0])
            self.assertEqual([r["post_replay"] for r in result["cases"]],[0,0,0,0,1])


if __name__ == "__main__": unittest.main()
