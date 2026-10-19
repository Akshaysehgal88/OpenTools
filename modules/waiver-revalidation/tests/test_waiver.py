"""Behavioral and CLI tests, plus optional native Verilator integration."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
from waiver_core import InputError, compare, markdown, read_json
from verilator_capture import capture, parse_diagnostics, validate_waiver_file


def finding(identifier="f1", obj="rtl/top.sv:3:9", message="Signal is not used: 'unused_a'"):
    return {"id": identifier, "object": obj, "rule": "UNUSEDSIGNAL", "message": message,
            "evidence_ref": "native:without-waiver.log"}


def snapshot(run_id="A", findings=None):
    return {"format": "opentools.waiver-snapshot.v1", "run_id": run_id,
            "scope": "example/soc", "configuration_ref": "config:" + run_id,
            "configuration": {"DEBUG_EN": 0, "UNRELATED": 0},
            "tool": {"name": "verilator", "version": "5.020", "ruleset": "Wall"},
            "identity_basis": "native-rule-location-header.v1", "population_complete": True,
            "waivers": [{"id": "debug", "definition_sha256": "a" * 64,
                         "complete": True, "findings": [finding()] if findings is None else findings}]}


def policy(value=0):
    return {"format": "opentools.waiver-policy.v1", "waivers": [
        {"id": "debug", "premises": [{"key": "DEBUG_EN", "equals": value, "evidence_ref": "review:premise"}]}]}


class ComparisonTests(unittest.TestCase):
    def test_unchanged_and_irrelevant_configuration_change(self):
        old, new = snapshot(), snapshot("B")
        new["configuration"]["UNRELATED"] = 1
        self.assertEqual(compare(old, new, policy())["status"], "unchanged_within_scope")

    def test_expansion_has_original_evidence(self):
        new = snapshot("B", [finding(), finding("f2", "rtl/top.sv:4:9")])
        result = compare(snapshot(), new)
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["waivers"][0]["added"][0]["evidence_ref"], "native:without-waiver.log")

    def test_changed_premise(self):
        new = snapshot("B")
        new["configuration"]["DEBUG_EN"] = 1
        result = compare(snapshot(), new, policy())
        self.assertEqual(result["waivers"][0]["premises"][0]["outcome"], "does_not_hold")
        self.assertEqual(result["status"], "review_required")

    def test_boolean_is_not_integer(self):
        new = snapshot("B")
        new["configuration"]["DEBUG_EN"] = False
        self.assertEqual(compare(snapshot(), new, policy())["status"], "review_required")

    def test_missing_or_null_premise_is_unknown(self):
        for value in ("missing", None):
            new = snapshot("B")
            if value == "missing":
                del new["configuration"]["DEBUG_EN"]
            else:
                new["configuration"]["DEBUG_EN"] = value
            self.assertEqual(compare(snapshot(), new, policy())["status"], "incomplete")

    def test_incomplete_even_when_there_are_review_findings(self):
        old, new = snapshot(), snapshot("B", [finding(), finding("f2")])
        new["population_complete"] = False
        result = compare(old, new)
        self.assertEqual(result["status"], "incomplete")
        self.assertTrue(result["review_required"])

    def test_partial_waiver_does_not_look_unchanged(self):
        new = snapshot("B")
        new["waivers"][0]["complete"] = False
        self.assertEqual(compare(snapshot(), new)["status"], "incomplete")

    def test_explicit_rename_mapping_and_no_automatic_rename(self):
        old, new = snapshot(), snapshot("B", [finding("renamed", "rtl/renamed.sv:3:9")])
        self.assertEqual(compare(old, new)["status"], "review_required")
        mapping = {"format": "opentools.waiver-identity-map.v1", "mappings": [
            {"waiver_id": "debug", "from": "f1", "to": "renamed", "evidence_ref": "review:rename"}]}
        result = compare(old, new, identity_map=mapping)
        self.assertEqual(result["status"], "unchanged_within_scope")
        self.assertIn("review:rename", markdown(result))

    def test_mapping_cannot_hide_changed_meaning(self):
        old = snapshot()
        new = snapshot("B", [finding("renamed", message="Different diagnostic meaning")])
        mapping = {"format": "opentools.waiver-identity-map.v1", "mappings": [
            {"waiver_id": "debug", "from": "f1", "to": "renamed", "evidence_ref": "review:rename"}]}
        self.assertEqual(compare(old, new, identity_map=mapping)["status"], "review_required")

    def test_many_to_one_mapping_rejected(self):
        old, new = snapshot(findings=[finding(), finding("f2")]), snapshot("B")
        mapping = {"format": "opentools.waiver-identity-map.v1", "mappings": [
            {"waiver_id": "debug", "from": "f2", "to": "f1", "evidence_ref": "review:wrong"}]}
        with self.assertRaises(InputError):
            compare(old, new, identity_map=mapping)

    def test_versions_scope_rules_and_identity_must_be_comparable(self):
        for field in ("version", "ruleset", "name"):
            new = snapshot("B")
            new["tool"][field] = "changed"
            self.assertEqual(compare(snapshot(), new)["status"], "incomplete")
        new = snapshot("B")
        new["scope"] = "another-project"
        self.assertEqual(compare(snapshot(), new)["status"], "incomplete")

    def test_definition_change_and_zero_population_need_review(self):
        new = snapshot("B")
        new["waivers"][0]["definition_sha256"] = "b" * 64
        self.assertEqual(compare(snapshot(), new)["status"], "review_required")
        self.assertEqual(compare(snapshot(findings=[]), snapshot("B", []))["status"], "review_required")

    def test_configuration_basis_change_is_not_silently_equated(self):
        new = snapshot("B")
        new["configuration_basis"] = "command-line-macro-inputs"
        self.assertEqual(compare(snapshot(), new)["status"], "incomplete")

    def test_duplicate_and_untyped_completeness_rejected(self):
        new = snapshot("B", [finding(), finding()])
        with self.assertRaises(InputError):
            compare(snapshot(), new)
        new = snapshot("B")
        new["population_complete"] = "true"
        with self.assertRaises(InputError):
            compare(snapshot(), new)

    def test_absent_waiver_does_not_inherit_unchanged(self):
        new = snapshot("B")
        new["waivers"][0]["id"] = "new-waiver"
        self.assertEqual(compare(snapshot(), new)["status"], "review_required")

    def test_markdown_escapes_native_text(self):
        new = snapshot("B", [finding(), finding("f2", "a|b<script>")])
        text = markdown(compare(snapshot(), new))
        self.assertIn("&#124;", text)
        self.assertNotIn("<script>", text)

    def test_json_duplicates_and_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            for content in ('{"x":1,"x":2}', '{"x":NaN}'):
                path.write_text(content)
                with self.assertRaises(InputError):
                    read_json(path)


class AdapterTests(unittest.TestCase):
    def test_native_header_parser_and_unknown_formats(self):
        with tempfile.TemporaryDirectory() as directory:
            log = "%Warning-UNUSEDSIGNAL: top.sv:3:9: Signal is not used: 'a'\n  3 | logic a;\n"
            findings, issues = parse_diagnostics(log, directory, "native.log")
            self.assertFalse(issues)
            self.assertEqual(next(iter(findings.values()))["object"], "top.sv:3:9")
            self.assertTrue(parse_diagnostics("%Warning: malformed", directory, "native.log")[1])

    def test_control_file_rejects_nonwaiver_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "waiver.vlt"
            for command in ('`include "other.vlt"', 'public -module "*" -var "*"', 'lint_on -rule WIDTH',
                            'lint_off -rule UNUSEDSIGNAL public -module "*"',
                            'lint_off -rule WIDTH -lines 9 - 2'):
                path.write_text("`verilator_config\n" + command + "\n")
                with self.assertRaises(InputError):
                    validate_waiver_file(path)

    def test_control_selector_values_stay_native(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "waiver.vlt"
            path.write_text('`verilator_config\nlint_off -rule UNUSEDSIGNAL -file "*/some path/top.sv" -match "*spare*" -lines 2 - 9 // rationale\n')
            validate_waiver_file(path)

    def test_capture_context_difference_is_incomplete(self):
        old, new = snapshot(), snapshot("B")
        old["capture"] = {"profile": "same", "top": "top_a", "population_basis": "same"}
        new["capture"] = {"profile": "same", "top": "top_b", "population_basis": "same"}
        self.assertEqual(compare(old, new)["status"], "incomplete")


class CliTests(unittest.TestCase):
    def test_exit_codes_and_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            old_path, new_path = directory / "old.json", directory / "new.json"
            old_path.write_text(json.dumps(snapshot()))
            cases = [(snapshot("B"), 0), (snapshot("B", [finding(), finding("f2")]), 1)]
            partial = snapshot("B")
            partial["population_complete"] = False
            cases += [(partial, 2), ({}, 3)]
            for record, expected in cases:
                new_path.write_text(json.dumps(record))
                process = subprocess.run([sys.executable, str(MODULE / "waiver_revalidate.py"),
                                          "compare", str(old_path), str(new_path), "--format", "json"],
                                         capture_output=True, text=True)
                self.assertEqual(process.returncode, expected, process.stderr)
                if expected != 3:
                    self.assertEqual(json.loads(process.stdout)["format"], "opentools.waiver-audit.v1")
            new_path.write_text(json.dumps(snapshot("B")))
            report_path = directory / "report.json"
            command = [sys.executable, str(MODULE / "waiver_revalidate.py"), "compare",
                       str(old_path), str(new_path), "--json-out", str(report_path)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 3)


@unittest.skipUnless(os.environ.get("OPENTOOLS_VERILATOR"), "Set OPENTOOLS_VERILATOR to test a real Verilator 5.020 binary")
class NativeIntegrationTests(unittest.TestCase):
    def test_real_native_suppression_and_expansion(self):
        with tempfile.TemporaryDirectory(prefix="opentools native ") as directory:
            directory = Path(directory)
            source = directory / "top.sv"
            waiver = directory / "waiver.vlt"
            waiver.write_text("`verilator_config\nlint_off -rule UNUSEDSIGNAL\n")
            def collect(name, extra="", complete=True):
                source.write_text("module top(input logic clk, output logic out);\nlogic spare_a;\n" + extra + "assign out = clk;\nendmodule\n")
                return capture(executable=os.environ["OPENTOOLS_VERILATOR"], sources=[source],
                               waiver_file=waiver, waiver_id="unused", configuration={}, scope="example/top",
                               run_id=name, evidence_dir=directory / name, top="top",
                               complete_inputs=complete, cwd=directory)
            old = collect("baseline")
            self.assertTrue(old["population_complete"], old["capture"]["issues"])
            self.assertEqual(len(old["waivers"][0]["findings"]), 1, old["capture"]["invocations"])
            new = collect("current", "logic spare_b;\n")
            self.assertTrue(new["population_complete"], new["capture"]["issues"])
            result = compare(old, new)
            self.assertEqual(result["status"], "review_required")
            self.assertEqual(len(result["waivers"][0]["added"]), 1)
            self.assertEqual(compare(new, collect("unchanged", "logic spare_b;\n"))["status"], "unchanged_within_scope")
            self.assertEqual(compare(new, collect("partial", "logic spare_b;\n", False))["status"], "incomplete")

    def test_native_failure_is_retained_as_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source, waiver = directory / "top.sv", directory / "waiver.vlt"
            source.write_text("module top; deliberate syntax error endmodule\n")
            waiver.write_text("`verilator_config\nlint_off -rule UNUSEDSIGNAL\n")
            result = capture(executable=os.environ["OPENTOOLS_VERILATOR"], sources=[source],
                             waiver_file=waiver, waiver_id="unused", configuration={}, scope="example/top",
                             run_id="failed", evidence_dir=directory / "evidence", top="top",
                             complete_inputs=True, cwd=directory)
            self.assertFalse(result["population_complete"])
            self.assertTrue(result["capture"]["issues"])
            self.assertNotEqual(result["capture"]["invocations"][0]["returncode"], 0)

    def test_capture_cli_applies_configuration_and_writes_evidence(self):
        with tempfile.TemporaryDirectory(prefix="opentools cli ") as directory:
            directory = Path(directory)
            source, waiver, config = directory / "top.sv", directory / "waiver.vlt", directory / "config.json"
            source.write_text('module top(input logic clk, output logic out);\nlogic spare;\nassign out = clk;\nendmodule\n')
            waiver.write_text("`verilator_config\nlint_off -rule UNUSEDSIGNAL\n")
            config.write_text('{"DEBUG_EN":0}')
            output = directory / "snapshot.json"
            process = subprocess.run([sys.executable, str(MODULE / "waiver_revalidate.py"), "capture",
                                      "--verilator", os.environ["OPENTOOLS_VERILATOR"], "--source", str(source),
                                      "--waiver-file", str(waiver), "--waiver-id", "unused",
                                      "--configuration", str(config), "--scope", "example/top", "--run-id", "A",
                                      "--top", "top", "--complete-inputs", "--output", str(output)],
                                     cwd=directory, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            record = read_json(output)
            self.assertEqual(record["configuration"], {"DEBUG_EN": 0})
            self.assertIn("-DDEBUG_EN=0", record["capture"]["invocations"][0]["argv"])
            self.assertTrue((directory / "snapshot.evidence" / "without-waiver.log").is_file())


if __name__ == "__main__":
    unittest.main()
