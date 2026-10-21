import copy
import importlib.metadata
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
from contract_core import digest, exit_code, read_json, review
from create_example import contract, record


class ContractTests(unittest.TestCase):
    def check(self, current=None, policy=None, baseline=None):
        current = current or record()
        return review(current, policy or contract(current, baseline), baseline)

    def test_unchanged_and_reduced_capacity(self):
        old, new = record(), record(8, 4)
        result = self.check(new, contract(new, old), old)
        self.assertEqual(exit_code(result), 1)
        self.assertEqual(result["checks"][0]["status"], "exceeds_capacity")
        self.assertEqual(result["changes"], [{"id": "available", "before": 8, "after": 4, "delta": -4, "unit": "transactions"}])
        self.assertEqual(exit_code(self.check()), 0)

    def test_demand_reduction_is_a_valid_changed_control(self):
        self.assertEqual(exit_code(self.check(record(4, 4))), 0)

    def test_queue_and_tag_profiles_use_the_same_activity(self):
        for profile in ("queue", "tag"):
            with self.subTest(profile=profile):
                self.assertEqual(exit_code(self.check(record(8, 4, profile))), 1)
                self.assertEqual(exit_code(self.check(record(4, 4, profile))), 0)

    def test_small_bounds_agree_with_independent_allocation(self):
        for available in range(9):
            for demand in range(10):
                free = list(range(available))
                missed = []
                for transaction in range(demand):
                    if free:
                        free.pop()
                    else:
                        missed.append(transaction)
                result = self.check(record(demand, available))
                self.assertEqual(exit_code(result), int(bool(missed)), (demand, available))

    def test_missing_value_and_meaning_do_not_become_zero_or_pass(self):
        for field in ("value", "unit", "basis_ref", "value_ref", "meaning_ref"):
            current = record()
            current["facts"][0][field] = None
            self.assertEqual(exit_code(self.check(current)), 2, field)

    def test_boolean_float_negative_and_duplicate_facts_rejected(self):
        for value in (True, 1.5, -1, "8"):
            current = record()
            current["facts"][0]["value"] = value
            with self.assertRaises(ValueError):
                self.check(current)
        current = record()
        current["facts"].append(copy.deepcopy(current["facts"][0]))
        with self.assertRaises(ValueError):
            self.check(current)

    def test_incomparable_unit_or_counting_basis_blocks_numeric_verdict(self):
        for field, value in (("unit", "bytes"), ("basis_ref", "per-bank")):
            current = record(8, 4)
            current["facts"][1][field] = value
            result = self.check(current)
            self.assertEqual(exit_code(result), 2)
            self.assertEqual(result["checks"][0]["status"], "needs_evidence")

    def test_wrong_and_missing_record_binding_never_compare(self):
        for binding in (None, "0" * 64):
            current = record(8, 4)
            policy = contract(current)
            policy["record_sha256"] = binding
            result = self.check(current, policy)
            self.assertEqual(exit_code(result), 2)
            self.assertFalse(result["findings"])

    def test_foreign_configuration_project_interface_or_mode(self):
        for field in ("project_ref", "interface_ref", "configuration_ref", "mode_ref"):
            current = record(8, 4)
            policy = contract(current)
            policy["scope"][field] = "foreign"
            self.assertEqual(exit_code(self.check(current, policy)), 2)

    def test_missing_scope_revision_or_population_stays_incomplete(self):
        current = record()
        current["scope"]["mode_ref"] = None
        policy = contract(record())
        policy["record_sha256"] = digest(current)
        self.assertEqual(exit_code(self.check(current, policy)), 2)
        for field in ("revision_ref", "inputs_complete"):
            current = record()
            current[field] = None
            self.assertEqual(exit_code(self.check(current)), 2)
        current = record()
        policy = contract(current)
        policy["population_complete"] = False
        self.assertEqual(exit_code(self.check(current, policy)), 2)

    def test_false_premise_is_review_and_unknown_premise_is_not_satisfied(self):
        for holds, expected in ((False, 1), (None, 2)):
            current = record()
            policy = contract(current)
            policy["checks"][0]["premises"][0]["holds"] = holds
            self.assertEqual(exit_code(self.check(current, policy)), expected)
        policy["checks"][0]["premises"][0].update(holds=False, evidence_ref=None)
        self.assertEqual(exit_code(self.check(current, policy)), 2)

    def test_known_findings_survive_other_unknown_evidence(self):
        current = record(8, 4)
        policy = contract(current)
        other = copy.deepcopy(policy["checks"][0])
        other.update(id="missing-demand", required_fact="absent")
        policy["checks"].append(other)
        result = self.check(current, policy)
        self.assertEqual(exit_code(result), 1)
        self.assertTrue(result["gaps"])
        self.assertEqual(len(result["checks"]), 2)

    def test_absent_fact_does_not_prove_removal(self):
        current = record()
        current["facts"].pop()
        result = self.check(current)
        self.assertEqual(exit_code(result), 2)
        self.assertFalse(result["findings"])

    def test_wrong_baseline_does_not_manufacture_change(self):
        old, new = record(), record(4, 4)
        policy = contract(new, old)
        old["facts"][1]["value"] = 9
        result = self.check(new, policy, old)
        self.assertEqual(exit_code(result), 2)
        self.assertEqual(result["changes"], [])

    def test_baseline_unknown_scope_or_units_and_missing_baseline(self):
        old, current = record(), record(4, 4)
        old["scope"]["interface_ref"] = "other"
        self.assertEqual(exit_code(self.check(current, contract(current, old), old)), 2)
        old = record()
        old["facts"][1]["unit"] = "bytes"
        self.assertEqual(self.check(current, contract(current, old), old)["changes"], [{"id": "required", "before": 8, "after": 4, "delta": -4, "unit": "transactions"}])
        self.assertEqual(exit_code(self.check(current, contract(current, old))), 2)

    def test_shape_and_self_comparison_are_rejected(self):
        current = record()
        policy = contract(current)
        policy["checks"][0]["available_fact"] = "required"
        with self.assertRaises(ValueError):
            self.check(current, policy)
        current["extra"] = True
        with self.assertRaises(ValueError):
            self.check(current)

    def test_hash_is_stable_but_does_not_authenticate_semantics(self):
        current = record()
        reordered = dict(reversed(list(current.items())))
        self.assertEqual(digest(current), digest(reordered))
        # An incorrect but fully asserted semantic mapping can pass; source review is required.
        current["facts"][0]["value"] = 1
        current["facts"][0]["meaning_ref"] = "unsupported:wrong-parameter-role"
        self.assertEqual(exit_code(self.check(current)), 0)


class CliTests(unittest.TestCase):
    def test_real_example_review_no_overwrite_unicode_and_error_states(self):
        with tempfile.TemporaryDirectory(prefix="capacity space ") as tmp:
            parent = Path(tmp)
            example = parent / "records"
            subprocess.run([sys.executable, str(MODULE / "examples/create_example.py"), str(example)], check=True)
            out = parent / "review-é.json"
            cmd = [sys.executable, str(MODULE / "contract_review.py"), "review", str(example / "current.json"),
                   str(example / "contract.json"), "--baseline", str(example / "baseline.json"), "--json-out", str(out)]
            env = dict(os.environ, PYTHONIOENCODING="ascii")
            result = subprocess.run(cmd, capture_output=True, env=env)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(read_json(out)["status"], "review_required")
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 3)
            self.assertEqual(subprocess.run([sys.executable, str(MODULE / "contract_review.py"), "review"], capture_output=True).returncode, 2)

    def test_duplicate_json_keys_nonfinite_and_overwriting_inputs_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            for text in ('{"value":1,"value":2}', '{"value":NaN}'):
                p.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_json(p)
            p.write_text(json.dumps(record()), encoding="utf-8")
            result = subprocess.run([sys.executable, str(MODULE / "contract_review.py"), "review", str(p), str(p),
                                     "--json-out", str(p)], capture_output=True)
            self.assertEqual(result.returncode, 3)


def has_slang():
    try:
        return importlib.metadata.version("pyslang") == "12.0.0"
    except importlib.metadata.PackageNotFoundError:
        return False


@unittest.skipUnless(has_slang(), "Optional pyslang 12.0.0 is absent")
class NativeCaptureTests(unittest.TestCase):
    def capture(self, output, parameters=None, mapping=None, complete=True):
        from slang_capacity import capture_parameters
        current = record()
        mapping = mapping or {"format": "opentools.capacity-mapping.v1", "facts": [
            {"id": f["id"], "symbol": "ISSUE_LIMIT" if f["id"] == "required" else "AVAILABLE",
             "unit": f["unit"], "basis_ref": f["basis_ref"], "meaning_ref": f["meaning_ref"]} for f in current["facts"]]}
        return capture_parameters([str(MODULE / "examples/native/capacity.sv")], [], "capacity_case",
                                  parameters or {}, mapping, current["scope"], "capture", "owned-v1", complete, output)

    def test_actual_elaboration_overrides_and_derived_capacity(self):
        with tempfile.TemporaryDirectory() as tmp:
            current = self.capture(Path(tmp) / "evidence", {"CAPACITY": 7, "RESERVED": 2, "ISSUE_LIMIT": 6})
            self.assertEqual([f["value"] for f in current["facts"]], [6, 5])
            self.assertEqual(exit_code(review(current, contract(current))), 1)
            self.assertTrue((Path(tmp) / "evidence/diagnostics.json").is_file())

    def test_partial_capture_and_unconfirmed_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            current = self.capture(Path(tmp) / "partial", complete=False)
            self.assertEqual(exit_code(review(current, contract(current))), 2)
            with self.assertRaises(ValueError):
                self.capture(Path(tmp) / "unknown", {"NOT_A_PARAMETER": 2})

    def test_unknown_nonparameter_or_negative_selected_values_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i, symbol in enumerate(("missing", "accepted")):
                mapping = {"format": "opentools.capacity-mapping.v1", "facts": [
                    {"id": "x", "symbol": symbol, "unit": "transactions", "basis_ref": "window", "meaning_ref": "test:role"}]}
                with self.assertRaises(ValueError):
                    self.capture(Path(tmp) / str(i), mapping=mapping)
            with self.assertRaises(ValueError):
                self.capture(Path(tmp) / "negative", {"ISSUE_LIMIT": -1})

    def test_capture_cli_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            current = record()
            mapping = {"format": "opentools.capacity-mapping.v1", "facts": [
                {"id": f["id"], "symbol": "ISSUE_LIMIT" if f["id"] == "required" else "AVAILABLE",
                 "unit": f["unit"], "basis_ref": f["basis_ref"], "meaning_ref": f["meaning_ref"]} for f in current["facts"]]}
            for name, data in (("scope", current["scope"]), ("mapping", mapping), ("parameters", {})):
                (path / (name + ".json")).write_text(json.dumps(data), encoding="utf-8")
            cmd = [sys.executable, str(MODULE / "contract_review.py"), "capture-slang", "--source", str(MODULE / "examples/native/capacity.sv"),
                   "--top", "capacity_case", "--parameters", str(path / "parameters.json"), "--mapping", str(path / "mapping.json"),
                   "--scope", str(path / "scope.json"), "--record-ref", "native", "--revision-ref", "owned-v1", "--output", str(path / "snapshot.json")]
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 2)
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 3)


@unittest.skipUnless(os.environ.get("OPENTOOLS_CONTRACT_NATIVE"), "Opt-in native Verilator recipe is disabled")
class NativeSimulationTests(unittest.TestCase):
    def test_two_native_profiles_and_independent_reference_controls(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("capacity_native_example", MODULE / "examples/native/run_example.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        retained = os.environ.get("OPENTOOLS_CONTRACT_OUTPUT")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(retained) if retained else Path(tmp) / "native"
            results = module.run_example(target, os.environ["OPENTOOLS_CONTRACT_NATIVE"], os.environ.get("VERILATOR_ROOT"))
            self.assertEqual(len(results), 6)
            self.assertEqual(sum(r["native"]["violations"] > 0 for r in results), 2)


if __name__ == "__main__":
    unittest.main()
