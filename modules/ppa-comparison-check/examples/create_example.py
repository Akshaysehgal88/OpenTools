#!/usr/bin/env python3
"""Create a synthetic area/timing experiment; these are not measured PPA results."""
import argparse
import copy
import json
from pathlib import Path


def condition(value, reference="synthetic:run-record"):
    return {"value": value, "evidence_ref": reference}


def rule(role, reason="Declared comparison basis", parents=None):
    value = {"role": role, "reason": reason, "evidence_ref": "synthetic:experiment-contract"}
    if parents is not None: value["from"] = parents
    return value


def snapshot(current=False):
    common = {"design_ref": "synthetic:top", "rtl_ref": "rtl:B" if current else "rtl:A", "netlist_ref": "netlist:B" if current else "netlist:A",
              "stage": "finish", "tool_ref": "synthetic-tool-v1", "flow_ref": "synthetic-flow-v1", "library_ref": "library:L1",
              "corner_ref": "analysis-view:slow", "constraints_ref": "sdc:B" if current else "sdc:A", "clock_period_ns": 12 if current else 10}
    metrics = []
    for kind, unit, value in (("stdcell_area", "um2", 900 if current else 1000), ("setup_slack", "ns", 0.2 if current else -0.4)):
        metrics.append({"id": kind, "kind": kind, "definition_ref": "synthetic:" + kind + ".v1", "scope_ref": "synthetic:whole-top",
                        "value": value, "unit": unit, "unit_evidence": "synthetic:metric-definition", "evidence_ref": "synthetic:report#" + kind,
                        "measurement_complete": True, "conditions": {key: condition(v) for key, v in common.items()}})
    return {"format": "opentools.ppa-snapshot.v1", "run_id": "current" if current else "baseline", "source_ref": "synthetic:current-report" if current else "synthetic:baseline-report",
            "context_ref": "synthetic:current-context" if current else "synthetic:baseline-context", "metrics": metrics}


def contract(baseline=None, current=None):
    baseline, current = baseline or snapshot(), current or snapshot(True)
    entries = []
    for metric in baseline["metrics"]:
        rules = {key: rule("fixed") for key in metric["conditions"]}
        rules["rtl_ref"] = rule("intended", "Study the supplied RTL change")
        rules["netlist_ref"] = rule("derived", "Final netlist changes with selected RTL and constraints", ["rtl_ref", "constraints_ref"])
        if metric["kind"] == "stdcell_area":
            rules["constraints_ref"] = rule("intended", "Describe area for the new RTL/constraints configuration, without isolating RTL")
            rules["clock_period_ns"] = rule("intended", "Clock relaxation is part of this declared area comparison")
            claim = "Describe reported standard-cell area for the new RTL/constraints configuration; do not isolate the RTL effect."
        else:
            claim = "Assess the claim that the RTL change improved setup slack under fixed constraints."
        entries.append({"id": metric["id"], "claim": claim, "rules": rules})
    return {"format": "opentools.ppa-contract.v1", "baseline_run_id": baseline["run_id"], "current_run_id": current["run_id"], "metrics": entries}


def controls():
    a = snapshot(); b = copy.deepcopy(a); b["run_id"] = "current"; b["source_ref"] = "synthetic:independent-control"
    p = {"format": "opentools.ppa-contract.v1", "baseline_run_id": a["run_id"], "current_run_id": b["run_id"],
         "metrics": [{"id": m["id"], "claim": "Compare matched control records.", "rules": {key: rule("fixed") for key in m["conditions"]}} for m in a["metrics"]]}
    return a, b, p


def power_metric(value=0.1):
    metric = copy.deepcopy(snapshot()["metrics"][0])
    metric.update(id="total_power", kind="total_power", definition_ref="synthetic:estimated-total-power.v1", value=value, unit="W", evidence_ref="synthetic:power-report")
    metric["conditions"].update({key: condition(v, "synthetic:activity-annotation-report") for key, v in {
        "activity_source_ref": "saif:A", "activity_window": "0..100us", "activity_scope_ref": "synthetic:top",
        "activity_mapping_ref": "mapping:A", "annotation_scope_ref": "pins:top", "annotation_basis": "pins in selected analysis scope",
        "annotated_fraction": 0.95, "unannotated_policy": "synthetic:documented-default-toggle-policy"}.items()})
    return metric


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("output_directory")
    out = Path(parser.parse_args().output_directory); out.mkdir(parents=True, exist_ok=False)
    for name, value in (("baseline", snapshot()), ("current", snapshot(True)), ("contract", contract())):
        (out / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(f"Created synthetic experiment in {out}")


if __name__ == "__main__": main()
