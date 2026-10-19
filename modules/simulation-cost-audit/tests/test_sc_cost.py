import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
from cost_core import InputError, analyze
from sc_cost_import import context_template, import_manifest, inspect_manifest


def leaf(value, pernode="never", step="*", index="*"):
    return {"type": "str", "pernode": pernode, "node": {step: {index: {"value": value}}}}


def fixture():
    values = {"starttime": "2026-01-01 00:00:00.000000", "endtime": "2026-01-01 00:00:10.000000",
              "status": "success", "toolexitcode": 0, "scversion": "0.38.11", "toolversion": "5.020", "toolpath": "/synthetic/verilator", "machine": None}
    metrics = {"exetime": (8.5, "s"), "tasktime": (10, "s"), "totaltime": (10, "s"), "memory": (1024, "B")}
    return {"__meta__": {"class": "siliconcompiler.project/Project"}, "schemaversion": leaf("0.57.2"),
            "option": {"design": leaf("top"), "flow": leaf("lintflow"), "jobname": leaf("job0")},
            "record": {key: leaf(value, "required", "lint", "0") for key, value in values.items()},
            "metric": {key: {**leaf(value, "required", "lint", "0"), "unit": unit} for key, (value, unit) in metrics.items()}}


class NativeCostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / "native.pkg.json"
        self.context_path = self.root / "context.json"
        self.document = fixture()
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.document), encoding="utf-8")

    def context(self):
        context = context_template(inspect_manifest(self.manifest))
        context.update(clock_ref="synthetic:single-host-recorded-UTC", clock_evidence_ref="synthetic:clock-basis", scope_ref="selected-node:lint")
        context["collection"] = {"complete": True, "evidence_ref": "synthetic:all-selected-node-records"}
        return context

    def load(self, context):
        self.context_path.write_text(json.dumps(context), encoding="utf-8")
        return import_manifest(self.manifest, self.context_path)

    def test_native_elapsed_observations_not_cpu_and_not_added(self):
        run = self.load(self.context())
        report = analyze(run)
        self.assertEqual(report["status"], "accounted_window")
        self.assertEqual(report["window_wall_s"], "10.0")
        self.assertEqual([r["kind"] for r in report["resource_observations"]], ["elapsed_time", "elapsed_time", "elapsed_time", "peak_memory"])
        self.assertIn("cpu_time", report["unmeasured_quantities"])
        self.assertEqual(run["completion"]["outcome"], "completed")
        self.assertIsNone(run["completion"]["required_evidence_complete"])

    def test_template_preserves_unknown_clock_and_scope(self):
        context = context_template(inspect_manifest(self.manifest))
        report = analyze(self.load(context))
        self.assertIsNone(report["window_wall_s"])
        self.assertEqual(report["status"], "partial_accounting")

    def test_unfinished_or_absent_selected_node_no_false_total(self):
        self.document["record"]["endtime"]["node"]["lint"]["0"]["value"] = None
        self.save()
        run = self.load(self.context())
        self.assertIsNone(analyze(run)["window_wall_s"])
        context = self.context()
        context["nodes"].append({"step": "missing", "index": "0", "stage": "simulate", "accounting": "stage"})
        run = self.load(context)
        self.assertEqual(run["completion"]["outcome"], "unknown")
        self.assertIsNone(run["phases"][1]["start_s"])

    def test_native_failed_execution_costs_retained(self):
        self.document["record"]["status"]["node"]["lint"]["0"]["value"] = "error"
        self.document["record"]["toolexitcode"]["node"]["lint"]["0"]["value"] = 1
        self.save()
        run = self.load(self.context())
        self.assertEqual(run["completion"]["outcome"], "failed")
        self.assertEqual(analyze(run)["status"], "accounted_window")

    def test_digest_duplicate_selection_and_native_outcome_override_guards(self):
        context = self.context(); context["manifest_sha256"] = "0" * 64
        with self.assertRaises(InputError):
            self.load(context)
        context = self.context(); context["nodes"] *= 2
        with self.assertRaises(InputError):
            self.load(context)
        context = self.context(); context["completion"]["outcome"] = "completed"
        with self.assertRaises(InputError):
            self.load(context)

    def test_unknown_native_units_remain_unknown_and_history_not_searched(self):
        self.document["metric"]["memory"]["unit"] = None
        self.save()
        report = analyze(self.load(self.context()))
        self.assertIsNone(report["resource_observations"][3]["normalized_value"])
        self.document["history"] = {"old": copy.deepcopy(self.document)}
        for record in self.document["record"].values():
            record["node"] = {"default": {"default": {"value": None}}}
        self.save()
        self.assertEqual(inspect_manifest(self.manifest)["nodes"], [])
        self.assertIsNone(analyze(self.load(self.context()))["window_wall_s"])

    def test_wrong_version_reverse_clock_and_invalid_metric_rejected(self):
        documents = []
        doc = fixture(); doc["schemaversion"] = leaf("future"); documents.append(doc)
        doc = fixture(); doc["record"]["scversion"] = leaf("other", "required", "lint", "0"); documents.append(doc)
        doc = fixture(); doc["record"]["endtime"] = leaf("2025-01-01 00:00:00.000000", "required", "lint", "0"); documents.append(doc)
        doc = fixture(); doc["metric"]["exetime"]["node"]["lint"]["0"]["value"] = True; documents.append(doc)
        for doc in documents:
            self.document = doc; self.save()
            with self.subTest(doc=doc), self.assertRaises(InputError):
                inspect_manifest(self.manifest)

    def test_native_cli_template_import_partial(self):
        command = [sys.executable, str(MODULE / "cost_audit.py")]
        p = subprocess.run(command + ["inspect-sc", str(self.manifest), "--output", str(self.root / "inventory.json"), "--context-template", str(self.context_path)], capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        p = subprocess.run(command + ["import-sc", str(self.manifest), "--context", str(self.context_path), "--output", str(self.root / "run.json")], capture_output=True)
        self.assertEqual(p.returncode, 2, p.stderr)

    @unittest.skipUnless(os.environ.get("OPENTOOLS_SC_MANIFEST"), "Set OPENTOOLS_SC_MANIFEST to an actual qualified job manifest")
    def test_actual_native_records_against_sc_api_and_independent_datetime(self):
        from datetime import datetime
        from siliconcompiler import Project
        path = Path(os.environ["OPENTOOLS_SC_MANIFEST"])
        info = inspect_manifest(path)
        project = Project.from_manifest(str(path))
        node = next(n for n in info["nodes"] if n["step"] == "lint" and n["index"] == "0")
        for name, metric in node["metrics"].items():
            self.assertEqual(metric["value"], project.get("metric", name, step="lint", index="0"))
            self.assertEqual(metric["unit"], project.get("metric", name, field="unit"))
        context = context_template(info)
        context.update(clock_ref="control:single-host-UTC", clock_evidence_ref="retained-single-host-control", scope_ref="selected-lint-node")
        context["collection"] = {"complete": True, "evidence_ref": "retained-native-node-population"}
        self.context_path.write_text(json.dumps(context))
        report = analyze(import_manifest(path, self.context_path))
        start = datetime.strptime(project.get("record", "starttime", step="lint", index="0"), "%Y-%m-%d %H:%M:%S.%f")
        end = datetime.strptime(project.get("record", "endtime", step="lint", index="0"), "%Y-%m-%d %H:%M:%S.%f")
        self.assertAlmostEqual(float(report["window_wall_s"]), (end-start).total_seconds(), places=9)
        self.assertEqual(report["status"], "accounted_window")
        self.assertIn("cpu_time", report["unmeasured_quantities"])


if __name__ == "__main__":
    unittest.main()
