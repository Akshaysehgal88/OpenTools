#!/usr/bin/env python3
"""Review saved capacity contracts or capture selected elaborated parameters."""
import argparse
import json
from pathlib import Path
import sys

from contract_core import digest, exit_code, markdown, read_json, require, review


def preflight(outputs, inputs):
    paths = [Path(p).resolve() for p in outputs if p]
    require(len(paths) == len(set(paths)), "Output paths must be distinct")
    require(not set(paths) & {Path(p).resolve() for p in inputs}, "Outputs must differ from inputs")
    require(all(not p.exists() and p.parent.is_dir() for p in paths), "Choose new output paths with existing parents")


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("review")
    check.add_argument("record")
    check.add_argument("contract")
    check.add_argument("--baseline")
    check.add_argument("--json-out")
    check.add_argument("--markdown-out")
    hash_cmd = commands.add_parser("digest")
    hash_cmd.add_argument("record")
    capture = commands.add_parser("capture-slang")
    capture.add_argument("--source", action="append", required=True)
    capture.add_argument("--dependency", action="append", default=[])
    capture.add_argument("--top", required=True)
    capture.add_argument("--parameters", required=True)
    capture.add_argument("--mapping", required=True)
    capture.add_argument("--scope", required=True)
    capture.add_argument("--record-ref", required=True)
    capture.add_argument("--revision-ref", required=True)
    capture.add_argument("--complete-inputs", action="store_true")
    capture.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "digest":
            print(digest(read_json(args.record)))
            return 0
        if args.command == "review":
            preflight([args.json_out, args.markdown_out], [args.record, args.contract, *([args.baseline] if args.baseline else [])])
            report = review(read_json(args.record), read_json(args.contract), read_json(args.baseline) if args.baseline else None)
            if args.json_out:
                write(args.json_out, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
            if args.markdown_out:
                write(args.markdown_out, markdown(report))
            print(markdown(report), end="")
            return exit_code(report)
        from slang_capacity import capture_parameters
        preflight([args.output], args.source + args.dependency + [args.parameters, args.mapping, args.scope])
        result = capture_parameters(args.source, args.dependency, args.top, read_json(args.parameters),
                                    read_json(args.mapping), read_json(args.scope), args.record_ref,
                                    args.revision_ref, args.complete_inputs, Path(args.output).with_suffix(".evidence"))
        write(args.output, json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        return 0 if args.complete_inputs else 2
    except (ValueError, OSError, TypeError, KeyError, UnicodeError, ImportError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
