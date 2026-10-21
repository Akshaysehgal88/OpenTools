#!/usr/bin/env python3
"""Generate owned maps, compile the software table and exercise an RTL decoder."""
import argparse
import copy
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
from address_core import ATTRIBUTES, PERMISSIONS, compare, require
from create_example import maps, policy


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def flags(window):
    return sum(int(window[group][key]) << bit for bit, (group, key) in enumerate(
        [("permissions", k) for k in PERMISSIONS] + [("attributes", k) for k in ATTRIBUTES]))


def software_capture(record, case, scratch, compiler):
    """Native GCC reads an owned C table; this is not a general C-source parser."""
    rows = []
    for index, window in enumerate(record["windows"]):
        require(all(re.fullmatch(r"[A-Za-z0-9_-]+", window[k]) for k in ("id", "initiator_ref", "target_ref")), "Owned table identifiers required")
        rows.append('{"%s","%s",0x%xULL,0x%xULL,"%s",0x%xULL,%du}' % (
            window["id"], window["initiator_ref"], window["base"], window["size"], window["target_ref"], window["target_base"], flags(window)))
    header = ('struct region {const char *id,*initiator; unsigned long long base,size; const char *target; '
              'unsigned long long target_base; unsigned flags;};\nstatic const struct region regions[]={\n'
              + ',\n'.join(rows) + '\n};\n')
    (case / "software_map.h").write_text(header, encoding="utf-8")
    code = r'''#include <stdio.h>
#include "software_map.h"
int main(void) {
  for (unsigned i=0; i<sizeof(regions)/sizeof(regions[0]); ++i) {
    const struct region *r=&regions[i];
    printf("{\"id\":\"%s\",\"initiator_ref\":\"%s\",\"base\":%llu,\"size\":%llu,\"target_ref\":\"%s\",\"target_base\":%llu,\"flags\":%u}\n",
      r->id,r->initiator,r->base,r->size,r->target,r->target_base,r->flags);
  }
  return 0;
}
'''
    (case / "probe.c").write_text(code, encoding="utf-8")
    for name in ("software_map.h", "probe.c"):
        shutil.copyfile(case / name, scratch / name)
    command = [compiler, "-std=c11", "-O0", str(scratch / "probe.c"), "-o", str(scratch / "probe")]
    save(case / "software.command.json", command)
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=30)
    (case / "software.stderr.txt").write_text(compiled.stderr, encoding="utf-8")
    require(compiled.returncode == 0, "Native software table compilation failed")
    native = subprocess.run([str(scratch / "probe")], check=True, capture_output=True, text=True, timeout=10)
    (case / "software.stdout.txt").write_text(native.stdout, encoding="utf-8")
    captured = copy.deepcopy(record)
    captured["windows"] = []
    for index, line in enumerate(native.stdout.splitlines()):
        row = json.loads(line)
        value = row.pop("flags")
        row["permissions"] = {k: bool(value & (1 << bit)) for bit, k in enumerate(PERMISSIONS)}
        row["attributes"] = {k: bool(value & (1 << (bit + 3))) for bit, k in enumerate(ATTRIBUTES)}
        row["evidence_ref"] = "software_map.h:region-" + str(index)
        captured["windows"].append(row)
    require(len(captured["windows"]) == len(record["windows"]), "Native software population is incomplete")
    captured["provenance"] = {"reader": "owned-gcc-table-v1", "header_sha256": hashlib.sha256((case / "software_map.h").read_bytes()).hexdigest(),
                              "probe_sha256": hashlib.sha256((case / "probe.c").read_bytes()).hexdigest()}
    return captured


def decoder_source(record, addresses, initiators, targets):
    lines = ["module address_top;", "int unsigned initiator=0,address=0,operation=0,secure=0;",
             "int hit_count,allowed,target; longint unsigned offset; int unsigned attributes;"]
    lines += ["always_comb begin", "hit_count=0;allowed=0;target=-1;offset=0;attributes=0;"]
    for window in record["windows"]:
        base, end = window["base"], window["base"] + window["size"]
        lines += [f"if (initiator=={initiators.index(window['initiator_ref'])} && address>=32'h{base:x} && address<32'h{end:x}) begin",
                  f"if (hit_count==0) begin target={targets.index(window['target_ref'])};offset=64'd{window['target_base']}+(address-32'h{base:x});attributes={flags(window)};",
                  "allowed=((attributes & (1<<operation))!=0) && (((attributes & 32)==0) || secure);end",
                  "hit_count=hit_count+1;end"]
    lines += ["end", f"int unsigned queries[{len(addresses)}] = '{{" + ",".join(f"32'h{a:x}" for a in addresses) + "};",
              "initial begin", f"for (int i=0;i<{len(initiators)};i++) for (int a=0;a<{len(addresses)};a++)",
              "for (int op=0;op<3;op++) for (int sec=0;sec<2;sec++) begin",
              "initiator=i;address=queries[a];operation=op;secure=sec;#1;"]
    keys = ["initiator", "address", "operation", "secure", "matches", "allowed", "target", "offset", "attributes"]
    fmt = "OT_ACCESS {" + ",".join(r'\"' + key + r'\":%0d' for key in keys) + "}"
    signals = ["hit_count" if key == "matches" else key for key in keys]
    lines += ['$display("' + fmt + '",' + ",".join(signals) + ");", "end", "$finish;end", "endmodule"]
    return "\n".join(lines) + "\n"


def byte_reference(record):
    """Expand owned tiny windows into byte entries instead of repeating RTL ranges."""
    entries = {}
    for window in record["windows"]:
        for offset in range(window["size"]):
            entries.setdefault((window["initiator_ref"], window["base"] + offset), []).append(
                (window["target_ref"], window["target_base"] + offset, flags(window)))
    return entries


def expected_access(table, query, initiators, targets):
    entries = table.get((initiators[query["initiator"]], query["address"]), [])
    if not entries:
        return {**query, "matches": 0, "allowed": 0, "target": -1, "offset": 0, "attributes": 0}
    target, offset, attributes = entries[0]
    allowed = bool(attributes & (1 << query["operation"])) and (not attributes & 32 or query["secure"])
    return {**query, "matches": len(entries), "allowed": int(bool(allowed)), "target": targets.index(target),
            "offset": offset, "attributes": attributes}


def run_native(directory, verilator, verilator_root=None, compiler="gcc"):
    require(sys.platform.startswith("linux"), "This native example is qualified on Linux")
    directory = Path(directory).resolve()
    require(not directory.exists() and directory.parent.is_dir(), "Choose a new directory with an existing parent")
    environment = os.environ.copy()
    if verilator_root:
        environment["VERILATOR_ROOT"] = str(Path(verilator_root).resolve())
    native_version = subprocess.run([verilator, "--version"], check=True, capture_output=True, text=True, env=environment).stdout.strip()
    gcc_version = subprocess.run([compiler, "-dumpfullversion"], check=True, capture_output=True, text=True).stdout.strip()
    target = subprocess.run([compiler, "-dumpmachine"], check=True, capture_output=True, text=True).stdout.strip()
    require(re.match(r"Verilator 5\.020\b", native_version) and gcc_version == "13.3.0" and target == "x86_64-linux-gnu", "Qualified native profile is Verilator5.020/GCC13.3 x86_64-linux-gnu")
    directory.mkdir()
    save(directory / "tools.json", {"verilator": native_version, "gcc": gcc_version, "target": target})
    summaries = []
    with tempfile.TemporaryDirectory(prefix="opentools-address-", dir="/tmp") as tmp:
        scratch = Path(tmp)
        if environment.get("VERILATOR_ROOT"):
            runtime = Path(environment["VERILATOR_ROOT"]).resolve()
            require(runtime.is_dir(), "Verilator runtime is absent")
            (scratch / "runtime").symlink_to(runtime, target_is_directory=True)
            environment["VERILATOR_ROOT"] = str(scratch / "runtime")
        for name in ("valid", "overlap", "permission", "hole", "paired"):
            case = directory / name
            case.mkdir()
            work = scratch / name
            work.mkdir()
            hardware, supplied_software = maps(name)
            software = software_capture(supplied_software, case, work, compiler)
            all_windows = hardware["windows"] + software["windows"]
            addresses = sorted({a for w in all_windows for a in range(max(0, w["base"] - 1), w["base"] + w["size"] + 1)})
            initiators = sorted({w["initiator_ref"] for w in all_windows})
            targets = sorted({w["target_ref"] for w in all_windows})
            source = decoder_source(hardware, addresses, initiators, targets)
            (case / "decoder.sv").write_text(source, encoding="utf-8")
            (work / "decoder.sv").write_text(source, encoding="utf-8")
            hardware["provenance"] = {"generator": "owned-two-initiator-v1", "source_sha256": hashlib.sha256(source.encode()).hexdigest()}
            for window in hardware["windows"]:
                window["evidence_ref"] = "decoder.sv:generated-" + window["id"]
            rules = policy(hardware, software)
            report = compare(hardware, software, rules)
            for label, value in (("hardware", hardware), ("software", software), ("policy", rules), ("review", report)):
                save(case / (label + ".json"), value)
            command = [verilator, "--binary", "--timing", "-Wno-fatal", "--top-module", "address_top", "--Mdir", str(work / "obj"), "-j", "2", str(work / "decoder.sv")]
            save(case / "build.command.json", command)
            built = subprocess.run(command, capture_output=True, text=True, env=environment, timeout=120)
            (case / "build.stdout.txt").write_text(built.stdout, encoding="utf-8")
            (case / "build.stderr.txt").write_text(built.stderr, encoding="utf-8")
            require(built.returncode == 0, "Native decoder build failed; inspect retained logs")
            shutil.copy2(work / "obj/Vaddress_top", case / "simulation")
            process = subprocess.run([str(case / "simulation")], capture_output=True, text=True, timeout=20)
            (case / "run.stdout.txt").write_text(process.stdout, encoding="utf-8")
            (case / "run.stderr.txt").write_text(process.stderr, encoding="utf-8")
            require(process.returncode == 0, "Native decoder simulation failed")
            accesses = [json.loads(line[len("OT_ACCESS "):]) for line in process.stdout.splitlines() if line.startswith("OT_ACCESS ")]
            require(len(accesses) == len(initiators) * len(addresses) * 6, "Native query population is incomplete")
            hw_table, sw_table = byte_reference(hardware), byte_reference(software)
            disagreements = []
            for access in accesses:
                query = {k: access[k] for k in ("initiator", "address", "operation", "secure")}
                require(access == expected_access(hw_table, query, initiators, targets), "Native decoder disagrees with independent byte reference")
                expected = expected_access(sw_table, query, initiators, targets)
                if access != expected:
                    disagreements.append({"query": query, "native": access, "software_expected": expected})
            require(bool(disagreements) == (name in ("overlap", "permission", "hole")), "Native/software disagreement control failed")
            require((report["status"] == "review_required") == bool(disagreements), "Map review does not match owned native control")
            save(case / "observations.json", {"initiators": initiators, "targets": targets, "addresses": addresses,
                 "query_count": len(accesses), "native": accesses, "disagreements": disagreements,
                 "binary_sha256": hashlib.sha256((case / "simulation").read_bytes()).hexdigest()})
            summaries.append({"case": name, "status": report["status"], "queries": len(accesses), "disagreements": len(disagreements)})
    save(directory / "summary.json", {"cases": summaries, "limits": "Owned generated 32-bit byte decoder and C table; selected windows/boundaries only, no general translation or security qualification."})
    return summaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--verilator", required=True)
    parser.add_argument("--verilator-root")
    parser.add_argument("--cc", default="gcc")
    args = parser.parse_args()
    print(json.dumps(run_native(args.directory, args.verilator, args.verilator_root, args.cc), indent=2))
