"""Logic tests are synthetic; the optional saved-native matrix uses actual tool output."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PROFILE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROFILE))
from equivalence_core import InputError, exit_code, markdown, review
from yosys_equivalence import REQUIRED_FIELDS, capture, contained, file_hash, module, parse_recipe, recipe, revalidate, witness


def load(path):return json.loads(Path(path).read_text(encoding="utf-8"))


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root = Path(self.temp.name)
        artifact = self.root / "result.txt";artifact.write_text("SYNTHETIC LOGIC TEST; NO NATIVE EXECUTION\n")
        fields = {k: {"value": {"synthetic": k}, "evidence_ref": "synthetic:test-only"} for k in REQUIRED_FIELDS}
        fields["partition"]["value"] = {"id": "miter"}
        fields["engine_profile"]["value"] = {"proof_kind": "synthetic-no-proof"}
        fields["mode_constraint"] = {"value": {"signal": "in_mode", "allowed_values": [0, 1]}, "evidence_ref": "synthetic:scope"}
        self.snapshot = {"format": "opentools.result-snapshot.v1", "run_ref": "synthetic:run", "manifest_ref": "synthetic:manifest",
            "execution": {"state": "completed", "evidence_ref": "synthetic:execution", "command": ["synthetic-never-executed"], "executable_ref": "synthetic",
                          "dependency_capture_complete": True, "dependency_evidence_ref": "synthetic:dependency"},
            "result": {"outcome": "pass", "native_status": "PASS", "complete": True, "producer_run_ref": "synthetic:run", "evidence_ref": "synthetic:result",
                       "artifact": {"path": "result.txt", "sha256": file_hash(artifact)}}, "fields": fields,
            "provenance": {"context": {"eco_ref": "synthetic:eco", "scope_basis_ref": "synthetic:stateless"}, "native_counterexample": None}}
        self.intent = {"format": "opentools.equivalence-intent.v1", "claim_id": "synthetic:claim", "claim": "Synthetic review logic only", "scope_ref": "synthetic:scope",
            "eco_ref": "synthetic:eco", "eco_intent_ref": "synthetic:intent", "owner_ref": "synthetic:owner", "run_ref": "synthetic:run",
            "required_fields": {k: copy.deepcopy(fields[k]) for k in REQUIRED_FIELDS}, "mode_input": "in_mode", "required_modes": [0, 1], "mode_basis_ref": "synthetic:modes",
            "mapping_review": {"status": "approved", "reviewer_ref": "synthetic-reviewer-not-real-approval", "basis_ref": "synthetic:map"}}

    def check(self):
        # Only native revalidation is mocked; the real existing parent comparator checks the record and artifact.
        with patch("equivalence_core.revalidate"):
            return review(self.intent, self.snapshot, self.root)

    def test_matching_pass(self):self.assertEqual(exit_code(self.check()), 0)
    def test_pass_excludes_required_mode(self):
        self.snapshot["fields"]["mode_constraint"]["value"]["allowed_values"] = [0]
        r = self.check();self.assertEqual(exit_code(r), 1);self.assertEqual(r["native"]["status"], "PASS")
        self.assertIn("excludes", r["findings"][0])
    def test_legitimate_narrow_request(self):
        self.intent["required_modes"] = [0];self.snapshot["fields"]["mode_constraint"]["value"]["allowed_values"] = [0]
        self.assertEqual(exit_code(self.check()), 0)
    def failure(self, mode):
        self.snapshot["result"].update(outcome="fail", native_status="FAIL")
        self.snapshot["provenance"]["native_counterexample"] = {"in_mode": mode, "trigger": 1}
    def test_counterexample_in_scope(self):
        self.failure(1);self.assertEqual(exit_code(self.check()), 1)
    def test_counterexample_outside_scope_is_not_pass(self):
        self.failure(1);self.intent["required_modes"] = [0]
        r = self.check();self.assertEqual(exit_code(r), 2);self.assertIn("neither refutes nor proves", r["gaps"][0])
    def test_missing_mode_basis(self):
        self.intent["mode_basis_ref"] = None;self.assertEqual(exit_code(self.check()), 2)
    def test_missing_mode_selection(self):
        self.intent["mode_input"] = None;self.assertEqual(exit_code(self.check()), 2)
    def test_different_mode_not_automatically_mapped(self):
        self.intent["mode_input"] = "in_other_mode";self.assertEqual(exit_code(self.check()), 2)
    def test_missing_required_modes(self):
        self.intent["required_modes"] = None;self.assertEqual(exit_code(self.check()), 2)
    def test_modes_reject_duplicates_boolean_and_empty(self):
        for modes in ([0, 0], [True], [], [1, 0], [2]):
            with self.subTest(modes=modes):
                self.intent["required_modes"] = modes
                with self.assertRaises(InputError):self.check()
    def test_proposed_mapping_is_not_approval(self):
        self.intent["mapping_review"]["status"] = "proposed";self.assertEqual(exit_code(self.check()), 2)
    def test_missing_mapping_basis(self):
        self.intent["mapping_review"]["basis_ref"] = None;self.assertEqual(exit_code(self.check()), 2)
    def test_missing_intent_and_owner(self):
        self.intent["owner_ref"] = None;self.intent["eco_intent_ref"] = None;self.assertEqual(exit_code(self.check()), 2)
    def test_foreign_run_quarantines_failure(self):
        self.failure(1);self.intent["run_ref"] = "foreign:run"
        r = self.check();self.assertEqual(exit_code(r), 1);self.assertIsNone(r["native"])
    def test_foreign_eco(self):
        self.intent["eco_ref"] = "foreign:eco";self.assertIsNone(self.check()["native"])
    def test_missing_run(self):
        self.intent["run_ref"] = None;self.assertEqual(exit_code(self.check()), 2)
    def test_parameter_build_mapping_partition_and_model_mismatch(self):
        for field in ("designs", "mapping", "partition", "model_boundary", "engine_profile"):
            with self.subTest(field=field):
                original = copy.deepcopy(self.intent["required_fields"][field])
                self.intent["required_fields"][field]["value"] = {"different": field}
                r = self.check();self.assertEqual(exit_code(r), 1);self.assertIsNone(r["native"])
                self.intent["required_fields"][field] = original
    def test_unknown_model_is_gap(self):
        self.intent["required_fields"]["model_boundary"]["value"] = None;self.assertEqual(exit_code(self.check()), 2)
    def test_omitted_compare_field_is_invalid(self):
        del self.intent["required_fields"]["mapping"]
        with self.assertRaises(InputError):self.check()
    def test_stale_and_missing_artifact(self):
        p = self.root / "result.txt";p.write_text("changed")
        self.assertEqual(exit_code(self.check()), 2);p.unlink();self.assertEqual(exit_code(self.check()), 2)
    def test_dependency_unknown(self):
        self.snapshot["execution"]["dependency_capture_complete"] = None;self.assertEqual(exit_code(self.check()), 2)
    def test_capture_error_is_gap_not_hardware_failure(self):
        with patch("equivalence_core.revalidate", side_effect=InputError("stale source")):
            r = review(self.intent, self.snapshot, self.root)
        self.assertEqual(exit_code(r), 2);self.assertIsNone(r["native"])
    def test_markdown_escapes(self):
        self.intent["claim"] = "<script>|untrusted";self.assertIn("&lt;script&gt;&#124;untrusted", markdown(self.check()))


class ReaderTests(unittest.TestCase):
    def test_explicit_generic_parameters_and_mode(self):
        params = {"gold": {"LANES": 32}, "gate": {"LANES": 32, "PIPELINE": 0}}
        script = recipe(params, ("in_test_mode", 1));self.assertEqual(parse_recipe(script), (params, ("in_test_mode", 1)))
    def test_no_parameter_required(self):self.assertEqual(parse_recipe(recipe({"gold": {}, "gate": {}})), ({"gold": {}, "gate": {}}, None))
    def test_extra_script_cannot_execute(self):
        for suffix in ("exec touch marker\n", "delete gate.sideband\n", "sat -prove trigger 1\n"):
            with self.subTest(suffix=suffix), self.assertRaises(InputError):parse_recipe(recipe({"gold": {}, "gate": {}}) + suffix)
    def test_parameter_boolean_and_duplicate_rejected(self):
        with self.assertRaises(InputError):recipe({"gold": {"W": True}, "gate": {}})
        script = recipe({"gold": {"W": 4}, "gate": {}}).replace("chparam -set W 4 gold\n", "chparam -set W 4 gold\n" * 2)
        with self.assertRaises(InputError):parse_recipe(script)
    def node(self):
        return {"ports": {"a": {"direction": "input", "bits": [2]}, "y": {"direction": "output", "bits": [3]}},
                "cells": {"n": {"type": "$not", "port_directions": {"A": "input", "Y": "output"}, "connections": {"A": [2], "Y": [3]}}}}
    def test_state_memory_blackbox_and_unknown_cell_rejected(self):
        for key in ("state", "memory", "blackbox", "unknown"):
            n = self.node()
            if key == "memory":n["memories"] = {"m": {}}
            elif key == "blackbox":n["attributes"] = {"blackbox": "1"}
            else:n["cells"]["n"]["type"] = "$dff" if key == "state" else "$opaque"
            with self.subTest(key=key), self.assertRaises(InputError):module(n)
    def test_undefined_and_cycle_rejected(self):
        for bit in ("x", 3, 99):
            n = self.node();n["cells"]["n"]["connections"]["A"] = [bit]
            with self.subTest(bit=bit), self.assertRaises(InputError):module(n)
    def test_input_cannot_be_unknown(self):
        n = self.node();n["ports"]["a"]["bits"] = ["x"]
        with self.assertRaises(InputError):module(n)
    def test_deep_combinational_graph(self):
        n = self.node();n["ports"]["y"]["bits"] = [2502];n["cells"] = {}
        for bit in range(3, 2503):n["cells"][str(bit)] = {"type": "$not", "port_directions": {"A": "input", "Y": "output"}, "connections": {"A": [bit - 1], "Y": [bit]}}
        self.assertIs(module(n), n)
    def test_duplicate_driver_rejected(self):
        n = self.node();n["cells"]["duplicate"] = copy.deepcopy(n["cells"]["n"])
        with self.assertRaises(InputError):module(n)
    def test_native_32bit_signed_display_is_bitpattern(self):
        ports = {"gate_pending": {"bits": list(range(32))}, "trigger": {"bits": [40]}}
        binary = "1" + "0" * 31
        log = "  \\gate_pending -2147483648 80000000 " + binary + "\n  \\trigger 1 1 1\n"
        wave = {"signal": [{"name": "gate_pending", "wave": "=4", "data": [binary, ""]}, {"name": "trigger", "wave": "14"}]}
        self.assertEqual(witness(log, wave, ports), {"gate_pending": 2 ** 31, "trigger": 1})
        wave["signal"][1]["wave"] = "04"
        with self.assertRaises(InputError):witness(log, wave, ports)
    def test_escape_paths_rejected(self):
        for value in ("../other", "/tmp/other", "C:/other", "a\\b", "a/./b"):
            with self.subTest(value=value), self.assertRaises(InputError):contained(".", value)


@unittest.skipUnless(os.environ.get("OPENTOOLS_EQUIVALENCE_EXAMPLE"), "Set OPENTOOLS_EQUIVALENCE_EXAMPLE to retained native example output")
class NativeTests(unittest.TestCase):
    def setUp(self):self.native = Path(os.environ["OPENTOOLS_EQUIVALENCE_EXAMPLE"])
    def test_full_native_matrix(self):
        summary = load(self.native / "summary.json");self.assertEqual(len(summary["native_jobs"]), 10);self.assertEqual(len(summary["cases"]), 14)
        self.assertEqual(sum(v["vectors_checked"] for v in summary["native_jobs"]), 394752)
        for row in summary["cases"]:
            with self.subTest(case=row["case"]):
                folder = self.native / row["case"];s = load(folder / "snapshot.json");i = load(folder / "intent.json")
                revalidate(s, folder);r = review(i, s, folder);self.assertEqual(r, load(folder / "report.json"));self.assertEqual(exit_code(r), row["exit"])
    def copy_case(self, name):
        temp = tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);dest = Path(temp.name) / "case";shutil.copytree(self.native / name, dest);return dest
    def test_saved_source_and_parameter_identity(self):
        normal = load(self.native / "control-rewrite-all-modes/snapshot.json")["fields"]["designs"]["value"]
        wide = load(self.native / "control-wide-rewrite/snapshot.json")["fields"]["designs"]["value"]
        self.assertEqual(normal["gold"]["source_sha256"], wide["gold"]["source_sha256"])
        self.assertEqual(int(normal["gold"]["parameters"]["WIDTH"], 2), 8);self.assertEqual(int(wide["gold"]["parameters"]["WIDTH"], 2), 32)
    def test_changed_source_and_forged_receipt(self):
        p = self.copy_case("control-wide-rewrite");s = load(p / "snapshot.json")
        (p / "run/reference.v").write_text("changed")
        self.assertEqual(exit_code(review(load(p / "intent.json"), s, p)), 2)
        s["fields"]["designs"]["value"]["gold"]["source_sha256"] = file_hash(p / "run/reference.v")
        with self.assertRaises(InputError):revalidate(s, p)
    def test_missing_witness_truncated_log_and_unsupported_version(self):
        for filename, value in (("witness.json", None), ("equivalence.log", "truncated"), ("version.txt", "Yosys unqualified")):
            p = self.copy_case("control-wide-counterexample");s = load(p / "snapshot.json");path = p / "run" / filename
            if value is None:path.unlink()
            else:path.write_text(value)
            with self.subTest(filename=filename):self.assertEqual(exit_code(review(load(p / "intent.json"), s, p)), 2)
    def test_hidden_native_constraint_rejected_on_recapture(self):
        p = self.copy_case("arithmetic-rewrite-all-modes");ctx = load(p / "capture-context.json")
        text = (p / "run/equivalence.log").read_text();new = "Import set-constraint: \\in_operand_a = 4'0000\n" + text
        (p / "run/equivalence.log").write_text(new);(p / "run/native.log").write_text(new)
        with self.assertRaises(InputError):capture(p, "run", ctx)
    def test_cli_is_data_only_and_preserves_outputs(self):
        p = self.copy_case("control-hidden-functional-change");output = p / "fresh.json"
        r = subprocess.run([sys.executable, str(PROFILE / "equivalence_review.py"), "capture", str(p), "run", str(p / "capture-context.json"), "--output", str(output)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr);self.assertEqual(load(output), load(p / "snapshot.json"))
        original = output.read_bytes()
        r = subprocess.run([sys.executable, str(PROFILE / "equivalence_review.py"), "capture", str(p), "run", str(p / "capture-context.json"), "--output", str(output)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 3);self.assertEqual(output.read_bytes(), original)
        (p / "run/run.ys").write_text("exec touch SHOULD_NOT_EXECUTE\n")
        r = subprocess.run([sys.executable, str(PROFILE / "equivalence_review.py"), "capture", str(p), "run", str(p / "capture-context.json"), "--output", str(p / "never.json")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 3);self.assertFalse((p / "SHOULD_NOT_EXECUTE").exists());self.assertFalse((p / "never.json").exists())


if __name__ == "__main__":unittest.main()
