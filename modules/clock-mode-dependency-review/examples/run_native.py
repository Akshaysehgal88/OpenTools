#!/usr/bin/env python3
"""Observe bounded boot/wake progress in an owned gated-clock sequencer."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
from clock_core import analyze, exit_code, require
from create_example import CASES, example, save


def reference(bad, wake, restore):
    # Independent event schedule: sample after each root rising edge, then update
    # the gate at the following falling edge. This is not prerequisite closure.
    gate, ready, done, edges = False, False, False, 0
    rows = []
    for step in range(8):
        old_ready = ready
        if gate:
            edges += 1
            ready |= not wake or edges >= 2
        done |= old_ready
        rows.append([step, 0, 1, int(gate), int(ready), int(done), edges, int(restore)])
        gate = (not wake or restore) and (not bad or ready)
    return rows


def run(output, verilator, verilator_root):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = output / "clock_path.sv"
    shutil.copyfile(MODULE / "examples/clock_path.sv", source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    native_version = subprocess.run([verilator, "--version"], check=True, capture_output=True, text=True).stdout.strip()
    require(native_version.startswith("Verilator 5.020"), "This native recipe is qualified with Verilator 5.020")
    with tempfile.TemporaryDirectory(prefix="opentools-clock-") as temporary:
        scratch = Path(temporary)
        runtime = scratch / "runtime"
        runtime.symlink_to(Path(verilator_root).resolve(), target_is_directory=True)
        env = os.environ.copy()
        env["VERILATOR_ROOT"] = str(runtime)
        shutil.copyfile(source, scratch / source.name)
        command = [verilator, "--binary", "--timing", "-Wno-fatal", "--top-module", "clock_top", "--Mdir", str(scratch / "obj"), str(scratch / source.name)]
        save(output / "build.command.json", command)
        build = subprocess.run(command, cwd=scratch, env=env, capture_output=True, text=True, timeout=180)
        (output / "build.stdout.txt").write_text(build.stdout, encoding="utf-8")
        (output / "build.stderr.txt").write_text(build.stderr, encoding="utf-8")
        require(build.returncode == 0, "Native build failed; inspect retained diagnostics")
        binary = scratch / "obj/Vclock_top"
        shutil.copy2(binary, output / "Vclock_top")
        observed = subprocess.run([str(binary)], cwd=scratch, env=env, capture_output=True, text=True, timeout=20)
        (output / "native.stdout.txt").write_text(observed.stdout, encoding="utf-8")
        (output / "native.stderr.txt").write_text(observed.stderr, encoding="utf-8")
        require(observed.returncode == 0, "Native simulation failed")
    require(hashlib.sha256(source.read_bytes()).hexdigest() == source_hash, "Source changed during native run")
    configurations, rows = {}, {i: [] for i in range(5)}
    for line in observed.stdout.splitlines():
        if line.startswith("CONFIG "):
            i, bad, wake, restore = [int(v) for v in line.split()[1:]]
            require(i not in configurations, "Duplicate native configuration")
            configurations[i] = [bad, wake, restore]
        elif line.startswith("CLOCK "):
            values = [int(v) for v in line.split()[1:]]
            require(len(values) == 9 and values[0] in rows, "Invalid native observation columns")
            rows[values[0]].append(values[1:])
    summary = []
    for i, case in enumerate(CASES):
        expected_config = [int(case.endswith("cycle")), int(case.startswith("wake")), int(case != "wake-no-restore")]
        require(configurations.get(i) == expected_config, "Observed native parameters differ from selected profile")
        require(rows[i] == reference(*expected_config), "Native trace contradicts independent event model: " + case)
        model, request = example(case)
        model["provenance"] = {"native_source_sha256": source_hash, "native_parameters": {"BAD": expected_config[0], "WAKE": expected_config[1], "restore_ready": expected_config[2]},
                               "role": "Owned, manually source-reviewed prerequisite mapping; not an automatic RTL extractor."}
        from clock_core import digest
        request["model_sha256"] = digest(model)
        result = analyze(model, request)
        expected_code = 0 if case.endswith("fixed") else 1
        require(exit_code(result) == expected_code, "Unexpected static disposition")
        final = rows[i][-1]
        require(bool(final[5]) == (expected_code == 0), "Bounded native progress differs from static control")
        folder = output / case
        folder.mkdir()
        observation = {"format": "opentools.clock.owned-observation.v1", "scope": model["scope"], "model_sha256": digest(model),
            "source_sha256": source_hash, "native_parameters": configurations[i],
            "columns": ["step", "reset", "request", "gate_enabled", "worker_ready", "transition_done", "worker_edges", "restore_ready"],
            "rows": rows[i], "interpretation": "Observed completion within eight root edges" if final[5] else "No completion observed within eight root edges; not an unbounded deadlock proof"}
        for name, value in (("model", model), ("request", request), ("report", result), ("observation", observation)):
            save(folder / (name + ".json"), value)
        summary.append({"case": case, "static_status": result["status"], "observed_completion": bool(final[5]), "worker_edges": final[6], "candidate_cycles": len(result["candidate_cycles"])})
    result = {"verilator": native_version, "source_sha256": source_hash, "cases": summary,
              "independent_reference": "Explicit root rising/falling-edge state schedule; 40 sampled rows across five native instances."}
    save(output / "summary.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--verilator", required=True)
    parser.add_argument("--verilator-root", required=True)
    args = parser.parse_args()
    print(run(args.directory, args.verilator, args.verilator_root))


if __name__ == "__main__":
    main()
