import copy
import importlib.util
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
from access_core import digest, exit_code, read_json, review
from create_example import example, policy_for


def bind(spec, trace, policy):
    trace["spec_sha256"] = digest(spec)
    policy["spec_sha256"] = digest(spec)
    policy["trace_sha256"] = digest(trace)


class AccessTests(unittest.TestCase):
    def test_direct_mask_and_explicit_diagnostic_consumption(self):
        for case in ("direct-mask", "diagnostic-consume"):
            with self.subTest(case=case):
                self.assertEqual(exit_code(review(*example(case))), 0)

    def test_rmw_clears_unrelated_pending_cause(self):
        report = review(*example("rmw"))
        self.assertEqual(exit_code(report), 1)
        self.assertEqual(report["findings"], [{"kind": "unexpected_clear", "seq": 2, "mask": 2,
            "intent_ref": "create_example.py:policy_for:caller-requests-cause-0-or-diagnostic-consume"}])

    def test_disabled_low_lane_leaves_requested_ack_pending(self):
        report = review(*example("disabled-low-byte"))
        self.assertEqual([f["kind"] for f in report["findings"]], ["required_clear_not_observed"])

    def test_observation_read_destroys_diagnostic_evidence(self):
        kinds = [f["kind"] for f in review(*example("diagnostic-peek"))["findings"]]
        self.assertIn("destructive_observation", kinds)
        self.assertIn("unexpected_clear", kinds)

    def test_foreign_or_stale_binding_does_not_compare(self):
        for case in ("scope", "spec", "trace"):
            spec, trace, policy = example()
            if case == "scope": trace["scope"]["mode"] = "test"
            if case == "spec": trace["spec_sha256"] = "0" * 64
            if case == "trace": policy["trace_sha256"] = "0" * 64
            report = review(spec, trace, policy)
            self.assertEqual(exit_code(report), 2)
            self.assertFalse(report["observations"])

    def test_missing_evidence_remains_incomplete(self):
        for key in ("before", "after", "accepted", "error", "hardware_quiet", "reset_inactive", "write_data", "byte_enable", "bit_enable"):
            spec, trace, policy = example()
            trace["events"][0][key] = None
            bind(spec, trace, policy)
            self.assertEqual(exit_code(review(spec, trace, policy)), 2, key)

    def test_hardware_or_reset_activity_prevents_attribution(self):
        for key in ("hardware_quiet", "reset_inactive"):
            spec, trace, policy = example("rmw")
            trace["events"][-1][key] = False
            bind(spec, trace, policy)
            report = review(spec, trace, policy)
            self.assertEqual(exit_code(report), 2)
            self.assertFalse(report["findings"])

    def test_known_finding_survives_missing_read_sample(self):
        spec, trace, policy = example("diagnostic-peek")
        trace["events"][0]["read_data"] = None
        bind(spec, trace, policy)
        report = review(spec, trace, policy)
        self.assertEqual(exit_code(report), 1)
        self.assertTrue(report["gaps"])

    def test_unknown_effect_or_caller_intent_is_a_gap(self):
        for variant in ("effect", "intent", "policy", "register", "partial"):
            spec, trace, policy = example()
            if variant == "effect": spec["registers"][0]["fields"][0]["onwrite"] = "unsupported"
            if variant == "intent": policy["events"][0]["allowed_clear_mask"] = None
            if variant == "policy": policy["events"] = []
            if variant == "register": trace["events"][0]["register_ref"] = "absent"
            if variant == "partial": trace["inputs_complete"] = False
            bind(spec, trace, policy)
            self.assertEqual(exit_code(review(spec, trace, policy)), 2, variant)

    def test_byte_lane_mismatch_is_not_silently_normalized(self):
        spec, trace, policy = example()
        trace["events"][0]["bit_enable"] = 1
        bind(spec, trace, policy)
        self.assertIn("byte_lane_mapping_mismatch", [g["kind"] for g in review(spec, trace, policy)["gaps"]])

    def test_state_or_readback_contradictions_are_findings(self):
        for key in ("after", "read_data"):
            spec, trace, policy = example("rmw")
            trace["events"][0][key] = 0
            bind(spec, trace, policy)
            kinds = [f["kind"] for f in review(spec, trace, policy)["findings"]]
            self.assertIn("native_state_mismatch" if key == "after" else "read_value_mismatch", kinds)

    def test_required_order_and_population_are_checked(self):
        spec, trace, policy = example()
        policy["events"][0]["after_seq"] = [2]
        self.assertIn("required_order_absent", [f["kind"] for f in review(spec, trace, policy)["findings"]])
        policy["events"][0]["seq"] = 2
        self.assertEqual(exit_code(review(spec, trace, policy)), 2)

    def test_native_error_retained_with_incomplete_acceptance(self):
        spec, trace, policy = example()
        trace["events"][0]["error"] = True
        bind(spec, trace, policy)
        report = review(spec, trace, policy)
        self.assertEqual(exit_code(report), 1)
        self.assertEqual(report["findings"][0]["kind"], "native_access_error")
        self.assertTrue(report["gaps"])

    def test_partial_trace_does_not_prove_missing_predecessor(self):
        spec, trace, policy = example()
        trace["inputs_complete"] = False
        policy["events"][0]["after_seq"] = [0]
        bind(spec, trace, policy)
        report = review(spec, trace, policy)
        self.assertEqual(exit_code(report), 2)
        self.assertIn("required_order_unobserved", [g["kind"] for g in report["gaps"]])

    def test_read_write_only_and_write_read_only_are_not_ordinary_accesses(self):
        for kind, access in (("read", "w"), ("write", "r")):
            spec, trace, policy = example("rmw" if kind == "read" else "direct-mask")
            trace["events"] = trace["events"][:1]
            trace["events"][0]["after"] = 3
            spec["registers"][0]["fields"][0].update(sw=access, onread="none", onwrite="assign" if access == "w" else "none")
            policy = policy_for(spec, trace, "direct-mask")
            bind(spec, trace, policy)
            self.assertIn("no_accessible_selected_field", [f["kind"] for f in review(spec, trace, policy)["findings"]])

    def test_invalid_population_types_and_field_overlap(self):
        for variant in ("overlap", "boolean", "duplicate", "order", "width"):
            spec, trace, policy = example("rmw")
            if variant == "overlap": spec["registers"][0]["fields"].append(dict(spec["registers"][0]["fields"][0], name="other"))
            if variant == "boolean": trace["events"][0]["before"] = True
            if variant == "duplicate": policy["events"].append(copy.deepcopy(policy["events"][0]))
            if variant == "order": trace["events"].reverse()
            if variant == "width": spec["registers"][0]["access_width"] = 8
            bind(spec, trace, policy)
            with self.assertRaises(ValueError): review(spec, trace, policy)

    def test_reader_and_cli_preserve_inputs_and_reject_duplicate_json(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            records = example()
            for name, record in zip(("spec", "trace", "policy"), records):
                (folder / (name + ".json")).write_text(json.dumps(record), encoding="utf-8")
            command = [sys.executable, str(MODULE / "access_review.py"), "review"] + [str(folder / (n + ".json")) for n in ("spec", "trace", "policy")]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(command + ["--json-out", str(folder / "spec.json")], capture_output=True).returncode, 3)
            (folder / "duplicate.json").write_text('{"x":1,"x":2}', encoding="utf-8")
            with self.assertRaises(ValueError): read_json(folder / "duplicate.json")

    @unittest.skipUnless(importlib.util.find_spec("systemrdl"), "Optional SystemRDL SDK not installed")
    def test_effective_native_semantics_and_unsupported_field(self):
        from rdl_effects import capture
        record = capture([MODULE / "examples/effects.rdl"], ["effects.pending", "effects.diagnostic"], example()[0]["scope"], "unbuffered-effects-v1", True)
        self.assertEqual(record["registers"][0]["fields"][0]["onwrite"], "one_clear")
        self.assertEqual(record["registers"][1]["fields"][0]["onread"], "clear")
        self.assertEqual(record["registers"][1]["fields"][0]["reset"], 0)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "other.rdl"
            path.write_text('addrmap other {reg {field {sw=rw;hw=rw;woset;} f;} status_reg;};', encoding="utf-8")
            other = capture([path], ["other.status_reg"], record["scope"], "other")
            self.assertEqual(other["registers"][0]["fields"][0]["onwrite"], "unsupported")
        with self.assertRaises(ValueError): capture([MODULE / "examples/effects.rdl"], ["absent"], record["scope"], "other")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "external.rdl"
            path.write_text('addrmap other {external reg {field {sw=rw;hw=rw;} f;} extreg;};', encoding="utf-8")
            with self.assertRaises(ValueError): capture([path], ["other.extreg"], record["scope"], "other")

    @unittest.skipUnless(os.environ.get("OPENTOOLS_VERILATOR") and os.environ.get("OPENTOOLS_VERILATOR_ROOT"), "Native Linux simulation tools not configured")
    def test_generated_native_register_block_and_independent_state_model(self):
        from run_native import run
        with tempfile.TemporaryDirectory() as temp:
            result = run(Path(temp) / "native", os.environ["OPENTOOLS_VERILATOR"], os.environ["OPENTOOLS_VERILATOR_ROOT"])
            self.assertEqual(len(result["cases"]), 5)
            self.assertEqual(sum(row["events"] for row in result["cases"]), 6)


if __name__ == "__main__":
    unittest.main()
