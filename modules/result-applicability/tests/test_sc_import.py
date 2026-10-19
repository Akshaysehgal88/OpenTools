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
from applicability_core import InputError, file_hash
from sc_import import context_template, import_manifest, inspect_manifest, pointer


def leaf(value, pernode="never", step="*", index="*"):
    return {"type": "str", "pernode": pernode, "node": {step: {index: {"value": value}}}}


def native_fixture():
    fields = {"status": "success", "toolexitcode": 0, "toolpath": "/synthetic/verilator",
              "toolargs": "--lint-only top.sv", "toolversion": "5.020", "scversion": "0.38.11",
              "starttime": "2026-01-01 00:00:00.000000", "endtime": "2026-01-01 00:00:01.000000"}
    return {"__meta__": {"class": "siliconcompiler.project/Project"}, "schemaversion": leaf("0.57.2"),
            "option": {"design": leaf("top"), "flow": leaf("lintflow"), "jobname": leaf("job0")},
            "record": {key: leaf(value, "required", "lint", "0") for key, value in fields.items()},
            "library": {"top": {"fileset": {"rtl": {"param": {"ECC_EN": leaf("0")}}}}}}


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / "native.pkg.json"
        self.document = native_fixture()
        self.save()
        self.context = self.root / "context.json"
        self.output = self.root / "snapshot.json"

    def save(self):
        self.manifest.write_text(json.dumps(self.document), encoding="utf-8")

    def prepare(self):
        inventory = inspect_manifest(self.manifest, "lint", "0")
        context = context_template(inventory)
        context["selectors"]["configuration.ECC_EN"] = "/library/top/fileset/rtl/param/ECC_EN/node/*/*/value"
        return context

    def import_context(self, context):
        self.context.write_text(json.dumps(context), encoding="utf-8")
        return import_manifest(self.manifest, self.context, self.output)

    def test_native_success_not_automatically_a_test_pass(self):
        record = self.import_context(self.prepare())
        self.assertEqual(record["execution"]["state"], "completed")
        self.assertEqual(record["result"]["outcome"], "unknown")
        self.assertIsNone(record["execution"]["dependency_capture_complete"])
        self.assertIsNone(record["execution"]["executable_ref"])
        self.assertEqual(record["fields"]["configuration.ECC_EN"]["value"], "0")

    def test_exact_node_selection_no_history_or_default_fallback(self):
        inventory = inspect_manifest(self.manifest, "lint", "1")
        self.assertIsNone(inventory["fields"]["sc.status"]["value"])
        self.document["history"] = {"old": copy.deepcopy(self.document)}
        self.document["record"] = {}
        self.save()
        self.assertIsNone(inspect_manifest(self.manifest, "lint", "0")["fields"]["sc.status"]["value"])
        with self.assertRaises(InputError):
            inspect_manifest(self.manifest, "default", "0")

    def test_required_native_basis_not_inferred_from_one_status(self):
        for key in ("toolexitcode", "starttime", "endtime", "scversion"):
            with self.subTest(key=key):
                document = native_fixture()
                document["record"][key]["node"]["lint"]["0"]["value"] = None
                self.document = document; self.save()
                self.assertEqual(self.import_context(self.prepare())["execution"]["state"], "unknown")

    def test_manifest_context_and_native_override_guards(self):
        context = self.prepare()
        context["manifest_sha256"] = "0" * 64
        with self.assertRaises(InputError):
            self.import_context(context)
        context = self.prepare()
        context["fields"]["sc.status"] = {"value": "success", "evidence_ref": "invented"}
        with self.assertRaises(InputError):
            self.import_context(context)
        context = self.prepare()
        context["execution"]["state"] = "completed"
        with self.assertRaises(InputError):
            self.import_context(context)

    def test_result_artifact_identity_and_output_relative_path(self):
        context = self.prepare()
        result_file = self.root / "lint.log"
        result_file.write_text("synthetic checker result")
        context["result"]["artifact"] = {"path": "lint.log", "sha256": file_hash(result_file)}
        self.assertEqual(self.import_context(context)["result"]["artifact"]["path"], "lint.log")
        result_file.write_text("stale copied report")
        with self.assertRaises(InputError):
            self.import_context(context)

    def test_selectors_missing_paths_and_escape_rules(self):
        context = self.prepare()
        context["selectors"]["firmware.ref"] = "/library/top/missing/firmware"
        self.assertIsNone(self.import_context(context)["fields"]["firmware.ref"]["value"])
        self.assertEqual(pointer({"a/b": {"~key": [7]}}, "/a~1b/~0key/0"), 7)
        for path in ("relative", "/bad~escape", "/x/01"):
            with self.subTest(path=path), self.assertRaises(InputError):
                pointer({"x": [1]}, path)

    def test_unqualified_versions_types_and_project_class_rejected(self):
        documents = []
        document = native_fixture(); document["__meta__"]["class"] = "arbitrary/module"; documents.append(document)
        document = native_fixture(); document["__meta__"] = None; documents.append(document)
        document = native_fixture(); document["schemaversion"] = leaf("future"); documents.append(document)
        document = native_fixture(); document["schemaversion"]["node"] = None; documents.append(document)
        document = native_fixture(); document["record"]["scversion"] = leaf("other", "required", "lint", "0"); documents.append(document)
        document = native_fixture(); document["record"]["toolexitcode"] = leaf(False, "required", "lint", "0"); documents.append(document)
        for document in documents:
            self.document = document; self.save()
            with self.subTest(document=document), self.assertRaises(InputError):
                inspect_manifest(self.manifest, "lint", "0")

    def test_inspect_and_import_cli(self):
        inventory = self.root / "inventory.json"
        command = [sys.executable, str(MODULE / "applicability_check.py")]
        proc = subprocess.run(command + ["inspect-sc", str(self.manifest), "--step", "lint", "--index", "0", "--output", str(inventory), "--context-template", str(self.context)], capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = subprocess.run(command + ["import-sc", str(self.manifest), "--context", str(self.context), "--output", str(self.output)], capture_output=True)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertEqual(json.loads(self.output.read_text())["result"]["outcome"], "unknown")

    @unittest.skipUnless(os.environ.get("OPENTOOLS_SC_MANIFEST"), "Set OPENTOOLS_SC_MANIFEST to a real qualified lint job manifest")
    def test_real_native_manifest_matches_independent_sc_api(self):
        path = Path(os.environ["OPENTOOLS_SC_MANIFEST"])
        inventory = inspect_manifest(path, "lint", "0")
        from siliconcompiler import Project
        project = Project.from_manifest(str(path))
        for name in ("status", "toolexitcode", "toolargs", "toolversion", "scversion", "starttime", "endtime"):
            self.assertEqual(inventory["fields"]["sc." + name]["value"], project.get("record", name, step="lint", index="0"))
        self.assertEqual(inventory["fields"]["sc.status"]["value"], "success")
        document = json.loads(path.read_text())
        location = "/library/top/fileset/rtl/param/ECC_EN/node/*/*/value"
        self.assertEqual(pointer(document, location), project.design.get("fileset", "rtl", "param", "ECC_EN"))
        self.assertEqual(pointer(document, location), "0")
        self.assertTrue(pointer(document, "/library/top/fileset/rtl/file/systemverilog/node/*/*/filehash/0"))


if __name__ == "__main__":
    unittest.main()
