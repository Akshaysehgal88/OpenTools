"""Read a qualified original Yosys miter/SAT equivalence task; never execute it."""
from __future__ import annotations
from pathlib import Path, PurePosixPath
from itertools import product
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from applicability_core import canonical, digest, file_hash, read_json, require, shape, text

VERSION = "Yosys 0.33 (git sha1 2584903a060)"
PROFILE = "yosys-0.33-defined-combinational-miter-sat.v1"
REQUIRED_FIELDS = {"designs", "mapping", "model_boundary", "engine_profile", "partition"}
COMBINATIONAL = {"$add", "$and", "$or", "$xor", "$not", "$logic_and", "$logic_or", "$logic_not",
                 "$mux", "$eq", "$ne", "$eqx", "$reduce_or", "$reduce_and", "$reduce_bool"}


def contained(root, relative):
    require(text(relative) and "\\" not in relative and ":" not in relative, "Use relative POSIX evidence paths")
    value = PurePosixPath(relative)
    require(not value.is_absolute() and all(p not in ("", ".", "..") for p in relative.split("/")), "Evidence path escapes root")
    root = Path(root).resolve();target = (root / relative).resolve()
    require(target.is_relative_to(root), "Evidence path escapes root")
    current = root
    for part in value.parts:
        current /= part;require(not current.is_symlink(), "Linked evidence is unsupported")
    return target


def recipe(parameters, restriction=None):
    shape(parameters, {"gold", "gate"})
    lines = ["read_verilog reference.v implementation.v"]
    for side in ("gold", "gate"):
        require(isinstance(parameters[side], dict) and len(parameters[side]) <= 8, "Select at most eight parameters per compared design")
        for name, value in sorted(parameters[side].items()):
            require(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", name) is not None and type(value) is int and 0 <= value < 2 ** 31, "Use explicit unsigned integer parameter selections")
            lines.append("chparam -set " + name + " " + str(value) + " " + side)
    command = "sat -set-def-inputs -prove trigger 0 -show-inputs -show-outputs -dump_json witness.json"
    if restriction is not None:
        name, value = restriction
        require(isinstance(name, str) and re.fullmatch(r"in_[A-Za-z_][A-Za-z_0-9]*", name) is not None and type(value) is int and value in (0, 1), "Select one explicit scalar mode restriction")
        command += " -set " + name + " " + str(value)
    return "\n".join(lines + ["proc", "write_json compared.json", "miter -equiv -make_outputs -make_outcmp -flatten gold gate miter",
                              "prep -top miter", "write_json miter.json", "tee -o equivalence.log " + command]) + "\n"


def parse_recipe(content):
    lines = content.splitlines();require(lines and lines[0] == "read_verilog reference.v implementation.v", "Unsupported native input-read command")
    parameters = {"gold": {}, "gate": {}}
    for line in lines[1:]:
        if not line.startswith("chparam "):break
        match = re.fullmatch(r"chparam -set ([A-Za-z_][A-Za-z_0-9]*) (\d+) (gold|gate)", line)
        require(match is not None and match[1] not in parameters[match[3]], "Invalid/duplicate explicit parameter selection")
        parameters[match[3]][match[1]] = int(match[2])
    end = re.search(r" -set (in_[A-Za-z_][A-Za-z_0-9]*) ([01])$", lines[-1])
    restriction = (end[1], int(end[2])) if end else None
    require(recipe(parameters, restriction) == content, "Native equivalence script outside qualified profile; it is never executed")
    return parameters, restriction


def module(value):
    require(isinstance(value, dict) and isinstance(value.get("ports"), dict) and isinstance(value.get("cells"), dict), "Native module/port/cell data missing")
    require(not value.get("memories"), "Native memory model outside this profile")
    for name in ("blackbox", "whitebox"):
        require(value.get("attributes", {}).get(name, "0") in (0, "0", "00000000000000000000000000000000"), "Blackbox/whitebox semantics outside this profile")
    inputs, drivers, used = set(), {}, []
    for port in value["ports"].values():
        require(port.get("direction") in ("input", "output") and 1 <= len(port.get("bits", [])) <= 32 and port.get("signed", 0) == 0,
                "Qualified ports are unsigned input/output vectors of1..32 bits")
        if port["direction"] == "input":
            require(all(type(bit) is int and bit >= 0 for bit in port["bits"]), "Native input identities must be defined wire bits")
            inputs.update(port["bits"])
        else:used.extend(port["bits"])
    for cell in value["cells"].values():
        require(cell.get("type") in COMBINATIONAL, "State, constraints, unknown cells or unsupported native logic class")
        connections, directions = cell.get("connections", {}), cell.get("port_directions", {})
        require(set(connections) == set(directions) and all(d in ("input", "output") for d in directions.values()), "Native cell port directions missing")
        deps = [bit for name, bits in connections.items() if directions[name] == "input" for bit in bits]
        used.extend(deps)
        for name, bits in connections.items():
            if directions[name] == "output":
                for bit in bits:
                    require(type(bit) is int and bit not in drivers and bit not in inputs, "Native logic driver ambiguous")
                    drivers[bit] = deps
    visiting, complete = set(), set()
    for root in used:
        pending = [(root, False)]
        while pending:
            bit, leave = pending.pop()
            if bit in ("0", "1") or bit in inputs or bit in complete:continue
            require(type(bit) is int and bit in drivers, "Undriven/undefined native bit outside defined-input profile")
            if leave:
                visiting.remove(bit);complete.add(bit);continue
            require(bit not in visiting, "Combinational cycle outside this native profile")
            visiting.add(bit);pending.append((bit, True))
            pending.extend((dep, False) for dep in drivers[bit])
    return value


def interface(value):
    return {name: {"direction": p["direction"], "width": len(p["bits"]), "signed": False} for name, p in sorted(value["ports"].items())}


def correspondence(gold, gate, miter, mode_input):
    ports = interface(gold);require(ports == interface(gate), "Native gold/gate interface differs; no automatic matching is provided")
    require(all(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", n) is not None for n in ports), "Qualified native interface names are ordinary identifiers")
    ins = [n for n, p in ports.items() if p["direction"] == "input"]
    outs = [n for n, p in ports.items() if p["direction"] == "output"]
    require(1 <= len(ins) <= 16 and 1 <= len(outs) <= 16 and sum(ports[n]["width"] for n in ins) <= 128 and
            sum(ports[n]["width"] for n in outs) <= 128, "Native interface exceeds the bounded16-port/128-bit profile")
    require(mode_input in {"in_" + n for n in ins} and ports[mode_input[3:]]["width"] == 1, "Select an actual scalar common miter input as the mode")
    expected = {"in_" + n for n in ins} | {prefix + n for n in outs for prefix in ("gold_", "gate_", "cmp_")} | {"trigger"}
    require(set(miter["ports"]) == expected, "Native whole-miter port population differs")
    points = {"inputs": [], "outputs": []}
    for name in ins:
        observed = miter["ports"]["in_" + name]
        require(observed["direction"] == "input" and len(observed["bits"]) == ports[name]["width"], "Native common-input mapping differs")
        require(all(miter["netnames"].get(side + "." + name, {}).get("bits") == observed["bits"] for side in ("gold", "gate")), "Native designs do not share the declared input")
        points["inputs"].append({"gold": "gold." + name, "gate": "gate." + name, "miter_input": "in_" + name,
                                  "width": ports[name]["width"], "signed": False})
    cmp_bits = []
    for name in outs:
        a, b, cmp = (miter["ports"][prefix + name] for prefix in ("gold_", "gate_", "cmp_"))
        require(all(p["direction"] == "output" for p in (a, b, cmp)) and len(a["bits"]) == len(b["bits"]) == ports[name]["width"] and len(cmp["bits"]) == 1,
                "Native compare-output width/direction differs")
        require(miter["netnames"].get("gold." + name, {}).get("bits") == a["bits"] and
                miter["netnames"].get("gate." + name, {}).get("bits") == b["bits"], "Native output exposure does not bind the compared design")
        if cmp["bits"] == ["1"]:
            require(a["bits"] == b["bits"], "Unsupported optimized native equality")
        else:
            eqs = [c for c in miter["cells"].values() if c["type"] == "$eqx" and c["connections"]["Y"] == cmp["bits"]]
            require(len(eqs) == 1 and eqs[0]["connections"]["A"] == a["bits"] and eqs[0]["connections"]["B"] == b["bits"], "Native output comparator wiring differs")
        cmp_bits += cmp["bits"]
        points["outputs"].append({"gold": "gold." + name, "gate": "gate." + name, "native_compare": "cmp_" + name,
                                   "width": ports[name]["width"], "signed": False})
    trigger = miter["ports"]["trigger"]
    require(trigger["direction"] == "output" and len(trigger["bits"]) == 1, "Native trigger output differs")
    variables = sorted({b for b in cmp_bits if type(b) is int})
    drivers = {bit: c for c in miter["cells"].values() for port, bits in c["connections"].items()
               if c["port_directions"][port] == "output" for bit in bits}
    def protocol(bit, values):
        if bit in ("0", "1"):return int(bit)
        if bit in values:return values[bit]
        require(bit in drivers, "Native trigger driver missing")
        cell = drivers[bit];kind = cell["type"]
        require(kind in ("$not", "$logic_not", "$reduce_and", "$reduce_or", "$and", "$or"), "Unsupported native trigger protocol")
        pins = cell["connections"];a = [protocol(b, values) for b in pins["A"]]
        if kind in ("$not", "$logic_not"):require(len(a) == 1, "Native trigger negation is not scalar");return int(not a[0])
        if kind == "$reduce_and":return int(all(a))
        if kind == "$reduce_or":return int(any(a))
        b = [protocol(v, values) for v in pins["B"]];require(len(a) == len(b) == 1, "Native trigger gate is not scalar")
        return int(a[0] and b[0]) if kind == "$and" else int(a[0] or b[0])
    for combination in product((0, 1), repeat=len(variables)):
        values = dict(zip(variables, combination))
        require(protocol(trigger["bits"][0], values) == int(not all(protocol(bit, values) for bit in cmp_bits)),
                "Native trigger does not include every selected output comparator")
    return points


def witness(log, wave, ports):
    values = {}
    for name, decimal, hexadecimal, binary in re.findall(r"^\s+\\([A-Za-z_][A-Za-z_0-9]*)\s+(-?\d+)\s+([0-9a-fA-F]+)\s+([01]+)\s*$", log, re.MULTILINE):
        require(name in ports and name not in values and len(binary) == len(ports[name]["bits"]) and
                int(hexadecimal, 16) == int(binary, 2) and int(decimal) in (int(binary, 2), int(binary, 2) - 2 ** len(binary)), "Malformed native counterexample table")
        values[name] = int(binary, 2)
    require(set(values) == set(ports), "Native counterexample does not include all input/compare outputs")
    require(isinstance(wave.get("signal"), list), "Native WaveJSON missing")
    decoded = {}
    for item in wave["signal"]:
        name = item.get("name");require(name in ports and name not in decoded, "Unknown/duplicate native witness signal")
        width = len(ports[name]["bits"])
        if width == 1:
            require(item.get("wave") in ("04", "14") and "data" not in item, "Unqualified scalar native WaveJSON")
            decoded[name] = int(item["wave"][0])
        else:
            require(item.get("wave") == "=4" and isinstance(item.get("data"), list) and len(item["data"]) == 2 and
                    re.fullmatch("[01]{" + str(width) + "}", item["data"][0]) is not None and item["data"][1] == "", "Unqualified vector native WaveJSON")
            decoded[name] = int(item["data"][0], 2)
    require(values == decoded, "Native witness/log counterexample differs")
    return values


def capture(root, workdir, context):
    shape(context, {"format", "run_ref", "manifest_ref", "eco_ref", "mode_input", "scope_basis_ref", "dependencies_complete", "dependency_basis_ref"})
    require(context["format"] == "opentools.equivalence-capture-context.v1" and all(text(context[k]) for k in ("run_ref", "manifest_ref", "eco_ref")), "Invalid native capture context")
    require(all(context[k] is None or text(context[k]) for k in ("scope_basis_ref", "dependency_basis_ref")), "Invalid capture basis")
    require(context["dependencies_complete"] is None or type(context["dependencies_complete"]) is bool, "Invalid dependency completeness")
    require(text(context["mode_input"]) and re.fullmatch(r"in_[A-Za-z_][A-Za-z_0-9]*", context["mode_input"]) is not None, "Explicit native mode input selector required")
    require(contained(root, workdir).is_dir(), "Native workdir missing");hashes = {}
    def read(name, json=False):
        relative = workdir + "/" + name;path = contained(root, relative)
        require(path.is_file(), "Missing native artifact: " + relative);hashes[relative] = file_hash(path)
        return read_json(path) if json else path.read_text(encoding="utf-8")
    require(read("version.txt").strip() == VERSION, "Unqualified native version")
    script = read("run.ys");parameters, restriction = parse_recipe(script)
    require(restriction is None or restriction[0] == context["mode_input"], "Native restriction is not the selected scalar mode")
    mode = restriction[1] if restriction else None
    read("reference.v");read("implementation.v")
    compared, compiled = read("compared.json", True), read("miter.json", True)
    require(compared.get("creator") == compiled.get("creator") == VERSION and set(compared.get("modules", {})) == {"gold", "gate"} and
            set(compiled.get("modules", {})) == {"miter"}, "Compared native design/module inventory differs")
    gold, gate = (module(compared["modules"][n]) for n in ("gold", "gate"));miter = module(compiled["modules"]["miter"])
    for side, node in (("gold", gold), ("gate", gate)):
        actual = node.get("parameter_default_values", {})
        require(isinstance(actual, dict) and all(isinstance(v, str) and re.fullmatch("[01]+", v) for v in actual.values()), "Unknown/undefined native parameter identity")
        require(all(n in actual and int(actual[n], 2) == v for n, v in parameters[side].items()), "Native resolved parameter differs from its explicit selection")
    mapping = correspondence(gold, gate, miter, context["mode_input"])
    command, execution = read("command.json", True), read("execution.json", True)
    require(isinstance(command, list) and len(command) == 5 and all(text(v) for v in command) and command[1:] == ["-Q", "-T", "-s", "run.ys"], "Original native command missing/outside profile")
    shape(execution, {"exit_code"});require(type(execution["exit_code"]) is int and execution["exit_code"] == 0, "Native tool execution incomplete")
    main, log = read("native.log"), read("equivalence.log")
    require("ERROR:" not in main and log in main, "Native equivalence log missing/contradictory with original output")
    status = re.findall(r"SAT proof finished - (no model found: SUCCESS!|model found: FAIL!)", log)
    require(len(status) == 1, "Complete native equivalence verdict missing/ambiguous")
    require(re.findall(r"Import proof-constraint: \\trigger = 1'([01])", log) == ["0"], "Native proof target differs")
    constraints = re.findall(r"^Import set-constraint: (.+)$", log, re.MULTILINE)
    require(constraints == ([] if mode is None else ["\\" + context["mode_input"] + " = 1'" + str(mode)]), "Native input restriction differs from original task")
    defined = re.findall(r"Import def constraint for this timestep: \\([A-Za-z_][A-Za-z_0-9]*)", log)
    require(len(defined) == len(set(defined)) and set(defined) == {n for n, p in miter["ports"].items() if p["direction"] == "input"}, "Native input-definedness scope incomplete")
    outcome = "pass" if status[0].startswith("no model") else "fail";counterexample = None
    if outcome == "fail":
        counterexample = witness(log, read("witness.json", True), miter["ports"])
        require(counterexample["trigger"] == 1 and (mode is None or counterexample[context["mode_input"]] == mode), "Native failure witness outside the actual task")
        unequal = []
        for pair in mapping["outputs"]:
            name = pair["gold"].split(".", 1)[1];same = counterexample["gold_" + name] == counterexample["gate_" + name]
            require(counterexample["cmp_" + name] == int(same), "Native compare-point witness is inconsistent")
            if not same:unequal.append(name)
        require(unequal, "Native failure witness has no output mismatch")
    boundary = {"class": "defined_two_state_combinational", "state_cells": [], "memories": [], "blackboxes": [], "reset_history": "not_applicable_no_state"}
    values = {"designs": {side: {"top": side, "source_sha256": hashes[workdir + "/" + source],
                                 "parameters": node.get("parameter_default_values", {}), "compared_netlist_sha256": digest(node)}
                          for side, source, node in (("gold", "reference.v", gold), ("gate", "implementation.v", gate))},
              "mapping": mapping, "model_boundary": boundary,
              "engine_profile": {"profile": PROFILE, "version": VERSION, "proof_kind": "complete_combinational_equivalence"},
              "partition": {"id": "miter", "kind": "whole_miter", "compared_outputs": [p["gold"].split(".", 1)[1] for p in mapping["outputs"]], "excluded_points": []},
              "mode_constraint": {"signal": context["mode_input"], "allowed_values": [0, 1] if mode is None else [mode]}}
    fields = {k: {"value": v, "evidence_ref": workdir + ("/equivalence.log" if k == "mode_constraint" else "/miter.json" if k in ("mapping", "partition") else "/compared.json")} for k, v in values.items()}
    return {"format": "opentools.result-snapshot.v1", "run_ref": context["run_ref"], "manifest_ref": context["manifest_ref"],
            "execution": {"state": "completed", "evidence_ref": workdir + "/execution.json", "command": command, "executable_ref": VERSION,
                          "dependency_capture_complete": context["dependencies_complete"], "dependency_evidence_ref": context["dependency_basis_ref"]},
            "result": {"outcome": outcome, "native_status": "PASS" if outcome == "pass" else "FAIL", "complete": True,
                       "producer_run_ref": context["run_ref"], "evidence_ref": workdir + "/equivalence.log",
                       "artifact": {"path": workdir + "/equivalence.log", "sha256": hashes[workdir + "/equivalence.log"]}},
            "fields": fields, "provenance": {"reader": PROFILE, "context": context, "workdir": workdir, "integrity_files": hashes,
                                           "native_counterexample": counterexample,
                                           "declarations": "ECO/scope/dependency and approval references are supplied evidence, not authenticated measurements. Native verdict/constraint/point facts do not accept an ECO or establish broader sequential equivalence."}}


def revalidate(snapshot, root):
    provenance = snapshot.get("provenance", {})
    require(provenance.get("reader") == PROFILE and isinstance(provenance.get("integrity_files"), dict), "Unsupported native equivalence receipt")
    for relative, checksum in provenance["integrity_files"].items():require(file_hash(contained(root, relative)) == checksum, "Changed native artifact: " + relative)
    require(canonical(capture(root, provenance.get("workdir"), provenance.get("context"))) == canonical(snapshot), "Snapshot differs from original native/context evidence")
