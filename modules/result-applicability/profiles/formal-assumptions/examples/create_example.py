"""Run owned SBY controls and retain data-only review bundles (Linux)."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PROFILE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROFILE))
from formal_core import digest, exit_code, markdown, review
from sby_capture import SBY_REVISION, YOSYS_VERSION, capture, file_hash
from finite_reference import check_trace, finite_consumer, finite_producer

CASES = {
    "wake-excluded": ("wake", 1, "prove", 8, 8),
    "wake-unrestricted": ("wake", 0, "prove", 8, 8),
    "wake-guaranteed": ("wake", 2, "prove", 8, 8),
    "wake-shallow-cover": ("wake", 2, "prove", 8, 1),
    "wake-short-bmc": ("wake", 0, "bmc", 3, 3),
    "stream-excluded": ("stream", 1, "prove", 8, 8),
    "stream-unrestricted": ("stream", 0, "prove", 8, 8),
    "stream-guaranteed": ("stream", 2, "prove", 8, 8),
}
SELECTIONS = {0: "// Unrestricted\n", 1: "`define EXCLUDED\n", 2: "`define HELD\n"}


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def scope(context, mode, producer=False):
    return {"clock_ref": context + ":logical-single-posedge", "reset_ref": context + ":age-zero-one-cycle-reset",
            "integration_mode_ref": context + (":holding-producer" if mode == 2 else ":pulse-capable" if context == "wake" else ":backpressure-allowed"),
            "model_scope_ref": context + (":isolated-producer" if producer else ":isolated-consumer")}


def capture_context(name, command, context, mode, producer=False):
    return {"format": "opentools.formal-capture-context.v1", "run_ref": "owned:" + name,
            "manifest_ref": "owned:" + name + ":config", "command": command,
            "sby_revision": SBY_REVISION, "solver_version": "Z3 version 4.8.12 - 64 bit",
            "dependency_capture_complete": True,
            "dependency_evidence_ref": "owned-flat-model-source-header-and-fixed-recipe",
            "scope": scope(context, mode, producer)}


def expected_model(snapshot, context, producer=False):
    values = {k: snapshot["fields"][k]["value"] for k in ("sources", "top", "scope", "cells")}
    values["basis_ref"] = "owned-example:" + context + ":source-and-obligation-review"
    if producer:
        values.update(condition_ref=context + ":hold-until-response", owner_ref="owned-source-owner",
                      port_binding_ref="owned-example:" + context + ":identity-output-to-input-binding")
    else:
        values.update(property_ref=context + ":response-or-stability", activation_ref=context + ":required-activation",
                      assumptions=[])
    return values


def make_bundle(folder, name, context, mode, proof, cover, guarantee=None):
    model = expected_model(proof, context)
    for cell in model["cells"]:
        if cell["type"] == "$assume":
            model["assumptions"].append({"cell_id": cell["id"], "owner_ref": "owned-source-owner",
                "condition_ref": context + (":hold-until-response" if mode == 2 else ":activation-excluding-premise"),
                "support_ref": "source-hold" if mode == 2 else None})
    spec = {"format": "opentools.formal-assumption-scope.v1", "scope_ref": "owned:" + name,
            "claim_ref": "owned:" + name + ":integration-claim", "claim": "The selected consumer safety property has applicable premise support and its required activation is reachable in the declared logical integration mode.",
            "owner_ref": "owned-review-owner", "consumer": model,
            "guarantees": {"source-hold": expected_model(guarantee, context, True)} if guarantee else {},
            "run_refs": {"proof": proof["run_ref"], "cover": cover["run_ref"],
                         "guarantees": {"source-hold": guarantee["run_ref"]} if guarantee else {}}}
    evidence = {"format": "opentools.formal-assumption-evidence.v1", "scope_sha256": digest(spec),
                "proof": proof, "cover": cover, "guarantees": {"source-hold": guarantee} if guarantee else {}}
    report = review(spec, evidence, folder)
    save(folder / "scope.json", spec)
    save(folder / "evidence.json", evidence)
    save(folder / "report.json", report)
    (folder / "report.md").write_text(markdown(report), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sby", type=Path, required=True, help="Existing pinned SBY sbysrc/sby.py")
    parser.add_argument("--yosys-prefix", type=Path, required=True, help="Existing prefix containing bin/yosys, bin/yosys-smtbmc, bin/z3 and share/yosys")
    args = parser.parse_args()
    if os.name != "posix":
        parser.error("This native recipe is qualified on Linux; saved-data review also works on Windows")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sby, prefix = args.sby.resolve(), args.yosys_prefix.resolve()
    revision = subprocess.run(["git", "-C", str(sby.parent.parent), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    if revision != SBY_REVISION:
        parser.error("Use the qualified SBY source revision listed in FORMAT.md")
    with tempfile.TemporaryDirectory(prefix="opentools-formal-") as temporary:
        temporary = Path(temporary)
        (temporary / "tools").symlink_to(prefix, target_is_directory=True)
        tools = temporary / "tools"
        env = dict(os.environ, PATH=str(tools / "bin") + os.pathsep + os.environ.get("PATH", ""),
                   LD_LIBRARY_PATH=str(tools / "lib/x86_64-linux-gnu") + os.pathsep + os.environ.get("LD_LIBRARY_PATH", ""),
                   PYTHONPATH=str(tools / "share/yosys") + os.pathsep + os.environ.get("PYTHONPATH", ""))
        versions = {}
        for key, argv in (("yosys", [str(tools / "bin/yosys"), "-V"]), ("solver", [str(tools / "bin/z3"), "--version"])):
            versions[key] = subprocess.run(argv, env=env, capture_output=True, text=True, check=True).stdout.strip()
        assert versions == {"yosys": YOSYS_VERSION, "solver": "Z3 version 4.8.12 - 64 bit"}, versions
        versions["sby_revision"] = revision
        save(output / "versions.json", versions)
        jobs = []

        def run(name, context, assumption, top, mode, depth, destination):
            job = temporary / name
            job.mkdir()
            shutil.copy2(PROFILE / "examples" / (context + ".sv"), job / "model.sv")
            (job / "selection.vh").write_text(SELECTIONS[assumption], encoding="utf-8")
            before = {n: file_hash(job / n) for n in ("model.sv", "selection.vh")}
            recipe = f"[options]\nmode {mode}\ndepth {depth}\n\n[engines]\nsmtbmc z3\n\n[script]\nread -formal model.sv\nprep -top {top}\nwrite_json cells.json\n\n[files]\nmodel.sv\nselection.vh\n"
            (job / "task.sby").write_text(recipe, encoding="utf-8")
            command = [sys.executable, str(sby), "--yosys", str(tools / "bin/yosys"), "--smtbmc", str(tools / "bin/yosys-smtbmc"), "-d", "run", "task.sby"]
            native = subprocess.run(command, cwd=job, env=env, capture_output=True, text=True, timeout=120)
            shutil.copytree(job / "run", destination)
            (destination / "invocation.txt").write_text(native.stdout + native.stderr, encoding="utf-8")
            status = (destination / "status").read_text().split()[0]
            assert native.returncode == (0 if status == "PASS" else 2 if status == "FAIL" else -1), native.stdout
            jobs.append({"name": name, "native_status": status, "returncode": native.returncode, "mode": mode, "depth": depth})
            return command, before

        producers = {}
        for context in ("wake", "stream"):
            dest = output / (context + "-producer")
            command, before = run(context + "-producer", context, 2, "producer", "prove", 8, dest)
            producer_reference = finite_producer(context)
            assert producer_reference["violations"] == 0 and not producer_reference["hold_assumed"]
            producers[context] = (dest, command, before, producer_reference)
        cases = []
        for name, (context, assumption, proof_mode, proof_depth, cover_depth) in CASES.items():
            folder = output / name
            folder.mkdir()
            snapshots = {}
            for role, mode, depth in (("proof", proof_mode, proof_depth), ("cover", "cover", cover_depth)):
                command, before = run(name + "-" + role, context, assumption, "consumer", mode, depth, folder / role)
                ctx = capture_context(name + ":" + role, command, context, assumption)
                save(folder / (role + "-context.json"), ctx)
                snapshots[role] = capture(folder, role, ctx)
                assert snapshots[role]["fields"]["sources"]["value"] == before
            guarantee = None
            if assumption == 2:
                dest, command, before, producer_reference = producers[context]
                shutil.copytree(dest, folder / "producer")
                ctx = capture_context(context + ":producer", command, context, 2, True)
                save(folder / "producer-context.json", ctx)
                guarantee = capture(folder, "producer", ctx)
                assert guarantee["fields"]["sources"]["value"] == before
            reference = finite_consumer(context, assumption)
            assert reference["activation_reachable"] == (assumption != 1)
            assert reference["safety_counterexample_exists"] == (assumption == 0)
            witnesses = []
            for snapshot in snapshots.values():
                semantic = snapshot["fields"]["semantics"]["value"]
                if semantic in ("counterexample", "activation_witness"):
                    vcd = next(p for p in snapshot["provenance"]["witnesses"] if p.endswith(".vcd"))
                    witnesses.append(check_trace(context, assumption, folder / vcd, semantic))
            report = make_bundle(folder, name, context, assumption, snapshots["proof"], snapshots["cover"], guarantee)
            expected = 1 if name.endswith("unrestricted") else 2 if name.endswith("excluded") or name in ("wake-shallow-cover", "wake-short-bmc") else 0
            assert exit_code(report) == expected, report
            save(folder / "independent-reference.json", {"consumer": reference, "producer": producers[context][3] if guarantee else None, "witnesses": witnesses,
                  "limits": "Complete reachable-state enumeration of these small owned logical models only. Native bounded cover failure alone is not an unreachability proof."})
            cases.append({"case": name, "status": report["status"], "exit": expected, "reference": reference, "witnesses": witnesses})
            print(name + ": " + report["status"], flush=True)
        save(output / "summary.json", {"versions": versions, "native_jobs": jobs, "cases": cases,
                                       "method": "Actual SBY runs plus independent finite-state recurrence and native witness checks; owned logical examples, not physical or whole-system qualification."})


if __name__ == "__main__":
    main()
