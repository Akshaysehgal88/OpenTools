"""Read qualified retained Verilator bind/clock/coverage artifacts without executing them."""
from __future__ import annotations
import re
from itertools import product
import xml.etree.ElementTree as ET
from activation_core import InputError, canonical, contained, file_hash, read_json, require, scope, shape, text

INPUTS = {"aon_clk", "functional_clk", "reset", "mode", "event_req", "condition_ok"}
SOURCES = ("top.sv", "checker.sv", "composition.vh", "selection.vh", "main.cpp")
BUILD = ["--cc", "--exe", "--build", "-j", "2", "--assert", "--coverage-user", "-Wno-fatal", "--top-module", "top", "--Mdir", "obj", "top.sv", "main.cpp"]
XML = ["--xml-only", "--assert", "--coverage-user", "-Wno-fatal", "--top-module", "top", "--xml-output", "model.xml", "top.sv"]


def hierarchy(value):
    require(text(value), "Native hierarchy missing")
    return value.removeprefix("TOP.")


def expression(node, environment):
    if node.tag == "sampled":
        require(len(node) == 1, "Invalid native sampled expression")
        return expression(node[0], environment)
    if node.tag == "varref":
        name = node.get("name");require(name in environment, "Unresolved native port alias")
        return environment[name]
    if node.tag == "const":
        match = re.fullmatch(r"1'[hb]([01])", node.get("name", ""))
        require(match is not None, "Only scalar native constants are qualified")
        return {"op": "constant", "value": int(match[1])}
    operators = {"or": ("or", 2), "logor": ("or", 2), "and": ("and", 2), "logand": ("and", 2), "not": ("not", 1)}
    require(node.tag in operators, "Unsupported native binding expression: " + node.tag)
    op, count = operators[node.tag];require(len(node) == count, "Invalid native expression arity")
    return {"op": op, "args": [expression(child, environment) for child in node]}


def evaluate(node, drive):
    if node["op"] == "constant":return node["value"]
    if node["op"] == "signal":return drive[node["ref"].removeprefix("top.")]
    values = [evaluate(arg, drive) for arg in node["args"]]
    return int(any(values)) if node["op"] == "or" else int(all(values)) if node["op"] == "and" else int(not values[0])


def family(definition, clock_pin, checker):
    """Check the native lowered Boolean family, not arbitrary SVA adequacy."""
    roles = ("reset", "mode", "extra_disable", "event_req", "condition_ok")
    environment = {name: {"op": "signal", "ref": "top." + name} for name in roles}
    direct = definition.findall("always")
    require(len(direct) == 1, "Native sample observer body differs")
    formats = direct[0].findall(".//sformatf")
    expected_names = ["reset", "mode"] + (["extra_disable"] if checker else []) + ["event_req", "condition_ok"]
    require(len(formats) == 1 and formats[0].get("name", "").startswith("SAMPLE " if checker else "REQUIRED ") and
            [v.get("name") for v in formats[0].findall("varref")] == expected_names, "Native sample fields do not describe the qualified input roles")
    checks = {}
    labels = ("p_transition", "c_active_any", "c_active_normal", "c_active_risk") if checker else ("c_required_normal", "c_required_risk")
    for label in labels:
        bodies = [b for b in definition.findall("begin") if b.get("name") == label]
        require(len(bodies) == 1, "Qualified native property/cover label missing: " + label)
        senses = bodies[0].findall(".//senitem")
        require(len(senses) == 1 and senses[0].get("edgeType") == "POS" and len(senses[0]) == 1 and senses[0][0].get("name") == clock_pin,
                "Native property/cover clock differs from the qualified family")
        predicates = []
        for branch in bodies[0].iter("if"):
            try:predicate = expression(branch[0], environment)
            except InputError:continue  # Native opaque C++ gates are not decoded as Boolean RTL.
            predicates.append(predicate)
        require(len(predicates) == 1, "Native Boolean property/cover predicate is ambiguous")
        checks[label] = predicates[0]
        if label != "p_transition":require(len(bodies[0].findall(".//coverinc")) == 1, "Native cover increment missing")
    for values in product((0, 1), repeat=len(roles)):
        r = dict(zip(roles, values));enabled = not r["reset"] and not r["extra_disable"]
        expected = ({"p_transition": enabled and r["event_req"] and not r["condition_ok"],
                     "c_active_any": enabled and r["event_req"], "c_active_normal": enabled and not r["mode"] and r["event_req"],
                     "c_active_risk": enabled and r["mode"] and r["event_req"]} if checker else
                    {"c_required_normal": not r["reset"] and not r["mode"] and r["event_req"],
                     "c_required_risk": not r["reset"] and r["mode"] and r["event_req"]})
        require(all(bool(evaluate(predicate, r)) == bool(expected[label]) for label, predicate in checks.items()),
                "Native Boolean predicate differs from the qualified same-cycle property/cover family")


def xml_bindings(content):
    require("<!DOCTYPE" not in content and "<!ENTITY" not in content, "XML entities are unsupported")
    try:root = ET.fromstring(content)
    except ET.ParseError as exc:raise ValueError("Malformed native XML: " + str(exc)) from exc
    require(root.tag == "verilator_xml", "Unsupported native XML")
    definitions = root.findall("./netlist/module");modules = {m.get("name"): m for m in definitions}
    require(len(modules) == len(definitions) and "top" in modules and modules["top"].get("topModule") == "1", "Native top/module population differs")
    cells = list(root.find("cells").iter("cell"));paths = {c.get("hier"): c for c in cells}
    require(len(paths) == len(cells) and "top" in paths, "Ambiguous native hierarchy")
    top_ports = {v.get("name") for v in modules["top"].findall("var") if v.get("dir") == "input"}
    require(top_ports == INPUTS, "Qualified native top requires the six scalar drive inputs")
    types = {t.get("id"): t for t in root.findall("./netlist/typetable/basicdtype")}
    def scalar_inputs(definition):
        for var in definition.findall("var"):
            if var.get("dir") != "input":continue
            dtype = types.get(var.get("dtype_id"))
            require(dtype is not None and dtype.get("name") in ("logic", "bit") and
                    (dtype.get("left") is None and dtype.get("right") is None or dtype.get("left") == dtype.get("right") == "0"),
                    "Only scalar native checker/observer/target inputs are qualified")
    scalar_inputs(modules["top"])
    files = {f.get("id"): f.get("filename") for f in root.findall("./files/file")}

    def pins(instance, environment):
        result = {}
        for port in instance.findall("port"):
            name = port.get("name");require(name not in result and len(port) == 1, "Ambiguous native port mapping")
            result[name] = expression(port[0], environment)
        return result

    def selected(module_name, clock_pin, names, property_name=None):
        chosen = [c for c in cells if modules[c.get("submodname")].get("origName") == module_name]
        require(len(chosen) <= 1, "One selected checker/observer instance is qualified")
        if not chosen:return None
        cell = chosen[0];parts = cell.get("hier").split(".")
        require(len(parts) == 3 and parts[0] == "top", "Qualified binding has one target level under top")
        parent_path = ".".join(parts[:2]);parent = paths[parent_path];parent_module = modules[parent.get("submodname")]
        scalar_inputs(parent_module)
        top_instance = [i for i in modules["top"].findall("instance") if i.get("name") == parts[1]]
        require(len(top_instance) == 1, "Native target instance missing")
        environment = pins(top_instance[0], {name: {"op": "signal", "ref": "top." + name} for name in INPUTS})
        child = [i for i in parent_module.findall("instance") if i.get("name") == parts[2] and i.get("defName") == cell.get("submodname")]
        require(len(child) == 1, "Bound native checker/observer port instance missing")
        values = pins(child[0], environment);require(set(values) == names, "Native checker/observer port population differs")
        require(values[clock_pin].get("op") == "signal" and values[clock_pin]["ref"] in ("top.aon_clk", "top.functional_clk"), "Only direct settled scalar sample clocks are qualified")
        definition = modules[cell.get("submodname")]
        scalar_inputs(definition)
        family(definition, clock_pin, property_name is not None)
        if property_name:
            bodies = [b for b in definition.findall("begin") if b.get("name") == property_name]
            require(len(bodies) == 1, "Selected native property body missing")
            body = bodies[0]
        else:
            bodies = definition.findall("always");require(len(bodies) == 1, "Independent observer sample body differs")
            body = bodies[0]
        senses = body.findall(".//senitem")
        require(len(senses) == 1 and senses[0].get("edgeType") == "POS" and len(senses[0]) == 1 and
                senses[0][0].tag == "varref" and senses[0][0].get("name") == clock_pin, "Unqualified native property/observer sample edge")
        location = body.get("loc", "").split(",")
        require(len(location) == 5 and location[0] in files, "Native property/observer source location missing")
        return {"hier": cell.get("hier"), "target": parent_path, "target_module": parent_module.get("origName"),
                "pins": values, "edge": "posedge", "property_name": property_name,
                "source_ref": files[location[0]] + ":" + location[1]}
    checker = selected("activation_checker", "checker_clk", {"checker_clk", "reset", "mode", "extra_disable", "event_req", "condition_ok"}, "p_transition")
    observer = selected("obligation_observer", "observer_clk", {"observer_clk", "reset", "mode", "event_req", "condition_ok"})
    require(observer is not None, "Independent native obligation observer missing")
    return checker, observer


def coverage(content):
    lines = content.splitlines();require(lines and lines[0] == "# SystemC::Coverage-3", "Unqualified native coverage format")
    result = {}
    for line in lines[1:]:
        if not line.strip():continue
        match = re.fullmatch(r"C '(.*)' (\d+)", line);require(match is not None, "Malformed native coverage record")
        fields = {}
        for item in match[1].split("\x01"):
            if not item:continue
            pair = item.split("\x02");require(len(pair) == 2 and pair[0] not in fields, "Duplicate/invalid native cover field")
            fields[pair[0]] = pair[1]
        require(set(fields) == {"f", "l", "n", "page", "o", "h"} and fields["page"].startswith("v_user/"), "Only qualified native user cover points are supported")
        path = hierarchy(fields["h"]);require(path not in result and fields["l"].isdigit() and fields["n"].isdigit(), "Ambiguous cover point/source")
        result[path] = {"hier": path, "label": fields["o"], "count": int(match[2]), "source_ref": fields["f"] + ":" + fields["l"]}
    return result


def transcript(content):
    drive, required, samples, failures, ends = [], [], [], [], []
    columns = {"DRIVE": (8, ("tick", "aon_clk", "functional_clk", "reset", "mode", "event_req", "condition_ok", "assertions_enabled")),
               "REQUIRED": (5, ("tick", "reset", "mode", "event_req", "condition_ok")),
               "SAMPLE": (6, ("tick", "reset", "mode", "extra_disable", "event_req", "condition_ok"))}
    lines = content.splitlines()
    for line in lines:
        parts = line.split();require(parts, "Unexpected empty native trace line")
        kind = parts.pop(0)
        if kind in columns:
            count, names = columns[kind];path = hierarchy(parts.pop(0)) if kind != "DRIVE" else None
            require(len(parts) == count and all(p.isdigit() for p in parts), "Native trace field population differs")
            row = dict(zip(names, map(int, parts)));require(all(row[k] in (0, 1) for k in names if k != "tick"), "Native trace scalar is not Boolean")
            if path is not None:row["hier"] = path
            (drive if kind == "DRIVE" else required if kind == "REQUIRED" else samples).append(row)
        elif kind == "ASSERT_FAIL":
            require(len(parts) == 2 and parts[1].isdigit(), "Invalid native assertion failure")
            failures.append({"hier": hierarchy(parts[0]), "tick": int(parts[1])})
        elif kind == "RUN_END":
            require(len(parts) == 2 and all(p.isdigit() for p in parts), "Native completion marker differs")
            ends.append(tuple(map(int, parts)))
        else:require(False, "Unknown native trace record: " + kind)
    require(len(ends) == 1 and lines[-1].startswith("RUN_END "), "Native window completion missing/truncated")
    end, cycles = ends[0]
    require(1 <= cycles <= 64 and end == 2 * cycles and len(drive) == cycles and [r["tick"] for r in drive] == list(range(1, end, 2)) and
            all(r["aon_clk"] == 1 for r in drive), "Qualified native drive window/clock edges differ")
    return {"drive": drive, "required_samples": required, "checker_samples": samples, "assertion_failures": failures,
            "window": {"start_tick": 0, "end_tick": end, "cycles": cycles}}


def validate_observations(observations, checker, observer, points):
    def expected(entity, clock_pin, roles):
        result = []
        for row in observations["drive"]:
            if evaluate(entity["pins"][clock_pin], row):
                result.append({"tick": row["tick"], **{name: evaluate(entity["pins"][name], row) for name in roles}, "hier": entity["hier"]})
        return result
    required = expected(observer, "observer_clk", ("reset", "mode", "event_req", "condition_ok"))
    sampled = expected(checker, "checker_clk", ("reset", "mode", "extra_disable", "event_req", "condition_ok")) if checker else []
    require(required == observations["required_samples"], "Native independent observer samples disagree with clock/port/drive records")
    require(sampled == observations["checker_samples"], "Native checker samples are missing or disagree with clock/port/drive records")
    failure_rows = []
    for row in sampled:
        enabled = next(d["assertions_enabled"] for d in observations["drive"] if d["tick"] == row["tick"])
        if enabled and not row["reset"] and not row["extra_disable"] and row["event_req"] and not row["condition_ok"]:
            failure_rows.append({"hier": checker["hier"] + ".p_transition", "tick": row["tick"]})
    require(failure_rows == observations["assertion_failures"], "Native assertion actions disagree with the qualified sampled property family")
    counts = {observer["hier"] + ".c_required_normal": sum(not r["reset"] and not r["mode"] and r["event_req"] for r in required),
              observer["hier"] + ".c_required_risk": sum(not r["reset"] and r["mode"] and r["event_req"] for r in required)}
    if checker:
        # Verilator user covers remain independent of the runtime assertOn gate.
        active = [r for r in sampled if not r["reset"] and not r["extra_disable"] and r["event_req"]]
        counts.update({checker["hier"] + ".c_active_any": len(active), checker["hier"] + ".c_active_normal": sum(not r["mode"] for r in active),
                       checker["hier"] + ".c_active_risk": sum(bool(r["mode"]) for r in active)})
    require(set(points) == set(counts), "Native required/active cover population missing or unexpected")
    require(all(points[name]["count"] == value and points[name]["label"] == name.rsplit(".", 1)[1] for name, value in counts.items()),
            "Native cover counters disagree with sampled activation records")


def capture(root, workdir, context):
    shape(context, {"format", "run_ref", "scope", "family_basis_ref", "dependencies_complete", "dependency_basis_ref"})
    require(context["format"] == "opentools.activation-capture-context.v1" and text(context["run_ref"]), "Unsupported native capture context")
    scope(context["scope"])
    require(all(context[k] is None or text(context[k]) for k in ("family_basis_ref", "dependency_basis_ref")), "Invalid native basis reference")
    require(context["dependencies_complete"] is None or type(context["dependencies_complete"]) is bool, "Invalid dependency declaration")
    require(contained(root, workdir).is_dir(), "Retained native workdir missing")
    hashes = {}
    def read(name, json=False):
        relative = workdir + "/" + name;path = contained(root, relative)
        require(path.is_file(), "Missing native artifact: " + relative);hashes[relative] = file_hash(path)
        return read_json(path) if json else path.read_text(encoding="utf-8")
    version = read("version.txt").strip();require(version.startswith("Verilator 5.020 "), "Unqualified native compiler version")
    for name in SOURCES:read(name)
    sources = {name: hashes[workdir + "/" + name] for name in SOURCES}
    build, xml_command, run_command = read("build.command.json", True), read("xml.command.json", True), read("run.command.json", True)
    require(isinstance(build, list) and build[1:] == BUILD and isinstance(xml_command, list) and xml_command[1:] == XML and
            text(build[0]) and text(xml_command[0]), "Original build/XML flags outside qualified profile")
    require(isinstance(run_command, list) and len(run_command) == 3 and all(text(v) for v in run_command), "Original native run command missing")
    execution = read("execution.json", True);shape(execution, {"build_exit", "xml_exit", "run_exit", "compiled_binary_sha256"})
    require(all(type(execution[k]) is int and execution[k] == 0 for k in ("build_exit", "xml_exit", "run_exit")), "Native execution did not complete")
    binary = contained(root, workdir + "/Vtop");require(binary.is_file(), "Original compiled artifact missing")
    hashes[workdir + "/Vtop"] = file_hash(binary)
    with binary.open("rb") as stream:require(stream.read(4) == b"\x7fELF", "Qualified native artifact is an ELF executable; it is read, never run")
    require(hashes[workdir + "/Vtop"] == execution["compiled_binary_sha256"], "Compiled artifact identity differs from original execution record")
    for name in ("build.stdout.txt", "build.stderr.txt", "xml.stdout.txt", "xml.stderr.txt"):read(name)
    require(not read("run.stderr.txt").strip(), "Native runtime diagnostics unresolved")
    checker, observer = xml_bindings(read("model.xml"))
    observations = transcript(read("run.stdout.txt"));points = coverage(read("coverage.dat"))
    validate_observations(observations, checker, observer, points)
    return {"format": "opentools.verilator-activation.v1", "run_ref": context["run_ref"], "scope": context["scope"],
            "method": "bounded_simulation", "sources": sources, "family_basis_ref": context["family_basis_ref"],
            "dependencies_complete": context["dependencies_complete"], "dependency_basis_ref": context["dependency_basis_ref"],
            "checker": checker, "observer": observer, "covers": points, **observations,
            "native_outcome": "assertion_failure_observed" if observations["assertion_failures"] else "no_assertion_failure_observed",
            "provenance": {"reader": "opentools.verilator-activation-reader.v1", "version": version, "workdir": workdir,
                           "context": context, "integrity_files": hashes,
                           "declarations": "Run/scope, family semantics and dependency completeness are supplied evidence, not authenticated measurements. XML/trace/cover facts are structurally reconciled, not an adequacy or proof decision."}}


def revalidate(snapshot, root):
    require(snapshot.get("format") == "opentools.verilator-activation.v1", "Unsupported native snapshot")
    provenance = snapshot.get("provenance", {});require(provenance.get("reader") == "opentools.verilator-activation-reader.v1" and isinstance(provenance.get("integrity_files"), dict), "Native integrity receipt missing")
    for relative, checksum in provenance["integrity_files"].items():require(file_hash(contained(root, relative)) == checksum, "Changed native artifact: " + relative)
    require(canonical(capture(root, provenance.get("workdir"), provenance.get("context"))) == canonical(snapshot), "Snapshot differs from native/context evidence")
