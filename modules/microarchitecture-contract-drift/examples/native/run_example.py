#!/usr/bin/env python3
"""Elaborate and simulate two owned capacity profiles; preserve native observations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

MODULE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(MODULE / "examples"))
from contract_core import digest, markdown, require, review
from create_example import contract, record
from slang_capacity import capture_parameters


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def run_example(directory, verilator, verilator_root=None):
    directory = Path(directory).resolve()
    require(not directory.exists() and directory.parent.is_dir(), "Choose a new output directory with an existing parent")
    environment = os.environ.copy()
    if verilator_root:
        environment["VERILATOR_ROOT"] = str(Path(verilator_root).resolve())
    version = subprocess.run([verilator, "--version"], capture_output=True, text=True, check=True, env=environment).stdout
    require(re.match(r"Verilator 5\.020\b", version), "Native example is qualified with Verilator 5.020")
    require(sys.platform.startswith("linux"), "This native build recipe is qualified on Linux")
    directory.mkdir()
    shutil.copyfile(Path(__file__).with_name("capacity.sv"), directory / "capacity.sv")
    save(directory / "tool.json", {"version": version.strip(), "source_sha256": hashlib.sha256((directory / "capacity.sv").read_bytes()).hexdigest()})
    summaries = []
    # This temporary directory is owned by the recipe; GNU Make needs space-free paths.
    with tempfile.TemporaryDirectory(prefix="opentools-capacity-", dir="/tmp") as scratch:
        if environment.get("VERILATOR_ROOT"):
            runtime = Path(environment["VERILATOR_ROOT"]).resolve()
            require(runtime.is_dir(), "Verilator runtime directory is absent")
            alias = Path(scratch) / "verilator-runtime"
            alias.symlink_to(runtime, target_is_directory=True)
            environment["VERILATOR_ROOT"] = str(alias)
        source = Path(scratch) / "capacity.sv"
        shutil.copyfile(directory / "capacity.sv", source)
        for profile in ("queue", "tag"):
            baseline = None
            for name, capacity, demand in (("baseline", 8, 8), ("reduced", 4, 8), ("paired", 4, 4)):
                case = directory / f"{profile}-{name}"
                case.mkdir()
                template = record(demand, capacity, profile)
                mapping = {"format": "opentools.capacity-mapping.v1", "facts": [
                    {"id": f["id"], "symbol": "ISSUE_LIMIT" if f["id"] == "required" else "AVAILABLE",
                     "unit": f["unit"], "basis_ref": f["basis_ref"], "meaning_ref": "capacity.sv:" + ("issue-loop" if f["id"] == "required" else "queue-or-tag-pool")}
                    for f in template["facts"]]}
                parameters = {"CAPACITY": capacity, "ISSUE_LIMIT": demand, "RESERVED": 0, "PROFILE": int(profile == "tag")}
                snapshot = capture_parameters([str(directory / "capacity.sv")], [], "capacity_case", parameters,
                                              mapping, template["scope"], profile + "-" + name,
                                              "owned-native-capacity-v1", True, case / "slang.evidence")
                save(case / "snapshot.json", snapshot)
                policy = contract(snapshot, baseline)
                save(case / "contract.json", policy)
                report = review(snapshot, policy, baseline)
                save(case / "review.json", report)
                (case / "review.md").write_text(markdown(report), encoding="utf-8")
                build = Path(scratch) / f"{profile}-{name}"
                command = [str(verilator), "--binary", "--timing", "-Wno-fatal", "--top-module", "capacity_case",
                           "--Mdir", str(build), "-j", "2", *[f"-G{k}={v}" for k, v in parameters.items()], str(source)]
                save(case / "build.command.json", command)
                compiled = subprocess.run(command, capture_output=True, text=True, env=environment, timeout=120)
                (case / "build.stdout.txt").write_text(compiled.stdout, encoding="utf-8")
                (case / "build.stderr.txt").write_text(compiled.stderr, encoding="utf-8")
                require(compiled.returncode == 0, "Native build failed; inspect retained logs")
                shutil.copy2(build / "Vcapacity_case", case / "simulation")
                result = subprocess.run([str(case / "simulation")], capture_output=True, text=True, timeout=15)
                (case / "run.stdout.txt").write_text(result.stdout, encoding="utf-8")
                (case / "run.stderr.txt").write_text(result.stderr, encoding="utf-8")
                require(result.returncode == 0, "Native simulation failed")
                selected = [line[len("OT_RESULT "):] for line in result.stdout.splitlines() if line.startswith("OT_RESULT ")]
                require(len(selected) == 1, "Native observation absent or ambiguous")
                observation = json.loads(selected[0])
                # Independent set allocation reference, without native occupancy or busy state.
                identities = list(range(demand)) if profile == "queue" else [n % capacity for n in range(demand)]
                served = set(identities[:capacity])
                expected = {"issued": demand, "accepted": len(served), "violations": demand - len(served), "profile": int(profile == "tag")}
                require(observation == expected, "Native observations disagree with reference allocation")
                require((report["status"] == "review_required") == (observation["violations"] > 0),
                        "Declared contract and owned native behavior disagree")
                save(case / "observation.json", {"native": observation, "reference": expected,
                     "binary_sha256": hashlib.sha256((case / "simulation").read_bytes()).hexdigest(), "snapshot_sha256": digest(snapshot)})
                summaries.append({"case": case.name, "status": report["status"], "native": observation})
                if name == "baseline":
                    baseline = snapshot
    save(directory / "summary.json", {"format": "opentools.capacity-example.v1", "cases": summaries,
         "limits": "Owned no-retirement queue/tag profiles; not a production protocol, throughput or independent user-benefit qualification."})
    return summaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--verilator", required=True)
    parser.add_argument("--verilator-root")
    args = parser.parse_args()
    print(json.dumps(run_example(args.directory, args.verilator, args.verilator_root), indent=2))
