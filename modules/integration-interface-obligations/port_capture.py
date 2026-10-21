#!/usr/bin/env python3
"""Capture selected direct port connections using the Slang elaborated model."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import sys


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", value), "Plain identifiers required")
    return value


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda value: require(False, "Non-finite JSON value"))


def capture(sources, dependencies, top, parameters, selection, scope, complete_inputs, evidence_dir):
    require(version("pyslang") == "12.0.0", "Qualified native profile requires pyslang 12.0.0")
    import pyslang
    from pyslang import ast, syntax
    identifier(top)
    require(type(complete_inputs) is bool, "Input completeness must be boolean")
    require(isinstance(parameters, dict) and all(identifier(k) and type(v) is int for k, v in parameters.items()), "Invalid integer overrides")
    require(isinstance(scope, dict) and set(scope) == {"project_ref", "interface_ref", "configuration_ref", "mode_ref"}
            and all(isinstance(v, str) and v.strip() for v in scope.values()), "Declare exact scope")
    require(isinstance(selection, dict) and set(selection) == {"format", "links"}
            and selection["format"] == "opentools.port-selection.v1" and isinstance(selection["links"], list)
            and selection["links"], "Select source/sink port links")
    ids = set()
    for item in selection["links"]:
        require(isinstance(item, dict) and set(item) == {"id", "source", "sink"}
                and isinstance(item["id"], str) and item["id"].strip() and item["id"] not in ids, "Unique link IDs required")
        ids.add(item["id"])
        for key in ("source", "sink"):
            require(isinstance(item[key], str) and len(item[key].split(".")) >= 2
                    and all(identifier(n) for n in item[key].split(".")), "Select instance.port paths relative to top")
    paths = [Path(p).resolve() for p in sources + dependencies]
    require(paths and len(set(paths)) == len(paths), "Declare unique source/dependency files")

    def inventory():
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

    before = inventory()
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(exist_ok=False)
    options = ast.CompilationOptions()
    options.topModules = {top}
    options.paramOverrides = [f"{name}={value}" for name, value in parameters.items()]
    compilation = ast.Compilation(pyslang.Bag([options]))
    manager = pyslang.SourceManager()
    compilation.addSyntaxTree(syntax.SyntaxTree.fromFiles([str(Path(p).resolve()) for p in sources], manager))
    root = compilation.getRoot()
    diagnostics = compilation.getAllDiagnostics()
    (evidence_dir / "diagnostics.json").write_text(json.dumps(
        [{"code": str(d.code), "error": d.isError()} for d in diagnostics], indent=2) + "\n", encoding="utf-8")
    require(not any(d.isError() for d in diagnostics), "Slang compilation failed; inspect retained diagnostics")
    tops = [i for i in root.topInstances if i.name == top]
    require(len(tops) == 1, "Selected top is absent or ambiguous")
    body = tops[0].body
    for name, value in parameters.items():
        symbol = body.find(name)
        require(symbol is not None and symbol.kind == ast.SymbolKind.Parameter and symbol.isPortParam
                and not symbol.value.value.hasUnknown and int(symbol.value.value) == value, "Override was not confirmed: " + name)

    def endpoint(path):
        names = path.split(".")
        owner = body
        for name in names[:-1]:
            instance = owner.find(name)
            require(instance is not None and instance.kind == ast.SymbolKind.Instance, "Instance is absent/unsupported: " + path)
            owner = instance.body
        ports = [p for p in owner.portList if p.name == names[-1]]
        require(len(ports) == 1, "Port is absent/unsupported: " + path)
        port = ports[0]
        require(hasattr(port, "direction") and hasattr(port, "type"), "Only ordinary input/output ports are supported")
        connection = instance.getPortConnection(port)
        expression = connection.expression if connection is not None else None
        symbol = expression.getSymbolReference() if expression is not None else None
        supported = symbol is not None and symbol.kind in (ast.SymbolKind.Net, ast.SymbolKind.Variable)
        return {"path": path, "direction": str(port.direction).split(".")[-1],
                "width_bits": port.type.bitWidth, "net": symbol.hierarchicalPath if supported else None,
                "net_width_bits": symbol.type.bitWidth if supported else None,
                "expression_kind": str(expression.kind) if expression is not None else "unconnected",
                "evidence_ref": f"{manager.getFileName(port.location)}:{manager.getLineNumber(port.location)}#{top}.{path}"}

    links, gaps = [], []
    for item in selection["links"]:
        source, sink = endpoint(item["source"]), endpoint(item["sink"])
        if source["net"] is None or sink["net"] is None:
            status = "needs_evidence"
            gaps.append(item["id"] + ": connection expression is not a supported direct net")
        elif source["direction"] != "Out" or sink["direction"] != "In":
            status = "direction_mismatch"
        elif not (source["width_bits"] == sink["width_bits"] == source["net_width_bits"] == sink["net_width_bits"]):
            status = "width_mismatch"
        elif source["net"] != sink["net"]:
            status = "different_nets"
        else:
            status = "directly_connected"
        links.append({"id": item["id"], "status": status, "source": source, "sink": sink})
    require(inventory() == before, "Inputs changed during elaboration")
    if not complete_inputs:
        gaps.append("Input completeness was not declared")
    findings = [l["id"] for l in links if l["status"] not in ("directly_connected", "needs_evidence")]
    result = {"format": "opentools.interface-connections.v1", "scope": scope,
              "status": "review_required" if findings else "incomplete" if gaps else "connected_within_profile",
              "links": links, "gaps": gaps, "findings": findings,
              "provenance": {"frontend": "pyslang 12.0.0", "top": top, "parameters": parameters,
                             "sources": before, "selection": selection, "inputs_complete": complete_inputs},
              "limits": ["Selected direct port nets only; no complete connectivity closure.",
                         "Matching nets/directions/widths do not establish event, cancellation, clock or reset compatibility.",
                         "Intent and protocol semantics require source/native evidence and engineering review."]}
    (evidence_dir / "connections.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--dependency", action="append", default=[])
    parser.add_argument("--top", required=True)
    parser.add_argument("--parameters", required=True)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--complete-inputs", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        out = Path(args.output)
        require(not out.exists() and out.parent.is_dir(), "Choose a new output with an existing parent")
        result = capture(args.source, args.dependency, args.top, read_json(args.parameters), read_json(args.selection),
                         read_json(args.scope), args.complete_inputs, out.with_suffix(".evidence"))
        with out.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
        print(result["status"])
        return {"connected_within_profile": 0, "review_required": 1, "incomplete": 2}[result["status"]]
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, ImportError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
