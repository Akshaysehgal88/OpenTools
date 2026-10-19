#!/usr/bin/env python3
"""Read-only cost timeline, comparison and native accounting import."""
import argparse
import json
from pathlib import Path
import sys

from cost_core import analyze, compare, exit_code, markdown, read_json, require


def preflight(outputs, inputs=()):
    outputs = [Path(p).resolve() for p in outputs if p]
    require(len(set(outputs)) == len(outputs), "Output paths must be distinct")
    require(not set(outputs) & {Path(p).resolve() for p in inputs}, "Outputs must differ from inputs")
    require(all(not p.exists() and p.parent.is_dir() for p in outputs), "Choose new output paths with existing parents")


def write(path, content):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(content)


def emit(report, args):
    rendered = markdown(report)
    if args.json_out:
        write(args.json_out, json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    if args.markdown_out:
        write(args.markdown_out, rendered)
    print(rendered, end="")
    return exit_code(report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    one = commands.add_parser("analyze")
    one.add_argument("run")
    two = commands.add_parser("compare")
    two.add_argument("baseline")
    two.add_argument("current")
    two.add_argument("policy")
    for command in (one, two):
        command.add_argument("--json-out")
        command.add_argument("--markdown-out")
    inspect = commands.add_parser("inspect-sc")
    inspect.add_argument("manifest")
    inspect.add_argument("--output", required=True)
    inspect.add_argument("--context-template")
    imp = commands.add_parser("import-sc")
    imp.add_argument("manifest")
    imp.add_argument("--context", required=True)
    imp.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "analyze":
            preflight([args.json_out, args.markdown_out], [args.run])
            return emit(analyze(read_json(args.run)), args)
        if args.command == "compare":
            preflight([args.json_out, args.markdown_out], [args.baseline, args.current, args.policy])
            return emit(compare(read_json(args.baseline), read_json(args.current), read_json(args.policy)), args)
        from sc_cost_import import inspect_manifest, context_template, import_manifest
        if args.command == "inspect-sc":
            preflight([args.output, args.context_template], [args.manifest])
            info = inspect_manifest(args.manifest)
            write(args.output, json.dumps(info, indent=2, ensure_ascii=False) + "\n")
            if args.context_template:
                write(args.context_template, json.dumps(context_template(info), indent=2, ensure_ascii=False) + "\n")
            return 0
        preflight([args.output], [args.manifest, args.context])
        run = import_manifest(args.manifest, args.context)
        write(args.output, json.dumps(run, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        return exit_code(analyze(run))
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
