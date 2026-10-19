#!/usr/bin/env python3
"""Compare reported PPA measurements under an explicit experiment contract."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from ppa_core import compare, markdown, read_json, require


def write(path, content):
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as stream: stream.write(content)


def dumps(value):
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    audit = sub.add_parser("compare")
    for name in ("baseline", "current", "contract"): audit.add_argument(name)
    audit.add_argument("--json-out"); audit.add_argument("--markdown-out")
    inspect = sub.add_parser("inspect-orfs")
    inspect.add_argument("metadata"); inspect.add_argument("--output", required=True); inspect.add_argument("--context-template")
    native = sub.add_parser("import-orfs")
    native.add_argument("metadata"); native.add_argument("--context", required=True); native.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        outputs = [Path(p).resolve() for p in (getattr(args, name, None) for name in ("json_out", "markdown_out", "output", "context_template")) if p]
        require(len(set(outputs)) == len(outputs) and not any(p.exists() for p in outputs), "Outputs must differ and must not already exist")
        if args.action == "compare":
            report = compare(read_json(args.baseline), read_json(args.current), read_json(args.contract))
            if args.json_out: write(args.json_out, dumps(report))
            if args.markdown_out: write(args.markdown_out, markdown(report))
            print(markdown(report), end="")
            return {"comparable_within_contract": 0, "confounded": 1, "incomplete": 2}[report["status"]]
        from orfs_import import context_template, import_metadata, inspect
        if args.action == "inspect-orfs":
            inventory = inspect(args.metadata)
            write(args.output, dumps(inventory))
            if args.context_template: write(args.context_template, dumps(context_template(inventory)))
            print(f"Inventoried {len(inventory['metrics'])} supported native metric(s); units/context still need evidence")
            return 0
        snapshot = import_metadata(args.metadata, read_json(args.context), Path(args.context).resolve().parent)
        write(args.output, dumps(snapshot))
        print(f"Imported {len(snapshot['metrics'])} metric(s); semantic qualification requires a comparison contract")
        return 0 if all(m["measurement_complete"] for m in snapshot["metrics"]) else 2
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"ppa-check: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__": raise SystemExit(main())
