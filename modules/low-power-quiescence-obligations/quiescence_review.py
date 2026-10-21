#!/usr/bin/env python3
"""Review owner drain and shutdown prerequisites across a sampled transition."""
import argparse
import json
from pathlib import Path
import sys
from quiescence_core import digest, exit_code, markdown, read_json, require, review


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__);commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("review")
    for name in ("inventory", "journal", "policy"): check.add_argument(name)
    check.add_argument("--json-out");check.add_argument("--markdown-out")
    hashes = commands.add_parser("digest");hashes.add_argument("record");args = parser.parse_args(argv)
    try:
        if args.command == "digest": print(digest(read_json(args.record)));return 0
        inputs = {Path(p).resolve() for p in (args.inventory, args.journal, args.policy)}
        outputs = [Path(p).resolve() for p in (args.json_out, args.markdown_out) if p]
        require(len(outputs) == len(set(outputs)) and not inputs & set(outputs), "Distinct outputs required")
        require(all(not p.exists() and p.parent.is_dir() for p in outputs), "Choose new outputs with existing parents")
        report = review(read_json(args.inventory), read_json(args.journal), read_json(args.policy))
        for path, content in ((args.json_out, json.dumps(report, indent=2) + "\n"), (args.markdown_out, markdown(report))):
            if path:
                with Path(path).open("x", encoding="utf-8") as stream: stream.write(content)
        print(markdown(report), end="");return exit_code(report)
    except (ValueError, TypeError, KeyError, OSError, UnicodeError) as exc:
        print("error: " + str(exc), file=sys.stderr);return 3


if __name__ == "__main__": sys.exit(main())
