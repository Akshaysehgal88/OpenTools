import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE)); sys.path.insert(0, str(MODULE / "examples"))
from create_example import condition, contract, controls, power_metric, rule, snapshot
from ppa_core import InputError, compare, markdown, read_json
from orfs_import import context_template, import_metadata, inspect


class ComparisonTests(unittest.TestCase):
    def setUp(self): self.a, self.b, self.p = controls()
    def audit(self): return compare(self.a, self.b, self.p)

    def test_matched_control(self):
        r = self.audit()
        self.assertEqual(r["status"], "comparable_within_contract")
        self.assertTrue(all(Decimal(m["delta"]) == 0 for m in r["metrics"]))

    def test_same_field_is_intended_in_area_and_confounding_in_timing(self):
        r = compare(snapshot(), snapshot(True), contract())
        self.assertEqual([m["status"] for m in r["metrics"]], ["comparable_within_contract", "confounded"])
        self.assertEqual(r["metrics"][0]["percent_change"], "-10.0")
        self.assertEqual(r["metrics"][1]["delta"], "0.6")
        self.assertIsNone(r["metrics"][1]["percent_change"])

    def test_corner_difference_is_confounder(self):
        self.b["metrics"][1]["conditions"]["corner_ref"] = condition("different-view")
        self.assertEqual(self.audit()["metrics"][1]["confounders"], ["corner_ref"])

    def test_intentional_cross_library_and_derived_netlist(self):
        for m in self.b["metrics"]:
            m["conditions"].update(library_ref=condition("library:L2"), netlist_ref=condition("netlist:L2"))
        for c in self.p["metrics"]:
            c["rules"]["library_ref"] = rule("intended", "Compare technology-library implementations")
            c["rules"]["netlist_ref"] = rule("derived", "Mapping changes with library", ["library_ref"])
        self.assertEqual(self.audit()["status"], "comparable_within_contract")

    def test_evidence_backed_equivalence_is_local_and_pair_bound(self):
        self.b["metrics"][0]["conditions"]["corner_ref"] = condition("local:slow-alias")
        self.p["metrics"][0]["equivalences"] = [{"field": "corner_ref", "baseline": "analysis-view:slow", "current": "local:slow-alias", "evidence_ref": "review:characterization-equivalence"}]
        self.assertEqual(self.audit()["status"], "comparable_within_contract")
        self.p["metrics"][0]["equivalences"][0]["current"] = "wrong"
        with self.assertRaises(InputError): self.audit()

    def test_missing_evidence_does_not_mean_equal(self):
        self.b["metrics"][0]["conditions"]["library_ref"]["evidence_ref"] = None
        self.assertEqual(self.audit()["metrics"][0]["status"], "incomplete")

    def test_irrelevant_activity_change_does_not_reject_area(self):
        for metric in self.a["metrics"]: metric["conditions"]["activity_source_ref"] = condition("saif:A")
        for metric in self.b["metrics"]: metric["conditions"]["activity_source_ref"] = condition("saif:B")
        for c in self.p["metrics"]: c["rules"]["activity_source_ref"] = rule("irrelevant", "This fixed-netlist static measurement does not use activity")
        self.assertEqual(self.audit()["status"], "comparable_within_contract")

    def test_power_needs_inspectable_activity_basis(self):
        self.a["metrics"] = [power_metric()]; self.b["metrics"] = [power_metric(0.09)]
        self.p["metrics"] = [{"id": "total_power", "claim": "Compare reported estimates.", "rules": {k: rule("fixed") for k in self.a["metrics"][0]["conditions"]}}]
        self.assertEqual(self.audit()["metrics"][0]["percent_change"], "-10.0")
        self.b["metrics"][0]["conditions"]["activity_source_ref"] = condition("saif:B")
        self.assertEqual(self.audit()["status"], "confounded")
        self.b["metrics"][0]["conditions"]["annotated_fraction"] = {"value": None, "evidence_ref": None}
        self.assertEqual(self.audit()["status"], "incomplete")

    def test_power_unknowns_cannot_be_hidden_as_irrelevant(self):
        self.a["metrics"] = [power_metric()]; self.b["metrics"] = [power_metric()]
        self.p["metrics"] = [{"id": "total_power", "claim": "A limited estimate comparison", "rules": {k: rule("fixed") for k in self.a["metrics"][0]["conditions"]}}]
        self.b["metrics"][0]["conditions"]["activity_mapping_ref"] = condition(None)
        self.p["metrics"][0]["rules"]["activity_mapping_ref"] = rule("irrelevant")
        self.assertEqual(self.audit()["status"], "incomplete")

    def test_supported_unit_conversion(self):
        self.b["metrics"][1].update(value=-400, unit="ps")
        self.assertEqual(Decimal(self.audit()["metrics"][1]["delta"]), 0)
        self.b["metrics"][0].update(value=0.001, unit="mm2")
        self.assertEqual(float(self.audit()["metrics"][0]["delta"]), 0)

    def test_missing_or_unrecognized_units_are_incomplete(self):
        self.b["metrics"][1]["unit"] = None
        self.assertEqual(self.audit()["metrics"][1]["status"], "incomplete")
        self.b["metrics"][1]["unit"] = "library-units"
        self.assertIsNone(self.audit()["metrics"][1]["delta"])

    def test_unknown_metric_value_not_zero(self):
        self.b["metrics"][0]["value"] = None
        r = self.audit()["metrics"][0]
        self.assertIsNone(r["delta"]); self.assertEqual(r["status"], "incomplete")

    def test_definition_or_scope_difference_blocks_arithmetic(self):
        for key in ("definition_ref", "scope_ref", "kind"):
            with self.subTest(key=key):
                b = copy.deepcopy(self.b); b["metrics"][0][key] = "die_area" if key == "kind" else "different"
                self.assertIsNone(compare(self.a, b, self.p)["metrics"][0]["delta"])

    def test_unclassified_change_and_missing_required_role(self):
        self.b["metrics"][0]["conditions"]["new-setting"] = condition(1)
        self.assertEqual(self.audit()["status"], "incomplete")
        self.a["metrics"][0]["conditions"]["new-setting"] = condition(1)
        self.assertEqual(self.audit()["status"], "comparable_within_contract")
        del self.p["metrics"][0]["rules"]["corner_ref"]
        self.assertEqual(self.audit()["status"], "incomplete")

    def test_derived_change_without_changed_parent_is_unresolved(self):
        self.b["metrics"][0]["conditions"]["netlist_ref"] = condition("different")
        self.p["metrics"][0]["rules"]["netlist_ref"] = rule("derived", parents=["rtl_ref"])
        self.assertEqual(self.audit()["status"], "incomplete")

    def test_derived_cycle_is_invalid(self):
        self.p["metrics"][0]["rules"].update(netlist_ref=rule("derived", parents=["rtl_ref"]), rtl_ref=rule("derived", parents=["netlist_ref"]))
        with self.assertRaises(InputError): self.audit()

    def test_equivalent_alias_does_not_explain_a_changed_derived_netlist(self):
        self.b["metrics"][0]["conditions"].update(corner_ref=condition("alias"), netlist_ref=condition("changed-netlist"))
        self.p["metrics"][0]["rules"]["netlist_ref"] = rule("derived", parents=["corner_ref"])
        self.p["metrics"][0]["equivalences"] = [{"field": "corner_ref", "baseline": "analysis-view:slow", "current": "alias", "evidence_ref": "review:alias"}]
        self.assertEqual(self.audit()["metrics"][0]["status"], "incomplete")

    def test_missing_selected_metric_and_unselected_metrics_are_visible(self):
        self.b["metrics"] = self.b["metrics"][:1]
        self.assertEqual(self.audit()["metrics"][1]["status"], "incomplete")
        self.p["metrics"] = self.p["metrics"][:1]
        self.assertEqual(self.audit()["unselected_metrics"], ["setup_slack"])

    def test_same_source_ref_does_not_mean_independent_run(self):
        self.b["source_ref"] = self.a["source_ref"]
        r = self.audit()
        self.assertFalse(r["same_snapshot"]); self.assertTrue(r["same_source_ref"])
        self.assertIn("different labels do not establish", markdown(r))

    def test_annotation_fraction_and_identity_types(self):
        for value in (True, -0.1, 1.1):
            b = copy.deepcopy(self.b); b["metrics"][0]["conditions"]["annotated_fraction"] = condition(value)
            with self.assertRaises(InputError): compare(self.a,b,self.p)
        self.b["metrics"][0]["conditions"]["netlist_ref"] = condition(False)
        with self.assertRaises(InputError): self.audit()

    def test_invalid_numbers_and_run_binding(self):
        for value in (True, float("nan"), -1):
            b = copy.deepcopy(self.b); b["metrics"][0]["value"] = value
            with self.assertRaises(InputError): compare(self.a, b, self.p)
        self.p["current_run_id"] = "stale-run"
        with self.assertRaises(InputError): self.audit()

    def test_zero_baseline_and_incomplete_precedence(self):
        self.a["metrics"][0]["value"] = 0
        self.assertIsNone(self.audit()["metrics"][0]["percent_change"])
        self.b["metrics"][0]["conditions"]["corner_ref"] = condition("different")
        self.b["metrics"][1]["measurement_complete"] = False
        r = self.audit(); self.assertTrue(r["confounders_found"]); self.assertEqual(r["status"], "incomplete")

    def test_html_escape_and_same_capture_limit(self):
        self.p["current_run_id"] = self.a["run_id"]
        self.p["metrics"][0]["claim"] = "<script>claim</script>"
        report = compare(self.a, self.a, self.p)
        self.assertTrue(report["same_snapshot"])
        self.assertNotIn("<script>", markdown(report))


class NativeReaderTests(unittest.TestCase):
    def fixture(self, path):
        data = {"run__flow__metrics_version": "Metrics_2.1.2", "run__flow__uuid": "native:run", "run__flow__openroad_version": "native-tool-version",
                "run__flow__scripts_commit": "flow:revision", "run__flow__design": "example", "run__flow__platform": "example-platform",
                "run__flow__platform__time_units": "1ns", "run__flow__platform__power_units": "1nW", "constraints__clocks__details": ["clk: 10"],
                "finish__design__instance__area__stdcell": 1000, "finish__timing__setup__ws": -0.4}
        path.write_text(json.dumps(data), encoding="utf-8"); return data

    def test_native_values_preserved_units_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"metadata.json"; self.fixture(path)
            inv = inspect(path.parent); ctx = context_template(inv)
            snapshot_ = import_metadata(path, ctx, tmp)
            self.assertEqual([m["value"] for m in snapshot_["metrics"]], [1000, -0.4])
            self.assertTrue(all(m["unit"] is None for m in snapshot_["metrics"]))
            self.assertEqual(snapshot_["provenance"]["platform_unit_labels"]["run__flow__platform__power_units"], "1nW")

    def test_digest_and_native_override_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"metadata.json"; self.fixture(path); ctx = context_template(inspect(path))
            ctx["metadata_sha256"] = "0"*64
            with self.assertRaises(InputError): import_metadata(path, ctx, tmp)
            ctx = context_template(inspect(path)); ctx["conditions"]["tool_ref"] = condition("invented")
            with self.assertRaises(InputError): import_metadata(path, ctx, tmp)

    def test_declared_artifacts_hash_exact_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); path=tmp/"metadata.json"; self.fixture(path); ctx=context_template(inspect(path))
            (tmp/"final.sdc").write_bytes(b"clock-configuration\n")
            del ctx["conditions"]["constraints_ref"]; ctx["artifacts"]["constraints_ref"] = "final.sdc"
            result=import_metadata(path, ctx, tmp)
            self.assertEqual(result["metrics"][0]["conditions"]["constraints_ref"]["value"], "sha256:"+hashlib.sha256(b"clock-configuration\n").hexdigest())

    def test_nonfinite_or_error_native_metric_becomes_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"metadata.json"; data=self.fixture(path); data["finish__timing__setup__ws"] = float("inf")
            path.write_text(json.dumps(data)); snapshot_=import_metadata(path,context_template(inspect(path)),tmp)
            self.assertIsNone(snapshot_["metrics"][1]["value"])
            json.dumps(snapshot_,allow_nan=False)

    def test_wrong_version_and_unsupported_power_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"metadata.json"; data=self.fixture(path); ctx=context_template(inspect(path));ctx["metrics"][0]["key"]="finish__power__total"
            with self.assertRaises(InputError): import_metadata(path,ctx,tmp)
            data["run__flow__metrics_version"]="unknown";path.write_text(json.dumps(data))
            with self.assertRaises(InputError): inspect(path)

    @unittest.skipUnless(os.environ.get("OPENTOOLS_ORFS_METADATA"), "Set OPENTOOLS_ORFS_METADATA to the documented pinned native metadata file")
    def test_real_historical_orfs_artifact(self):
        path=Path(os.environ["OPENTOOLS_ORFS_METADATA"])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), "26fee48996075b7ecfe43805d9da105b209d082991fa4dd24cb2f859bab79e86")
        inv=inspect(path); ctx=context_template(inv); snapshot_=import_metadata(path,ctx,path.parent)
        values={m["kind"]:m["value"] for m in snapshot_["metrics"]}
        self.assertEqual(values["stdcell_area"],174960);self.assertEqual(values["setup_slack"],0.333871)
        self.assertEqual(snapshot_["provenance"]["native_run_id"],"5826cc6e-b52b-4382-a43b-c44fe8e8a546")
        self.assertTrue(all(m["unit"] is None for m in snapshot_["metrics"]))


class CliTests(unittest.TestCase):
    def test_duplicate_contract_role_cannot_silently_replace_intent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"duplicate.json"
            path.write_text('{"rules":{"clock":{"role":"fixed","role":"intended"}}}',encoding="utf-8")
            with self.assertRaises(InputError): read_json(path)

    def test_comparison_and_intake_exit_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); a,b,p=controls();paths=[tmp/(name+".json") for name in ("a","b","p")]
            def write_inputs():
                for path,value in zip(paths,(a,b,p)):path.write_text(json.dumps(value),encoding="utf-8")
            base=[sys.executable,str(MODULE/"ppa_check.py")];write_inputs()
            command=base+["compare",*map(str,paths)]
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)
            b["metrics"][0]["conditions"]["corner_ref"]=condition("different");write_inputs()
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,1)
            b["metrics"][1]["unit_evidence"]=None;write_inputs()
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,2)
            result=subprocess.run(command+["--json-out",str(tmp/"audit.json")],capture_output=True);self.assertEqual(result.returncode,2)
            self.assertEqual(subprocess.run(command+["--json-out",str(tmp/"audit.json")],capture_output=True).returncode,3)
            meta=tmp/"metadata.json";NativeReaderTests().fixture(meta)
            r=subprocess.run(base+["inspect-orfs",str(meta),"--output",str(tmp/"inventory.json"),"--context-template",str(tmp/"context.json")],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
            r=subprocess.run(base+["import-orfs",str(meta),"--context",str(tmp/"context.json"),"--output",str(tmp/"snapshot.json")],capture_output=True,text=True);self.assertEqual(r.returncode,2,r.stderr)


if __name__ == "__main__": unittest.main()
