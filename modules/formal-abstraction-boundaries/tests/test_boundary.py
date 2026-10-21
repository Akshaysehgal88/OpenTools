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

MODULE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(MODULE), str(MODULE / "examples")]
from boundary_core import InputError, contained, digest, exit_code, markdown, relation, review
from yosys_capture import DOMAIN, VERSION, capture, enumeration, model, recipe, table
from create_example import CASES, allowed, context, reference


def records():
    scope = context("synthetic", ["synthetic-never-executed"], "tags")["scope"]
    sources = {"model.sv": "a" * 64, "selection.vh": "b" * 64}
    rows = reference("tags", "exact", False)
    views = {}
    for view in ("concrete", "abstract"):
        views[view] = {"format": "synthetic-core-test-not-native", "run_ref": view, "sources": sources,
                       "scope": scope, "domain": DOMAIN, "property_ref": "tags:tag-identity",
                       "original_command": ["synthetic-never-executed"], "dependency_capture_complete": True,
                       "dependency_basis_ref": "synthetic", "rows": copy.deepcopy(rows), "outcome": "pass", "witness": None,
                       "cutpoints": ["left", "right"] if view == "abstract" else [], "assumption_cells": [],
                       "cone_ports": {"before": ["source", "left", "right"], "after": ["left", "right"]}}
    contract = {"format": "opentools.abstraction-boundary.v1", "review_ref": "synthetic", "claim": "Selected stateless tag equality",
                "owner_ref": "synthetic-owner", "scope_ref": "synthetic-scope", "scope": scope, "domain": DOMAIN,
                "property": {"ref": "tags:tag-identity", "basis_ref": "synthetic-intent", "allowed_rows": allowed("tags")},
                "views": {k: {"run_ref": k, "sources": sources, "basis_ref": "synthetic-intent"} for k in views}, "obligations": []}
    return contract, {"format": "opentools.abstraction-evidence.v1", "contract_sha256": digest(contract), **views}


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.contract, self.evidence = records()
        self.mock = patch("yosys_capture.revalidate", return_value=None)
        self.mock.start();self.addCleanup(self.mock.stop)

    def check(self):
        self.evidence["contract_sha256"] = digest(self.contract)
        return review(self.contract, self.evidence)

    def test_equal_relation(self):
        r = self.check();self.assertEqual(exit_code(r), 0)
        self.assertEqual(r["observations"]["relation_direction"], "equal")

    def test_conservative_lost_correlation_is_not_concrete_failure(self):
        self.evidence["abstract"].update(rows=reference("tags", "independent", True), outcome="fail", witness=[0, 0, 1])
        r = self.check();self.assertEqual(exit_code(r), 1)
        self.assertEqual(r["observations"]["relation_direction"], "conservative_expansion")
        self.assertEqual(r["observations"]["abstract_witness_classification"], "absent_from_selected_concrete_relation")
        self.assertFalse(r["observations"]["excludes_concrete"])

    def test_green_restriction_excludes_allowed_inputs(self):
        self.evidence["abstract"]["rows"] = [[0, 1, 1]]
        r = self.check();self.assertEqual(exit_code(r), 1)
        self.assertEqual(r["observations"]["relation_direction"], "restrictive_subset")
        self.assertEqual(len(r["observations"]["excludes_concrete"]), 3)

    def test_incomparable_green_hides_concrete_fault(self):
        self.evidence["concrete"].update(rows=reference("tags", "unsupported-green", False), outcome="fail", witness=[2, 3, 0])
        self.evidence["abstract"]["rows"] = reference("tags", "unsupported-green", True)
        r = self.check();self.assertEqual(exit_code(r), 1)
        self.assertEqual(r["observations"]["relation_direction"], "incomparable")
        self.assertIn([2, 3, 0], r["observations"]["excludes_concrete"])
        self.assertEqual(r["native"]["abstract"]["outcome"], "pass")

    def test_concrete_feasible_abstract_counterexample(self):
        self.evidence["concrete"].update(rows=reference("tags", "unsupported-green", False), outcome="fail", witness=[2, 3, 0])
        self.evidence["abstract"].update(rows=reference("tags", "independent", True), outcome="fail", witness=[2, 3, 0])
        self.assertEqual(self.check()["observations"]["abstract_witness_classification"], "feasible_in_selected_concrete_relation")

    def test_missing_concrete(self):
        self.evidence["concrete"] = None;self.assertEqual(exit_code(self.check()), 2)

    def test_missing_abstract(self):
        self.evidence["abstract"] = None;self.assertEqual(exit_code(self.check()), 2)

    def test_stale_binding_quarantines(self):
        self.evidence["contract_sha256"] = "stale"
        r = review(self.contract, self.evidence);self.assertEqual(exit_code(r), 2);self.assertFalse(r["native"])

    def test_foreign_native_run(self):
        self.contract["views"]["abstract"]["run_ref"] = "other"
        r = self.check();self.assertEqual(exit_code(r), 1);self.assertNotIn("abstract", r["native"])

    def test_wrong_source(self):
        self.contract = copy.deepcopy(self.contract)
        self.contract["views"]["abstract"]["sources"] = {"model.sv": "0" * 64, "selection.vh": "b" * 64}
        self.assertEqual(exit_code(self.check()), 1)

    def test_missing_source_identity(self):
        self.contract["views"]["abstract"]["sources"] = None;self.assertEqual(exit_code(self.check()), 2)

    def test_unknown_scope_fact(self):
        self.evidence["abstract"]["scope"] = copy.deepcopy(self.evidence["abstract"]["scope"])
        self.evidence["abstract"]["scope"]["mode_ref"] = None
        self.assertEqual(exit_code(self.check()), 2)

    def test_incomplete_dependencies(self):
        self.evidence["abstract"]["dependency_capture_complete"] = False;self.assertEqual(exit_code(self.check()), 2)

    def test_missing_command(self):
        self.evidence["concrete"]["original_command"] = None;self.assertEqual(exit_code(self.check()), 2)

    def test_empty_abstract_environment(self):
        self.evidence["abstract"]["rows"] = [];r = self.check()
        self.assertEqual(exit_code(r), 1);self.assertTrue(r["gaps"])

    def test_missing_required_property_relation(self):
        self.contract["property"]["allowed_rows"] = None;self.assertEqual(exit_code(self.check()), 2)

    def test_native_pass_does_not_redefine_required_property(self):
        self.contract["property"]["allowed_rows"] = []
        self.assertEqual(exit_code(self.check()), 1)

    def test_mismatched_witness_not_concrete_failure(self):
        self.evidence["abstract"].update(outcome="fail", witness=[0, 1, 1])
        r = self.check();self.assertTrue(any("does not demonstrate" in v for v in r["gaps"]))

    def test_no_actual_abstract_cutpoint(self):
        self.evidence["abstract"]["cutpoints"] = [];self.assertEqual(exit_code(self.check()), 2)

    def test_concrete_premises_outside_first_scope(self):
        self.evidence["concrete"]["assumption_cells"] = [{"id": "premise", "source": "synthetic"}]
        self.assertEqual(exit_code(self.check()), 2)

    def test_omitted_invariant_obligation(self):
        self.evidence["abstract"]["assumption_cells"] = [{"id": "premise", "source": "synthetic"}]
        self.assertEqual(exit_code(self.check()), 1)

    def test_missing_obligation_population(self):
        self.contract["obligations"] = None;self.assertEqual(exit_code(self.check()), 2)

    def test_unowned_invariant(self):
        self.evidence["abstract"]["assumption_cells"] = [{"id": "premise", "source": "synthetic"}]
        self.contract["obligations"] = [{"cell_id": "premise", "owner_ref": None, "basis_ref": "synthetic"}]
        self.assertEqual(exit_code(self.check()), 2)

    def test_cone_membership_not_used_as_sufficiency(self):
        self.evidence["abstract"]["cone_ports"] = {"before": [], "after": []}
        self.evidence["abstract"]["rows"] = [[0, 1, 1]]
        self.assertEqual(exit_code(self.check()), 1)

    def test_duplicate_and_boolean_rows_rejected(self):
        for rows in ([[0, 1, 1], [0, 1, 1]], [[False, 1, 1]], [[0, 1, 4]]):
            with self.assertRaises(InputError):relation(rows, [2, 2, 2])

    def test_sequential_claim_not_accepted(self):
        self.contract["scope"]["model_class"] = "sequential_refinement"
        with self.assertRaises(InputError):self.check()

    def test_oversized_relation_domain_rejected(self):
        self.contract["domain"] = [{"name": "a", "width": 8}, {"name": "b", "width": 8}]
        with self.assertRaises(InputError):self.check()

    def test_markdown_escapes(self):
        self.contract["claim"] = "<script> | claim"
        result = markdown(self.check());self.assertNotIn("<script>", result);self.assertIn("&#124;", result)


class ReaderTests(unittest.TestCase):
    def test_native_table_scalar_tuple(self):
        self.assertEqual(table("  \\source 0 0 00\n  \\left 1 1 01\n  \\right 2 2 10\n"), [0, 1, 2])

    def test_ambiguous_or_unknown_table_rejected(self):
        for content in ("\\source x", "  \\source 0 0 00\n  \\left 1 1 01\n  \\right 2 3 10\n", "  \\source 0 0 00\n" * 2):
            with self.assertRaises(InputError):table(content)

    def test_complete_enumeration(self):
        log = "SAT solving finished - model found:\n  \\source 0 0 00\n  \\left 1 1 01\n  \\right 2 2 10\nSAT solving finished - no more models found (after 1 distinct solutions).\n"
        self.assertEqual(enumeration(log), [[0, 1, 2]])
        with self.assertRaises(InputError):enumeration(log.replace("after 1", "after 2"))
        with self.assertRaises(InputError):enumeration(log.split("SAT solving finished - no more")[0])

    def test_empty_enumeration_is_explicit(self):
        self.assertEqual(enumeration("SAT solving finished - no model found.\n"), [])

    def test_duplicate_selected_tuple_rejected(self):
        block = "SAT solving finished - model found:\n  \\source 0 0 00\n  \\left 1 1 01\n  \\right 2 2 10\n"
        with self.assertRaises(InputError):enumeration(block * 2 + "SAT solving finished - no more models found (after 2 distinct solutions).\n")

    def test_data_only_rejects_executable_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);(root / "run").mkdir();(root / "run/run.ys").write_text("shell touch marker\n")
            with self.assertRaises(InputError):capture(root, "run", context("synthetic", ["never-executed"], "tags"))
            self.assertFalse((root / "marker").exists())

    def test_paths_stay_inside_root(self):
        for path in ("../outside", "/outside", "C:/outside", "run/../outside", "run\\status"):
            with self.assertRaises(InputError):contained(".", path)

    def test_wrong_creator_or_hierarchy_rejected(self):
        for value in ({"creator": "other", "modules": {}}, {"creator": VERSION, "modules": {"top": {}, "other": {}}}):
            with self.assertRaises(InputError):model(value)

    def test_finite_reference_independent_contexts(self):
        for family in ("operands", "tags"):
            self.assertEqual(len(reference(family, "exact", False)), 4)
            self.assertEqual(len(reference(family, "independent", True)), 64)
            self.assertEqual(len(reference(family, "restricted", True)), 1)
            c = {tuple(v) for v in reference(family, "unsupported-green", False)}
            a = {tuple(v) for v in reference(family, "unsupported-green", True)}
            self.assertEqual(len(c - a), 1)

    @unittest.skipUnless(os.environ.get("OPENTOOLS_ABSTRACTION_EXAMPLE"), "Set OPENTOOLS_ABSTRACTION_EXAMPLE to the retained native example root")
    def test_actual_native_matrix_integrity_and_witnesses(self):
        root = Path(os.environ["OPENTOOLS_ABSTRACTION_EXAMPLE"])
        summary = json.loads((root / "summary.json").read_text());self.assertEqual(summary["native_invocations"], 16)
        for name, (family, kind) in CASES.items():
            folder = root / name;contract = json.loads((folder / "contract.json").read_text());evidence = json.loads((folder / "evidence.json").read_text())
            self.assertEqual(review(contract, evidence, folder), json.loads((folder / "report.json").read_text()))
            for view in ("concrete", "abstract"):
                self.assertEqual(evidence[view]["rows"], reference(family, kind, view == "abstract"))
                self.assertEqual(evidence[view]["sources"]["model.sv"], hashlib.sha256((MODULE / "examples" / (family + ".sv")).read_bytes()).hexdigest())
        with tempfile.TemporaryDirectory() as tmp:
            src = root / "operands-exact";dest = Path(tmp) / "case";shutil.copytree(src, dest)
            c = json.loads((dest / "contract.json").read_text());e = json.loads((dest / "evidence.json").read_text())
            (dest / "abstract/relation.log").write_text("truncated\n")
            r = review(c, e, dest);self.assertEqual(exit_code(r), 2);self.assertNotIn("abstract", r["native"])
            ctx = e["abstract"]["provenance"]["context"]
            with self.assertRaises(InputError):capture(dest, "abstract", ctx)
            shutil.copy2(src / "abstract/relation.log", dest / "abstract/relation.log")
            e["abstract"]["rows"] = []
            self.assertEqual(exit_code(review(c, e, dest)), 2)
            e = json.loads((src / "evidence.json").read_text())
            (dest / "abstract/after.json").unlink()
            self.assertEqual(exit_code(review(c, e, dest)), 2)
        cli = subprocess.run([sys.executable, str(MODULE / "boundary_check.py"), "review", str(root / "tags-exact/contract.json"), str(root / "tags-exact/evidence.json")], capture_output=True, text=True)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.json"
            argv = [sys.executable, str(MODULE / "boundary_check.py"), "review", str(root / "tags-exact/contract.json"), str(root / "tags-exact/evidence.json"), "--json-out", str(output)]
            self.assertEqual(subprocess.run(argv, capture_output=True).returncode, 0)
            before = output.read_bytes()
            self.assertEqual(subprocess.run(argv, capture_output=True).returncode, 3)
            self.assertEqual(output.read_bytes(), before)


if __name__ == "__main__":unittest.main()
