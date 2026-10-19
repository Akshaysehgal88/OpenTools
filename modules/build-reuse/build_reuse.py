#!/usr/bin/env python3
"""Explain saved build reuse evidence without changing a build or cache."""
import argparse
import json
from pathlib import Path
import sys

from reuse_core import compare, exit_code, markdown, read_json, require


def preflight(outputs, inputs):
    paths = [Path(p).resolve() for p in outputs if p]
    require(len(paths) == len(set(paths)), 'Output paths must be distinct')
    require(not set(paths) & {Path(p).resolve() for p in inputs}, 'Outputs must differ from inputs')
    require(all(not p.exists() and p.parent.is_dir() for p in paths), 'Choose new output paths with existing parents')


def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(value)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('compare')
    for name in ('baseline', 'requested', 'profile'):
        check.add_argument(name)
    check.add_argument('--artifact-root')
    check.add_argument('--json-out')
    check.add_argument('--markdown-out')
    inspect = commands.add_parser('inspect-verilator')
    inspect.add_argument('manifest')
    inspect.add_argument('--producer-version', required=True)
    inspect.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'compare':
            records = [read_json(p) for p in (args.baseline, args.requested, args.profile)]
            # Reports cannot overwrite any declared baseline artifact.
            inputs = [args.baseline, args.requested, args.profile]
            if args.artifact_root:
                inputs += [Path(args.artifact_root) / a['path'] for a in records[0]['build']['artifacts']]
            preflight([args.json_out, args.markdown_out], inputs)
            report = compare(*records, artifact_root=args.artifact_root)
            if args.json_out:
                write(args.json_out, json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
            if args.markdown_out:
                write(args.markdown_out, markdown(report))
            print(markdown(report), end='')
            return exit_code(report)
        from verilator_evidence import inspect_manifest
        preflight([args.output], [args.manifest])
        report = inspect_manifest(args.manifest, args.producer_version)
        write(args.output, json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        return 0
    except (ValueError, OSError, TypeError, KeyError, UnicodeError) as exc:
        print('error: ' + str(exc), file=sys.stderr)
        return 3


if __name__ == '__main__':
    sys.exit(main())
