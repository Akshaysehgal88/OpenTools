#!/usr/bin/env python3
"""Generate a native register block and simulate five access intent controls."""
import argparse
from importlib.metadata import version
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
from access_core import exit_code, require, review
from rdl_effects import capture
from create_example import CASES, SCOPE, event, policy_for, save, trace_for


def run(output, verilator, verilator_root):
    from systemrdl import RDLCompiler
    from peakrdl_regblock import RegblockExporter
    from peakrdl_regblock.cpuif.passthrough import PassthroughCpuif
    from peakrdl_regblock.udps import ALL_UDPS
    require(version("peakrdl-regblock") == "1.3.1", "Use peakrdl-regblock==1.3.1")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    for name in ("effects.rdl", "access_tb.sv"):
        shutil.copyfile(MODULE / "examples" / name, output / name)
    source = output / "effects.rdl"
    record = capture([source], ["effects.pending", "effects.diagnostic"], SCOPE, "unbuffered-effects-v1", True)
    save(output / "spec.json", record)
    compiler = RDLCompiler()
    for udp in ALL_UDPS:
        compiler.register_udp(udp)
    compiler.compile_file(str(source))
    generated = output / "generated"
    generated.mkdir()
    RegblockExporter().export(compiler.elaborate(), str(generated), cpuif_cls=PassthroughCpuif,
                             generate_hwif_report=True, err_if_bad_rw=True)
    native_version = subprocess.run([verilator, "--version"], check=True, capture_output=True, text=True).stdout.strip()
    require(native_version.startswith("Verilator 5.020"), "This native recipe is qualified with Verilator 5.020")
    with tempfile.TemporaryDirectory(prefix="opentools-effects-") as temporary:
        scratch = Path(temporary)
        runtime = scratch / "runtime"
        runtime.symlink_to(Path(verilator_root).resolve(), target_is_directory=True)
        env = os.environ.copy()
        env["VERILATOR_ROOT"] = str(runtime)
        for path in generated.iterdir():
            if path.suffix == ".sv":
                shutil.copyfile(path, scratch / path.name)
        shutil.copyfile(output / "access_tb.sv", scratch / "access_tb.sv")
        command = [verilator, "--binary", "--timing", "-Wno-fatal", "--top-module", "access_tb", "--Mdir", str(scratch / "obj"),
                   str(scratch / "effects_pkg.sv"), str(scratch / "effects.sv"), str(scratch / "access_tb.sv")]
        save(output / "build.command.json", command)
        compiled = subprocess.run(command, cwd=scratch, env=env, capture_output=True, text=True, timeout=180)
        (output / "build.stdout.txt").write_text(compiled.stdout, encoding="utf-8")
        (output / "build.stderr.txt").write_text(compiled.stderr, encoding="utf-8")
        require(compiled.returncode == 0, "Native RTL build failed; inspect retained diagnostics")
        binary = scratch / "obj" / "Vaccess_tb"
        shutil.copy2(binary, output / "Vaccess_tb")
        observed = subprocess.run([str(binary)], cwd=scratch, env=env, capture_output=True, text=True, timeout=20)
        (output / "native.stdout.txt").write_text(observed.stdout, encoding="utf-8")
        (output / "native.stderr.txt").write_text(observed.stderr, encoding="utf-8")
        require(observed.returncode == 0, "Native simulation failed")
    groups = {case: [] for case in CASES}
    for line_number, line in enumerate(observed.stdout.splitlines(), 1):
        if not line.startswith("ACCESS "):
            continue
        values = [int(value) for value in line.split()[1:]]
        require(len(values) == 14, "Unexpected native trace columns")
        scenario, seq, wr, diagnostic, before, after, read, data, be, biten, accepted, error, reset, hardware = values
        require(0 <= scenario < len(CASES) and wr in (0, 1) and diagnostic in (0, 1), "Invalid native event")
        item = event(seq, "diagnostic" if diagnostic else "pending", "write" if wr else "read", before, after, data, be, read)
        item.update(accepted=bool(accepted), error=bool(error), reset_inactive=not bool(reset), hardware_quiet=not bool(hardware),
                    evidence_ref="native.stdout.txt:" + str(line_number))
        if wr:
            item["bit_enable"] = biten
        groups[CASES[scenario]].append(item)
    summary = []
    expected_codes = {"rmw": 1, "direct-mask": 0, "disabled-low-byte": 1, "diagnostic-peek": 1, "diagnostic-consume": 0}
    for case, events in groups.items():
        require(len(events) == (2 if case == "rmw" else 1), "Missing native events")
        # Independent state reference: pending cause IDs in a set, not a register mask formula.
        pending = {0, 1}
        for item in events:
            require(item["accepted"] and not item["error"] and item["hardware_quiet"] and item["reset_inactive"], "Native handshake/premise failed")
            require(item["before"] == sum(2 ** bit for bit in pending), "Native pre-state contradicts independent model")
            if item["kind"] == "read":
                require(item["read_data"] & 3 == sum(2 ** bit for bit in pending), "Read sample mismatch")
                if item["register_ref"] == "effects.diagnostic":
                    pending.clear()
            else:
                pending.difference_update(bit for bit in range(2) if item["byte_enable"] & 1 and (item["write_data"] // (2 ** bit)) % 2)
            require(item["after"] == sum(2 ** bit for bit in pending), "Native post-state contradicts independent model")
        trace = trace_for(record, events)
        policy = policy_for(record, trace, case)
        result = review(record, trace, policy)
        require(exit_code(result) == expected_codes[case], "Unexpected review disposition for " + case)
        folder = output / case
        folder.mkdir()
        for name, value in (("trace", trace), ("policy", policy), ("report", result)):
            save(folder / (name + ".json"), value)
        summary.append({"case": case, "events": len(events), "status": result["status"], "findings": [f["kind"] for f in result["findings"]]})
    result = {"native": {"systemrdl-compiler": version("systemrdl-compiler"), "peakrdl-regblock": version("peakrdl-regblock"), "verilator": native_version},
              "cases": summary, "independent_reference": "Cause-ID set transitions, with reset/prime between scenarios; six observed accesses."}
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
