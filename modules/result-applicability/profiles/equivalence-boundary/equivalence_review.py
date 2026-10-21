"""Data-only import and applicability review of one saved native equivalence task."""
import argparse
import json
from pathlib import Path
from equivalence_core import InputError, exit_code, markdown, review
from yosys_equivalence import capture, read_json, require


def write_new(path, content):
    path = Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:stream.write(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__);sub = parser.add_subparsers(dest="command", required=True)
    native = sub.add_parser("capture", help="Read native files without executing their script")
    native.add_argument("root", type=Path);native.add_argument("workdir");native.add_argument("context", type=Path);native.add_argument("--output", type=Path, required=True)
    check = sub.add_parser("review");check.add_argument("intent", type=Path);check.add_argument("snapshot", type=Path)
    check.add_argument("--json-out", type=Path);check.add_argument("--markdown-out", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "capture":
            require(not args.output.exists(), "Output exists")
            record = capture(args.root, args.workdir, read_json(args.context));write_new(args.output, json.dumps(record, indent=2) + "\n")
            print(json.dumps({"native_status": record["result"]["native_status"], "run_ref": record["run_ref"]}));return 0
        for path in (args.json_out, args.markdown_out):require(path is None or not path.exists(), "Output exists")
        require(not args.json_out or not args.markdown_out or args.json_out.resolve() != args.markdown_out.resolve(), "Select distinct outputs")
        report = review(read_json(args.intent), read_json(args.snapshot), args.snapshot.parent);content = json.dumps(report, indent=2) + "\n"
        if args.json_out:write_new(args.json_out, content)
        if args.markdown_out:write_new(args.markdown_out, markdown(report))
        print(content, end="");return exit_code(report)
    except (InputError, OSError, ValueError, KeyError, TypeError) as exc:parser.exit(3, str(exc) + "\n")


if __name__ == "__main__":raise SystemExit(main())
