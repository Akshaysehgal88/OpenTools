#!/usr/bin/env python3
"""Observe partial reset, coordinated reset, drain and retained-event replay."""
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
from reset_core import digest, exit_code, require, review
from create_example import CASES, STATE_NAMES, inventory_for, journal_for, policy_for, reference_rows, save


def run(output, verilator, verilator_root):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = output / "reset_path.sv"
    shutil.copyfile(MODULE / "examples/reset_path.sv", source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    native_version = subprocess.run([verilator, "--version"], check=True, capture_output=True, text=True).stdout.strip()
    require(native_version.startswith("Verilator 5.020"), "This native recipe is qualified with Verilator 5.020")
    with tempfile.TemporaryDirectory(prefix="opentools-reset-") as temporary:
        scratch = Path(temporary)
        runtime = scratch / "runtime"
        runtime.symlink_to(Path(verilator_root).resolve(), target_is_directory=True)
        env = os.environ.copy()
        env["VERILATOR_ROOT"] = str(runtime)
        shutil.copyfile(source, scratch / source.name)
        command = [verilator, "--binary", "--timing", "-Wno-fatal", "--top-module", "reset_top", "--Mdir", str(scratch / "obj"), str(scratch / source.name)]
        save(output / "build.command.json", command)
        build = subprocess.run(command, cwd=scratch, env=env, capture_output=True, text=True, timeout=180)
        (output / "build.stdout.txt").write_text(build.stdout, encoding="utf-8")
        (output / "build.stderr.txt").write_text(build.stderr, encoding="utf-8")
        require(build.returncode == 0, "Native build failed; inspect retained diagnostics")
        binary = scratch / "obj/Vreset_top"
        shutil.copy2(binary, output / "Vreset_top")
        observed = subprocess.run([str(binary)], cwd=scratch, env=env, capture_output=True, text=True, timeout=20)
        (output / "native.stdout.txt").write_text(observed.stdout, encoding="utf-8")
        (output / "native.stderr.txt").write_text(observed.stderr, encoding="utf-8")
        require(observed.returncode == 0, "Native simulation failed")
    require(hashlib.sha256(source.read_bytes()).hexdigest() == source_hash, "Source changed during native run")
    configurations, rows = {}, {i: [] for i in range(5)}
    for line_number, line in enumerate(observed.stdout.splitlines(), 1):
        if line.startswith("CONFIG "):
            values = [int(v) for v in line.split()[1:]]
            require(len(values) == 5 and values[0] not in configurations, "Invalid native configuration")
            configurations[values[0]] = values[1:]
        elif line.startswith("RESET "):
            values = [int(v) for v in line.split()[1:]]
            require(len(values) == 15 and values[0] in rows, "Invalid native sample columns")
            rows[values[0]].append((line_number, values[1:]))
    summary = []
    for index, case in enumerate(CASES):
        expected_config = [int(index >= 3), int(index == 4), int(index == 1), int(index == 2)]
        require(configurations.get(index) == expected_config, "Native parameters differ from selected profile")
        require(len(rows[index]) == 4, "Missing phase observations")
        inventory = inventory_for(case)
        inventory["provenance"] = {"native_source_sha256": source_hash, "native_parameters": configurations[index], "role": "Owned manually reviewed state-owner mapping; no general reset-tree extractor."}
        phases = []
        expected_states = reference_rows(case)
        for expected_phase, (line_number, values) in enumerate(rows[index]):
            phase, *data = values
            require(phase == expected_phase and data[:6] == [expected_states[phase][key] for key in STATE_NAMES], "Native state contradicts independent reset schedule")
            producer_reset, consumer_reset, quiet, initialized, replay_ready, clock_available, root_edges = data[6:]
            require([producer_reset, consumer_reset] == [int(phase == 1 and index == 1), int(phase == 1)], "Native reset scope mismatch")
            require(root_edges == [3, 4, 4, 6][phase], "Unexpected native clock journal")
            phases.append({"phase": ("before", "held", "released", "post")[phase], "values": dict(zip(STATE_NAMES, data[:6])),
                "reset_active": {"producer-reset": bool(producer_reset), "consumer-reset": bool(consumer_reset)}, "hardware_quiet": bool(quiet),
                "prerequisites": {"clock_available": bool(clock_available), "consumer_initialized": bool(initialized), "replay_ready": bool(replay_ready)},
                "native_root_edges": root_edges, "evidence_ref": "native.stdout.txt:" + str(line_number)})
        journal = journal_for(inventory, phases)
        policy = policy_for(inventory, journal, case)
        report = review(inventory, journal, policy)
        require(exit_code(report) == (1 if index in (0, 3) else 0), "Unexpected reset review disposition")
        folder = output / case
        folder.mkdir()
        for name, value in (("inventory", inventory), ("journal", journal), ("policy", policy), ("report", report)): save(folder / (name + ".json"), value)
        summary.append({"case": case, "status": report["status"], "findings": [f["kind"] for f in report["findings"]],
                        "post_orphan": expected_states[3]["orphan"], "post_replay": expected_states[3]["replay"]})
    result = {"verilator": native_version, "source_sha256": source_hash, "cases": summary,
              "independent_reference": "Explicit reset and delivery schedule, separately checking state transitions and reset/clock controls; 20 native phase rows."}
    save(output / "summary.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--verilator", required=True)
    parser.add_argument("--verilator-root", required=True)
    args = parser.parse_args()
    print(run(args.directory, args.verilator, args.verilator_root))


if __name__ == "__main__": main()
