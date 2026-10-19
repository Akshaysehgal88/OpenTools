"""Qualify reported PPA deltas against explicit per-metric experiment contracts."""
from __future__ import annotations

import hashlib
import html
import json
import math
from decimal import Decimal, localcontext
from pathlib import Path

COMMON = {"design_ref", "rtl_ref", "netlist_ref", "stage", "tool_ref", "flow_ref", "library_ref", "corner_ref", "constraints_ref"}
IDENTITY = {"design_ref", "rtl_ref", "netlist_ref", "stage", "tool_ref", "flow_ref"}
POWER = {"activity_source_ref", "activity_window", "activity_scope_ref", "activity_mapping_ref", "annotation_scope_ref", "annotation_basis", "annotated_fraction", "unannotated_policy"}
FAMILIES = {"instance_area": "area", "stdcell_area": "area", "die_area": "area", "setup_slack": "time", "total_power": "power", "dynamic_power": "power", "leakage_power": "power"}
UNITS = {"area": ("um2", {"nm2": "0.000001", "um2": "1", "mm2": "1000000", "m2": "1000000000000"}),
         "time": ("ns", {"fs": "0.000001", "ps": "0.001", "ns": "1", "us": "1000", "ms": "1000000", "s": "1000000000"}),
         "power": ("W", {"W": "1", "mW": "0.001", "uW": "0.000001", "nW": "0.000000001"})}


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


def pairs(values):
    result = {}
    for k, v in values:
        require(k not in result, f"Duplicate JSON key: {k}")
        result[k] = v
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(InputError(f"Invalid number: {value}")))


def index(items, label):
    require(isinstance(items, list), f"{label} must be a list")
    result = {}
    for item in items:
        require(isinstance(item, dict) and text(item.get("id")) and item["id"] not in result, f"{label}: unique nonempty ids are required")
        result[item["id"]] = item
    return result


def known(condition):
    return condition is not None and condition["value"] is not None and (not isinstance(condition["value"], str) or text(condition["value"])) and text(condition.get("evidence_ref"))


def validate_conditions(conditions):
    require(isinstance(conditions, dict), "conditions must be an object")
    for name, item in conditions.items():
        require(text(name) and isinstance(item, dict) and set(item) == {"value", "evidence_ref"}, "Condition needs value and evidence_ref")
        value = item["value"]
        scalar = lambda v: v is None or type(v) in (str, bool, int) or (type(v) is float and math.isfinite(v))
        require(scalar(value) or (isinstance(value, list) and all(scalar(v) and v is not None for v in value)), "Condition values must be scalars or flat known scalar lists")
        require(item["evidence_ref"] is None or text(item["evidence_ref"]), "Use null for missing evidence_ref")
        if name in IDENTITY and value is not None:
            require(text(value), f"{name} must be a nonempty identity string or null")
        if name == "annotated_fraction" and value is not None:
            require(number(value) and 0 <= value <= 1, "annotated_fraction must be 0..1 or null")


def validate_snapshot(snapshot):
    require(isinstance(snapshot, dict) and snapshot.get("format") == "opentools.ppa-snapshot.v1", "Unsupported snapshot format")
    require(set(snapshot) <= {"format", "run_id", "source_ref", "context_ref", "metrics", "provenance"}, "Unsupported snapshot property")
    for key in ("run_id", "source_ref", "context_ref"):
        require(text(snapshot.get(key)), f"Snapshot requires {key}")
    metrics = index(snapshot.get("metrics"), "metrics")
    require(metrics, "Select at least one metric")
    for metric in metrics.values():
        require(set(metric) == {"id", "kind", "definition_ref", "scope_ref", "value", "unit", "unit_evidence", "evidence_ref", "measurement_complete", "conditions"}, "Unexpected or missing metric property")
        require(metric["kind"] in FAMILIES and text(metric["definition_ref"]) and text(metric["evidence_ref"]), "Metric kind/definition/evidence is required")
        for key in ("scope_ref", "unit", "unit_evidence"):
            require(metric[key] is None or text(metric[key]), f"Metric {key} must be nonempty or null")
        require(metric["value"] is None or number(metric["value"]), "Metric value must be finite numeric or null")
        if metric["value"] is not None and FAMILIES[metric["kind"]] != "time":
            require(metric["value"] >= 0, "Area/power cannot be negative")
        require(type(metric["measurement_complete"]) is bool, "measurement_complete must be boolean")
        validate_conditions(metric["conditions"])
    return metrics


def _rules(entry):
    require(set(entry) <= {"id", "claim", "rules", "equivalences"} and text(entry.get("claim")), "Metric contract requires claim and rules")
    rules = entry.get("rules")
    require(isinstance(rules, dict), "rules must be an object")
    for name, rule in rules.items():
        require(text(name) and isinstance(rule, dict), "Invalid condition rule")
        require(set(rule) <= {"role", "reason", "evidence_ref", "from"}, "Unsupported rule property")
        require(rule.get("role") in ("fixed", "intended", "derived", "irrelevant"), "Unknown condition role")
        require(text(rule.get("reason")) and text(rule.get("evidence_ref")), "Every rule requires reason and evidence_ref")
        if rule["role"] == "derived":
            require(isinstance(rule.get("from"), list) and rule["from"] and all(text(k) and k in rules for k in rule["from"]), "Derived rules require declared parent conditions")
            require(len(rule["from"]) == len(set(rule["from"])), "Repeated derived parent")
        else:
            require("from" not in rule, "Only derived rules can declare parents")
    visiting, done = set(), set()
    def visit(name):
        require(name not in visiting, "Derived condition cycle")
        if name in done: return
        visiting.add(name)
        for parent in rules[name].get("from", []): visit(parent)
        visiting.remove(name); done.add(name)
    for name in rules: visit(name)
    return rules


def _decimal(value, family, unit):
    if value is None or unit not in UNITS[family][1]: return None
    return Decimal(str(value)) * Decimal(UNITS[family][1][unit])


def compare(baseline, current, contract):
    before, after = validate_snapshot(baseline), validate_snapshot(current)
    require(isinstance(contract, dict) and contract.get("format") == "opentools.ppa-contract.v1", "Unsupported contract format")
    require(set(contract) == {"format", "baseline_run_id", "current_run_id", "metrics"}, "Unexpected or missing contract property")
    require(contract["baseline_run_id"] == baseline["run_id"] and contract["current_run_id"] == current["run_id"], "Contract run binding differs")
    selected = index(contract["metrics"], "contract metrics")
    require(selected, "Contract selects no metrics")
    rows = []
    for metric_id, entry in selected.items():
        rules = _rules(entry)
        a, b = before.get(metric_id), after.get(metric_id)
        issues, confounders, warnings, conditions = [], [], [], []
        row = {"id": metric_id, "claim": entry["claim"], "baseline": a, "current": b,
               "conditions": conditions, "issues": issues, "confounders": confounders, "warnings": warnings,
               "delta": None, "percent_change": None, "canonical_unit": None, "normalized_values": None}
        if a is None or b is None:
            issues.append("Selected metric is missing in one snapshot")
            row["status"] = "incomplete"; rows.append(row); continue
        required = COMMON | (POWER if FAMILIES[a["kind"]] == "power" else set())
        ca, cb = a["conditions"], b["conditions"]
        for side, metric in (("baseline", a), ("current", b)):
            if not metric["measurement_complete"]: issues.append(f"{side} measurement is incomplete")
            if metric["value"] is None: issues.append(f"{side} native metric value is unavailable")
            if not text(metric["scope_ref"]): issues.append(f"{side} metric scope is unknown")
            if not text(metric["unit_evidence"]): issues.append(f"{side} metric unit basis is unknown")
            hard = IDENTITY | (POWER if FAMILIES[metric["kind"]] == "power" else set())
            for name in sorted(hard):
                if not known(metric["conditions"].get(name)): issues.append(f"{side} required provenance/activity basis {name} is unknown")
        structural = a["kind"] == b["kind"] and a["definition_ref"] == b["definition_ref"] and a["scope_ref"] == b["scope_ref"] and text(a["scope_ref"])
        if not structural: issues.append("Metric kind, definition or scope is not established as comparable; no arithmetic comparison is established")
        equivalents = {}
        require(isinstance(entry.get("equivalences", []), list), "equivalences must be a list")
        for eq in entry.get("equivalences", []):
            require(isinstance(eq, dict) and set(eq) == {"field", "baseline", "current", "evidence_ref"}, "Invalid equivalence declaration")
            name = eq["field"]
            require(text(name) and name in rules and rules[name]["role"] == "fixed" and name not in equivalents and text(eq["evidence_ref"]), "Equivalence requires a unique fixed field and evidence")
            require(known(ca.get(name)) and known(cb.get(name)) and canonical(eq["baseline"]) == canonical(ca[name]["value"]) and canonical(eq["current"]) == canonical(cb[name]["value"]), "Equivalence does not match the observed pair")
            require(canonical(eq["baseline"]) != canonical(eq["current"]), "Equivalence is unnecessary for equal values")
            equivalents[name] = eq
        changed = {name for name in set(ca) | set(cb) if known(ca.get(name)) and known(cb.get(name)) and canonical(ca[name]["value"]) != canonical(cb[name]["value"])}
        def changed_ancestor(name):
            return any((parent in changed and parent not in equivalents) or changed_ancestor(parent) for parent in rules[name].get("from", []))
        for name in sorted(set(ca) | set(cb) | set(rules) | required):
            old, new, rule = ca.get(name), cb.get(name), rules.get(name)
            role = rule["role"] if rule else "unclassified"
            observed = known(old) and known(new)
            is_changed = name in changed
            if role == "irrelevant": outcome = "declared_irrelevant"
            elif not observed:
                outcome = "unknown"; issues.append(f"{name}: comparison evidence is missing")
            elif not rule:
                outcome = "unclassified_change" if is_changed else "unchanged_unclassified"
                if is_changed or name in required: issues.append(f"{name}: experiment role is not declared")
            elif role == "fixed":
                outcome = "reviewed_equivalent" if name in equivalents else "fixed_difference" if is_changed else "fixed_equal"
                if is_changed and name not in equivalents: confounders.append(name)
            elif role == "intended":
                outcome = "intended_change" if is_changed else "intended_unchanged"
                if not is_changed: warnings.append(f"{name}: intended variable did not change in the supplied record")
            else:
                outcome = "declared_derived_change" if is_changed else "derived_equal"
                if is_changed and not changed_ancestor(name): issues.append(f"{name}: derived value changed without an observed change in its declared ancestors")
            conditions.append({"field": name, "role": role, "outcome": outcome, "baseline": old, "current": new,
                               "rule": rule, "equivalence": equivalents.get(name)})
        if structural:
            family = FAMILIES[a["kind"]]
            with localcontext() as decimal_context:
                decimal_context.prec = 40
                av, bv = _decimal(a["value"], family, a["unit"]), _decimal(b["value"], family, b["unit"])
                if av is None or bv is None: issues.append("Metric unit/value is unknown or outside the supported conversion table")
                elif text(a["unit_evidence"]) and text(b["unit_evidence"]):
                    row.update(canonical_unit=UNITS[family][0], normalized_values=[str(av), str(bv)], delta=str(bv-av))
                    if family != "time" and av > 0: row["percent_change"] = str((bv-av)/av*100)
        row["status"] = "incomplete" if issues else "confounded" if confounders else "comparable_within_contract"
        rows.append(row)
    return {"format": "opentools.ppa-audit.v1", "baseline_run_id": baseline["run_id"], "current_run_id": current["run_id"],
            "status": "incomplete" if any(r["issues"] for r in rows) else "confounded" if any(r["confounders"] for r in rows) else "comparable_within_contract",
            "confounders_found": any(r["confounders"] for r in rows), "metrics": rows,
            "input_fingerprints": {"baseline": digest(baseline), "current": digest(current), "contract": digest(contract)},
            "same_snapshot": digest(baseline) == digest(current),
            "same_source_ref": baseline["source_ref"] == current["source_ref"],
            "unselected_metrics": sorted((set(before) | set(after)) - set(selected)),
            "limits": ["Qualification is relative to the explicit contract and supplied evidence, not a causal or signoff proof.",
                       "Arithmetic may be shown for confounded or incomplete conditions; it remains an unqualified reported delta.",
                       "Derived relationships, irrelevant fields and equivalences are declared by the contract, not independently proved.",
                       "Slack delta is not frequency gain. No timing percentage, cross-metric average or PPA prediction is produced."]}


def markdown(report):
    esc = lambda v: html.escape(str(v)).replace("|", "&#124;").replace("\n", " ").replace("\r", " ")
    lines = ["# PPA comparison check", "", f"Status: **{report['status']}**", "",
             f"Runs: {esc(report['baseline_run_id'])} / {esc(report['current_run_id'])}.", ""]
    for metric in report["metrics"]:
        lines += [f"## {esc(metric['id'])}", "", esc(metric["claim"]), "", f"Result: **{metric['status']}**. Reported delta: {esc(metric['delta'])} {esc(metric['canonical_unit'])}.", "",
                  "| Condition | Role | Outcome | Baseline | Current | Evidence / policy |", "|---|---|---|---|---|---|"]
        for c in metric["conditions"]:
            evidence = [v["evidence_ref"] for v in (c["baseline"], c["current"], c["rule"], c["equivalence"]) if v and text(v.get("evidence_ref"))]
            lines.append("| " + " | ".join(esc(v) for v in (c["field"], c["role"], c["outcome"], canonical(c["baseline"]["value"]) if c["baseline"] else "unknown", canonical(c["current"]["value"]) if c["current"] else "unknown", "; ".join(evidence))) + " |")
        for key in ("issues", "confounders", "warnings"):
            lines += ["", f"{key.capitalize()}: " + esc("; ".join(metric[key]) or "none")]
        for side in ("baseline", "current"):
            native = metric[side]
            if native:
                lines += ["", f"{side.capitalize()} reported value: {esc(native['value'])} {esc(native['unit'])}; source: {esc(native['evidence_ref'])}; unit basis: {esc(native['unit_evidence'])}."]
        lines.append("")
    lines += ["## Interpretation limits", ""] + ["- " + esc(v) for v in report["limits"]]
    if report["same_snapshot"]: lines += ["", "The same snapshot was supplied twice; this is not an independent rerun."]
    elif report["same_source_ref"]: lines += ["", "Both snapshots name the same source reference; different labels do not establish independent runs."]
    return "\n".join(lines) + "\n"
