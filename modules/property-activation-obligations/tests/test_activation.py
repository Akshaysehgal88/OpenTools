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
from unittest.mock import patch
import xml.etree.ElementTree as ET

MODULE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(MODULE), str(MODULE / "examples")]
from activation_core import InputError, contained, digest, exit_code, markdown, review
from native_capture import capture, coverage, family, transcript, xml_bindings
from reference_model import CASES, RUNTIME_OFF, expected
from create_example import context_for, records


def synthetic():
    reference = expected("active", True)
    def signal(name):return {"op": "signal", "ref": "top." + name}
    checker = {"hier": "top.dut.audit", "target": "top.dut", "target_module": "power_subject", "edge": "posedge", "property_name": "p_transition",
               "pins": {"checker_clk": signal("aon_clk"), "reset": signal("reset"), "mode": signal("mode"), "extra_disable": {"op": "constant", "value": 0},
                        "event_req": signal("event_req"), "condition_ok": signal("condition_ok")}, "source_ref": "synthetic:checker"}
    observer = {"hier": "top.dut.observe", "target": "top.dut", "edge": "posedge", "property_name": None,
                "pins": {"observer_clk": signal("aon_clk"), **{k: signal(k) for k in ("reset", "mode", "event_req", "condition_ok")}}}
    evidence = {"format": "synthetic-core-only-not-native", "run_ref": "owned:synthetic", "scope": context_for("synthetic", "power", "active")["scope"],
                "sources": {"top.sv": "a" * 64}, "dependencies_complete": True, "dependency_basis_ref": "synthetic-dependencies",
                "family_basis_ref": "synthetic-family", "method": "bounded_simulation", "checker": checker, "observer": observer,
                "native_outcome": "no_assertion_failure_observed", "covers": {}, **{k: reference[k] for k in ("drive", "required_samples", "checker_samples", "assertion_failures", "window")}}
    roster, model = records("synthetic", "power", evidence)
    return roster, model, evidence


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.roster, self.model, self.evidence = synthetic()
        mocked = patch("native_capture.revalidate", return_value=None)
        mocked.start();self.addCleanup(mocked.stop)

    def check(self):
        self.model["roster_sha256"] = digest(self.roster)
        return review(self.roster, self.model, self.evidence)

    def kinds(self):return {v["kind"] for v in self.check()["findings"]}

    def test_valid_selected_activation(self):
        r = self.check();self.assertEqual(exit_code(r), 0)
        self.assertTrue(all(v["activation_observed"] for v in r["obligations"]))

    def test_disabled_risk_event_despite_normal_activation(self):
        self.evidence.update({k: v for k, v in expected("disabled", True).items() if k != "coverage_counts"})
        r = self.check();self.assertEqual(exit_code(r), 1)
        self.assertTrue(r["obligations"][0]["activation_observed"])
        self.assertFalse(r["obligations"][1]["activation_observed"])
        self.assertIn("checker_disabled_during_required_event", {v["kind"] for v in r["findings"]})

    def test_runtime_off_with_positive_coverage_does_not_activate_assertion(self):
        self.evidence.update({k: v for k, v in expected("active", True, False).items() if k != "coverage_counts"})
        self.evidence["covers"] = {"top.dut.audit.c_active_any": {"count": 2}}
        self.assertIn("native_assertions_disabled_at_required_slot", self.kinds())
        self.assertFalse(any(r["activation_observed"] for r in self.check()["obligations"]))

    def test_active_fault_remains_failure_after_activation_fix(self):
        self.evidence.update({k: v for k, v in expected("active", False).items() if k != "coverage_counts"})
        self.evidence["native_outcome"] = "assertion_failure_observed"
        r = self.check();self.assertEqual(exit_code(r), 1)
        self.assertTrue(all(o["activation_observed"] for o in r["obligations"]))
        self.assertIn("native_assertion_failure_observed", {f["kind"] for f in r["findings"]})

    def test_wrong_clock_and_missing_required_sample(self):
        self.evidence["checker"]["pins"]["checker_clk"] = {"op": "signal", "ref": "top.functional_clk"}
        self.evidence["checker_samples"] = expected("gated-clock", True)["checker_samples"]
        self.assertTrue({"checker_clock_differs_required_clock", "no_checker_sample_at_required_slot"} <= self.kinds())

    def test_wrong_target_not_selected_automatically(self):
        self.evidence["checker"].update(hier="top.decoy.audit", target="top.decoy")
        self.assertIn("required_bound_checker_absent", self.kinds())

    def test_retarged_mapping_cannot_change_independent_required_target(self):
        self.evidence["checker"].update(hier="top.decoy.audit", target="top.decoy")
        for binding in self.model["bindings"]:binding["checker_ref"] = "top.decoy.audit"
        self.assertIn("checker_target_differs_required_target", self.kinds())

    def test_absent_binding_not_a_pass(self):
        self.evidence["checker"] = None;self.evidence["checker_samples"] = []
        self.assertIn("required_bound_checker_absent", self.kinds())

    def test_reset_scope_can_mask_required_event(self):
        self.evidence["checker_samples"] = expected("reset-mask", True)["checker_samples"]
        self.assertIn("checker_disabled_during_required_event", self.kinds())

    def test_aggregate_cover_cannot_replace_mode_cover(self):
        self.model["bindings"][1]["activation_cover"] = "c_active_any"
        self.assertIn("activation_cover_does_not_select_required_mode", self.kinds())

    def test_omitted_required_mapping(self):
        self.model["bindings"].pop();self.assertEqual(exit_code(self.check()), 2)

    def test_unknown_owner_preserves_activation_findings(self):
        self.roster["obligations"][1]["owner_ref"] = None
        self.evidence["checker_samples"] = expected("disabled", True)["checker_samples"]
        r = self.check();self.assertEqual(exit_code(r), 1);self.assertTrue(r["gaps"])

    def test_incomplete_requirement_inventory(self):
        self.roster["inventory_complete"] = None;self.assertEqual(exit_code(self.check()), 2)

    def test_missing_condition_meaning_is_not_backfilled(self):
        self.roster["obligations"][1]["condition_ref"] = None;self.assertEqual(exit_code(self.check()), 2)

    def test_missing_clock_reference(self):
        self.roster["obligations"][0]["clock_ref"] = None;self.assertEqual(exit_code(self.check()), 2)

    def test_unexercised_required_event(self):
        self.roster["obligations"][1]["tick"] = 7
        self.assertEqual(exit_code(self.check()), 2)

    def test_observer_cannot_measure_other_target(self):
        self.roster["obligations"][1]["target_ref"] = "top.other"
        self.assertEqual(exit_code(self.check()), 2)

    def test_no_implicit_edge_equivalence(self):
        self.roster["obligations"][1]["edge"] = "negedge"
        self.assertEqual(exit_code(self.check()), 2)

    def test_bounded_run_never_becomes_unbounded_proof(self):
        self.roster["claim_kind"] = "unbounded_property_proof"
        self.assertEqual(exit_code(self.check()), 2)

    def test_joint_omission_needs_ai_intent_review(self):
        self.roster["obligations"].pop();self.model["bindings"].pop()
        r = self.check();self.assertEqual(exit_code(r), 0)
        self.assertEqual([e["tick"] for e in r["unselected_observer_events"]], [9])
        self.assertIn("supplied, not authenticated", r["limits"])

    def test_duplicate_sample_obligations_rejected(self):
        duplicate = copy.deepcopy(self.roster["obligations"][0]);duplicate["id"] = "duplicate"
        self.roster["obligations"].append(duplicate)
        with self.assertRaises(InputError):self.check()

    def test_boolean_not_mode_integer(self):
        self.roster["obligations"][0]["mode"] = False
        with self.assertRaises(InputError):self.check()

    def test_stale_roster_digest_quarantines(self):
        self.model["roster_sha256"] = "stale"
        r = review(self.roster, self.model, self.evidence);self.assertEqual(exit_code(r), 2);self.assertFalse(r["native"])

    def test_foreign_run_quarantines_failure(self):
        self.evidence["run_ref"] = "foreign";self.evidence["native_outcome"] = "assertion_failure_observed"
        r = self.check();self.assertEqual(exit_code(r), 1);self.assertFalse(r["native"])

    def test_unknown_source_identity(self):
        self.model["sources"] = None;self.assertEqual(exit_code(self.check()), 2)

    def test_foreign_scope(self):
        self.evidence["scope"] = dict(self.evidence["scope"], design_ref="other")
        self.assertEqual(exit_code(self.check()), 1)

    def test_incomplete_dependencies(self):
        self.evidence["dependencies_complete"] = False
        self.assertEqual(exit_code(self.check()), 2)

    def test_missing_family_basis(self):
        self.evidence["family_basis_ref"] = None;self.assertEqual(exit_code(self.check()), 2)

    def test_markdown_escaping(self):
        self.roster["claim"] = "<script> | claim"
        m = markdown(self.check());self.assertNotIn("<script>", m);self.assertIn("&#124;", m)


class ReaderTests(unittest.TestCase):
    def test_paths_cannot_escape(self):
        for path in ("../outside", "/outside", "C:/outside", "run/../outside", "run\\file"):
            with self.assertRaises(InputError):contained(".", path)

    def test_unknown_coverage_format_rejected(self):
        for data in ("", "# SystemC::Coverage-4\n", "# SystemC::Coverage-3\nmalformed\n"):
            with self.assertRaises(InputError):coverage(data)

    def test_missing_window_end_is_not_completed_execution(self):
        with self.assertRaises(InputError):transcript("DRIVE 1 1 1 0 0 1 1 1\n")

    def test_invalid_trace_fields_rejected(self):
        with self.assertRaises(InputError):transcript("DRIVE 1 1 1 0 0 2 1 1\nRUN_END 2 1\n")

    def test_xml_entities_not_expanded(self):
        with self.assertRaises(InputError):xml_bindings('<!DOCTYPE x [<!ENTITY e SYSTEM "file:///outside">]><verilator_xml/>')

    @unittest.skipUnless(os.environ.get("OPENTOOLS_ACTIVATION_EXAMPLE"), "Set OPENTOOLS_ACTIVATION_EXAMPLE to retained native example root")
    def test_actual_native_matrix_sources_samples_covers(self):
        root = Path(os.environ["OPENTOOLS_ACTIVATION_EXAMPLE"])
        summary = json.loads((root / "summary.json").read_text());self.assertEqual(summary["native_runs"], 12)
        for name, (family_name, config, clean) in CASES.items():
            folder = root / name;evidence = json.loads((folder / "evidence.json").read_text())
            roster = json.loads((folder / "obligations.json").read_text());bindings = json.loads((folder / "bindings.json").read_text())
            self.assertEqual(review(roster, bindings, evidence, folder), json.loads((folder / "report.json").read_text()))
            ref = expected(config, clean, name not in RUNTIME_OFF)
            for key in ("drive", "required_samples", "checker_samples", "assertion_failures", "window"):self.assertEqual(evidence[key], ref[key])
            self.assertEqual({p: v["count"] for p, v in evidence["covers"].items()}, ref["coverage_counts"])
            self.assertEqual(evidence["sources"]["top.sv"], hashlib.sha256((MODULE / "examples" / (family_name + ".sv")).read_bytes()).hexdigest())
        off = json.loads((root / "power-runtime-off/evidence.json").read_text())
        self.assertEqual(off["covers"]["top.dut.audit.c_active_risk"]["count"], 1)
        self.assertFalse(off["assertion_failures"])

    @unittest.skipUnless(os.environ.get("OPENTOOLS_ACTIVATION_EXAMPLE"), "Set OPENTOOLS_ACTIVATION_EXAMPLE for actual reader failure controls")
    def test_actual_native_integrity_semantics_and_cli(self):
        original = Path(os.environ["OPENTOOLS_ACTIVATION_EXAMPLE"]) / "power-clean"
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "case";shutil.copytree(original, dest)
            def load(name):return json.loads((dest / name).read_text())
            roster, bindings, evidence = load("obligations.json"), load("bindings.json"), load("evidence.json")
            ctx = load("capture-context.json")
            with patch("subprocess.run", side_effect=AssertionError("A native import must not execute any command")):
                self.assertEqual(capture(dest, "run", ctx), evidence)
            (dest / "run/coverage.dat").write_text("truncated\n")
            self.assertEqual(exit_code(review(roster, bindings, evidence, dest)), 2)
            shutil.copy2(original / "run/coverage.dat", dest / "run/coverage.dat")
            evidence["checker_samples"] = []
            self.assertEqual(exit_code(review(roster, bindings, evidence, dest)), 2)
            evidence = load("evidence.json")
            (dest / "run/model.xml").unlink()
            self.assertEqual(exit_code(review(roster, bindings, evidence, dest)), 2)
            shutil.copy2(original / "run/model.xml", dest / "run/model.xml")
            root = ET.fromstring((dest / "run/model.xml").read_text())
            definition = next(m for m in root.findall("./netlist/module") if m.get("origName") == "activation_checker")
            body = next(b for b in definition.findall("begin") if b.get("name") == "p_transition")
            condition = next(v for v in body.iter("varref") if v.get("name") == "condition_ok");condition.set("name", "event_req")
            with self.assertRaises(InputError):family(definition, "checker_clk", True)
            argv = [sys.executable, str(MODULE / "activation_check.py"), "review", str(dest / "obligations.json"), str(dest / "bindings.json"), str(dest / "evidence.json"), "--json-out", str(dest / "new-report.json")]
            first = subprocess.run(argv, capture_output=True, text=True);self.assertEqual(first.returncode, 0, first.stderr)
            before = (dest / "new-report.json").read_bytes()
            self.assertEqual(subprocess.run(argv, capture_output=True).returncode, 3)
            self.assertEqual((dest / "new-report.json").read_bytes(), before)


if __name__ == "__main__":unittest.main()
