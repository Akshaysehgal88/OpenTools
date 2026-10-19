"""Extract layouts using Slang and a native GCC layout probe."""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
from importlib.metadata import version
from pathlib import Path

from layout_core import fields, require, text


def identifier(name):
    require(isinstance(name, str) and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", name), "Expected a plain source identifier")
    return name


def inputs(paths):
    require(paths, "Source inventory is empty")
    return {str(Path(p).resolve()): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}


def source_ref(inventory, configuration):
    return "sha256:" + hashlib.sha256(json.dumps([inventory, configuration], sort_keys=True).encode()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def hardware(sources, dependencies, top, type_name, parameters, interface_ref, configuration_ref, complete_inputs, evidence_dir):
    require(version("pyslang") == "12.0.0", "This adapter is qualified with pyslang 12.0.0")
    import pyslang
    from pyslang import ast, syntax
    identifier(top)
    require(all(identifier(n) for n in type_name.split("::")), "Invalid type name")
    require(isinstance(parameters, dict) and all(identifier(k) and type(v) is int for k, v in parameters.items()), "Parameters must map identifiers to integer values")
    inventory = inputs(sources + dependencies)
    evidence_dir = Path(evidence_dir); evidence_dir.mkdir(parents=True, exist_ok=False)
    options = ast.CompilationOptions(); options.topModules = {top}
    options.paramOverrides = [f"{name}={value}" for name, value in parameters.items()]
    compilation = ast.Compilation(pyslang.Bag([options]))
    manager = pyslang.SourceManager()
    compilation.addSyntaxTree(syntax.SyntaxTree.fromFiles([str(Path(p).resolve()) for p in sources], manager))
    root = compilation.getRoot()
    diagnostics = compilation.getAllDiagnostics()
    save(evidence_dir / "diagnostics.json", [{"code": str(d.code), "error": d.isError()} for d in diagnostics])
    require(not any(d.isError() for d in diagnostics), "Slang compilation failed; see retained diagnostics")
    tops = [instance for instance in root.topInstances if instance.name == top]
    require(len(tops) == 1, "Selected top is absent or ambiguous")
    body = tops[0].body
    for name, value in parameters.items():
        symbol = body.find(name)
        require(symbol is not None and symbol.kind == ast.SymbolKind.Parameter and int(symbol.value.value) == value,
                f"Parameter override not confirmed: {name}")
    symbol = body.lookupName(type_name)
    require(isinstance(symbol, ast.Type), "Selected symbol is not a type")
    record = symbol.canonicalType
    require(record.kind == ast.SymbolKind.PackedStructType, "Only packed structs are supported")
    ref = source_ref(inventory, parameters)
    result = []
    for member in record:
        require(isinstance(member, ast.FieldSymbol), "Unexpected packed record member")
        ty = member.type.canonicalType
        base = ty.baseType.canonicalType if ty.isEnum else ty
        require(base.isSimpleBitVector or base.isPredefinedInteger, "Only scalar integer/bit-vector/enum fields are supported")
        if base.hasFixedRange:
            require(base.fixedRange.right == 0 and base.fixedRange.left >= 0, "Only descending zero-based scalar ranges are supported")
        values = {}
        if ty.isEnum:
            for value in ty:
                require(not value.value.value.hasUnknown, "Unknown enum bits are unsupported")
                values[value.name] = int(value.value.value)
        result.append({"name": member.name, "offset_bits": member.bitOffset, "width_bits": ty.bitWidth,
                       "signed": ty.isSigned, "enum_values": values,
                       "evidence_ref": f"{ref}#{manager.getFileName(member.location)}:{manager.getLineNumber(member.location)}"})
    actual_parameters = {symbol.name: str(symbol.value) for symbol in body if symbol.kind == ast.SymbolKind.Parameter and symbol.isPortParam}
    snapshot = {"format": "opentools.record-layout.v1", "kind": "hardware", "basis": "packed-lsb", "record": f"{top}.{type_name}",
                "interface_ref": interface_ref, "configuration_ref": configuration_ref, "source_ref": ref, "frontend_ref": "pyslang 12.0.0",
                "inputs_complete": complete_inputs, "fields_complete": True, "size_bits": record.bitWidth, "fields": result,
                "provenance": {"sources": inventory, "requested_parameters": parameters, "actual_port_parameters": actual_parameters}}
    require(inputs(sources + dependencies) == inventory, "Source inputs changed during extraction")
    fields(snapshot)
    save(evidence_dir / "frontend-layout.json", snapshot)
    return snapshot


def software(header, dependencies, struct_name, profile, compiler, interface_ref, configuration_ref,
             complete_inputs, complete_fields, evidence_dir, timeout=60):
    identifier(struct_name)
    require(isinstance(profile, dict) and set(profile) <= {"fields", "defines"}, "C profile supports fields and defines only")
    selected = profile.get("fields")
    require(isinstance(selected, list) and selected, "Select C fields explicitly")
    names = set()
    for field in selected:
        require(isinstance(field, dict) and set(field) <= {"name", "encodings"}, "Invalid C field profile")
        name = identifier(field.get("name")); require(name not in names, "Duplicate C field"); names.add(name)
        encodings = field.get("encodings", {})
        require(isinstance(encodings, dict) and all(identifier(k) and identifier(v) for k, v in encodings.items()), "C encodings map labels to constant identifiers")
    defines = profile.get("defines", {})
    require(isinstance(defines, dict) and all(identifier(k) and type(v) is int for k, v in defines.items()), "C defines must map identifiers to integer values")
    paths = [header] + dependencies
    inventory = inputs(paths)
    evidence_dir = Path(evidence_dir); evidence_dir.mkdir(parents=True, exist_ok=False)

    def run(command, name):
        save(evidence_dir / f"{name}.command.json", command)
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        (evidence_dir / f"{name}.stdout.txt").write_text(result.stdout, encoding="utf-8")
        (evidence_dir / f"{name}.stderr.txt").write_text(result.stderr, encoding="utf-8")
        require(result.returncode == 0, f"{name} failed; see retained evidence")
        return result.stdout.strip()

    compiler_version = run([compiler, "-dumpfullversion"], "version")
    target = run([compiler, "-dumpmachine"], "target")
    require(compiler_version == "13.3.0" and target == "x86_64-linux-gnu", "Qualified native C profile is GCC 13.3.0 x86_64-linux-gnu")
    record = f"struct {struct_name}"
    code = ['#include <stddef.h>', '#include <stdint.h>', '#include <stdio.h>', '#include <limits.h>',
            '#include ' + json.dumps(str(Path(header).resolve()).replace('\\', '/')),
            '_Static_assert(CHAR_BIT==8 && sizeof(void*)==8 && sizeof(long)==8, "LP64 required");',
            '_Static_assert(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__, "little endian required");', 'int main(void) {',
            f'printf("{{\\"size_bits\\":%zu,\\"alignment_bytes\\":%zu,\\"fields\\":[", sizeof({record})*CHAR_BIT, _Alignof({record}));']
    for index, field in enumerate(selected):
        name = field["name"]; expr = f"((({record}*)0)->{name})"
        code.append(f'_Static_assert(__builtin_classify_type({expr})==1, "integral scalar field required");')
        code.append(f'_Static_assert(!__builtin_types_compatible_p(__typeof__({expr}), _Bool), "boolean fields require separate value semantics");')
        fmt = ("," if index else "") + '{"name":' + json.dumps(name) + ',"offset_bits":%zu,"width_bits":%zu,"signed":%s,"enum_values":{'
        code.append(f'printf({json.dumps(fmt)}, offsetof({record},{name})*CHAR_BIT, sizeof({expr})*CHAR_BIT, ((__typeof__({expr}))-1 < (__typeof__({expr}))0) ? "true":"false");')
        for n, (label, constant) in enumerate(field.get("encodings", {}).items()):
            code.append(f'_Static_assert((__int128)({constant}) >= LLONG_MIN && (__int128)({constant}) <= LLONG_MAX, "encoding outside signed 64-bit vocabulary");')
            fmt = ("," if n else "") + json.dumps(label) + ":%lld"
            code.append(f'printf({json.dumps(fmt)}, (long long)({constant}));')
        code.append('printf("}}");')
    code += ['printf("]}\\n");', 'return 0;', '}']
    probe = evidence_dir / "probe.c"; probe.write_text("\n".join(code) + "\n", encoding="utf-8")
    executable = evidence_dir / "probe"
    command = [compiler, "-std=gnu11", "-m64", "-O0", "-fno-short-enums", *[f"-D{k}={v}" for k, v in defines.items()], str(probe), "-o", str(executable)]
    run(command, "compile")
    result = json.loads(run([str(executable.resolve())], "probe"))
    ref = source_ref(inventory, profile)
    for field in result["fields"]:
        field["evidence_ref"] = f"{ref}#{struct_name}.{field['name']};probe.c"
    snapshot = {"format": "opentools.record-layout.v1", "kind": "software", "basis": "c-object", "record": record,
                "interface_ref": interface_ref, "configuration_ref": configuration_ref, "source_ref": ref,
                "frontend_ref": f"GCC {compiler_version}", "target_abi": "x86_64-linux-gnu LP64 -m64 -fno-short-enums", "byte_order": "little",
                "integer_representation": "binary-twos-complement",
                "inputs_complete": complete_inputs, "fields_complete": complete_fields,
                "provenance": {"sources": inventory, "profile": profile, "compiler_target": target}, **result}
    require(inputs(paths) == inventory, "Source inputs changed during extraction")
    fields(snapshot)
    return snapshot
