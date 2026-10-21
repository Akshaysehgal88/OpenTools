"""Run owned native finite cutpoint controls with an existing Linux Yosys."""
from __future__ import annotations
import argparse
from itertools import product
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
from boundary_core import digest, exit_code, file_hash, markdown, review
from yosys_capture import DOMAIN, VERSION, capture, recipe

CASES = {family + "-" + kind: (family, kind) for family in ("operands", "tags")
         for kind in ("independent", "exact", "unsupported-green", "restricted")}


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:stream.write(json.dumps(value, indent=2) + "\n")


def allowed(family):
    return [list(row) for row in product(range(4), repeat=3) if (row[1] + row[2] == 3 if family == "operands" else row[1] == row[2])]


def reference(family, kind, abstract):
    result = []
    for source, left, right in product(range(4), repeat=3):
        if abstract:
            if kind != "independent" and not (left + right == 3 if family == "operands" else left == right):continue
            if kind == "exact" and left != (source + 1) % 4:continue
            if kind == "restricted" and (source != 0 or left != 1):continue
        else:
            expected_left = (source + 1) % 4
            expected_right = 3 - expected_left if family == "operands" else expected_left
            if kind == "unsupported-green" and source == 2:expected_right = 1 if family == "operands" else 0
            if (left, right) != (expected_left, expected_right):continue
        result.append([source, left, right])
    return result


def context(name, command, family):
    return {"format": "opentools.yosys-boundary-context.v1", "run_ref": "owned:" + name,
            "scope": {"boundary_ref": family + ":selected-output-pair", "mode_ref": family + ":all-four-source-values",
                      "model_class": "finite_combinational_relation", "basis_ref": "owned:" + family + ":stateless-interface-review"},
            "property_ref": family + ":complement-sum" if family == "operands" else family + ":tag-identity",
            "original_command": command, "dependency_capture_complete": True,
            "dependency_basis_ref": "owned:fixed-single-source-and-selection-header"}


def bundle(folder, name, family, snapshots):
    contract = {"format": "opentools.abstraction-boundary.v1", "review_ref": "owned:" + name,
                "claim": "The selected abstract property and boundary relation support the original stateless integration obligation for all declared source values.",
                "owner_ref": "owned-model-review-owner", "scope_ref": "owned:" + name + ":finite-boundary",
                "scope": snapshots["concrete"]["scope"], "domain": DOMAIN,
                "property": {"ref": snapshots["concrete"]["property_ref"], "basis_ref": "owned:" + family + ":independent-required-predicate",
                             "allowed_rows": allowed(family)},
                "views": {view: {"run_ref": snapshot["run_ref"], "sources": snapshot["sources"],
                                 "basis_ref": "owned:" + name + ":reviewed-input-identities"} for view, snapshot in snapshots.items()},
                "obligations": [{"cell_id": cell["id"], "owner_ref": "owned-abstraction-owner",
                                 "basis_ref": "owned:" + name + ":check-concrete-inclusion-not-just-green-proof"}
                                for cell in snapshots["abstract"]["assumption_cells"]]}
    evidence = {"format": "opentools.abstraction-evidence.v1", "contract_sha256": digest(contract), **snapshots}
    report = review(contract, evidence, folder)
    save(folder / "contract.json", contract);save(folder / "evidence.json", evidence);save(folder / "report.json", report)
    (folder / "report.md").write_text(markdown(report), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--yosys-prefix", type=Path, required=True, help="Existing prefix with bin/yosys and any needed lib/x86_64-linux-gnu runtime")
    args = parser.parse_args()
    if os.name != "posix":parser.error("Native recipe is qualified on Linux; saved-data review also works on Windows")
    output = args.output.resolve();output.mkdir(parents=True, exist_ok=False)
    prefix = args.yosys_prefix.resolve()
    env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib/x86_64-linux-gnu") + os.pathsep + os.environ.get("LD_LIBRARY_PATH", ""))
    executable = str(prefix / "bin/yosys")
    version = subprocess.run([executable, "-V"], env=env, capture_output=True, text=True, check=True).stdout.strip()
    assert version == VERSION, version
    results = []
    for name, (family, kind) in CASES.items():
        folder = output / name;folder.mkdir();snapshots = {};references = {}
        for view in ("concrete", "abstract"):
            abstract = view == "abstract";dest = folder / view;dest.mkdir()
            shutil.copy2(MODULE / "examples" / (family + ".sv"), dest / "model.sv")
            flags = ["BUG"] if kind == "unsupported-green" else []
            if abstract and kind != "independent":flags.append("CORRELATED")
            if abstract and kind == "exact":flags.append("EXACT")
            if abstract and kind == "restricted":flags.append("RESTRICTED")
            (dest / "selection.vh").write_text("".join("`define " + flag + "\n" for flag in flags) or "// No restrictions\n", encoding="utf-8")
            before = {n: file_hash(dest / n) for n in ("model.sv", "selection.vh")}
            (dest / "run.ys").write_text(recipe(abstract), encoding="utf-8")
            command = [executable, "-Q", "-T", "-s", "run.ys"]
            native = subprocess.run(command, cwd=dest, env=env, capture_output=True, text=True, timeout=60)
            (dest / "native.log").write_text(native.stdout + native.stderr, encoding="utf-8")
            assert native.returncode == 0, native.stderr
            ctx = context(name + ":" + view, command, family);save(folder / (view + "-context.json"), ctx)
            snapshots[view] = capture(folder, view, ctx)
            assert snapshots[view]["sources"] == before
            ref = reference(family, kind, abstract);assert snapshots[view]["rows"] == ref
            property_pass = all(row in allowed(family) for row in ref)
            assert snapshots[view]["outcome"] == ("pass" if property_pass else "fail")
            if not property_pass:
                assert snapshots[view]["witness"] in ref and snapshots[view]["witness"] not in allowed(family)
            references[view] = {"rows": ref, "required_property_holds": property_pass}
        report = bundle(folder, name, family, snapshots)
        assert exit_code(report) == (0 if kind == "exact" else 1), report
        expected_direction = {"exact": "equal", "independent": "conservative_expansion", "unsupported-green": "incomparable", "restricted": "restrictive_subset"}[kind]
        assert report["observations"]["relation_direction"] == expected_direction
        save(folder / "independent-reference.json", {"method": "Exhaustive independently computed arithmetic/tag tuple relations, not an interpretation of native proof color.", **references})
        results.append({"case": name, "status": report["status"], "direction": expected_direction,
                        "native_outcomes": {k: s["outcome"] for k, s in snapshots.items()},
                        "tuples": {k: len(s["rows"]) for k, s in snapshots.items()}})
        print(name + ": " + expected_direction, flush=True)
    save(output / "summary.json", {"version": version, "native_invocations": 16, "native_sat_queries": 32,
                                   "cases": results, "limits": "One stateless two-output finite cutpoint class and selected predicate; not sequential/memory refinement or arbitrary abstraction soundness."})


if __name__ == "__main__":main()
