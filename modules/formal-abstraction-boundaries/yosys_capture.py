"""Read a qualified retained Yosys cutpoint/SAT run; never execute scripts."""
from __future__ import annotations
import re

from boundary_core import canonical, contained, file_hash, read_json, require, shape, text

VERSION = "Yosys 0.33 (git sha1 2584903a060)"
DOMAIN = [{"name": name, "width": 2} for name in ("source", "left", "right")]
SAT = "sat -set-def-inputs -set-def-formal -set-assumes -prove-asserts -show source -show left -show right -dump_json witness.json"
ENUM = "sat -all -set-def-inputs -set-def-formal -set-assumes -show source -show left -show right"
COMBINATIONAL = {"$add", "$xor", "$not", "$mux", "$eq", "$logic_and", "$logic_not", "$assert", "$assume", "$anyseq"}


def recipe(cut):
    lines = ["read -formal model.sv", "hierarchy -top top", "proc", "write_json before.json"]
    if cut:lines.append("cutpoint w:boundary")
    return "\n".join(lines + ["prep -top top", "write_json after.json", "tee -o property.log " + SAT, "tee -o relation.log " + ENUM]) + "\n"


def model(value):
    require(value.get("creator") == VERSION and set(value.get("modules", {})) == {"top"}, "Unqualified creator or hierarchy")
    top = value["modules"]["top"]
    require(set(top.get("ports", {})) == {"source", "left", "right"}, "Unqualified boundary ports")
    for name, port in top["ports"].items():
        require(len(port["bits"]) == 2 and port["direction"] == ("input" if name == "source" else "output"), "Unqualified port width/direction")
    require(isinstance(top.get("cells"), dict), "Missing native cells")
    require(all(c.get("type") in COMBINATIONAL for c in top["cells"].values()), "Unsupported cell class; sequential/memory/hierarchical models are outside this reader")
    require(top.get("netnames", {}).get("boundary", {}).get("bits") == top["ports"]["left"]["bits"] + top["ports"]["right"]["bits"], "Boundary bus does not map to the selected outputs")
    require(sum(c["type"] == "$assert" for c in top["cells"].values()) == 1, "Qualified model requires one assertion")
    return top


def formal_cells(top, kind):
    result = []
    for name, cell in sorted(top["cells"].items()):
        if cell["type"] == kind:
            source = cell.get("attributes", {}).get("src")
            require(text(source), "Missing native formal source")
            result.append({"id": name, "source": source})
    return result


def cone_ports(top):
    """Bit-level combinational fan-in observation, not semantic sufficiency."""
    drivers = {}
    for cell in top["cells"].values():
        inputs = [b for p, bits in cell.get("connections", {}).items() if cell["port_directions"][p] == "input" for b in bits]
        for port, bits in cell.get("connections", {}).items():
            if cell["port_directions"][port] == "output":
                for bit in bits:
                    require(bit not in drivers, "Multiple combinational drivers are unsupported")
                    drivers[bit] = inputs
    assertion = next(c for c in top["cells"].values() if c["type"] == "$assert")
    todo, seen = list(assertion["connections"]["A"]), set()
    while todo:
        bit = todo.pop()
        if bit in seen or not isinstance(bit, int):continue
        seen.add(bit);todo.extend(drivers.get(bit, []))
    return sorted(name for name, p in top["ports"].items() if seen.intersection(p["bits"]))


def table(block):
    pattern = r"^\s+\\(source|left|right)\s+(\d+)\s+([0-9a-fA-F]+)\s+([01]+)\s*$"
    values = {}
    for name, decimal, hexadecimal, binary in re.findall(pattern, block, flags=re.MULTILINE):
        require(name not in values and len(binary) == 2 and int(decimal) == int(hexadecimal, 16) == int(binary, 2), "Ambiguous native SAT tuple")
        values[name] = int(decimal)
    require(set(values) == {"source", "left", "right"}, "Incomplete native SAT tuple")
    return [values[name] for name in ("source", "left", "right")]


def enumeration(log):
    blocks = log.split("SAT solving finished - model found:")
    rows = [table(block) for block in blocks[1:]]
    if rows:
        end = re.findall(r"SAT solving finished - no more models found \(after (\d+) distinct solutions\)\.", log)
        require(len(end) == 1 and int(end[0]) == len(rows) and log.strip().endswith("distinct solutions)."), "Native enumeration is incomplete/truncated")
    else:
        require(log.strip().endswith("SAT solving finished - no model found."), "Native empty enumeration is not established")
    require(len(rows) == len({tuple(v) for v in rows}) and len(rows) <= 64, "Duplicate/excess selected native tuples")
    return sorted(rows)


def capture(root, workdir, context):
    shape(context, {"format", "run_ref", "scope", "property_ref", "original_command", "dependency_capture_complete", "dependency_basis_ref"})
    require(context["format"] == "opentools.yosys-boundary-context.v1" and text(context["run_ref"]), "Invalid capture context")
    shape(context["scope"], {"boundary_ref", "mode_ref", "model_class", "basis_ref"})
    require(all(v is None or text(v) for v in context["scope"].values()), "Invalid scope declaration")
    require(context["property_ref"] is None or text(context["property_ref"]), "Invalid property reference")
    require(context["dependency_capture_complete"] is None or type(context["dependency_capture_complete"]) is bool, "Invalid dependency declaration")
    require(context["dependency_basis_ref"] is None or text(context["dependency_basis_ref"]), "Invalid dependency basis")
    require(context["original_command"] is None or (isinstance(context["original_command"], list) and context["original_command"] and all(text(v) for v in context["original_command"])), "Invalid original command")
    require(contained(root, workdir).is_dir(), "Retained native directory missing")
    hashes = {}
    def read(relative, json=False):
        full = workdir + "/" + relative;path = contained(root, full)
        require(path.is_file(), "Missing native artifact: " + full)
        hashes[full] = file_hash(path)
        return read_json(path) if json else path.read_text(encoding="utf-8")
    script = read("run.ys")
    require(script in (recipe(False), recipe(True)), "Unqualified native script; it will not be executed")
    cut = script == recipe(True)
    for name in ("model.sv", "selection.vh"):read(name)
    sources = {name: hashes[workdir + "/" + name] for name in ("model.sv", "selection.vh")}
    before, after = model(read("before.json", True)), model(read("after.json", True))
    require(not any(c["type"] == "$anyseq" for c in before["cells"].values()), "Concrete prepared source already has arbitrary cut drivers")
    arbitrary = [c for c in after["cells"].values() if c["type"] == "$anyseq"]
    if cut:
        require(len(arbitrary) == 2 and {tuple(c["connections"]["Y"]) for c in arbitrary} ==
                {tuple(after["ports"][name]["bits"]) for name in ("left", "right")}, "Native cut drivers do not cover exactly the selected outputs")
    else:
        require(not arbitrary, "Unexpected arbitrary driver without native cutpoint")
    main = read("native.log")
    require(main.count("Making wire top.boundary a cutpoint.") == int(cut), "Native cutpoint log disagrees with the retained task")
    require("ERROR:" not in main, "Native execution error is unresolved")
    property_log = read("property.log")
    require(property_log in main, "Native property tee log differs from the original combined log")
    statuses = re.findall(r"SAT proof finished - (no model found: SUCCESS!|model found: FAIL!)", property_log)
    require(len(statuses) == 1, "Native property status missing/contradictory")
    outcome = "pass" if statuses[0].startswith("no model") else "fail"
    witness = None
    if outcome == "fail":
        witness = table(property_log)
        wave = read("witness.json", True)
        require(isinstance(wave.get("signal"), list), "Native WaveJSON witness missing")
        signals = {}
        for item in wave["signal"]:
            require(item.get("name") in ("source", "left", "right") and item["name"] not in signals and
                    item.get("wave") == "=4" and isinstance(item.get("data"), list) and len(item["data"]) == 2 and
                    re.fullmatch(r"[01]{2}", item["data"][0]) is not None and item["data"][1] == "", "Unqualified WaveJSON witness")
            signals[item["name"]] = int(item["data"][0], 2)
        require(set(signals) == {"source", "left", "right"} and [signals[k] for k in ("source", "left", "right")] == witness, "Native witness/log values differ")
    relation_log = read("relation.log")
    require(relation_log in main, "Native enumeration tee log differs from the original combined log")
    rows = enumeration(relation_log)
    if witness is not None:require(witness in rows, "Property counterexample absent from the native enumerated relation")
    return {"format": "opentools.yosys-boundary-snapshot.v1", "run_ref": context["run_ref"], "scope": context["scope"],
            "domain": DOMAIN, "property_ref": context["property_ref"], "sources": sources,
            "original_command": context["original_command"], "dependency_capture_complete": context["dependency_capture_complete"],
            "dependency_basis_ref": context["dependency_basis_ref"], "rows": rows, "outcome": outcome, "witness": witness,
            "cutpoints": ["left", "right"] if cut else [], "assumption_cells": formal_cells(after, "$assume"),
            "assertion_cells": {"before": formal_cells(before, "$assert"), "after": formal_cells(after, "$assert")},
            "cone_ports": {"before": cone_ports(before), "after": cone_ports(after)},
            "provenance": {"reader": "opentools.yosys-finite-cut.v1", "version": VERSION, "workdir": workdir,
                           "context": context, "integrity_files": hashes,
                           "declarations": "Scope, semantic references, original command and dependency completeness are supplied evidence, not authenticated native measurements."}}


def revalidate(snapshot, root):
    require(snapshot.get("format") == "opentools.yosys-boundary-snapshot.v1", "Unsupported snapshot")
    provenance = snapshot.get("provenance", {})
    require(provenance.get("reader") == "opentools.yosys-finite-cut.v1" and isinstance(provenance.get("integrity_files"), dict), "Native receipt missing")
    for relative, checksum in provenance["integrity_files"].items():
        require(file_hash(contained(root, relative)) == checksum, "Changed native artifact: " + relative)
    require(canonical(capture(root, provenance.get("workdir"), provenance.get("context"))) == canonical(snapshot), "Snapshot differs from its native/context evidence")
