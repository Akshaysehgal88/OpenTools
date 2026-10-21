#!/usr/bin/env python3
"""Capture effective field semantics from selected ordinary SystemRDL registers."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys
from access_core import require


def capture(sources, registers, scope, basis_ref, complete=False, top=None):
    require(version("systemrdl-compiler") == "1.32.2", "Use systemrdl-compiler==1.32.2 for this reader")
    from systemrdl import RDLCompiler, RDLCompileError
    from systemrdl.node import RegNode, MemNode
    sources = [Path(p).resolve() for p in sources]
    require(sources and len(sources) == len(set(sources)), "Distinct source files required")
    require(registers and len(registers) == len(set(registers)), "Distinct selected register paths required")
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    compiler = RDLCompiler()
    try:
        for source in sources:
            compiler.compile_file(str(source))
        root = compiler.elaborate(top_def_name=top)
    except RDLCompileError as exc:
        raise ValueError("Native SystemRDL compilation/elaboration failed; retain diagnostics") from exc
    result = {"format": "opentools.access.spec.v1", "scope": scope, "basis_ref": basis_ref,
              "inputs_complete": complete, "registers": [],
              "provenance": {"reader": "systemrdl-compiler-1.32.2", "sources": hashes,
                             "boundary": "Explicit source list; supply included files too. No include closure attestation."}}
    for path in registers:
        reg = root.find_by_path(path)
        require(isinstance(reg, RegNode) and not reg.is_array and not reg.is_alias and not reg.external and reg.get_property("ispresent"),
                "Select present internal non-array, non-alias registers")
        ancestor = reg.parent
        while ancestor is not None:
            require(not getattr(ancestor, "is_array", False) and not isinstance(ancestor, MemNode), "Array/memory ancestors unsupported")
            ancestor = ancestor.parent
        record = {"id": path, "address": reg.absolute_address, "width": reg.get_property("regwidth"),
                  "access_width": reg.get_property("accesswidth"), "evidence_ref": source_ref(reg), "fields": []}
        require(record["width"] in (8, 16, 32, 64) and record["access_width"] == record["width"], "Select whole-register accesses of 8/16/32/64 bits")
        for field in reg.fields():
            access = field.get_property("sw")
            onread, onwrite = field.get_property("onread"), field.get_property("onwrite")
            sw = getattr(access, "name", None)
            read = "none" if onread is None else "clear" if onread.name == "rclr" else "unsupported"
            write = ("assign" if sw in ("w", "rw") else "none") if onwrite is None else "one_clear" if onwrite.name == "woclr" else "unsupported"
            if any(field.get_property(name) for name in ("singlepulse", "counter", "intr", "sticky", "stickybit")):
                read = write = "unsupported"
            reset = field.get_property("reset")
            record["fields"].append({"name": field.inst_name, "lsb": field.low, "width": field.width,
                                     "sw": sw if sw in ("r", "w", "rw") else None, "onread": read, "onwrite": write,
                                     "reset": reset if type(reset) is int else None, "evidence_ref": source_ref(field)})
        result["registers"].append(record)
    require(all(hashlib.sha256(p.read_bytes()).hexdigest() == hashes[str(p)] for p in sources), "Source changed during capture")
    return result


def source_ref(node):
    ref = node.inst.inst_src_ref
    if ref is None:
        return node.get_path()
    ref.derive_coordinates()
    return str(ref.path) + ":" + str(ref.line)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--register", action="append", required=True)
    for name in ("project", "configuration", "mode", "address-space-ref", "basis-ref", "out"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--top")
    parser.add_argument("--inputs-complete", action="store_true")
    args = parser.parse_args(argv)
    try:
        path = Path(args.out)
        require(not path.exists() and path.parent.is_dir(), "Choose a new output in an existing directory")
        scope = {k: getattr(args, k) for k in ("project", "configuration", "mode", "address_space_ref")}
        record = capture(args.source, args.register, scope, args.basis_ref, args.inputs_complete, args.top)
        with path.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2)
            stream.write("\n")
        return 0
    except (ValueError, TypeError, KeyError, OSError, ImportError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
