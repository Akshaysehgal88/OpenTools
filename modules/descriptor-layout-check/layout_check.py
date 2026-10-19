#!/usr/bin/env python3
"""Check shared record layouts using explicit representation and field pairing."""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path
from layout_core import compare, markdown, read_json, require


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)


def dumps(value):
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    audit = sub.add_parser("compare")
    for name in ("hardware", "software", "pairing"): audit.add_argument(name)
    audit.add_argument("--json-out"); audit.add_argument("--markdown-out")
    for action in ("capture-hardware", "capture-software"):
        capture = sub.add_parser(action)
        for name in ("interface-ref", "configuration-ref", "output"): capture.add_argument("--" + name, required=True)
        capture.add_argument("--dependency", action="append", default=[])
        capture.add_argument("--complete-inputs", action="store_true")
        if action == "capture-hardware":
            capture.add_argument("--source", action="append", required=True)
            capture.add_argument("--top", required=True); capture.add_argument("--type", required=True)
            capture.add_argument("--parameters", help="JSON object of integer top parameter overrides")
        else:
            capture.add_argument("--header", required=True); capture.add_argument("--struct", required=True)
            capture.add_argument("--profile", required=True); capture.add_argument("--gcc", default="gcc")
            capture.add_argument("--complete-fields", action="store_true")
            capture.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args(argv)
    try:
        outputs = [Path(p).resolve() for p in (getattr(args, k, None) for k in ("output", "json_out", "markdown_out")) if p]
        require(len(set(outputs)) == len(outputs) and not any(p.exists() for p in outputs), "Outputs must differ and must not already exist")
        if args.action == "compare":
            report = compare(read_json(args.hardware), read_json(args.software), read_json(args.pairing))
            if args.json_out: write(args.json_out, dumps(report))
            if args.markdown_out: write(args.markdown_out, markdown(report))
            print(markdown(report), end="")
            return {"matched_within_scope": 0, "mismatch": 1, "incomplete": 2}[report["status"]]
        from layout_capture import hardware, software
        evidence = Path(args.output).resolve().with_suffix(".evidence")
        if args.action == "capture-hardware":
            snapshot = hardware(args.source, args.dependency, args.top, args.type,
                                read_json(args.parameters) if args.parameters else {}, args.interface_ref, args.configuration_ref,
                                args.complete_inputs, evidence)
        else:
            require(math.isfinite(args.timeout) and args.timeout > 0, "Timeout must be finite and positive")
            snapshot = software(args.header, args.dependency, args.struct, read_json(args.profile), args.gcc,
                                args.interface_ref, args.configuration_ref, args.complete_inputs, args.complete_fields, evidence, args.timeout)
        write(args.output, dumps(snapshot))
        print(f"Captured {len(snapshot['fields'])} fields; output={args.output}")
        return 0 if snapshot["inputs_complete"] and snapshot["fields_complete"] else 2
    except Exception as exc:
        print(f"layout-check: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
