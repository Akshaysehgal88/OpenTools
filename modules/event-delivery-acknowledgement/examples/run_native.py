#!/usr/bin/env python3
"""Observe assertion, IRQ/wake capture, delivery, service and source clearing."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

MODULE = Path(__file__).resolve().parents[1];sys.path.insert(0, str(MODULE))
from event_core import exit_code, require, review
from create_example import CASES, COUNTERS, config, journal_for, normalize, policy_for, reference, save, topology_for


def run(output, verilator, verilator_root):
    output = Path(output).resolve();output.mkdir(parents=True, exist_ok=False)
    source = output / "event_path.sv";shutil.copyfile(MODULE / "examples/event_path.sv", source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    native_version = subprocess.run([verilator, "--version"], check=True, capture_output=True, text=True).stdout.strip()
    require(native_version.startswith("Verilator 5.020"), "This recipe is qualified with Verilator 5.020")
    with tempfile.TemporaryDirectory(prefix="opentools-event-") as temporary:
        scratch = Path(temporary);runtime = scratch / "runtime";runtime.symlink_to(Path(verilator_root).resolve(), target_is_directory=True)
        env = os.environ.copy();env["VERILATOR_ROOT"] = str(runtime);shutil.copyfile(source, scratch / source.name)
        command = [verilator, "--binary", "--timing", "-Wno-fatal", "--top-module", "event_top", "--Mdir", str(scratch / "obj"), str(scratch / source.name)]
        save(output / "build.command.json", command)
        build = subprocess.run(command, cwd=scratch, env=env, capture_output=True, text=True, timeout=180)
        (output / "build.stdout.txt").write_text(build.stdout, encoding="utf-8");(output / "build.stderr.txt").write_text(build.stderr, encoding="utf-8")
        require(build.returncode == 0, "Native build failed; inspect retained diagnostics")
        binary = scratch / "obj/Vevent_top";shutil.copy2(binary, output / "Vevent_top")
        observed = subprocess.run([str(binary)], cwd=scratch, env=env, capture_output=True, text=True, timeout=20)
        (output / "native.stdout.txt").write_text(observed.stdout, encoding="utf-8");(output / "native.stderr.txt").write_text(observed.stderr, encoding="utf-8")
        require(observed.returncode == 0, "Native simulation failed")
    require(hashlib.sha256(source.read_bytes()).hexdigest() == source_hash, "Retained source changed during native run")
    rows, configurations = {i: [] for i in range(6)}, {}
    for number, line in enumerate(observed.stdout.splitlines(), 1):
        if line.startswith("CONFIG "):
            values = [int(v) for v in line.split()[1:]];require(len(values) == 5 and values[0] not in configurations, "Invalid native configuration");configurations[values[0]] = values[1:]
        elif line.startswith("EVENT "):
            values = [int(v) for v in line.split()[1:]];require(len(values) == 22 and values[0] in rows, "Invalid native columns");rows[values[0]].append((number, values[1:]))
    summary = []
    # Independent expected end-state distinctions, not inferred from report status.
    expected = [(1,1,1,1,1,0,0),(1,1,1,1,1,1,1),(1,0,0,0,0,1,1),(1,1,1,1,1,1,1),(1,0,0,0,0,1,1),(1,1,1,1,0,1,1)]
    for index, case in enumerate(CASES):
        cfg = config(case);require(configurations.get(index) == [int(cfg[k]) for k in ("held", "clear_source", "gated", "late_aon")], "Native configuration differs")
        require(len(rows[index]) == 12, "Missing native samples")
        topology = topology_for(case);topology["provenance"] = {"source_sha256": source_hash, "native_parameters": configurations[index], "role": "Owned source-reviewed event/route mapping; no controller or firmware parser."}
        samples = [];previous = dict.fromkeys(COUNTERS, 0);expected_rows = reference(case)
        for expected_step, (line_number, values) in enumerate(rows[index]):
            step, time_tick, source_status, irq_pending, wake_pending, *rest = values
            require(step == expected_step, "Native sample order differs")
            state = dict(zip(COUNTERS, rest[:9]));state.update(source_status=source_status, interrupt_pending=irq_pending, wake_pending=wake_pending)
            func_enable, aon_enable, power, irq_enable, route, wake_enable, sleep_window = rest[9:]
            require(all(state[k] == expected_rows[step]["state"][k] for k in state), "Native state/counters contradict independent phase reference: " + case + " step " + str(step))
            require([func_enable, aon_enable, power, irq_enable, route, wake_enable, sleep_window] == [expected_rows[step]["functional_enable"], expected_rows[step]["aon_enable"], 1, 1, 1, 1, expected_rows[step]["sleep_window"]], "Native control mismatch")
            row = {"step": step, "time_tick": time_tick, "state": state, "sleep_window": sleep_window}
            samples.append(normalize(row, previous, "native.stdout.txt:" + str(line_number)));previous = state
        require(tuple(previous[k] for k in COUNTERS[:7]) == expected[index], "Unexpected end-to-end native counts")
        journal = journal_for(topology, samples);policy = policy_for(topology, journal, case);report = review(topology, journal, policy)
        require(exit_code(report) == (1 if index in (0, 2, 5) else 0), "Unexpected event review disposition")
        folder = output / case;folder.mkdir()
        for name, value in (("topology", topology), ("journal", journal), ("policy", policy), ("report", report)): save(folder / (name + ".json"), value)
        summary.append({"case": case, "status": report["status"], "counts": dict(zip(COUNTERS[:7], expected[index])), "findings": report["findings"]})
    result = {"verilator": native_version, "source_sha256": source_hash, "cases": summary,
              "independent_reference": "Separate root/gated-edge old-state reference plus explicit final per-stage counts; 72 native rows."}
    save(output / "summary.json", result);return result


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument("directory");parser.add_argument("--verilator", required=True);parser.add_argument("--verilator-root", required=True);args = parser.parse_args()
    print(run(args.directory, args.verilator, args.verilator_root))


if __name__ == "__main__": main()
