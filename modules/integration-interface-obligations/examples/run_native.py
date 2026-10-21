#!/usr/bin/env python3
"""Compare connected interface facts with actual receipt/completion/cancel behavior."""
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

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
from port_capture import capture, require
from create_inputs import inputs


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def run_native(directory, verilator, verilator_root=None):
    directory = Path(directory).resolve()
    require(not directory.exists() and directory.parent.is_dir(), "Choose a new directory with an existing parent")
    require(sys.platform.startswith("linux"), "Native build recipe is qualified on Linux")
    environment = os.environ.copy()
    if verilator_root:
        environment["VERILATOR_ROOT"] = str(Path(verilator_root).resolve())
    version = subprocess.run([verilator, "--version"], check=True, capture_output=True, text=True, env=environment).stdout.strip()
    require(re.match(r"Verilator 5\.020\b", version), "Qualified native example requires Verilator 5.020")
    directory.mkdir()
    shutil.copyfile(Path(__file__).with_name("handshake.sv"), directory / "handshake.sv")
    save(directory / "tool.json", {"version": version, "source_sha256": hashlib.sha256((directory / "handshake.sv").read_bytes()).hexdigest()})
    results = []
    with tempfile.TemporaryDirectory(prefix="opentools-interface-", dir="/tmp") as tmp:
        scratch = Path(tmp)
        if environment.get("VERILATOR_ROOT"):
            runtime = Path(environment["VERILATOR_ROOT"]).resolve()
            require(runtime.is_dir(), "Verilator runtime is absent")
            (scratch / "runtime").symlink_to(runtime, target_is_directory=True)
            environment["VERILATOR_ROOT"] = str(scratch / "runtime")
        shutil.copyfile(directory / "handshake.sv", scratch / "handshake.sv")
        for pulse in (0, 1):
            for name, bad_ack, bad_cancel, cancel_cycle in (("valid-late", 0, 0, 3), ("receipt-as-done", 1, 0, 3),
                                                          ("cancel-as-discard", 0, 1, 3), ("valid-early", 0, 0, 1)):
                case = directory / f"{'pulse' if pulse else 'level'}-{name}"
                case.mkdir()
                records = inputs()
                parameters = {"BAD_ACK": bad_ack, "BAD_CANCEL": bad_cancel,
                              "PULSE_REQUEST": pulse, "CANCEL_CYCLE": cancel_cycle}
                records["scope"]["configuration_ref"] = case.name
                structural = capture([str(directory / "handshake.sv")], [], "behavior_top", parameters,
                                     records["selection"], records["scope"], True, case / "ports.evidence")
                save(case / "connections.json", structural)
                require(structural["status"] == "connected_within_profile", "Owned direct interface did not resolve")
                build = scratch / case.name
                command = [verilator, "--binary", "--timing", "-Wno-fatal", "--top-module", "behavior_top",
                           "--Mdir", str(build), "-j", "2", *[f"-G{k}={v}" for k, v in parameters.items()], str(scratch / "handshake.sv")]
                save(case / "build.command.json", command)
                compiled = subprocess.run(command, capture_output=True, text=True, env=environment, timeout=120)
                (case / "build.stdout.txt").write_text(compiled.stdout, encoding="utf-8")
                (case / "build.stderr.txt").write_text(compiled.stderr, encoding="utf-8")
                require(compiled.returncode == 0, "Native build failed; inspect retained logs")
                shutil.copy2(build / "Vbehavior_top", case / "simulation")
                native = subprocess.run([str(case / "simulation")], capture_output=True, text=True, timeout=15)
                (case / "run.stdout.txt").write_text(native.stdout, encoding="utf-8")
                (case / "run.stderr.txt").write_text(native.stderr, encoding="utf-8")
                require(native.returncode == 0, "Native run failed")
                events = [json.loads(line[len("OT_EVENT "):]) for line in native.stdout.splitlines() if line.startswith("OT_EVENT ")]
                summaries = [json.loads(line[len("OT_RESULT "):]) for line in native.stdout.splitlines() if line.startswith("OT_RESULT ")]
                require(len(events) == 9 and len(summaries) == 1, "Native observation population is incomplete")
                # Reference event schedule derives from the declared four-step lifecycle,
                # not from the DUT's internal age/started/inflight variables.
                early = cancel_cycle == 1
                expected = []
                for cycle in range(1, 10):
                    accepted, complete = int(cycle == 1), int(cycle == 4 and not early)
                    expected.append({"cycle": cycle, "request": int(cycle == 1 or not pulse and cycle == 2),
                                     "accepted": accepted, "committed": int(cycle >= 2 and not early),
                                     "completed": complete, "cancel": int(cycle == cancel_cycle),
                                     "server_discarded": int(cycle == 1 and early),
                                     "client_done": accepted if bad_ack else complete,
                                     "client_discarded": int(cycle == cancel_cycle) if bad_cancel else int(cycle == 1 and early)})
                require(events == expected, "Native event trace disagrees with independent schedule")
                verdict = {"premature_completion": sum(e["client_done"] and not e["completed"] for e in expected),
                           "false_discard": sum(e["client_discarded"] and e["committed"] for e in expected)}
                require(summaries[0] == verdict, "Native checker counts disagree with reference events")
                save(case / "observations.json", {"scope": records["scope"], "native": events, "reference": expected,
                     "verdict": verdict, "parameters": parameters,
                     "binary_sha256": hashlib.sha256((case / "simulation").read_bytes()).hexdigest()})
                results.append({"case": case.name, "port_status": structural["status"], "behavior": verdict})
    save(directory / "summary.json", {"cases": results,
         "limits": "Owned single-outstanding pulse/level profiles; no general protocol, CDC/RDC, reset-recovery or production qualification."})
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--verilator", required=True)
    parser.add_argument("--verilator-root")
    args = parser.parse_args()
    print(json.dumps(run_native(args.directory, args.verilator, args.verilator_root), indent=2))
