#!/usr/bin/env python3
"""Create synthetic complete-task timelines with overlapping trace observations."""
import argparse
import copy
import json
from pathlib import Path


def fact(value):
    return {"value": value, "evidence_ref": "synthetic:run-context"}


def phase(name, stage, start, end, accounting="stage", basis="measured"):
    return {"id": name, "stage": stage, "accounting": accounting, "start_s": start, "end_s": end,
            "basis": basis, "evidence_ref": "synthetic:milestones#" + name}


def resource(name, kind, value, unit, scope="workflow:selected-task"):
    return {"id": name, "kind": kind, "value": value, "unit": unit, "scope_ref": scope,
            "basis": "measured", "definition_ref": "synthetic:measurement-definition#" + name, "evidence_ref": "synthetic:accounting#" + name}


def records():
    before = {"format": "opentools.cost-run.v1", "run_ref": "synthetic:before", "task": "Run the selected SoC stimulus and retain its required result",
              "window": {"start_s": 0, "end_s": 7200, "basis": "measured", "clock_ref": "synthetic:shared-monotonic-clock",
                         "scope_ref": "workflow:selected-task", "evidence_ref": "synthetic:runner-bounds"},
              "completion": {"outcome": "completed", "required_evidence_complete": True, "evidence_ref": "synthetic:required-results"},
              "collection": {"complete": True, "evidence_ref": "synthetic:complete-markers"},
              "phases": [phase("queue", "queue-wait", 0, 1200), phase("compile", "build", 1200, 3600),
                         phase("boot", "initialization", 3600, 6600), phase("stimulus", "active-stimulus", 6600, 7200),
                         phase("trace", "waveform-capture", 6600, 7200, "overlay"), phase("trace-detail", "waveform-capture", 6900, 7100, "overlay")],
              "resources": [resource("parallel-cpu", "cpu_time", 18000, "s", "all-child-processes:selected-task"),
                            resource("trace-size", "byte_count", 2048, "MiB", "trace-artifacts:selected-task"),
                            resource("engineer-review", "engineer_effort", 0.5, "h", "engineer:review")],
              "simulation_progress": {"amount": 600000, "unit": "cycles", "definition_ref": "synthetic:active-core-clock-cycle-counter", "scope_ref": "workflow:selected-task", "basis": "measured", "evidence_ref": "synthetic:checked-cycle-count"},
              "context": {"configuration_ref": fact("soc:configuration-A"), "workload_ref": fact("selected-stimulus:seed17"),
                          "instrumentation_ref": fact("trace:full-vcd"), "tool_ref": fact("simulator:example-version"), "evidence_scope_ref": fact("selected-checks:required-outputs")}}
    after = copy.deepcopy(before)
    after["run_ref"] = "synthetic:after"
    after["window"]["end_s"] = 5700
    after["phases"] = [phase("queue", "queue-wait", 0, 1200), phase("compile", "build", 1200, 2100),
                       phase("boot", "initialization", 2100, 5100), phase("stimulus", "active-stimulus", 5100, 5700),
                       phase("trace", "waveform-capture", 5100, 5700, "overlay"), phase("trace-detail", "waveform-capture", 5400, 5600, "overlay")]
    after["provenance"] = {"example_kind": "synthetic", "note": "Shorter reported build for arithmetic illustration; no actual optimization or CPU/storage saving established."}
    policy = {"format": "opentools.cost-comparison.v1", "baseline_run_ref": before["run_ref"], "current_run_ref": after["run_ref"],
              "question": "How did the reported selected-task wall window change under the stated matching context?",
              "roles": {name: {"role": "fixed", "reason": "Retain the same declared task and evidence basis", "evidence_ref": "synthetic:comparison-contract"} for name in before["context"]}}
    return before, after, policy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    args = parser.parse_args()
    target = Path(args.directory)
    target.mkdir(parents=True, exist_ok=False)
    for name, value in zip(("baseline", "current", "policy"), records()):
        (target / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
