#!/usr/bin/env python3
"""Read-only result correspondence and native manifest inspection CLI."""
import argparse
import json
import sys
from pathlib import Path

from applicability_core import audit, exit_code, markdown, read_json, require


def preflight(paths, inputs=()):
    paths = [Path(p).resolve() for p in paths if p]
    require(len(set(paths)) == len(paths), "Output paths must be distinct")
    require(not set(paths) & {Path(p).resolve() for p in inputs}, "Outputs must differ from inputs")
    require(all(not p.exists() and p.parent.is_dir() for p in paths), "Output already exists or parent directory is missing")


def write(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(value)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    compare = commands.add_parser("compare", help="Compare recorded evidence with a bounded claim")
    compare.add_argument("snapshot")
    compare.add_argument("request")
    compare.add_argument("--reuse")
    compare.add_argument("--json-out")
    compare.add_argument("--markdown-out")
    inspect = commands.add_parser("inspect-sc", help="Inventory a pinned SiliconCompiler JSON manifest")
    inspect.add_argument("manifest")
    inspect.add_argument("--step", required=True)
    inspect.add_argument("--index", required=True)
    inspect.add_argument("--output", required=True)
    inspect.add_argument("--context-template")
    imp = commands.add_parser("import-sc", help="Import a native node with digest-bound execution/result context")
    imp.add_argument("manifest")
    imp.add_argument("--context", required=True)
    imp.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "compare":
            preflight([args.json_out, args.markdown_out], [args.snapshot, args.request] + ([args.reuse] if args.reuse else []))
            report = audit(read_json(args.snapshot), read_json(args.request), read_json(args.reuse) if args.reuse else None,
                           Path(args.snapshot).resolve().parent)
            rendered = markdown(report)
            if args.json_out:
                write(args.json_out, json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
            if args.markdown_out:
                write(args.markdown_out, rendered)
            print(rendered, end="")
            return exit_code(report)
        from sc_import import inspect_manifest, context_template, import_manifest
        if args.command == "inspect-sc":
            preflight([args.output, args.context_template], [args.manifest])
            inventory = inspect_manifest(args.manifest, args.step, args.index)
            write(args.output, json.dumps(inventory, indent=2, ensure_ascii=False) + "\n")
            if args.context_template:
                write(args.context_template, json.dumps(context_template(inventory), indent=2, ensure_ascii=False) + "\n")
            return 0
        preflight([args.output], [args.manifest, args.context])
        snapshot = import_manifest(args.manifest, args.context, args.output)
        write(args.output, json.dumps(snapshot, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        execution, result = snapshot["execution"], snapshot["result"]
        basis_present = (execution["state"] == "completed" and execution["command"] and execution["executable_ref"]
                         and execution["dependency_capture_complete"] is True and execution["dependency_evidence_ref"]
                         and result["outcome"] in ("pass", "fail") and result["complete"] is True
                         and result["producer_run_ref"] == snapshot["run_ref"] and result["artifact"]
                         and result["native_status"] and result["evidence_ref"])
        return 0 if basis_present else 2
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
