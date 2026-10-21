"""Run owned Yosys equivalence controls and create independent claim reviews."""
from __future__ import annotations
import argparse
from itertools import product
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PROFILE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROFILE))
from equivalence_core import exit_code, markdown, review
from yosys_equivalence import REQUIRED_FIELDS, VERSION, capture, file_hash, recipe

INTERFACES = {"arithmetic": {"inputs": {"functional_mode": 1, "operand_a": 4, "operand_b": 4}, "outputs": {"carry": 1, "sum": 4}},
              "control": {"inputs": {"events": 8, "functional_mode": 1, "mask": 8}, "outputs": {"irq": 1, "pending": 8}}}
JOBS = {"rewrite": (0, None), "bug-unconstrained": (1, None), "bug-mode0": (1, 0), "bug-mode1": (1, 1)}
CASES = {"rewrite-all-modes": ("rewrite", [0, 1], 0), "hidden-functional-change": ("bug-mode0", [0, 1], 1),
         "unconstrained-counterexample": ("bug-unconstrained", [0, 1], 1), "mode1-counterexample": ("bug-mode1", [1], 1),
         "legitimate-mode0": ("bug-mode0", [0], 0), "outside-requested-mode": ("bug-unconstrained", [0], 2)}


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:stream.write(json.dumps(value, indent=2) + "\n")


def interface_for(family, width=None):
    if family == "control" and width is not None:
        return {"inputs": {"events": width, "functional_mode": 1, "mask": width}, "outputs": {"irq": 1, "pending": width}}
    return INTERFACES[family]


def expected_mapping(family, width=None):
    interface = interface_for(family, width)
    return {"inputs": [{"gold": "gold." + name, "gate": "gate." + name, "miter_input": "in_" + name, "width": width, "signed": False}
                       for name, width in sorted(interface["inputs"].items())],
            "outputs": [{"gold": "gold." + name, "gate": "gate." + name, "native_compare": "cmp_" + name, "width": width, "signed": False}
                        for name, width in sorted(interface["outputs"].items())]}


def reference(family, mutation, values, width=None):
    mode = values["functional_mode"]
    if family == "arithmetic":
        total = values["operand_a"] + values["operand_b"]
        gold = {"sum": total % 16, "carry": total // 16}
        gate = {"sum": (total % 16) ^ (1 if mutation and mode else 0), "carry": total // 16}
    else:
        pending = values["events"] & values["mask"]
        gold = {"pending": pending, "irq": int(pending != 0)}
        changed = pending ^ ((1 << ((width or 8) - 1)) if mutation and mode else 0)
        gate = {"pending": changed, "irq": int(changed != 0)}
    return gold, gate


def finite_check(family, mutation, mode, width=None):
    inputs = interface_for(family, width)["inputs"];names = sorted(inputs)
    if sum(inputs.values()) > 20:
        return {"vectors_checked": 0, "mismatch_count": None, "first_mismatch": None,
                "method": "Large-domain format control: actual native equivalence verdict and exact counterexample values checked; no exhaustive reference enumeration claimed."}
    tested, mismatches = 0, []
    for vector in product(*(range(2 ** inputs[n]) for n in names)):
        values = dict(zip(names, vector))
        if mode is not None and values["functional_mode"] != mode:continue
        tested += 1;gold, gate = reference(family, mutation, values, width)
        if gold != gate:mismatches.append({"inputs": values, "gold": gold, "gate": gate})
    return {"vectors_checked": tested, "mismatch_count": len(mismatches), "first_mismatch": mismatches[0] if mismatches else None,
            "method": "Independent finite arithmetic/Boolean reference validates the owned native test; it is not used to replace the native verdict in the product."}


def capture_context(family, job):
    return {"format": "opentools.equivalence-capture-context.v1", "run_ref": "owned:" + family + ":" + job,
            "manifest_ref": "owned:" + family + ":" + job + ":native-script", "eco_ref": "owned:" + family + ":rewrite-eco",
            "mode_input": "in_functional_mode", "scope_basis_ref": "owned:reviewed-stateless-defined-input-model-and-whole-miter",
            "dependencies_complete": True, "dependency_basis_ref": "owned:two-flat-source-inputs-and-pinned-native-runtime"}


def intent_for(name, family, snapshot, modes, width=None):
    fields = {k: {"value": snapshot["fields"][k]["value"], "evidence_ref": "owned:" + family + ":original-ECO-build-and-interface-record"} for k in REQUIRED_FIELDS}
    fields["mapping"]["value"] = expected_mapping(family, width)
    return {"format": "opentools.equivalence-intent.v1", "claim_id": "owned:" + name, "claim": "The selected ECO implementation retains reference behavior at every reviewed output for the explicitly required functional modes.",
            "scope_ref": "owned:" + name + ":comparison-boundary", "eco_ref": snapshot["provenance"]["context"]["eco_ref"],
            "eco_intent_ref": "owned:" + family + ":no-behavior-change-at-requested-modes", "owner_ref": "owned-ECO-review-owner", "run_ref": snapshot["run_ref"],
            "required_fields": fields, "mode_input": "in_functional_mode", "required_modes": modes, "mode_basis_ref": "owned:" + name + ":independent-mode-requirement",
            "mapping_review": {"status": "approved", "reviewer_ref": "synthetic-owned-fixture-reviewer",
                               "basis_ref": "owned:explicit-fixture-port-map-only-not-organization-approval"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument("output", type=Path);parser.add_argument("--yosys-prefix", type=Path, required=True)
    args = parser.parse_args()
    if os.name != "posix":parser.error("Native execution recipe is qualified on Linux; saved-data review is portable")
    output = args.output.resolve();output.mkdir(parents=True, exist_ok=False);prefix = args.yosys_prefix.resolve()
    env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib/x86_64-linux-gnu") + os.pathsep + os.environ.get("LD_LIBRARY_PATH", ""))
    executable = str(prefix / "bin/yosys")
    version = subprocess.run([executable, "-V"], env=env, capture_output=True, text=True, check=True).stdout.strip()
    assert version == VERSION, version
    jobs, cases = [], []
    for family in INTERFACES:
        job_specs = {name: (mutation, mode, None) for name, (mutation, mode) in JOBS.items()}
        if family == "control":job_specs.update({"wide-rewrite": (0, None, 32), "wide-bug": (1, 1, 32)})
        for job, (mutation, mode, width) in job_specs.items():
            folder = output / "jobs" / (family + "-" + job);folder.mkdir(parents=True)
            shutil.copy2(PROFILE / "examples" / ("reference_" + family + ".v"), folder / "reference.v")
            shutil.copy2(PROFILE / "examples" / ("implementation_" + family + ".v"), folder / "implementation.v")
            before = {n: file_hash(folder / n) for n in ("reference.v", "implementation.v")}
            parameters = {"gold": {}, "gate": {"MUTATION": mutation}}
            if family == "control":
                parameters["gold"]["WIDTH"] = parameters["gate"]["WIDTH"] = width or 8
            restriction = ("in_functional_mode", mode) if mode is not None else None
            (folder / "run.ys").write_text(recipe(parameters, restriction), encoding="utf-8")
            command = [executable, "-Q", "-T", "-s", "run.ys"]
            native = subprocess.run(command, cwd=folder, env=env, capture_output=True, text=True, timeout=60)
            (folder / "native.log").write_text(native.stdout + native.stderr, encoding="utf-8");(folder / "version.txt").write_text(version + "\n", encoding="utf-8")
            save(folder / "command.json", command);save(folder / "execution.json", {"exit_code": native.returncode})
            assert native.returncode == 0, native.stderr
            assert all(file_hash(folder / n) == checksum for n, checksum in before.items())
            ctx = capture_context(family, job);snapshot = capture(folder.parent, folder.name, ctx)
            assert snapshot["fields"]["mapping"]["value"] == expected_mapping(family, width)
            reference_result = finite_check(family, mutation, mode, width)
            expected_outcome = "pass" if not mutation or mode == 0 else "fail"
            assert snapshot["result"]["outcome"] == expected_outcome
            if reference_result["mismatch_count"] is not None:
                assert expected_outcome == ("fail" if reference_result["mismatch_count"] else "pass")
            cex = snapshot["provenance"]["native_counterexample"]
            if cex:
                inputs = {n: cex["in_" + n] for n in interface_for(family, width)["inputs"]};gold, gate = reference(family, mutation, inputs, width)
                assert gold != gate and all(cex["gold_" + n] == v for n, v in gold.items()) and all(cex["gate_" + n] == v for n, v in gate.items())
            save(folder / "independent-reference.json", reference_result)
            jobs.append({"job": family + "-" + job, "native_status": snapshot["result"]["native_status"], "mutation": mutation, "mode_constraint": mode, "width_override": width, **reference_result})
        case_specs = dict(CASES)
        if family == "control":case_specs.update({"wide-rewrite": ("wide-rewrite", [0, 1], 0), "wide-counterexample": ("wide-bug", [1], 1)})
        for case, (job, modes, expected_code) in case_specs.items():
            name = family + "-" + case;folder = output / name;shutil.copytree(output / "jobs" / (family + "-" + job), folder / "run")
            ctx = capture_context(family, job);snapshot = capture(folder, "run", ctx)
            width = job_specs[job][2]
            intent = intent_for(name, family, snapshot, modes, width);report = review(intent, snapshot, folder)
            assert exit_code(report) == expected_code, report
            save(folder / "capture-context.json", ctx);save(folder / "snapshot.json", snapshot);save(folder / "intent.json", intent);save(folder / "report.json", report)
            (folder / "report.md").write_text(markdown(report), encoding="utf-8")
            cases.append({"case": name, "job": family + "-" + job, "native_status": snapshot["result"]["native_status"], "required_modes": modes, "status": report["status"], "exit": expected_code})
            print(name + ": " + report["status"], flush=True)
    save(output / "summary.json", {"version": version, "native_jobs": jobs, "cases": cases,
                                   "limits": "One native whole-miter two-state combinational profile with explicit reviewed interfaces. Independent references validate examples, not replace native equivalence or approve an ECO."})


if __name__ == "__main__":main()
