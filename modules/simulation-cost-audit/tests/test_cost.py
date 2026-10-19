import copy
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(MODULE / "examples"))
from cost_core import InputError, analyze, canonical, compare, exit_code, markdown, read_json
from create_example import phase, records, resource


class CostTests(unittest.TestCase):
    def setUp(self):
        self.before, self.after, self.policy = records()

    def test_synthetic_wall_budget_not_double_counted(self):
        report = analyze(self.before)
        self.assertEqual(report["status"], "accounted_window")
        self.assertEqual(Decimal(report["window_wall_s"]), 7200)
        centers = {r["bucket"]: Decimal(r["wall_s"]) for r in report["ranked_cost_centers"]}
        self.assertEqual(centers, {"stage:initialization": 3000, "stage:build": 2400, "stage:queue-wait": 1200, "stage:active-stimulus": 600})
        self.assertEqual(sum(centers.values()), 7200)
        self.assertEqual(Decimal(report["overlay_union_s"]["waveform-capture"]), 600)
        self.assertEqual(Decimal(report["unallocated_wall_s"]), 0)

    def test_parallel_cpu_engineer_effort_and_storage_are_separate(self):
        report = analyze(self.before)
        resources = {r["id"]: r for r in report["resource_observations"]}
        self.assertEqual(Decimal(resources["parallel-cpu"]["normalized_value"]), 18000)
        self.assertEqual(Decimal(resources["engineer-review"]["normalized_value"]), 1800)
        self.assertEqual(Decimal(resources["trace-size"]["normalized_value"]), 2147483648)
        self.assertEqual(Decimal(report["window_wall_s"]), 7200)
        self.assertIn("peak_memory", report["unmeasured_quantities"])

    def test_cross_stage_overlap_and_unallocated_budget(self):
        self.before["window"]["end_s"] = 12
        self.before["phases"] = [phase("build", "build", 0, 6), phase("simulate", "simulate", 4, 10)]
        report = analyze(self.before)
        centers = {r["bucket"]: Decimal(r["wall_s"]) for r in report["ranked_cost_centers"]}
        self.assertEqual(centers, {"stage:build": 4, 'shared:["build","simulate"]': 2, "stage:simulate": 4, "unallocated": 2})
        self.assertEqual(Decimal(report["shared_wall_s"]), 2)
        self.assertEqual(report["status"], "partial_accounting")
        self.assertEqual(exit_code(report), 2)

    def test_same_stage_parallel_tasks_use_union(self):
        self.before["window"]["end_s"] = 10
        self.before["phases"] = [phase("compile-A", "build", 0, 7), phase("compile-B", "build", 4, 10)]
        report = analyze(self.before)
        self.assertEqual(report["ranked_cost_centers"], [{"bucket": "stage:build", "wall_s": "10"}])
        self.assertEqual(Decimal(report["shared_wall_s"]), 0)
        self.assertTrue(any(len(s["stage_phase_ids"]) == 2 for s in report["segments"]))

    def test_company_stage_labels_cannot_merge_distinct_overlap_groups(self):
        self.before["window"]["end_s"] = 8
        self.before["phases"] = [phase("one", "a+b", 0, 4), phase("two", "c", 0, 4),
                                 phase("three", "a", 4, 8), phase("four", "b+c", 4, 8)]
        report = analyze(self.before)
        self.assertEqual(len(report["ranked_cost_centers"]), 2)
        self.assertEqual(Decimal(report["shared_wall_s"]), 8)

    def test_overlay_only_cannot_fill_unknown_stage(self):
        self.before["phases"] = [phase("trace", "trace", 0, 7200, "overlay")]
        report = analyze(self.before)
        self.assertEqual(Decimal(report["unallocated_wall_s"]), 7200)
        self.assertEqual(Decimal(report["overlay_union_s"]["trace"]), 7200)

    def test_clipping_explicit_and_zero_length_is_not_expense(self):
        self.before["window"]["end_s"] = 10
        self.before["phases"] = [phase("outer", "simulate", -2, 14), phase("marker", "instant", 5, 5)]
        report = analyze(self.before)
        self.assertEqual(report["ranked_cost_centers"], [{"bucket": "stage:simulate", "wall_s": "10"}])
        self.assertTrue(any("clipped" in note for note in report["notes"]))

    def test_missing_estimated_or_unsourced_stage_stays_unknown(self):
        for key, value in (("end_s", None), ("basis", "estimated"), ("evidence_ref", None)):
            run = copy.deepcopy(self.before)
            run["phases"][1][key] = value
            report = analyze(run)
            with self.subTest(key=key):
                self.assertEqual(report["status"], "partial_accounting")
                self.assertEqual(Decimal(report["unallocated_wall_s"]), 2400)
                self.assertEqual(report["phase_records"][1][key], value)

    def test_uncertain_collection_or_window_no_invented_total(self):
        self.before["collection"]["complete"] = None
        self.assertEqual(analyze(self.before)["status"], "partial_accounting")
        for key in ("end_s", "clock_ref", "scope_ref", "evidence_ref"):
            run = copy.deepcopy(self.before); run["window"][key] = None
            with self.subTest(key=key):
                self.assertIsNone(analyze(run)["window_wall_s"])

    def test_estimated_overlay_and_resource_do_not_become_measured(self):
        self.before["phases"][4]["basis"] = "estimated"
        self.before["phases"][5]["basis"] = "estimated"
        self.before["resources"][0]["basis"] = "estimated"
        report = analyze(self.before)
        self.assertEqual(report["status"], "accounted_window")
        self.assertEqual(report["overlay_union_s"], {})
        self.assertIsNone(report["resource_observations"][0]["normalized_value"])
        self.assertIn("cpu_time", report["unmeasured_quantities"])

    def test_unknown_resource_unit_or_definition_retained(self):
        for key, value in (("unit", "ambiguous-KB"), ("definition_ref", None), ("scope_ref", None)):
            run = copy.deepcopy(self.before); run["resources"][1][key] = value
            report = analyze(run)
            with self.subTest(key=key):
                self.assertIsNone(report["resource_observations"][1]["normalized_value"])
                self.assertTrue(report["measurement_issues"])

    def test_progress_requires_definition_and_same_window_scope(self):
        report = analyze(self.before)
        self.assertEqual(report["progress_rate"]["unit"], "cycles/wall_s")
        self.assertAlmostEqual(float(report["progress_rate"]["value"]), 600000 / 7200)
        for key, value in (("scope_ref", "inner-stimulus-only"), ("definition_ref", None), ("basis", "estimated")):
            run = copy.deepcopy(self.before); run["simulation_progress"][key] = value
            with self.subTest(key=key):
                self.assertIsNone(analyze(run)["progress_rate"])

    def test_simulated_time_unit_conversion_and_zero_progress(self):
        self.before["simulation_progress"].update(amount=1000, unit="ns", definition_ref="simulated-time")
        self.after["simulation_progress"].update(amount=1000000, unit="ps", definition_ref="simulated-time")
        report = compare(self.before, self.after, self.policy)
        self.assertEqual(report["progress_correspondence"], "matched")
        self.before["simulation_progress"].update(amount=0, unit="cycles")
        self.assertEqual(Decimal(analyze(self.before)["progress_rate"]["value"]), 0)

    def test_failed_run_costs_remain_measured_not_successful_optimization(self):
        self.before["completion"]["outcome"] = "failed"
        report = analyze(self.before)
        self.assertEqual(report["status"], "accounted_window")
        self.assertTrue(report["notes"])
        self.assertEqual(compare(self.before, self.after, self.policy)["status"], "incomplete")

    def test_comparison_retains_raw_delta_without_causal_or_resource_claim(self):
        report = compare(self.before, self.after, self.policy)
        self.assertEqual(report["status"], "comparable_window_observation")
        self.assertEqual(Decimal(report["reported_wall_delta_s"]), -1500)
        self.assertEqual(report["progress_correspondence"], "matched")
        self.assertNotIn("cpu_savings", report)
        self.assertIn("not isolated causality", report["limits"])

    def test_instrumentation_can_be_intended_but_fixed_change_confounds(self):
        self.after["context"]["instrumentation_ref"]["value"] = "trace:narrow"
        self.assertEqual(compare(self.before, self.after, self.policy)["status"], "confounded")
        self.policy["roles"]["instrumentation_ref"]["role"] = "intended"
        report = compare(self.before, self.after, self.policy)
        self.assertEqual(report["status"], "comparable_window_observation")
        self.assertIn("instrumentation_ref", report["intended_changes"])

    def test_changed_work_or_check_scope_is_descriptive_not_same_work_benefit(self):
        for name in ("configuration_ref", "workload_ref", "evidence_scope_ref"):
            run = copy.deepcopy(self.after); policy = copy.deepcopy(self.policy)
            run["context"][name]["value"] = "different"
            policy["roles"][name]["role"] = "intended"
            with self.subTest(name=name):
                self.assertEqual(compare(self.before, run, policy)["status"], "descriptive_difference")
        self.after["simulation_progress"]["amount"] = 300000
        report = compare(self.before, self.after, self.policy)
        self.assertEqual(report["status"], "descriptive_difference")
        self.assertEqual(report["progress_correspondence"], "different_amount")
        self.assertIsNone(report["reported_progress_rate_ratio"])

    def test_wide_counter_difference_not_lost_to_rate_rounding(self):
        self.before["simulation_progress"]["amount"] = 2 ** 128
        self.after["simulation_progress"]["amount"] = 2 ** 128 + 1
        report = compare(self.before, self.after, self.policy)
        self.assertEqual(report["progress_correspondence"], "different_amount")
        self.assertIsNone(report["reported_progress_rate_ratio"])

    def test_unknowns_coexist_with_confounders_and_unqualified_delta(self):
        self.after["context"]["configuration_ref"]["value"] = "different"
        self.after["context"]["tool_ref"]["value"] = None
        report = compare(self.before, self.after, self.policy)
        self.assertEqual(report["status"], "confounded")
        self.assertTrue(report["unknowns"])
        self.assertEqual(Decimal(report["reported_wall_delta_s"]), -1500)

    def test_scope_or_missing_completion_blocks_qualified_comparison(self):
        self.after["window"]["scope_ref"] = "stimulus-only"
        self.assertEqual(compare(self.before, self.after, self.policy)["status"], "confounded")
        self.after["window"]["scope_ref"] = self.before["window"]["scope_ref"]
        self.after["completion"]["required_evidence_complete"] = None
        self.assertEqual(compare(self.before, self.after, self.policy)["status"], "incomplete")

    def test_zero_window_and_empty_phases_no_division(self):
        self.before["window"]["end_s"] = 0
        self.before["phases"] = []
        report = analyze(self.before)
        self.assertEqual(Decimal(report["window_wall_s"]), 0)
        self.assertIsNone(report["progress_rate"])
        report = compare(self.before, self.after, self.policy)
        self.assertIsNone(report["reported_wall_delta_percent"])

    def test_invalid_shapes_cycles_units_and_policy(self):
        runs = []
        run = copy.deepcopy(self.before); run["window"]["end_s"] = float("nan"); runs.append(run)
        run = copy.deepcopy(self.before); run["phases"][0]["end_s"] = -1; runs.append(run)
        run = copy.deepcopy(self.before); run["phases"].append(run["phases"][0]); runs.append(run)
        run = copy.deepcopy(self.before); run["resources"][0]["value"] = True; runs.append(run)
        run = copy.deepcopy(self.before); run["simulation_progress"]["amount"] = 0.5; runs.append(run)
        for run in runs:
            with self.subTest(run=run), self.assertRaises(InputError):
                analyze(run)
        policy = copy.deepcopy(self.policy); policy["roles"].pop("workload_ref")
        with self.assertRaises(InputError):
            compare(self.before, self.after, policy)
        self.policy["current_run_ref"] = "wrong-run"
        with self.assertRaises(InputError):
            compare(self.before, self.after, self.policy)

    def test_no_input_mutation_html_escaping_and_duplicate_keys(self):
        original = canonical(self.before)
        self.before["task"] = "<script>cost</script> | test"
        output = markdown(analyze(self.before))
        self.assertIn("&lt;script&gt;", output)
        self.assertNotIn("<script>", output)
        self.before["task"] = json.loads(original)["task"]
        compare(self.before, self.after, self.policy)
        self.assertEqual(canonical(self.before), original)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"complete":false,"complete":true}')
            with self.assertRaises(InputError):
                read_json(path)

    def test_cli_statuses_outputs_and_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for name, value in zip(("before", "after", "policy"), (self.before, self.after, self.policy)):
                path = root / f"{name}.json"; path.write_text(json.dumps(value)); paths.append(str(path))
            command = [sys.executable, str(MODULE / "cost_audit.py")]
            proc = subprocess.run(command + ["analyze", paths[0], "--json-out", str(root / "audit.json"), "--markdown-out", str(root / "audit.md")], capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            proc = subprocess.run(command + ["analyze", paths[0], "--json-out", str(root / "audit.json")], capture_output=True)
            self.assertEqual(proc.returncode, 3)
            proc = subprocess.run(command + ["compare", *paths], capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.before["collection"]["complete"] = False
            Path(paths[0]).write_text(json.dumps(self.before))
            self.assertEqual(subprocess.run(command + ["analyze", paths[0]], capture_output=True).returncode, 2)
            self.after["context"]["tool_ref"]["value"] = "changed"
            Path(paths[1]).write_text(json.dumps(self.after))
            self.assertEqual(subprocess.run(command + ["compare", *paths], capture_output=True).returncode, 1)


if __name__ == "__main__":
    unittest.main()
