#!/usr/bin/env python3
"""Observe unsafe local-idle acknowledgement and owner-level drain controls."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

MODULE = Path(__file__).resolve().parents[1];sys.path.insert(0, str(MODULE))
from quiescence_core import exit_code, require, review
from create_example import CASES, FIELDS, config, inventory_for, journal_for, normalize, policy_for, reference, save


def run(output, verilator, verilator_root):
    output = Path(output).resolve();output.mkdir(parents=True, exist_ok=False)
    source = output / "quiescence_path.sv";shutil.copyfile(MODULE / "examples/quiescence_path.sv", source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    native_version = subprocess.run([verilator, "--version"], check=True, capture_output=True, text=True).stdout.strip()
    require(native_version.startswith("Verilator 5.020"), "This recipe is qualified with Verilator 5.020")
    with tempfile.TemporaryDirectory(prefix="opentools-quiescence-") as temporary:
        scratch = Path(temporary);runtime = scratch / "runtime";runtime.symlink_to(Path(verilator_root).resolve(), target_is_directory=True)
        env = os.environ.copy();env["VERILATOR_ROOT"] = str(runtime);shutil.copyfile(source, scratch / source.name)
        command = [verilator, "--binary", "--timing", "-Wno-fatal", "--top-module", "quiescence_top", "--Mdir", str(scratch / "obj"), str(scratch / source.name)]
        save(output / "build.command.json", command)
        build = subprocess.run(command, cwd=scratch, env=env, capture_output=True, text=True, timeout=180)
        (output / "build.stdout.txt").write_text(build.stdout, encoding="utf-8");(output / "build.stderr.txt").write_text(build.stderr, encoding="utf-8")
        require(build.returncode == 0, "Native build failed; inspect retained diagnostics")
        binary = scratch / "obj/Vquiescence_top";shutil.copy2(binary, output / "Vquiescence_top")
        observed = subprocess.run([str(binary)], cwd=scratch, env=env, capture_output=True, text=True, timeout=20)
        (output / "native.stdout.txt").write_text(observed.stdout, encoding="utf-8");(output / "native.stderr.txt").write_text(observed.stderr, encoding="utf-8")
        require(observed.returncode == 0, "Native simulation failed")
    require(hashlib.sha256(source.read_bytes()).hexdigest() == source_hash, "Retained source changed during native run")
    rows, configurations = {i: [] for i in range(6)}, {}
    for number, line in enumerate(observed.stdout.splitlines(), 1):
        if line.startswith("CONFIG "):
            values = [int(v) for v in line.split()[1:]];require(len(values) == 5 and values[0] not in configurations, "Invalid native configuration");configurations[values[0]] = values[1:]
        elif line.startswith("QUIESCENCE "):
            values = [int(v) for v in line.split()[1:]];require(len(values) == 19 and values[0] in rows, "Invalid native sample columns");rows[values[0]].append((number, values[1:]))
    summary = []
    expected = [(3,5,6,0,1),(7,9,10,1,1),(3,4,None,0,1),(8,9,None,1,1),(7,8,9,1,1),(7,9,10,1,2)]
    for index, case in enumerate(CASES):
        cfg = config(case);require(configurations.get(index) == [int(cfg[k]) for k in ("local_only", "power_mode", "no_isolation", "bad_admission")], "Native profile identity differs")
        require(len(rows[index]) == 12, "Missing native samples")
        inventory = inventory_for(case);inventory["provenance"] = {"source_sha256": source_hash, "native_parameters": configurations[index], "role": "Owned source-reviewed owner census; no UPF/native power-aware exporter."}
        samples = [];expected_rows = reference(case)
        for expected_step, (line_number, values) in enumerate(rows[index]):
            step, time_tick, *data = values
            require(step == expected_step, "Native sample sequence differs")
            state = dict(zip(FIELDS, data[:12]));issue, transfer, request, ready = data[12:]
            require(state == expected_rows[step]["state"], "Native state/counters contradict independent token ledger: " + case + " step " + str(step))
            require([issue, transfer, request, ready] == [expected_rows[step][k] for k in ("issue", "transfer", "request", "return_ready")], "Native input schedule differs")
            require(state["accepted"] - state["handed"] == state["local_pending"] and state["handed"] - state["returned"] == state["remote_pending"] and state["received"] == state["returned"], "Native owner accounting is not conserved")
            samples.append(normalize({"step": step, "time_tick": time_tick, "state": state, "request": request}, "native.stdout.txt:" + str(line_number)))
        actual = tuple(next((s["seq"] for s in samples if s["controls"][k] is v), None) for k, v in (("drain_ack", True), ("clock_available", False), ("power_available", False)))
        actual += (samples[-1]["native_counters"]["returned"], samples[-1]["native_counters"]["accepted"])
        require(actual == expected[index], "Unexpected native milestone/return control")
        journal = journal_for(inventory, samples);policy = policy_for(inventory, journal, case);report = review(inventory, journal, policy)
        require(exit_code(report) == (0 if index in (1, 3) else 1), "Unexpected quiescence disposition")
        folder = output / case;folder.mkdir()
        for name, value in (("inventory", inventory), ("journal", journal), ("policy", policy), ("report", report)): save(folder / (name + ".json"), value)
        summary.append({"case": case, "status": report["status"], "milestones": actual[:3], "returned": actual[3], "accepted": actual[4], "findings": report["findings"]})
    result = {"verilator": native_version, "source_sha256": source_hash, "cases": summary,
              "independent_reference": "Token ownership ledger, acceptance/handoff/return conservation and explicit milestone/control expectations; 72 native rows."}
    save(output / "summary.json", result);return result


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument("directory");parser.add_argument("--verilator", required=True);parser.add_argument("--verilator-root", required=True);args = parser.parse_args()
    print(run(args.directory, args.verilator, args.verilator_root))


if __name__ == "__main__": main()
