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
from clock_core import analyze, closure, digest, exit_code, read_json
from create_example import CASES, example


def bind(model, request):
    request["model_sha256"] = digest(model)


class ClockTests(unittest.TestCase):
    def test_boot_and_wake_circular_prerequisites(self):
        for case in ("boot-cycle", "wake-cycle"):
            result = analyze(*example(case))
            self.assertEqual(exit_code(result), 1)
            self.assertEqual(result["candidate_cycles"][0]["facts"], ["gate_enabled", "worker_ready"])
            self.assertEqual(result["goals"][0]["state"], "unreachable_in_declared_model")

    def test_fixed_controls_are_derivable_not_a_temporal_proof(self):
        for case in ("boot-fixed", "wake-fixed"):
            result = analyze(*example(case))
            self.assertEqual(exit_code(result), 0)
            self.assertFalse(result["candidate_cycles"])
            self.assertIn("transition_done", result["derivable_facts"])

    def test_missing_restore_is_not_misclassified_as_a_cycle(self):
        result = analyze(*example("wake-no-restore"))
        self.assertEqual(exit_code(result), 1)
        self.assertFalse(result["candidate_cycles"])
        self.assertIn("restore_ready", result["unprovided_prerequisites"])

    def test_clock_lineage_adds_root_and_gate_prerequisites(self):
        model, request = example("boot-fixed")
        result = analyze(model, request)
        rule = next(r for r in result["expanded_rules"] if r["id"] == "worker-ack")
        self.assertIn("gate_enabled", rule["requires"])
        self.assertIn("root_available", rule["requires"])
        model["facts"][0]["initial"] = False
        bind(model, request)
        self.assertEqual(exit_code(analyze(model, request)), 1)

    def test_alternative_seed_breaks_candidate_cycle(self):
        model, request = example()
        model["rules"].append({"id": "independent-wake", "produces": "gate_enabled", "requires": ["request"], "clock_ref": "root", "evidence_ref": "native:wake-bypass"})
        bind(model, request)
        result = analyze(model, request)
        self.assertEqual(exit_code(result), 0)
        self.assertFalse(result["candidate_cycles"])

    def test_unknown_seed_or_partial_model_cannot_prove_blocking(self):
        for variant in ("seed", "model", "request"):
            model, request = example()
            if variant == "seed": next(f for f in model["facts"] if f["id"] == "gate_enabled")["initial"] = None
            if variant == "model": model["inputs_complete"] = False
            if variant == "request": request["inputs_complete"] = False
            bind(model, request)
            result = analyze(model, request)
            self.assertEqual(exit_code(result), 2)
            self.assertFalse(result["findings"])

    def test_foreign_scope_stale_binding_and_semantic_basis(self):
        for variant in ("scope", "digest", "basis"):
            model, request = example()
            if variant == "scope": request["scope"]["mode"] = "scan"
            if variant == "digest": request["model_sha256"] = "0" * 64
            if variant == "basis": request["basis_ref"] = "different"
            result = analyze(model, request)
            self.assertEqual(exit_code(result), 2)
            self.assertFalse(result["goals"])

    def test_missing_owner_fact_or_lineage_remains_a_gap(self):
        for variant in ("owner", "fact", "parent", "cycle", "goal"):
            model, request = example()
            if variant == "owner": model["facts"][0]["owner_ref"] = None
            if variant == "fact": model["rules"][0]["requires"].append("unexported")
            if variant == "parent": model["clocks"][1]["parent_ref"] = "unexported"
            if variant == "cycle": model["clocks"][0]["parent_ref"] = "worker-clock"
            if variant == "goal": request["goals"][0]["fact_ref"] = "unexported"
            bind(model, request)
            self.assertEqual(exit_code(analyze(model, request)), 2, variant)

    def test_known_blocked_goal_retains_other_unknown_goal(self):
        model, request = example()
        model["facts"].append({"id": "other", "initial": None, "owner_ref": "other", "evidence_ref": "other"})
        request["goals"].append({"fact_ref": "other", "evidence_ref": "other-goal"})
        bind(model, request)
        result = analyze(model, request)
        self.assertEqual(exit_code(result), 1)
        self.assertTrue(result["gaps"])

    def test_initial_true_cycle_is_not_a_blocking_witness(self):
        model, request = example()
        next(f for f in model["facts"] if f["id"] == "worker_ready")["initial"] = True
        bind(model, request)
        self.assertEqual(exit_code(analyze(model, request)), 0)

    def test_conjunction_and_alternative_rules_are_not_interchanged(self):
        self.assertEqual(closure({"a"}, [{"requires": ["a", "b"], "produces": "c"}]), {"a"})
        self.assertEqual(closure({"a"}, [{"requires": ["a"], "produces": "c"}, {"requires": ["b"], "produces": "c"}]), {"a", "c"})

    def test_invalid_duplicate_identity_or_semantic_profile(self):
        for variant in ("fact", "rule", "initial", "semantics"):
            model, request = example()
            if variant == "fact": model["facts"].append(copy.deepcopy(model["facts"][0]))
            if variant == "rule": model["rules"].append(copy.deepcopy(model["rules"][0]))
            if variant == "initial": model["facts"][0]["initial"] = 1
            if variant == "semantics": model["semantics"] = "temporal-arbitrary"
            bind(model, request)
            with self.assertRaises(ValueError): analyze(model, request)

    def test_cli_and_duplicate_json_do_not_overwrite_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            model, request = example("boot-fixed")
            for name, value in (("model", model), ("request", request)):
                (folder / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")
            command = [sys.executable, str(MODULE / "clock_review.py"), "analyze", str(folder / "model.json"), str(folder / "request.json")]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(command + ["--json-out", str(folder / "model.json")], capture_output=True).returncode, 3)
            (folder / "duplicate.json").write_text('{"x":1,"x":2}', encoding="utf-8")
            with self.assertRaises(ValueError): read_json(folder / "duplicate.json")

    @unittest.skipUnless(os.environ.get("OPENTOOLS_VERILATOR") and os.environ.get("OPENTOOLS_VERILATOR_ROOT"), "Native Linux simulation tools not configured")
    def test_native_boot_wake_and_restore_controls(self):
        from run_native import run
        with tempfile.TemporaryDirectory() as temp:
            result = run(Path(temp) / "native", os.environ["OPENTOOLS_VERILATOR"], os.environ["OPENTOOLS_VERILATOR_ROOT"])
            self.assertEqual([r["observed_completion"] for r in result["cases"]], [False, True, False, True, False])


if __name__ == "__main__":
    unittest.main()
