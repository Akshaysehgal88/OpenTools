"""Run owned bound-checker controls with an existing Linux Verilator build."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from reference_model import CASES, CONFIGS, RUNTIME_OFF
EXAMPLES = Path(__file__).resolve().parent
SOURCES = ("top.sv", "checker.sv", "composition.vh", "selection.vh", "main.cpp")


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:stream.write(json.dumps(value, indent=2) + "\n")


def checksum(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def collect(output, verilator, verilator_root):
    output = Path(output).resolve();output.mkdir(parents=True, exist_ok=False)
    version = subprocess.run([verilator, "--version"], capture_output=True, text=True, check=True).stdout.strip()
    if not version.startswith("Verilator 5.020 "):raise ValueError("Native recipe is qualified with Verilator 5.020")
    builds = {};results = []
    with tempfile.TemporaryDirectory(prefix="opentools-activation-") as temporary:
        temporary = Path(temporary);(temporary / "runtime").symlink_to(Path(verilator_root).resolve(), target_is_directory=True)
        env = dict(os.environ, VERILATOR_ROOT=str(temporary / "runtime"))
        for name, (family, config, clean) in CASES.items():
            key = family + "-" + config
            if key not in builds:
                work = temporary / key;work.mkdir();retained = output / "builds" / key;retained.mkdir(parents=True)
                shutil.copy2(EXAMPLES / (family + ".sv"), work / "top.sv")
                for source in ("checker.sv", "composition.vh", "main.cpp"):shutil.copy2(EXAMPLES / source, work / source)
                (work / "selection.vh").write_text("".join("`define " + flag + "\n" for flag in CONFIGS[config]) or "// Active binding\n", encoding="utf-8")
                before = {source: checksum(work / source) for source in SOURCES}
                build_cmd = [verilator, "--cc", "--exe", "--build", "-j", "2", "--assert", "--coverage-user", "-Wno-fatal", "--top-module", "top", "--Mdir", "obj", "top.sv", "main.cpp"]
                build = subprocess.run(build_cmd, cwd=work, env=env, capture_output=True, text=True, timeout=180)
                (retained / "build.stdout.txt").write_text(build.stdout, encoding="utf-8");(retained / "build.stderr.txt").write_text(build.stderr, encoding="utf-8")
                save(retained / "build.command.json", build_cmd)
                if build.returncode:raise ValueError("Native build failed: " + key)
                xml_cmd = [verilator, "--xml-only", "--assert", "--coverage-user", "-Wno-fatal", "--top-module", "top", "--xml-output", "model.xml", "top.sv"]
                xml = subprocess.run(xml_cmd, cwd=work, env=env, capture_output=True, text=True, timeout=30)
                (retained / "xml.stdout.txt").write_text(xml.stdout, encoding="utf-8");(retained / "xml.stderr.txt").write_text(xml.stderr, encoding="utf-8")
                save(retained / "xml.command.json", xml_cmd)
                if xml.returncode:raise ValueError("Native XML generation failed: " + key)
                for source in SOURCES:
                    if checksum(work / source) != before[source]:raise ValueError("Build input changed: " + source)
                    shutil.copy2(work / source, retained / source)
                shutil.copy2(work / "model.xml", retained / "model.xml");shutil.copy2(work / "obj/Vtop", retained / "Vtop")
                (retained / "version.txt").write_text(version + "\n", encoding="utf-8")
                builds[key] = retained
            retained = builds[key];case = output / name;run = case / "run";run.mkdir(parents=True)
            for path in retained.iterdir():
                if path.is_file():shutil.copy2(path, run / path.name)
            command = [str(retained / "Vtop"), "clean" if clean else "fault", "off" if name in RUNTIME_OFF else "on"]
            native = subprocess.run(command, cwd=run, env=env, capture_output=True, text=True, timeout=30)
            (run / "run.stdout.txt").write_text(native.stdout, encoding="utf-8");(run / "run.stderr.txt").write_text(native.stderr, encoding="utf-8")
            save(run / "run.command.json", command)
            save(run / "execution.json", {"build_exit": 0, "xml_exit": 0, "run_exit": native.returncode,
                                           "compiled_binary_sha256": checksum(run / "Vtop")})
            if native.returncode:raise ValueError("Native execution did not complete: " + name)
            results.append({"case": name, "family": family, "configuration": config, "clean": clean,
                            "runtime_assertions": name not in RUNTIME_OFF, "source_sha256": {source: checksum(run / source) for source in SOURCES}})
            print(name + ": native data retained", flush=True)
    summary = {"version": version, "native_builds": len(builds), "native_runs": len(results), "cases": results,
               "limits": "Bounded stable-before-edge scalar SVA-bind observations and user cover counters. No unbounded formal proof or property adequacy qualification."}
    save(output / "collection.json", summary);return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path);parser.add_argument("--verilator", required=True);parser.add_argument("--verilator-root", required=True)
    parser.add_argument("--raw-only", action="store_true", help="Retain native artifacts without creating review records")
    args = parser.parse_args()
    if os.name != "posix":parser.error("Native recipe is qualified on Linux; saved-data review is portable")
    collect(args.output, args.verilator, args.verilator_root)
    if not args.raw_only:
        from create_example import from_native
        from_native(args.output)


if __name__ == "__main__":main()
