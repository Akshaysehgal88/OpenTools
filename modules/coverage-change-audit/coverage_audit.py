#!/usr/bin/env python3
"""Audit coverage population, hit, definition and scoring changes."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from coverage_core import compare, markdown, read_json, require


def write(path, content):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def dumps(value):
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    audit = sub.add_parser("compare", help="Compare normalized per-instance snapshots")
    audit.add_argument("baseline")
    audit.add_argument("current")
    audit.add_argument("--identity-map")
    audit.add_argument("--json-out")
    audit.add_argument("--markdown-out")
    audit.add_argument("--format", choices=("json", "markdown"), default="markdown")
    inspect = sub.add_parser("inspect-ucis", help="Inventory supported XML points and create an optional context template")
    inspect.add_argument("xml")
    inspect.add_argument("--output", required=True)
    inspect.add_argument("--context-template")
    native = sub.add_parser("import-ucis", help="Import selected XML points with digest-bound semantic context")
    native.add_argument("xml")
    native.add_argument("--context", required=True)
    native.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        names = [getattr(args, k, None) for k in ("json_out", "markdown_out", "output", "context_template")]
        outputs = [Path(p).resolve() for p in names if p]
        require(len(outputs) == len(set(outputs)), "Output paths must differ")
        require(not any(p.exists() for p in outputs), "Output exists; select a new path")
        if args.action == "compare":
            report = compare(read_json(args.baseline), read_json(args.current), read_json(args.identity_map) if args.identity_map else None)
            if args.json_out:
                write(args.json_out, dumps(report))
            if args.markdown_out:
                write(args.markdown_out, markdown(report))
            print(dumps(report) if args.format == "json" else markdown(report), end="")
            return {"unchanged_within_scope": 0, "review_required": 1, "incomplete": 2}[report["status"]]
        from ucis_import import context_template, import_xml, inspect_xml
        if args.action == "inspect-ucis":
            inventory = inspect_xml(args.xml)
            write(args.output, dumps(inventory))
            if args.context_template:
                write(args.context_template, dumps(context_template(inventory)))
            print(f"Inventoried {len(inventory['points'])} point instance(s)")
            return 0
        snapshot = import_xml(args.xml, read_json(args.context))
        write(args.output, dumps(snapshot))
        print(f"Imported {len(snapshot['points'])} point instance(s); population_complete={snapshot['population_complete']}")
        return 0 if snapshot["population_complete"] else 2
    except Exception as exc:
        # Native reader/schema errors vary by backend; never turn one into a clean audit.
        print(f"coverage-audit: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
