"""Owned boot/wake prerequisite examples; not a general RTL dependency extractor."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clock_core import digest, require

CASES = ("boot-cycle", "boot-fixed", "wake-cycle", "wake-fixed", "wake-no-restore")


def example(case="boot-cycle"):
    require(case in CASES, "Unknown example")
    wake, bad = case.startswith("wake"), case.endswith("cycle")
    scope = {"project": "clock-example", "configuration": "gated-worker", "mode": "wake" if wake else "boot"}
    model = {"format": "opentools.clock.model.v1", "scope": scope, "basis_ref": "source-reviewed-availability-v1", "inputs_complete": True,
             "semantics": "positive-monotonic-prerequisites", "facts": [], "clocks": [], "rules": []}
    for name, initial, owner in (("root_available", True, "root-source"), ("reset_inactive", True, "reset-controller"),
        ("request", True, "wake-source" if wake else "boot-host"), ("restore_ready", case != "wake-no-restore", "restore-controller"),
        ("gate_enabled", False, "gate-controller"), ("worker_ready", False, "worker"), ("transition_done", False, "sequence-controller")):
        model["facts"].append({"id": name, "initial": initial, "owner_ref": owner, "evidence_ref": "clock_path.sv:" + name})
    model["clocks"] = [
        {"id": "root", "parent_ref": None, "available_fact": "root_available", "owner_ref": "root-source", "evidence_ref": "clock_path.sv:root"},
        {"id": "worker-clock", "parent_ref": "root", "available_fact": "gate_enabled", "owner_ref": "gate-controller", "evidence_ref": "clock_path.sv:worker_clk"}]
    enable = ["request", "reset_inactive"] + (["restore_ready"] if wake else []) + (["worker_ready"] if bad else [])
    for name, requires, produces, clock in (("enable-gate", enable, "gate_enabled", "root"),
        ("worker-ack", ["request", "reset_inactive"], "worker_ready", "worker-clock"),
        ("release-wait", ["worker_ready", "reset_inactive"], "transition_done", "root")):
        model["rules"].append({"id": name, "requires": requires, "produces": produces, "clock_ref": clock, "evidence_ref": "clock_path.sv:" + name})
    request = {"format": "opentools.clock.request.v1", "scope": dict(scope), "basis_ref": model["basis_ref"], "inputs_complete": True,
               "model_sha256": digest(model), "goals": [{"fact_ref": "transition_done", "evidence_ref": "caller:complete-" + scope["mode"]}]}
    return model, request


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--case", choices=CASES, default="boot-cycle")
    args = parser.parse_args()
    output = Path(args.directory)
    output.mkdir(parents=True, exist_ok=False)
    for name, value in zip(("model", "request"), example(args.case)):
        save(output / (name + ".json"), value)


if __name__ == "__main__":
    main()
