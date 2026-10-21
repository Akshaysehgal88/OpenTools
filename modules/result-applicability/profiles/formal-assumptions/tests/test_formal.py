import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PROFILE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROFILE), str(PROFILE / "examples")]
from formal_core import InputError, digest, exit_code, markdown, review
from sby_capture import SBY_REVISION, YOSYS_VERSION, capture, configuration, contained, revalidate
from create_example import CASES, capture_context, make_bundle
from finite_reference import check_trace, finite_consumer, finite_producer


def synthetic_task(root, name, mode, top, assumption=True, status="PASS", depth=8):
    """Parser-only synthetic files. No solver execution or real proof is claimed."""
    folder = root / name
    (folder / "src").mkdir(parents=True)
    (folder / "engine_0").mkdir()
    config = f"[options]\nmode {mode}\ndepth {depth}\n\n[engines]\nsmtbmc z3\n\n[script]\nread -formal model.sv\nprep -top {top}\nwrite_json cells.json\n\n[files]\nmodel.sv\nselection.vh\n"
    (folder / "config.sby").write_text(config)
    rc = {"PASS": 0, "FAIL": 2, "UNKNOWN": 4, "ERROR": 16}[status]
    (folder / "status").write_text(f"{status} {rc} 0\n")
    (folder / "logfile.txt").write_text(f"SYNTHETIC PARSER TEST, NEVER EXECUTED\nDONE ({status}, rc={rc})\n")
    (folder / "src/model.sv").write_text("// Synthetic parser fixture, not a measured native model\nmodule " + top + "; endmodule\n")
    (folder / "src/selection.vh").write_text("// Synthetic selection\n")
    cells = {"property": {"type": "$assert", "attributes": {"src": "model.sv:1.1-1.2"}}}
    if top == "consumer":
        cells["activation"] = {"type": "$cover", "attributes": {"src": "model.sv:2.1-2.2"}}
    if assumption:
        cells["premise"] = {"type": "$assume", "attributes": {"src": "model.sv:3.1-3.2"}}
    (folder / "src/cells.json").write_text(json.dumps({"creator": YOSYS_VERSION, "modules": {top: {"cells": cells}}}))
    if mode == "prove":
        base = "Status: passed\n" if status == "PASS" else "BMC failed!\nAssert failed in consumer: synthetic\nStatus: failed\n"
        (folder / "engine_0/logfile_basecase.txt").write_text(base)
        (folder / "engine_0/logfile_induction.txt").write_text("Temporal induction successful.\nStatus: passed\n")
        if status == "FAIL":
            for suffix in ("vcd", "yw"):
                (folder / ("engine_0/trace." + suffix)).write_text("synthetic witness, parser-only\n")
    elif mode == "cover":
        lines = "Reached cover statement at synthetic in step 2.\nStatus: passed\n" if status == "PASS" else "".join(f"Checking cover reachability in step {i}..\n" for i in range(depth)) + "Unreached cover statement at synthetic\nStatus: failed\n"
        (folder / "engine_0/logfile.txt").write_text(lines)
        if status == "PASS":
            for suffix in ("vcd", "yw"):
                (folder / ("engine_0/trace0." + suffix)).write_text("synthetic witness, parser-only\n")
    else:
        (folder / "engine_0/logfile.txt").write_text("".join(f"Checking assertions in step {i}..\n" for i in range(depth)) + "Status: passed\n")
    ctx = capture_context("synthetic:" + name, ["synthetic-never-executed"], "wake", 2, top == "producer")
    return capture(root, name, ctx)


class FormalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        proof = synthetic_task(self.root, "proof", "prove", "consumer")
        cover = synthetic_task(self.root, "cover", "cover", "consumer")
        guarantee = synthetic_task(self.root, "producer", "prove", "producer", False)
        make_bundle(self.root, "synthetic", "wake", 2, proof, cover, guarantee)
        self.spec = json.loads((self.root / "scope.json").read_text())
        self.evidence = json.loads((self.root / "evidence.json").read_text())

    def bound(self):
        self.evidence["scope_sha256"] = digest(self.spec)

    def run_review(self):
        return review(self.spec, self.evidence, self.root)

    def recapture(self, key):
        old = self.evidence[key] if key != "producer" else self.evidence["guarantees"]["source-hold"]
        new = capture(self.root, key, old["provenance"]["context"])
        if key == "producer":
            self.evidence["guarantees"]["source-hold"] = new
        else:
            self.evidence[key] = new

    def test_supported_scoped_review(self):
        r = self.run_review()
        self.assertEqual(exit_code(r), 0)
        self.assertEqual(len(r["runs"]), 3)
        self.assertIn("not proof of composition", r["limits"])

    def test_missing_proof(self):
        self.evidence["proof"] = None
        self.assertEqual(exit_code(self.run_review()), 2)

    def test_missing_cover(self):
        self.evidence["cover"] = None
        self.assertEqual(exit_code(self.run_review()), 2)

    def test_missing_producer(self):
        self.evidence["guarantees"] = {}
        self.assertEqual(exit_code(self.run_review()), 2)

    def test_unknown_owner(self):
        self.spec["consumer"]["assumptions"][0]["owner_ref"] = None
        self.bound()
        self.assertEqual(exit_code(self.run_review()), 2)

    def test_missing_support(self):
        self.spec["consumer"]["assumptions"][0]["support_ref"] = None
        self.bound()
        self.assertEqual(exit_code(self.run_review()), 2)

    def test_missing_condition(self):
        self.spec["consumer"]["assumptions"][0]["condition_ref"] = None
        self.bound()
        self.assertNotEqual(exit_code(self.run_review()), 0)

    def test_different_guarantee_condition(self):
        self.spec["guarantees"]["source-hold"]["condition_ref"] = "different-predicate"
        self.bound()
        self.assertEqual(exit_code(self.run_review()), 1)

    def test_missing_port_binding(self):
        self.spec["guarantees"]["source-hold"]["port_binding_ref"] = None
        self.bound()
        self.assertEqual(exit_code(self.run_review()), 2)

    def test_omitted_assumption_mapping(self):
        self.spec["consumer"]["assumptions"] = []
        self.bound()
        self.assertEqual(exit_code(self.run_review()), 1)

    def test_omitted_assumption_census(self):
        self.spec["consumer"]["cells"] = [c for c in self.spec["consumer"]["cells"] if c["type"] != "$assume"]
        self.spec["consumer"]["assumptions"] = []
        self.bound()
        r = self.run_review()
        self.assertEqual(exit_code(r), 1)
        self.assertFalse(r["runs"])

    def test_unknown_model_inventory(self):
        self.spec["consumer"]["cells"] = None
        self.spec["consumer"]["assumptions"] = None
        self.bound()
        self.assertEqual(exit_code(self.run_review()), 2)

    def test_stale_scope_binding(self):
        self.spec["claim"] += " changed"
        r = self.run_review()
        self.assertEqual(exit_code(r), 2)
        self.assertFalse(r["runs"])

    def test_foreign_native_run(self):
        self.spec["run_refs"]["proof"] = "foreign-run"
        self.bound()
        r = self.run_review()
        self.assertEqual(exit_code(r), 1)
        self.assertNotIn("proof", [v["run"] for v in r["runs"]])

    def test_stale_source(self):
        (self.root / "proof/src/model.sv").write_text("changed\n")
        r = self.run_review()
        self.assertEqual(exit_code(r), 2)
        self.assertNotIn("proof", [v["run"] for v in r["runs"]])

    def test_changed_witness(self):
        (self.root / "cover/engine_0/trace0.vcd").write_text("changed witness\n")
        self.assertEqual(exit_code(self.run_review()), 2)

    def test_missing_model(self):
        (self.root / "proof/src/cells.json").unlink()
        self.assertEqual(exit_code(self.run_review()), 2)

    def test_forged_snapshot_values(self):
        self.evidence["proof"]["fields"]["mode"]["value"] = "cover"
        self.assertEqual(exit_code(self.run_review()), 2)

    def test_critical_file_removed_from_receipt(self):
        del self.evidence["proof"]["provenance"]["integrity_files"]["proof/src/model.sv"]
        self.assertEqual(exit_code(self.run_review()), 2)

    def test_redeclared_native_model_mismatch(self):
        self.spec["consumer"]["sources"]["model.sv"] = "0" * 64
        self.bound()
        self.assertEqual(exit_code(self.run_review()), 1)

    def test_producer_reset_scope_mismatch(self):
        self.spec["guarantees"]["source-hold"]["scope"]["reset_ref"] = "other-reset"
        self.bound()
        self.assertEqual(exit_code(self.run_review()), 1)

    def test_producer_with_self_assumption(self):
        p = self.root / "producer/src/cells.json"
        data = json.loads(p.read_text())
        data["modules"]["producer"]["cells"]["circular"] = {"type": "$assume", "attributes": {"src": "model.sv:1.2-1.3"}}
        p.write_text(json.dumps(data))
        self.recapture("producer")
        self.spec["guarantees"]["source-hold"]["cells"] = self.evidence["guarantees"]["source-hold"]["fields"]["cells"]["value"]
        self.bound()
        self.assertEqual(exit_code(self.run_review()), 2)

    def test_bounded_cover_failure_is_unknown_reachability(self):
        shutil.rmtree(self.root / "cover")
        self.evidence["cover"] = synthetic_task(self.root, "cover", "cover", "consumer", status="FAIL", depth=1)
        r = self.run_review()
        self.assertEqual(exit_code(r), 2)
        self.assertIn("does not establish universal", " ".join(r["gaps"]))

    def test_bmc_pass_not_unbounded_proof(self):
        shutil.rmtree(self.root / "proof")
        self.evidence["proof"] = synthetic_task(self.root, "proof", "bmc", "consumer", depth=3)
        r = self.run_review()
        self.assertEqual(exit_code(r), 2)
        self.assertIn("bounded only", " ".join(r["gaps"]))

    def test_actual_counterexample_preserved(self):
        shutil.rmtree(self.root / "proof")
        self.evidence["proof"] = synthetic_task(self.root, "proof", "prove", "consumer", status="FAIL")
        self.assertEqual(exit_code(self.run_review()), 1)

    def test_unknown_execution_does_not_become_failure(self):
        (self.root / "proof/status").write_text("UNKNOWN 4 0\n")
        (self.root / "proof/logfile.txt").write_text("DONE (UNKNOWN, rc=4)\n")
        self.recapture("proof")
        r = self.run_review()
        self.assertEqual(exit_code(r), 2)
        self.assertFalse(any("counterexample" in v for v in r["findings"]))

    def test_missing_original_command(self):
        ctx = self.evidence["proof"]["provenance"]["context"]
        ctx["command"] = None
        self.recapture("proof")
        self.assertEqual(exit_code(self.run_review()), 2)

    def test_dependency_capture_incomplete(self):
        self.evidence["proof"]["provenance"]["context"]["dependency_capture_complete"] = False
        self.recapture("proof")
        self.assertEqual(exit_code(self.run_review()), 2)

    def test_missing_required_activation_ref(self):
        self.spec["consumer"]["activation_ref"] = None
        self.bound()
        self.assertEqual(exit_code(self.run_review()), 2)

    def test_wrong_top_and_hierarchy_rejected(self):
        data = json.loads((self.root / "proof/src/cells.json").read_text())
        data["modules"]["other"] = {}
        (self.root / "proof/src/cells.json").write_text(json.dumps(data))
        with self.assertRaises(InputError):
            self.recapture("proof")

    def test_terminal_status_contradiction_rejected(self):
        (self.root / "proof/logfile.txt").write_text("DONE (FAIL, rc=2)\n")
        with self.assertRaises(InputError):
            self.recapture("proof")

    def test_reader_does_not_execute_config_commands(self):
        recipe = (self.root / "proof/config.sby").read_text()
        recipe = recipe.replace("read -formal model.sv", "shell touch marker")
        with self.assertRaises(InputError):
            configuration(recipe)
        self.assertFalse((self.root / "marker").exists())

    def test_engine_status_contradiction_rejected(self):
        (self.root / "proof/engine_0/logfile_basecase.txt").write_text("Status: passed\nStatus: failed\n")
        with self.assertRaises(InputError):
            self.recapture("proof")

    def test_truncated_engine_completion_rejected(self):
        (self.root / "proof/engine_0/logfile_induction.txt").write_text("Temporal induction successful.\n")
        with self.assertRaises(InputError):
            self.recapture("proof")

    def test_paths_cannot_escape(self):
        for path in ("../outside", "/outside", "C:/outside", "proof/../status", "proof\\status"):
            with self.assertRaises(InputError):
                contained(self.root, path)

    def test_unqualified_tools_rejected(self):
        ctx = copy.deepcopy(self.evidence["proof"]["provenance"]["context"])
        ctx["sby_revision"] = "other"
        with self.assertRaises(InputError):
            capture(self.root, "proof", ctx)

    def test_markdown_escapes_claim(self):
        self.spec["claim"] = "<script>alert(1)</script> | name"
        self.bound()
        m = markdown(self.run_review())
        self.assertNotIn("<script>", m)
        self.assertIn("&#124;", m)

    def test_cli_and_output_preservation(self):
        argv = [sys.executable, str(PROFILE / "formal_review.py"), "review", str(self.root / "scope.json"), str(self.root / "evidence.json"), "--json-out", str(self.root / "new.json")]
        first = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        before = (self.root / "new.json").read_bytes()
        self.assertEqual(subprocess.run(argv, capture_output=True).returncode, 3)
        self.assertEqual(before, (self.root / "new.json").read_bytes())

    def test_finite_reference_second_context(self):
        for context in ("wake", "stream"):
            for mode in (0, 1, 2):
                ref = finite_consumer(context, mode)
                self.assertEqual(ref["safety_counterexample_exists"], mode == 0)
                self.assertEqual(ref["activation_reachable"], mode != 1)
            self.assertEqual(finite_producer(context)["violations"], 0)

    @unittest.skipUnless(os.environ.get("OPENTOOLS_FORMAL_EXAMPLE"), "Set OPENTOOLS_FORMAL_EXAMPLE to a retained native example root")
    def test_actual_native_matrix_and_witnesses(self):
        root = Path(os.environ["OPENTOOLS_FORMAL_EXAMPLE"])
        summary = json.loads((root / "summary.json").read_text())
        self.assertEqual(len(summary["native_jobs"]), 18)
        for name, (context, assumption, _, _, _) in CASES.items():
            folder = root / name
            spec = json.loads((folder / "scope.json").read_text())
            evidence = json.loads((folder / "evidence.json").read_text())
            expected = json.loads((folder / "report.json").read_text())
            self.assertEqual(review(spec, evidence, folder), expected)
            self.assertEqual(spec["consumer"]["sources"]["model.sv"], hashlib.sha256((PROFILE / "examples" / (context + ".sv")).read_bytes()).hexdigest())
            for snapshot in (evidence["proof"], evidence["cover"]):
                meaning = snapshot["fields"]["semantics"]["value"]
                for relative in snapshot["provenance"]["witnesses"]:
                    if relative.endswith(".vcd"):
                        check_trace(context, assumption, folder / relative, meaning)


if __name__ == "__main__":
    unittest.main()
