#!/usr/bin/env python3
"""Compare native waiver populations and explicit configuration premises."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from waiver_core import InputError, compare, markdown, read_json, require


def write_output(path, content):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental report/input replacement.
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    audit = sub.add_parser("compare", help="Compare two normalized snapshots")
    audit.add_argument("baseline")
    audit.add_argument("current")
    audit.add_argument("--policy", help="Explicit configuration premises")
    audit.add_argument("--identity-map", help="Evidence-backed one-to-one finding correspondence")
    audit.add_argument("--json-out")
    audit.add_argument("--markdown-out")
    audit.add_argument("--format", choices=("json", "markdown"), default="markdown", help="stdout format")
    native = sub.add_parser("capture", help="Capture native Verilator 5.020 differential suppression")
    native.add_argument("--verilator", default="verilator")
    native.add_argument("--source", action="append", required=True)
    native.add_argument("--dependency", action="append", default=[])
    native.add_argument("--include-dir", action="append", default=[])
    native.add_argument("--waiver-file", required=True)
    native.add_argument("--waiver-id", required=True)
    native.add_argument("--configuration", required=True, help="JSON macro definitions applied to BOTH lint invocations")
    native.add_argument("--scope", required=True)
    native.add_argument("--run-id", required=True)
    native.add_argument("--top", required=True)
    native.add_argument("--complete-inputs", action="store_true", help="Declare the listed sources/dependencies a complete inventory for this lint profile")
    native.add_argument("--timeout", type=float, default=120)
    native.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "compare":
            outputs = [Path(p).resolve() for p in (args.json_out, args.markdown_out) if p]
            require(len(outputs) == len(set(outputs)), "JSON and Markdown outputs must differ")
            require(not any(p.exists() for p in outputs), "Output already exists; choose a new report path")
            report = compare(read_json(args.baseline), read_json(args.current),
                             read_json(args.policy) if args.policy else None,
                             read_json(args.identity_map) if args.identity_map else None)
            json_text = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
            md = markdown(report)
            if args.json_out:
                write_output(args.json_out, json_text)
            if args.markdown_out:
                write_output(args.markdown_out, md)
            sys.stdout.write(json_text if args.format == "json" else md)
            return {"unchanged_within_scope": 0, "review_required": 1, "incomplete": 2}[report["status"]]
        require(math.isfinite(args.timeout) and args.timeout > 0, "Timeout must be finite and positive")
        target = Path(args.output).resolve()
        require(not target.exists(), "Capture output exists; choose a new path")
        from verilator_capture import capture
        snapshot = capture(executable=args.verilator, sources=args.source, dependencies=args.dependency,
                           include_dirs=args.include_dir, waiver_file=args.waiver_file,
                           waiver_id=args.waiver_id, configuration=read_json(args.configuration),
                           scope=args.scope, run_id=args.run_id, top=args.top,
                           complete_inputs=args.complete_inputs, timeout=args.timeout,
                           evidence_dir=target.with_suffix(".evidence"))
        write_output(target, json.dumps(snapshot, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        print(f"Captured {len(snapshot['waivers'][0]['findings'])} suppressed finding(s); "
              f"complete={snapshot['population_complete']}; output={target}")
        return 0 if snapshot["population_complete"] else 2
    except (InputError, OSError, ValueError) as exc:
        print(f"waiver-revalidate: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
