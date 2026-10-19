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
from applicability_core import InputError, audit, canonical, exit_code, file_hash, markdown, read_json
from create_example import fact, records


class ApplicabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.snapshot, self.request, data = records()
        (self.root / "result.txt").write_bytes(data)

    def run_audit(self, rules=None):
        return audit(self.snapshot, self.request, rules, self.root)

    def matching(self):
        self.request["required_fields"]["configuration.ECC_EN"] = fact(0, "synthetic:request")

    def reuse(self):
        return {"format": "opentools.result-reuse.v1", "run_ref": "run:A", "claim_id": self.request["claim_id"],
                "exceptions": [{"field": "configuration.ECC_EN", "observed": 0, "requested": 1,
                                "rule_ref": "synthetic:approved-exception", "approved_by": "synthetic:reviewer",
                                "basis_ref": "synthetic:review-record", "reason": "Synthetic test only; not a real ECC equivalence"}]}

    def test_ecc_disabled_pass_not_applicable_to_enabled_request(self):
        report = self.run_audit()
        self.assertEqual(report["status"], "inapplicable")
        self.assertEqual(report["native_result"]["outcome"], "pass")
        self.assertEqual(exit_code(report), 1)
        self.assertEqual(report["unknowns"], [])

    def test_exact_match_is_scope_qualified(self):
        self.matching()
        report = self.run_audit()
        self.assertEqual(report["status"], "directly_applicable_within_scope")
        self.assertEqual(exit_code(report), 0)
        self.assertIn("runtime.trace_level", report["unselected_fields"])
        self.assertIn("no checker-sufficiency", report["limits"])

    def test_missing_firmware_provenance_stays_unknown(self):
        self.matching()
        self.snapshot["fields"]["runtime.inputs_ref"]["value"]["firmware"] = None
        report = self.run_audit()
        self.assertEqual(report["status"], "unresolved")
        self.assertEqual(exit_code(report), 2)

    def test_example_request_and_observed_inputs_are_independent(self):
        self.snapshot["fields"]["runtime.inputs_ref"]["value"]["firmware"] = None
        self.assertEqual(self.request["required_fields"]["runtime.inputs_ref"]["value"]["firmware"], "sha256:synthetic-fw-A")

    def test_missing_requested_value_or_evidence_not_equal(self):
        self.matching()
        for key in ("value", "evidence_ref"):
            with self.subTest(key=key):
                request = copy.deepcopy(self.request)
                request["required_fields"]["configuration.ECC_EN"][key] = None
                self.assertEqual(audit(self.snapshot, request, base_dir=self.root)["status"], "unresolved")

    def test_approved_rule_retained_and_bound(self):
        report = self.run_audit(self.reuse())
        self.assertEqual(report["status"], "applicable_with_reviewed_reuse")
        row = next(v for v in report["fields"] if v["field"] == "configuration.ECC_EN")
        self.assertEqual(row["reuse_rule"]["approved_by"], "synthetic:reviewer")
        self.assertIn("synthetic:review-record", markdown(report))

    def test_stale_unbound_duplicate_or_unapproved_rules_rejected(self):
        variants = []
        rule = self.reuse(); rule["run_ref"] = "another-run"; variants.append(rule)
        rule = self.reuse(); rule["claim_id"] = "another-claim"; variants.append(rule)
        rule = self.reuse(); rule["exceptions"][0]["observed"] = 2; variants.append(rule)
        rule = self.reuse(); rule["exceptions"][0]["approved_by"] = ""; variants.append(rule)
        rule = self.reuse(); rule["exceptions"] *= 2; variants.append(rule)
        for rules in variants:
            with self.subTest(rules=rules), self.assertRaises(InputError):
                self.run_audit(rules)

    def test_reuse_cannot_fill_missing_evidence_or_waive_result_integrity(self):
        self.snapshot["fields"]["configuration.ECC_EN"]["evidence_ref"] = None
        with self.assertRaises(InputError):
            self.run_audit(self.reuse())
        self.snapshot["fields"]["configuration.ECC_EN"]["evidence_ref"] = "synthetic:source"
        (self.root / "result.txt").write_text("COPIED PASS FROM ANOTHER RUN")
        report = self.run_audit(self.reuse())
        self.assertEqual(report["status"], "unresolved")
        self.assertEqual(report["result_integrity"]["status"], "changed")

    def test_unknowns_not_hidden_by_mismatch(self):
        self.snapshot["execution"]["dependency_capture_complete"] = False
        report = self.run_audit()
        self.assertEqual(report["status"], "inapplicable")
        self.assertTrue(report["unknowns"])
        self.assertTrue(report["mismatches"])

    def test_missing_truncated_unexecuted_result_never_passes(self):
        self.matching()
        variants = []
        for key, value in (("outcome", "not_run"), ("complete", False), ("producer_run_ref", "other"),
                           ("artifact", None), ("native_status", None)):
            record = copy.deepcopy(self.snapshot); record["result"][key] = value; variants.append(record)
        for state in ("failed", "not_run", "unknown"):
            record = copy.deepcopy(self.snapshot); record["execution"]["state"] = state; variants.append(record)
        for record in variants:
            with self.subTest(record=record):
                self.assertEqual(audit(record, self.request, base_dir=self.root)["status"], "unresolved")
        (self.root / "result.txt").write_bytes(b"SYNTHETIC")
        self.assertEqual(self.run_audit()["result_integrity"]["status"], "changed")
        (self.root / "result.txt").unlink()
        self.assertEqual(self.run_audit()["result_integrity"]["status"], "missing")

    def test_outcome_fail_preserved_any_observed_can_apply(self):
        self.matching()
        self.snapshot["result"]["outcome"] = "fail"
        self.snapshot["result"]["native_status"] = "ASSERTION FAILED"
        self.assertEqual(self.run_audit()["status"], "inapplicable")
        self.request["required_outcome"] = "any_observed"
        report = self.run_audit()
        self.assertEqual(report["status"], "directly_applicable_within_scope")
        self.assertEqual(report["native_result"]["outcome"], "fail")

    def test_undeclared_dependencies_command_executable_missing(self):
        self.matching()
        for key, value in (("dependency_capture_complete", None), ("dependency_evidence_ref", None),
                           ("command", None), ("executable_ref", None), ("evidence_ref", None)):
            record = copy.deepcopy(self.snapshot); record["execution"][key] = value
            with self.subTest(key=key):
                self.assertEqual(audit(record, self.request, base_dir=self.root)["status"], "unresolved")

    def test_current_checkout_not_substituted_for_original_inputs(self):
        self.matching()
        generated = self.root / "generated-untracked.hex"
        generated.write_text("old firmware")
        original = file_hash(generated)
        self.snapshot["fields"]["firmware.ref"] = fact(original, "synthetic:retained-input-manifest")
        generated.write_text("new firmware")
        self.request["required_fields"]["firmware.ref"] = fact(file_hash(generated), "synthetic:requested-image")
        report = self.run_audit()
        self.assertEqual(report["status"], "inapplicable")
        self.assertEqual(self.snapshot["fields"]["firmware.ref"]["value"], original)

    def test_types_not_python_coerced_and_array_order_retained(self):
        self.matching()
        for value in (False, "0", 0.0):
            self.request["required_fields"]["configuration.ECC_EN"]["value"] = value
            self.assertEqual(self.run_audit()["status"], "inapplicable")
        self.snapshot["fields"]["args"] = fact(["a", "b"])
        self.request["required_fields"]["args"] = fact(["b", "a"])
        self.assertTrue(any(row["status"] == "mismatch" for row in self.run_audit()["fields"] if row["field"] == "args"))

    def test_invalid_shapes_values_and_completeness(self):
        variants = []
        record = copy.deepcopy(self.snapshot); record["execution"]["dependency_capture_complete"] = 1; variants.append(record)
        record = copy.deepcopy(self.snapshot); record["result"]["complete"] = 1; variants.append(record)
        record = copy.deepcopy(self.snapshot); record["fields"]["x"] = fact(float("nan")); variants.append(record)
        record = copy.deepcopy(self.snapshot); record["format"] = "future"; variants.append(record)
        for record in variants:
            with self.subTest(record=record), self.assertRaises(InputError):
                audit(record, self.request, base_dir=self.root)
        self.request["required_fields"] = {}
        with self.assertRaises(InputError):
            self.run_audit()

    def test_duplicate_json_keys_rejected(self):
        path = self.root / "bad.json"
        path.write_text('{"required_outcome":"pass","required_outcome":"any_observed"}')
        with self.assertRaises(InputError):
            read_json(path)

    def test_html_escaping_and_no_mutation(self):
        before = canonical(self.snapshot)
        self.request["claim"] = "<script>claim</script> | test"
        rendered = markdown(self.run_audit())
        self.assertIn("&lt;script&gt;", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertEqual(before, canonical(self.snapshot))

    def test_cli_codes_and_no_overwrite(self):
        snapshot_path = self.root / "snapshot.json"
        request_path = self.root / "request.json"
        snapshot_path.write_text(json.dumps(self.snapshot))
        def run(*extra):
            request_path.write_text(json.dumps(self.request))
            return subprocess.run([sys.executable, str(MODULE / "applicability_check.py"), "compare", str(snapshot_path), str(request_path), *extra], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run().returncode, 1)
        self.matching()
        self.assertEqual(run().returncode, 0)
        self.snapshot["result"]["complete"] = False
        snapshot_path.write_text(json.dumps(self.snapshot))
        output = str(self.root / "audit.json")
        self.assertEqual(run("--json-out", output).returncode, 2)
        self.assertEqual(run("--json-out", output).returncode, 3)
        self.assertEqual(run("--json-out", str(request_path)).returncode, 3)


if __name__ == "__main__":
    unittest.main()
