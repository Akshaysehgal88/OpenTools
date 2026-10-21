"""Packaging and context CLI; model usage stays in the user's existing host."""
import argparse
import json
from pathlib import Path
import platform
import sys

from . import __version__
from .catalog import ROOT, module_catalog
from .common import read_json, require, write_json
from .context import ask, consume, make_request
from .install import HOST_DIRS, install, uninstall, verify_install


def output_available(path):
    path = Path(path)
    require(not path.exists() and path.parent.is_dir(), "Choose a new output path with an existing parent directory")


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    catalog = commands.add_parser("catalog", help="Discover available AI workflows and optional helpers")
    catalog.add_argument("--json", action="store_true")
    commands.add_parser("doctor", help="Report runtime and workflow availability without installing or contacting anything")
    setup = commands.add_parser("install", help="Copy a self-contained workflow package into a chosen project")
    setup.add_argument("--host", choices=HOST_DIRS, required=True)
    setup.add_argument("--project", required=True)
    setup.add_argument("--module", action="append")
    setup.add_argument("--dry-run", action="store_true")
    for name in ("verify", "uninstall"):
        sub = commands.add_parser(name)
        sub.add_argument("--host", choices=HOST_DIRS, required=True)
        sub.add_argument("--project", required=True)
    context = commands.add_parser("context", help="Consume optional scoped context, questions, seeds and helper capabilities")
    context_commands = context.add_subparsers(dest="context_command", required=True)
    prepare = context_commands.add_parser("prepare", help="Prepare a bound query or capability-discovery request; no source call")
    prepare.add_argument("--source", required=True)
    prepare.add_argument("--source-type", required=True)
    prepare.add_argument("--module", default="opentools")
    prepare.add_argument("--action", choices=("query", "capabilities"), default="query")
    prepare.add_argument("--capability", default="context")
    prepare.add_argument("--question")
    prepare.add_argument("--scope", required=True, help="JSON file with the explicit scope object")
    prepare.add_argument("--evidence", help="JSON list of selected ref/revision_ref records")
    prepare.add_argument("--out", required=True)
    run = context_commands.add_parser("ask", help="Call only the adapter explicitly configured for a prepared request")
    run.add_argument("request")
    run.add_argument("--settings", required=True)
    run.add_argument("--out", required=True)
    intake = context_commands.add_parser("consume", help="Validate a reply obtained through the user's existing integration")
    intake.add_argument("request")
    intake.add_argument("reply")
    intake.add_argument("--out", required=True)
    from .onboard_cli import arguments as onboarding_arguments
    onboarding_arguments(commands)
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            entries = module_catalog()
            if args.json:
                print(json.dumps(entries, indent=2, ensure_ascii=False))
            else:
                for entry in entries:
                    print(f"{entry['id']}: {entry['description']}")
            return 0
        if args.command == "onboard":
            from .onboard_cli import run
            return run(args)
        if args.command == "doctor":
            result = {"version": __version__, "python": platform.python_version(), "system": platform.system(),
                      "package_root": str(ROOT), "workflows": [m["id"] for m in module_catalog()],
                      "model": "Provided by your existing file/tool-enabled agent; no model account is configured or inspected here",
                      "optional_context": "Disabled unless you explicitly supply source settings and invoke it",
                      "native_adapters": "See each module's qualified tool/OS/dependency profile; this check does not install them"}
        elif args.command == "install":
            result = install(args.project, args.host, args.module, args.dry_run)
        elif args.command == "verify":
            receipt = verify_install(args.project, args.host)
            result = {"status": "verified", "version": receipt["version"], "modules": receipt["modules"], "file_count": len(receipt["files"])}
        elif args.command == "uninstall":
            result = uninstall(args.project, args.host)
        else:
            output_available(args.out)
            if args.context_command == "prepare":
                question = args.question or ("List available scoped capabilities" if args.action == "capabilities" else None)
                result = make_request(args.source, args.source_type, args.module, question,
                                      read_json(args.scope), read_json(args.evidence) if args.evidence else None,
                                      args.capability, args.action)
                write_json(args.out, result)
                print(json.dumps({"status": "prepared", "request_id": result["request_id"], "output": str(Path(args.out))}))
                return 0
            request = read_json(args.request)
            if args.context_command == "ask":
                result = ask(request, args.settings)
            else:
                require(Path(args.reply).stat().st_size <= 16 * 1024 * 1024, "Context file exceeds the 16 MiB intake limit")
                result = consume(request, read_json(args.reply))
            write_json(args.out, result)
            print(json.dumps({"status": result["status"], "output": str(Path(args.out)), "gaps": result["gaps"]}, ensure_ascii=False))
            return 0 if result["status"] == "available" else 2
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
