#!/usr/bin/env python3
"""Create local settings for the synthetic provider; no source is invoked here."""
import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    args = parser.parse_args()
    target = Path(args.directory).resolve()
    target.mkdir(parents=True, exist_ok=False)
    settings = {"format": "opentools.context-settings.v1", "sources": [{"id": "example", "type": "example",
        "protocol": "opentools.context.v1", "enabled": True,
        "command": [sys.executable, str(Path(__file__).resolve().with_name("provider.py"))],
        "timeout_seconds": 10, "max_reply_bytes": 1048576}]}
    scope = {"project_ref": "synthetic-demo", "revision_ref": "demo-1", "claim_ref": "selected-handoff"}
    for name, value in (("settings", settings), ("scope", scope)):
        (target / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(f"Synthetic settings created in {target}; no DVIT or model service was installed or contacted.")


if __name__ == "__main__":
    main()
