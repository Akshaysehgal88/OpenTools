#!/usr/bin/env python3
"""Review resolved hardware/software byte maps under explicit scope and alias policy."""
import argparse
import json
from pathlib import Path
import sys

from address_core import compare, digest, exit_code, markdown, read_json, require


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("compare")
    for name in ("hardware", "software", "policy"):
        check.add_argument(name)
    check.add_argument("--json-out")
    check.add_argument("--markdown-out")
    hash_cmd = commands.add_parser("digest")
    hash_cmd.add_argument("record")
    args = parser.parse_args(argv)
    try:
        if args.command == "digest":
            print(digest(read_json(args.record)))
            return 0
        outputs = [Path(p).resolve() for p in (args.json_out, args.markdown_out) if p]
        inputs = {Path(p).resolve() for p in (args.hardware, args.software, args.policy)}
        require(len(set(outputs)) == len(outputs) and not set(outputs) & inputs, "Outputs must be distinct from each other and inputs")
        require(all(not p.exists() and p.parent.is_dir() for p in outputs), "Choose new output paths with existing parents")
        report = compare(read_json(args.hardware), read_json(args.software), read_json(args.policy))
        for path, content in ((args.json_out, json.dumps(report, indent=2, ensure_ascii=False) + "\n"),
                              (args.markdown_out, markdown(report))):
            if path:
                with Path(path).open("x", encoding="utf-8") as stream:
                    stream.write(content)
        print(markdown(report), end="")
        return exit_code(report)
    except (ValueError, OSError, TypeError, KeyError, UnicodeError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
