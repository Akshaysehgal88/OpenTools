"""Evidence-qualified wall timelines, independent resource observations and comparisons."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, localcontext
import hashlib
import html
import json
import math
from pathlib import Path

CONTEXT = {"configuration_ref", "workload_ref", "instrumentation_ref", "tool_ref", "evidence_scope_ref"}
TIME_UNITS = {"fs": "0.000000000000001", "ps": "0.000000000001", "ns": "0.000000001", "us": "0.000001", "ms": "0.001", "s": "1", "min": "60", "h": "3600"}
BYTE_UNITS = {"B": "1", "kB": "1000", "MB": "1000000", "GB": "1000000000", "KiB": "1024", "MiB": "1048576", "GiB": "1073741824"}
RESOURCE_KINDS = {"cpu_time", "elapsed_time", "peak_memory", "byte_count", "engineer_effort"}


class InputError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise InputError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def number(value):
    return type(value) in (int, float) and (type(value) is int or math.isfinite(value))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(InputError(f"Invalid number: {value}")))


def shape(value, required, optional=()):
    require(isinstance(value, dict) and set(required) <= set(value) <= set(required) | set(optional),
            f"Expected fields {sorted(required)}, optional {sorted(optional)}")


def nullable_ref(value):
    return value is None or text(value)


def known(item):
    return item is not None and text(item["value"]) and text(item["evidence_ref"])


def validate_context(context):
    require(isinstance(context, dict) and set(context) == CONTEXT, "Provide all five distinct context reference fields, retaining nulls")
    for item in context.values():
        shape(item, {"value", "evidence_ref"})
        require(nullable_ref(item["value"]) and nullable_ref(item["evidence_ref"]), "Context values/references must be strings or null")


def validate_run(run):
    shape(run, {"format", "run_ref", "task", "window", "completion", "collection", "phases", "resources", "simulation_progress", "context"}, {"provenance"})
    require(run["format"] == "opentools.cost-run.v1" and text(run["run_ref"]) and text(run["task"]), "Run format, identity and task required")
    window = run["window"]
    shape(window, {"start_s", "end_s", "basis", "clock_ref", "scope_ref", "evidence_ref"})
    require(window["basis"] in ("measured", "estimated", "unknown"), "Invalid window basis")
    for key in ("clock_ref", "scope_ref", "evidence_ref"):
        require(nullable_ref(window[key]), "Invalid window reference")
    validate_bounds(window)
    completion = run["completion"]
    shape(completion, {"outcome", "required_evidence_complete", "evidence_ref"})
    require(completion["outcome"] in ("completed", "failed", "running", "unknown"), "Invalid run outcome")
    require(completion["required_evidence_complete"] is None or type(completion["required_evidence_complete"]) is bool, "Evidence completeness must be boolean or null")
    require(nullable_ref(completion["evidence_ref"]), "Invalid completion evidence")
    collection = run["collection"]
    shape(collection, {"complete", "evidence_ref"})
    require(collection["complete"] is None or type(collection["complete"]) is bool, "Collection completeness must be boolean or null")
    require(nullable_ref(collection["evidence_ref"]), "Invalid collection evidence")
    for items, label in ((run["phases"], "phases"), (run["resources"], "resources")):
        require(isinstance(items, list), f"{label} must be a list")
        ids = set()
        for item in items:
            require(isinstance(item, dict) and text(item.get("id")) and item["id"] not in ids, f"Unique {label} IDs required")
            ids.add(item["id"])
    for phase in run["phases"]:
        shape(phase, {"id", "stage", "accounting", "start_s", "end_s", "basis", "evidence_ref"})
        require(text(phase["stage"]) and phase["accounting"] in ("stage", "overlay"), "Invalid phase stage/accounting")
        require(phase["basis"] in ("measured", "estimated", "unknown") and nullable_ref(phase["evidence_ref"]), "Invalid phase basis/source")
        validate_bounds(phase)
    for resource in run["resources"]:
        shape(resource, {"id", "kind", "value", "unit", "definition_ref", "scope_ref", "basis", "evidence_ref"})
        require(resource["kind"] in RESOURCE_KINDS and resource["basis"] in ("measured", "estimated", "unknown"), "Invalid resource kind/basis")
        require(resource["value"] is None or (number(resource["value"]) and resource["value"] >= 0), "Resource value must be nonnegative finite numeric or null")
        require(all(nullable_ref(resource[k]) for k in ("unit", "definition_ref", "scope_ref", "evidence_ref")), "Invalid resource reference/unit")
    progress = run["simulation_progress"]
    shape(progress, {"amount", "unit", "definition_ref", "scope_ref", "basis", "evidence_ref"})
    require(progress["amount"] is None or (number(progress["amount"]) and progress["amount"] >= 0), "Progress must be nonnegative finite numeric or null")
    require(progress["unit"] is None or progress["unit"] in {"cycles", *TIME_UNITS}, "Unsupported simulation progress unit")
    require(progress["unit"] != "cycles" or progress["amount"] is None or type(progress["amount"]) is int, "Cycle counts must be integers")
    require(progress["basis"] in ("measured", "estimated", "unknown") and all(nullable_ref(progress[k]) for k in ("scope_ref", "definition_ref", "evidence_ref")), "Invalid progress basis/scope")
    validate_context(run["context"])


def validate_bounds(item):
    require(all(item[key] is None or number(item[key]) for key in ("start_s", "end_s")), "Boundary must be finite numeric seconds or null")
    require(item["start_s"] is None or item["end_s"] is None or item["end_s"] >= item["start_s"], "End precedes start on the declared clock")


def dec(value):
    return Decimal(str(value))


def rendered(value):
    return format(value, "f")


def measured_bounds(item):
    return item["basis"] == "measured" and item["start_s"] is not None and item["end_s"] is not None and text(item["evidence_ref"])


def analyze(run):
    validate_run(run)
    window = run["window"]
    issues, measurements, notes = [], [], []
    qualified_window = measured_bounds(window) and text(window["clock_ref"]) and text(window["scope_ref"])
    if not qualified_window:
        issues.append("Measured window boundaries, clock, scope or source are missing; no measured wall budget established")
    if run["collection"]["complete"] is not True or not text(run["collection"]["evidence_ref"]):
        issues.append("Selected phase collection is not declared complete with evidence")
    for phase in run["phases"]:
        if not measured_bounds(phase):
            target = issues if phase["accounting"] == "stage" else measurements
            target.append(f"Unqualified {phase['accounting']} interval: {phase['id']}")
    if run["completion"]["outcome"] != "completed":
        notes.append("The recorded run is not completed successfully; measured costs do not establish successful task evidence")
    wall, segments, centers, overlays, unallocated, shared = None, [], defaultdict(Decimal), defaultdict(Decimal), Decimal(0), Decimal(0)
    with localcontext() as ctx:
        ctx.prec = 40
        if qualified_window:
            start, end = dec(window["start_s"]), dec(window["end_s"])
            wall = end - start
            phases = []
            for phase in run["phases"]:
                if not measured_bounds(phase):
                    continue
                lo, hi = max(start, dec(phase["start_s"])), min(end, dec(phase["end_s"]))
                if dec(phase["start_s"]) < start or dec(phase["end_s"]) > end:
                    notes.append(f"Interval clipped to the selected window: {phase['id']}")
                if hi > lo:
                    phases.append((phase, lo, hi))
            boundaries = sorted({start, end, *(point for _, lo, hi in phases for point in (lo, hi))})
            for lo, hi in zip(boundaries, boundaries[1:]):
                active = [p for p, a, b in phases if a <= lo and b >= hi]
                stage_phases = [p for p in active if p["accounting"] == "stage"]
                stages = sorted({p["stage"] for p in stage_phases})
                label = "unallocated" if not stages else "stage:" + stages[0] if len(stages) == 1 else "shared:" + canonical(stages)
                duration = hi - lo
                centers[label] += duration
                if not stages:
                    unallocated += duration
                elif len(stages) > 1:
                    shared += duration
                for name in {p["stage"] for p in active if p["accounting"] == "overlay"}:
                    overlays[name] += duration
                segments.append({"start_s": rendered(lo), "end_s": rendered(hi), "wall_s": rendered(duration), "bucket": label,
                                 "stages": stages, "stage_phase_ids": sorted(p["id"] for p in stage_phases),
                                 "overlay_phase_ids": sorted(p["id"] for p in active if p["accounting"] == "overlay"),
                                 "evidence_refs": sorted({p["evidence_ref"] for p in active})})
            require(sum(centers.values(), Decimal(0)) == wall, "Internal accounting failed to conserve selected wall time")
            if unallocated:
                issues.append("Some measured wall time is unallocated; silence does not identify idle time or cause")
            if not wall:
                notes.append("Zero reported window duration; no rate or percentage denominator established")
        resources = []
        for resource in run["resources"]:
            units = BYTE_UNITS if resource["kind"] in ("peak_memory", "byte_count") else TIME_UNITS
            qualified = (resource["basis"] == "measured" and resource["value"] is not None and resource["unit"] in units
                         and all(text(resource[k]) for k in ("definition_ref", "scope_ref", "evidence_ref")))
            row = dict(resource)
            row.update(normalized_value=rendered(dec(resource["value"]) * dec(units[resource["unit"]])) if qualified else None,
                       normalized_unit=("B" if units is BYTE_UNITS else "s") if qualified else None)
            if not qualified:
                measurements.append(f"Unqualified resource observation: {resource['id']}")
            resources.append(row)
        progress = run["simulation_progress"]
        progress_known = (progress["basis"] == "measured" and progress["amount"] is not None and progress["unit"] is not None
                          and text(progress["evidence_ref"]) and text(progress["scope_ref"]) and text(progress["definition_ref"]))
        normalized_progress = None
        if progress_known:
            normalized_progress = dec(progress["amount"]) * (Decimal(1) if progress["unit"] == "cycles" else dec(TIME_UNITS[progress["unit"]]))
        rate = None
        if normalized_progress is not None and wall is not None and wall > 0 and progress["scope_ref"] == window["scope_ref"]:
            rate = {"value": rendered(normalized_progress / wall), "unit": "cycles/wall_s" if progress["unit"] == "cycles" else "sim_s/wall_s"}
        elif progress_known:
            measurements.append("Progress/window scope or positive measured wall denominator is not established for a rate")
    missing = sorted((RESOURCE_KINDS - {"elapsed_time"}) - {r["kind"] for r in resources if r["normalized_value"] is not None})
    if not progress_known:
        missing.append("simulation_progress")
    return {"format": "opentools.cost-audit.v1", "status": "partial_accounting" if issues else "accounted_window",
            "run_ref": run["run_ref"], "task": run["task"], "window": window, "completion": run["completion"],
            "collection": run["collection"], "context": run["context"], "phase_records": run["phases"],
            "window_wall_s": rendered(wall) if wall is not None else None, "segments": segments,
            "ranked_cost_centers": [{"bucket": name, "wall_s": rendered(value)} for name, value in sorted(centers.items(), key=lambda p: (-p[1], p[0]))],
            "shared_wall_s": rendered(shared) if wall is not None else None,
            "unallocated_wall_s": rendered(unallocated) if wall is not None else None,
            "overlay_union_s": {name: rendered(value) for name, value in sorted(overlays.items())},
            "resource_observations": resources, "simulation_progress": progress, "progress_rate": rate,
            "unmeasured_quantities": missing, "accounting_issues": issues, "measurement_issues": measurements, "notes": notes,
            "input_fingerprint": digest(run), "provenance": run.get("provenance"),
            "limits": "Measured selected-window accounting only. Overlays and inclusive resource observations are not added to its budget. No causal bottleneck, useful-work, financial saving or full-task improvement is inferred."}


def compare(before, after, policy):
    baseline, current = analyze(before), analyze(after)
    shape(policy, {"format", "baseline_run_ref", "current_run_ref", "question", "roles"})
    require(policy["format"] == "opentools.cost-comparison.v1" and policy["baseline_run_ref"] == before["run_ref"]
            and policy["current_run_ref"] == after["run_ref"] and text(policy["question"]), "Comparison policy must bind the selected runs and question")
    require(isinstance(policy["roles"], dict) and set(policy["roles"]) == CONTEXT, "Classify all five comparison context fields")
    unknowns, confounders, rows, intended = [], [], [], []
    for name in sorted(CONTEXT):
        rule = policy["roles"][name]
        shape(rule, {"role", "reason", "evidence_ref"})
        require(rule["role"] in ("fixed", "intended") and text(rule["reason"]) and text(rule["evidence_ref"]), "Each role needs a reason and source")
        old, new = before["context"][name], after["context"][name]
        if not known(old) or not known(new):
            finding = "unknown"
            unknowns.append(f"Comparison context is missing: {name}")
        elif old["value"] == new["value"]:
            finding = "equal"
        elif rule["role"] == "intended":
            finding = "intended_change"
            intended.append(name)
        else:
            finding = "confounder"
            confounders.append(f"Fixed comparison context differs: {name}")
        rows.append({"field": name, "baseline": old, "current": new, "rule": rule, "finding": finding})
    if not text(before["window"]["scope_ref"]) or not text(after["window"]["scope_ref"]):
        unknowns.append("Selected window scope is unknown")
    elif before["window"]["scope_ref"] != after["window"]["scope_ref"]:
        confounders.append("Selected measurement window scopes differ")
    for name, run, report in (("baseline", before, baseline), ("current", after, current)):
        if report["window_wall_s"] is None:
            unknowns.append(f"{name}: measured wall window is not established")
        completion = run["completion"]
        if completion["outcome"] != "completed" or completion["required_evidence_complete"] is not True or not text(completion["evidence_ref"]):
            unknowns.append(f"{name}: successful completion with required evidence is not established")
    delta = percentage = None
    with localcontext() as ctx:
        ctx.prec = 40
        if baseline["window_wall_s"] is not None and current["window_wall_s"] is not None:
            b, c = dec(baseline["window_wall_s"]), dec(current["window_wall_s"])
            delta = rendered(c - b)
            percentage = rendered((c - b) * 100 / b) if b > 0 else None
    p, q = baseline["simulation_progress"], current["simulation_progress"]
    progress_status, rate_ratio = "unknown", None
    if baseline["progress_rate"] is not None and current["progress_rate"] is not None:
        if p["definition_ref"] != q["definition_ref"] or baseline["progress_rate"]["unit"] != current["progress_rate"]["unit"]:
            progress_status = "different_definition"
        else:
            with localcontext() as ctx:
                # Preserve exact wide counter identity before computing rounded rates.
                ctx.prec = max(40, len(dec(p["amount"]).as_tuple().digits) + 20, len(dec(q["amount"]).as_tuple().digits) + 20)
                p_value = dec(p["amount"]) * (Decimal(1) if p["unit"] == "cycles" else dec(TIME_UNITS[p["unit"]]))
                q_value = dec(q["amount"]) * (Decimal(1) if q["unit"] == "cycles" else dec(TIME_UNITS[q["unit"]]))
                progress_status = "matched" if p_value == q_value else "different_amount"
            if progress_status == "matched" and dec(baseline["progress_rate"]["value"]) > 0:
                with localcontext() as ctx:
                    ctx.prec = 40
                    rate_ratio = rendered(dec(current["progress_rate"]["value"]) / dec(baseline["progress_rate"]["value"]))
    changed_task = any(k in intended for k in ("workload_ref", "evidence_scope_ref", "configuration_ref")) or progress_status.startswith("different_")
    status = "confounded" if confounders else "incomplete" if unknowns else "descriptive_difference" if changed_task else "comparable_window_observation"
    return {"format": "opentools.cost-comparison-report.v1", "status": status, "question": policy["question"],
            "baseline": baseline, "current": current, "conditions": rows, "intended_changes": intended,
            "confounders": confounders, "unknowns": unknowns, "reported_wall_delta_s": delta, "reported_wall_delta_percent": percentage,
            "progress_correspondence": progress_status, "reported_progress_rate_ratio": rate_ratio,
            "same_input_record": digest(before) == digest(after), "policy_fingerprint": digest(policy),
            "limits": "Reported selected-window difference under supplied context/roles; not isolated causality, equivalent verification, total workflow savings, resource savings or financial benefit. Partial stage attribution remains in each audit."}


def exit_code(report):
    return 1 if report["status"] == "confounded" else 2 if report["status"] in ("partial_accounting", "incomplete") else 0


def markdown(report):
    def esc(value):
        return html.escape(str(value)).replace("|", "&#124;").replace("\n", "<br>")
    if report["format"] == "opentools.cost-comparison-report.v1":
        lines = ["# Simulation cost comparison", "", f"Status: **{report['status']}**", "", esc(report["question"]), "",
                 f"Reported window delta: {esc(report['reported_wall_delta_s'])} s ({esc(report['reported_wall_delta_percent'])}%).", "",
                 f"Measured progress correspondence: {esc(report['progress_correspondence'])}; rate ratio: {esc(report['reported_progress_rate_ratio'])}.", "",
                 "| Context | Baseline | Current | Role / finding | Evidence |", "|---|---|---|---|---|"]
        for row in report["conditions"]:
            lines.append(f"| {row['field']} | {esc(row['baseline']['value'])} | {esc(row['current']['value'])} | {row['rule']['role']} / {row['finding']} | {esc(row['baseline']['evidence_ref'])}; {esc(row['current']['evidence_ref'])}; {esc(row['rule']['evidence_ref'])} |")
        for key in ("confounders", "unknowns"):
            lines.extend(["", key.capitalize() + ": " + esc("; ".join(report[key]) or "none")])
        lines.extend(["", esc(report["limits"]), "", "## Baseline window", "", markdown(report["baseline"]), "## Current window", "", markdown(report["current"])])
        return "\n".join(lines)
    lines = ["# Simulation cost audit", "", f"Status: **{report['status']}**", "", esc(report["task"]), "",
             f"Run: {esc(report['run_ref'])}. Outcome: {esc(report['completion']['outcome'])}.", "",
             f"Measured selected window: {esc(report['window_wall_s'])} s. Scope: {esc(report['window']['scope_ref'])}.", "",
             f"Clock: {esc(report['window']['clock_ref'])}. Window source: {esc(report['window']['evidence_ref'])}.", "",
             "| Wall budget bucket | Seconds |", "|---|---:|"]
    for center in report["ranked_cost_centers"]:
        lines.append(f"| {esc(center['bucket'])} | {center['wall_s']} |")
    lines.extend(["", "## Timeline", "", "| Start s | End s | Bucket | Overlays | Sources |", "|---:|---:|---|---|---|"])
    for segment in report["segments"]:
        lines.append(f"| {segment['start_s']} | {segment['end_s']} | {esc(segment['bucket'])} | {esc(', '.join(segment['overlay_phase_ids']))} | {esc('; '.join(segment['evidence_refs']))} |")
    lines.extend(["", "## Separate resource observations", "", "| Observation | Kind | Reported value/unit | Scope | Source |", "|---|---|---|---|---|"])
    for row in report["resource_observations"]:
        lines.append(f"| {esc(row['id'])} | {row['kind']} | {esc(row['value'])} {esc(row['unit'])} ({row['basis']}) | {esc(row['scope_ref'])} | {esc(row['evidence_ref'])}; {esc(row['definition_ref'])} |")
    lines.extend(["", "Progress rate: " + esc(canonical(report["progress_rate"])) + ".", "",
                  "Unmeasured/unqualified quantities: " + esc(", ".join(report["unmeasured_quantities"]) or "none") + "."])
    for label, key in (("Accounting gaps", "accounting_issues"), ("Measurement gaps", "measurement_issues"), ("Notes", "notes")):
        lines.extend(["", label + ": " + esc("; ".join(report[key]) or "none")])
    lines.extend(["", esc(report["limits"]), ""])
    return "\n".join(lines)
