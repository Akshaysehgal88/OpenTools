"""Capture integer parameter values; their capacity roles come from explicit mapping."""
from importlib.metadata import version
import hashlib
import json
from pathlib import Path
import re

from contract_core import SCOPE, require, shape, text, validate_record


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", value), "Plain identifiers required")
    return value


def capture_parameters(sources, dependencies, top, parameters, mapping, scope, record_ref,
                       revision_ref, complete_inputs, evidence_dir):
    require(version("pyslang") == "12.0.0", "Qualified capture requires pyslang 12.0.0")
    import pyslang
    from pyslang import ast, syntax
    identifier(top)
    require(isinstance(parameters, dict) and all(identifier(k) and type(v) is int for k, v in parameters.items()),
            "Parameter overrides map names to integers")
    shape(mapping, ("format", "facts"))
    require(mapping["format"] == "opentools.capacity-mapping.v1" and isinstance(mapping["facts"], list)
            and mapping["facts"], "Select parameter mappings")
    for item in mapping["facts"]:
        shape(item, ("id", "symbol", "unit", "basis_ref", "meaning_ref"))
        identifier(item["symbol"])
        require(text(item["id"]), "A fact ID is required")
    shape(scope, SCOPE)
    require(all(text(v) for v in scope.values()) and text(record_ref) and text(revision_ref), "Exact scope and identity required")
    paths = [Path(p).resolve() for p in sources + dependencies]
    require(len(set(paths)) == len(paths), "Duplicate source/dependency path")

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
    tops = [instance for instance in root.topInstances if instance.name == top]
    require(len(tops) == 1, "Selected top is absent or ambiguous")
    body = tops[0].body
    for name, value in parameters.items():
        symbol = body.find(name)
        require(symbol is not None and symbol.kind == ast.SymbolKind.Parameter and symbol.isPortParam
                and not symbol.value.value.hasUnknown and int(symbol.value.value) == value,
                "Override was not confirmed: " + name)
    facts = []
    for item in mapping["facts"]:
        symbol = body.find(item["symbol"])
        require(symbol is not None and symbol.kind == ast.SymbolKind.Parameter, "Selected symbol is not a parameter")
        require(symbol.type.canonicalType.isIntegral and not symbol.value.value.hasUnknown,
                "Only known integral parameter values are supported")
        value = int(symbol.value.value)
        require(value >= 0, "Negative capacity values require another interpretation")
        facts.append({"id": item["id"], "value": value, "unit": item["unit"], "basis_ref": item["basis_ref"],
                      "meaning_ref": item["meaning_ref"],
                      "value_ref": f"pyslang-12.0.0:{manager.getFileName(symbol.location)}:{manager.getLineNumber(symbol.location)}#{top}.{item['symbol']}"})
    require(inventory() == before, "Inputs changed during extraction")
    result = {"format": "opentools.capacity-record.v1", "record_ref": record_ref, "revision_ref": revision_ref,
              "scope": scope, "inputs_complete": complete_inputs, "facts": facts,
              "provenance": {"frontend": "pyslang 12.0.0", "sources": before, "top": top,
                             "parameters": parameters, "mapping": mapping,
                             "input_boundary": "Caller-declared source/dependency inventory; no automatic closure discovery"}}
    validate_record(result)
    (evidence_dir / "capture.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
