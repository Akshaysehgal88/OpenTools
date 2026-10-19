import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(MODULE / "examples"))
from coverage_core import InputError, compare, markdown, read_json
from create_example import context_for, normalized, write_ucis
from ucis_import import context_template, import_xml, inspect_xml


def categories(report):
    return [c["category"] for c in report["changes"]]


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.a = normalized()
        self.b = copy.deepcopy(self.a)
        self.b["run_id"] = "current"

    def audit(self):
        return compare(self.a, self.b)

    def test_unchanged(self):
        report = self.audit()
        self.assertEqual(report["status"], "unchanged_within_scope")
        self.assertEqual(report["changes"], [])

    def test_exclusion_only_180_200_to_180_180(self):
        report = compare(self.a, normalized(True))
        a, b = report["points"][0]["baseline"], report["points"][0]["current"]
        self.assertEqual((a["covered_bins"], a["applicable_bins"], a["bin_fraction_percent"]), (180, 200, 90))
        self.assertEqual((b["covered_bins"], b["applicable_bins"], b["bin_fraction_percent"]), (180, 180, 100))
        self.assertEqual(b["descriptive_population_bins"], 200)
        self.assertEqual(report["progress"]["newly_hit"], 0)
        self.assertEqual(categories(report).count("bin_kind_changed"), 20)

    def test_true_new_hit(self):
        self.b["points"][0]["bins"][180]["count"] = 1
        self.assertEqual(self.audit()["progress"]["newly_hit"], 1)
        self.assertEqual(self.audit()["progress"]["newly_satisfied"], 1)

    def test_same_name_changed_range_is_not_new_hit(self):
        self.b["points"][0]["bins"][180].update(count=1, definition="opcode in [180:190]")
        report = self.audit()
        self.assertIn("bin_definition_changed", categories(report))
        self.assertEqual(report["progress"]["newly_hit"], 0)

    def test_changed_sampling_is_not_new_hit(self):
        self.b["points"][0]["definition"] = "opcode iff different_enable"
        self.b["points"][0]["bins"][180]["count"] = 1
        self.assertEqual(self.audit()["progress"]["newly_hit"], 0)
        self.assertIn("point_definition_changed", categories(self.audit()))

    def test_missing_definitions_are_unknown(self):
        self.a["points"][0]["bins"][180]["definition"] = None
        self.b["points"][0]["bins"][180]["count"] = 1
        report = self.audit()
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["progress"]["newly_hit"], 0)

    def test_threshold_can_increase_score_without_hits(self):
        self.a["points"][0]["at_least"] = 2
        report = self.audit()
        self.assertEqual(report["progress"]["newly_hit"], 0)
        self.assertEqual(report["progress"]["newly_satisfied"], 180)
        self.assertIn("at_least_changed", categories(report))

    def test_threshold_new_hit_not_satisfied(self):
        self.a["points"][0]["at_least"] = self.b["points"][0]["at_least"] = 2
        self.b["points"][0]["bins"][180]["count"] = 1
        self.assertEqual(self.audit()["progress"]["newly_hit"], 1)
        self.assertEqual(self.audit()["progress"]["newly_satisfied"], 0)

    def test_weights_goals_do_not_change_bin_fraction(self):
        self.b["points"][0].update(weight=0, goal=50)
        report = self.audit()
        self.assertEqual(report["points"][0]["current"]["bin_fraction_percent"], 90)
        self.assertIn("weight_changed", categories(report))
        self.assertIn("goal_changed", categories(report))

    def test_partial_absence_is_not_removed(self):
        self.b["population_complete"] = False
        self.b["points"][0]["bins"].pop()
        report = self.audit()
        self.assertEqual(report["status"], "incomplete")
        self.assertIn("bin_not_observed_in_current", categories(report))
        self.assertNotIn("bin_removed", categories(report))

    def test_complete_removal_and_addition(self):
        self.b["points"][0]["bins"][-1]["id"] = "different"
        report = self.audit()
        self.assertIn("bin_removed", categories(report))
        self.assertIn("bin_added", categories(report))

    def test_rename_requires_explicit_map(self):
        self.b["points"][0]["bins"][-1].update(id="renamed", count=1)
        mapping = {"format": "opentools.coverage-map.v1", "baseline_run_id": "baseline", "current_run_id": "current",
                   "mappings": [{"point_id": self.a["points"][0]["id"], "from": "b199", "to": "renamed", "evidence_ref": "review#42"}]}
        self.assertEqual(self.audit()["progress"]["newly_hit"], 0)
        report = compare(self.a, self.b, mapping)
        self.assertIn("bin_renamed", categories(report))
        self.assertEqual(report["progress"]["newly_hit"], 1)
        mapping["mappings"][0]["to"] = "b198"
        with self.assertRaises(InputError):
            compare(self.a, self.b, mapping)

    def test_mapping_cannot_hide_changed_definition(self):
        self.b["points"][0]["bins"][-1].update(id="renamed", count=1, definition="different")
        mapping = {"format": "opentools.coverage-map.v1", "baseline_run_id": "baseline", "current_run_id": "current",
                   "mappings": [{"point_id": self.a["points"][0]["id"], "from": "b199", "to": "renamed", "evidence_ref": "review#42"}]}
        self.assertEqual(compare(self.a, self.b, mapping)["progress"]["newly_hit"], 0)

    def test_context_difference_is_not_progress(self):
        self.b["configuration_ref"] = "different"
        self.b["points"][0]["bins"][-1]["count"] = 1
        report = self.audit()
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["progress"]["newly_hit"], 0)

    def test_illegal_hits_are_separate(self):
        self.a["points"][0]["bins"][-1]["kind"] = "illegal"
        self.b["points"][0]["bins"][-1].update(kind="illegal", count=8)
        report = self.audit()
        self.assertEqual(report["points"][0]["current"]["illegal_hits"], 8)
        self.assertIn("illegal_bin_hit", categories(report))
        self.assertEqual(report["progress"]["newly_hit"], 0)

    def test_empty_denominator_is_undefined(self):
        for snapshot in (self.a, self.b):
            for bin_ in snapshot["points"][0]["bins"]:
                bin_["kind"] = "ignore"
        self.assertIsNone(self.audit()["points"][0]["current"]["bin_fraction_percent"])

    def test_reject_invalid_counts_ids_and_unsupported_weight(self):
        for update in ({"count": True}, {"count": -1}, {"weight": 2}, {"id": "b000"}):
            with self.subTest(update=update):
                invalid = copy.deepcopy(self.b)
                invalid["points"][0]["bins"][-1].update(update)
                with self.assertRaises(InputError):
                    compare(self.a, invalid)

    def test_markdown_escapes_evidence(self):
        self.b["points"][0]["bins"][-1]["count"] = 1
        self.b["points"][0]["bins"][-1]["evidence_ref"] = "report|line\n42"
        rendered = markdown(self.audit())
        self.assertIn("report\\|line 42", rendered)
        self.assertIn("## Unresolved correspondence", rendered)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text('{"x":1,"x":2}', encoding="utf-8")
            with self.assertRaises(InputError):
                read_json(p)


class CliTests(unittest.TestCase):
    def test_executable_reports_exit_codes_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            a, b, out = (tmp / name for name in ("a.json", "b.json", "report.json"))
            a.write_text(json.dumps(normalized()), encoding="utf-8")
            b.write_text(json.dumps(normalized(True)), encoding="utf-8")
            command = [sys.executable, str(MODULE / "coverage_audit.py"), "compare", str(a), str(b), "--json-out", str(out)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(read_json(out)["progress"]["newly_hit"], 0)
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 3)
            command = command[:-2]
            command[4] = str(a)
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            incomplete = normalized(); incomplete["population_complete"] = False
            b.write_text(json.dumps(incomplete), encoding="utf-8")
            command[4] = str(b)
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)


@unittest.skipUnless(importlib.util.find_spec("ucis"), "Optional PyUCIS integration dependency is not installed")
class NativeXmlTests(unittest.TestCase):
    def test_real_reader_exclusions_and_instance_separation(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.xml", Path(tmp) / "b.xml"
            write_ucis(a, instances=2); write_ucis(b, True, instances=2)
            before, after = import_xml(a, context_for(a)), import_xml(b, context_for(b, True))
            report = compare(before, after)
            self.assertEqual(len(report["points"]), 2)
            self.assertEqual(len({p["id"] for p in before["points"]}), 2)
            self.assertTrue(all(p["current"]["bin_fraction_percent"] == 100 for p in report["points"]))
            self.assertEqual(report["progress"]["newly_hit"], 0)
            self.assertEqual(categories(report).count("bin_kind_changed"), 40)

    def test_unknown_native_definitions_cannot_claim_equivalence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.xml"; write_ucis(path)
            context = context_template(inspect_xml(path))
            snapshot = import_xml(path, context)
            self.assertIsNone(snapshot["points"][0]["bins"][0]["definition"])
            self.assertEqual(compare(snapshot, snapshot)["status"], "incomplete")

    def test_native_point_threshold_weight_and_goal_are_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.xml", Path(tmp) / "b.xml"
            write_ucis(a)
            xml = a.read_text(encoding="utf-8").replace(
                '<options weight="1" goal="100" at_least="1" auto_bin_max=',
                '<options weight="3" goal="80" at_least="2" auto_bin_max=')
            b.write_text(xml, encoding="utf-8")
            before, after = import_xml(a, context_for(a)), import_xml(b, context_for(b))
            report = compare(before, after)
            point = report["points"][0]["current"]
            self.assertEqual((point["at_least"], point["weight"], point["goal"], point["covered_bins"]), (2, 3, 80, 0))
            self.assertEqual(report["progress"]["newly_hit"], 0)
            self.assertEqual(report["progress"]["no_longer_satisfied"], 180)

    def test_digest_binding_and_missing_bin_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.xml"; write_ucis(path)
            context = context_for(path)
            bad = copy.deepcopy(context); bad["database_sha256"] = "0" * 64
            with self.assertRaises(InputError): import_xml(path, bad)
            context["points"][0]["bins"].pop()
            with self.assertRaises(InputError): import_xml(path, context)

    def test_unsupported_xml_shape_and_missing_options_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp) / "a.xml"; write_ucis(original)
            xml = original.read_text(encoding="utf-8")
            for index, changed in enumerate((xml.replace('type="bins"', 'type="default"', 1),
                                              xml.replace(' at_least="1"', '', 2),
                                              xml.replace('<range from="-1" to="-1">', '<sequence>', 1).replace('</range>', '</sequence>', 1),
                                              xml.replace('</range>', '</range><range from="0" to="0"><contents coverageCount="1"/></range>', 1))):
                path = Path(tmp) / f"bad{index}.xml"; path.write_text(changed, encoding="utf-8")
                with self.assertRaises(InputError): inspect_xml(path)

    def test_doctype_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.xml"
            path.write_text('<!DOCTYPE UCIS [<!ENTITY x "content">]><UCIS/>', encoding="utf-8")
            with self.assertRaises(InputError): inspect_xml(path)

    def test_import_cli_and_context_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp); path = tmp / "a.xml"; write_ucis(path)
            inventory, template, context, out = (tmp / n for n in ("inventory.json", "template.json", "context.json", "out.json"))
            base = [sys.executable, str(MODULE / "coverage_audit.py")]
            result = subprocess.run(base + ["inspect-ucis", str(path), "--output", str(inventory), "--context-template", str(template)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(read_json(template)["population_complete"])
            context.write_text(json.dumps(context_for(path)), encoding="utf-8")
            result = subprocess.run(base + ["import-ucis", str(path), "--context", str(context), "--output", str(out)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(read_json(out)["points"][0]["bins"]), 200)


if __name__ == "__main__":
    unittest.main()
