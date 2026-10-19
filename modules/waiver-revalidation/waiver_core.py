"""Evidence-based waiver comparison. No tool matching or approval inference."""

from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path


SNAPSHOT_FORMAT = "opentools.waiver-snapshot.v1"
POLICY_FORMAT = "opentools.waiver-policy.v1"
MAPPING_FORMAT = "opentools.waiver-identity-map.v1"


class InputError(ValueError):
    """Input cannot support the requested analysis."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InputError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise InputError(f"Non-finite JSON number: {value}")

    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                          object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputError(f"Cannot read {path}: {exc}") from exc


def require(condition, message):
    if not condition:
        raise InputError(message)


def text_field(obj, key, context):
    value = obj.get(key)
    require(isinstance(value, str) and bool(value.strip()), f"{context}.{key}: nonempty string required")
    return value


def unique_index(items, context):
    require(isinstance(items, list), f"{context}: array required")
    result = {}
    for item in items:
        require(isinstance(item, dict), f"{context}: object required")
        item_id = text_field(item, "id", context)
        require(item_id not in result, f"{context}: duplicate id {item_id}")
        result[item_id] = item
    return result


def validate_snapshot(snapshot):
    require(isinstance(snapshot, dict), "Snapshot must be an object")
    require(snapshot.get("format") == SNAPSHOT_FORMAT, f"Expected format {SNAPSHOT_FORMAT}")
    for key in ("run_id", "scope", "configuration_ref", "identity_basis"):
        text_field(snapshot, key, "snapshot")
    tool = snapshot.get("tool")
    require(isinstance(tool, dict), "snapshot.tool: object required")
    for key in ("name", "version", "ruleset"):
        text_field(tool, key, "tool")
    require(isinstance(snapshot.get("configuration"), dict), "configuration: object required")
    if "configuration_basis" in snapshot:
        text_field(snapshot, "configuration_basis", "snapshot")
    require(type(snapshot.get("population_complete")) is bool,
            "population_complete: explicit boolean required")
    waivers = unique_index(snapshot.get("waivers"), "waivers")
    require(bool(waivers), "Snapshot must include at least one explicitly selected waiver")
    for waiver_id, waiver in waivers.items():
        definition = text_field(waiver, "definition_sha256", waiver_id)
        require(len(definition) == 64 and all(c in "0123456789abcdef" for c in definition),
                f"{waiver_id}: definition_sha256 must be a lowercase SHA-256 digest")
        require(type(waiver.get("complete")) is bool, f"{waiver_id}.complete: boolean required")
        for finding_id, finding in unique_index(waiver.get("findings"), f"{waiver_id}.findings").items():
            for key in ("object", "rule", "message", "evidence_ref"):
                text_field(finding, key, finding_id)
    canonical(snapshot)  # Also reject non-JSON/non-finite API values.
    return waivers


def validate_policy(policy, current_waivers):
    if policy is None:
        return {}
    require(isinstance(policy, dict) and policy.get("format") == POLICY_FORMAT,
            f"Expected policy format {POLICY_FORMAT}")
    indexed = unique_index(policy.get("waivers"), "policy.waivers")
    require(set(indexed) <= set(current_waivers), "Policy refers to an absent current waiver")
    for waiver_id, entry in indexed.items():
        premises = entry.get("premises")
        require(isinstance(premises, list), f"{waiver_id}.premises: array required")
        keys = set()
        for premise in premises:
            require(isinstance(premise, dict), "Premise must be an object")
            key = text_field(premise, "key", "premise")
            text_field(premise, "evidence_ref", "premise")
            require(key not in keys, f"Duplicate premise for {waiver_id}/{key}")
            keys.add(key)
            require("equals" in premise and type(premise["equals"]) in (str, int, float, bool),
                    "Premise equals must be a non-null JSON scalar")
    canonical(policy)
    return indexed


def validate_mappings(mapping, baseline, current):
    if mapping is None:
        return {}
    require(isinstance(mapping, dict) and mapping.get("format") == MAPPING_FORMAT,
            f"Expected mapping format {MAPPING_FORMAT}")
    entries = mapping.get("mappings")
    require(isinstance(entries, list), "mappings: array required")
    result = {}
    for entry in entries:
        require(isinstance(entry, dict), "Mapping must be an object")
        for key in ("waiver_id", "from", "to", "evidence_ref"):
            text_field(entry, key, "mapping")
        wid = entry["waiver_id"]
        require(wid in baseline and wid in current, f"Mapping waiver absent: {wid}")
        old = unique_index(baseline[wid]["findings"], "baseline findings")
        new = unique_index(current[wid]["findings"], "current findings")
        require(entry["from"] in old and entry["to"] in new, "Mapping endpoint absent")
        bucket = result.setdefault(wid, {})
        require(entry["from"] not in bucket, "Duplicate mapping source")
        bucket[entry["from"]] = entry
    for wid, bucket in result.items():
        ids = [bucket[f["id"]]["to"] if f["id"] in bucket else f["id"]
               for f in baseline[wid]["findings"]]
        require(len(ids) == len(set(ids)), "Mapping is not one-to-one, including unchanged identities")
    return result


def _issue(code, severity, message, **details):
    return {"code": code, "severity": severity, "message": message, **details}


def _status(issues):
    if any(item["severity"] == "unknown" for item in issues):
        return "incomplete"
    if any(item["severity"] == "review" for item in issues):
        return "review_required"
    return "unchanged_within_scope"


def compare(baseline, current, policy=None, identity_map=None):
    """Compare captured populations; differences never approve/revoke a waiver."""
    old = validate_snapshot(baseline)
    new = validate_snapshot(current)
    policies = validate_policy(policy, new)
    mappings = validate_mappings(identity_map, old, new)
    global_issues = []
    for key in ("scope", "identity_basis"):
        if baseline[key] != current[key]:
            global_issues.append(_issue(f"{key}_changed", "unknown", f"Comparison {key} differs.",
                                        baseline=baseline[key], current=current[key]))
    if baseline.get("configuration_basis", "exporter-defined") != current.get("configuration_basis", "exporter-defined"):
        global_issues.append(_issue("configuration_basis_changed", "unknown", "Configuration observation bases differ."))
    for key in ("name", "version", "ruleset"):
        if baseline["tool"][key] != current["tool"][key]:
            global_issues.append(_issue(f"tool_{key}_changed", "unknown",
                                        f"Native tool {key} differs; population comparability is unresolved."))
    if not baseline["population_complete"] or not current["population_complete"]:
        global_issues.append(_issue("incomplete_population", "unknown", "At least one capture is incomplete."))
    if "capture" in baseline and "capture" in current:
        for key in ("profile", "top", "population_basis"):
            if baseline["capture"].get(key) != current["capture"].get(key):
                global_issues.append(_issue("capture_context_changed", "unknown",
                                            f"Native capture context {key} differs."))
    results = []
    for wid in sorted(set(old) | set(new)):
        issues = []
        before, after = old.get(wid), new.get(wid)
        if before is None or after is None:
            issues.append(_issue("waiver_presence_changed", "review", "Waiver absent from one snapshot; no disposition inferred."))
            results.append({"id": wid, "status": _status(global_issues + issues), "issues": issues,
                            "added": [], "removed": [], "mappings": [], "premises": []})
            continue
        if not before["complete"] or not after["complete"]:
            issues.append(_issue("incomplete_waiver_population", "unknown", "The selected waiver population is incomplete."))
        if before["definition_sha256"] != after["definition_sha256"]:
            issues.append(_issue("waiver_definition_changed", "review", "Waiver file/definition content changed."))
        if not after["findings"] and after["complete"]:
            issues.append(_issue("empty_population", "review", "The selected waiver suppresses no observable findings in this capture; inspect applicability."))
        before_findings = unique_index(before["findings"], "baseline findings")
        after_findings = unique_index(after["findings"], "current findings")
        selected_map = mappings.get(wid, {})
        translated = {selected_map[key]["to"] if key in selected_map else key: value
                      for key, value in before_findings.items()}
        added = [after_findings[key] for key in sorted(set(after_findings) - set(translated))]
        removed = [translated[key] for key in sorted(set(translated) - set(after_findings))]
        if added:
            issues.append(_issue("population_expanded", "review", "Additional findings are suppressed in the current capture.", count=len(added)))
        if removed:
            issues.append(_issue("population_reduced_or_unmapped", "review", "Previously suppressed findings are absent or have changed identity; no removal inferred.", count=len(removed)))
        for key in sorted(set(translated) & set(after_findings)):
            previous, following = translated[key], after_findings[key]
            # Explicit correspondence may rename an object, but cannot silently rewrite rule/meaning.
            changed = [field for field in ("rule", "message") if previous[field] != following[field]]
            if previous["id"] == following["id"] and previous["object"] != following["object"]:
                changed.append("object")
            if changed:
                issues.append(_issue("finding_meaning_changed", "review", "Corresponding finding content changed.", finding_id=key, fields=changed))
        premise_results = []
        for premise in policies.get(wid, {}).get("premises", []):
            key = premise["key"]
            observed = current["configuration"].get(key)
            if key not in current["configuration"] or observed is None:
                outcome = "unknown"
                issues.append(_issue("premise_evidence_missing", "unknown", f"Current value of {key} is unavailable.", evidence_ref=premise["evidence_ref"]))
            elif type(observed) is not type(premise["equals"]) or observed != premise["equals"]:
                outcome = "does_not_hold"
                issues.append(_issue("premise_does_not_hold", "review", f"Recorded premise for {key} does not hold.", expected=premise["equals"], observed=observed, evidence_ref=premise["evidence_ref"]))
            else:
                outcome = "holds"
            premise_results.append({**premise, "observed": observed, "outcome": outcome,
                                    "configuration_ref": current["configuration_ref"]})
        results.append({"id": wid, "status": _status(global_issues + issues), "issues": issues,
                        "added": added, "removed": removed, "mappings": list(selected_map.values()),
                        "premises": premise_results})
    all_issues = global_issues + [issue for result in results for issue in result["issues"]]
    return {"format": "opentools.waiver-audit.v1", "baseline_run_id": baseline["run_id"],
            "current_run_id": current["run_id"], "scope": current["scope"], "status": _status(all_issues),
            "review_required": any(issue["severity"] == "review" for issue in all_issues),
            "global_issues": global_issues, "waivers": results,
            "input_fingerprints": {"baseline": digest(baseline), "current": digest(current),
                                   "policy": digest(policy) if policy is not None else None,
                                   "identity_map": digest(identity_map) if identity_map is not None else None},
            "meaning": "Comparison of observed suppression only; no waiver approval, rejection, or design-defect decision."}


def markdown(report):
    def escape(value):
        return html.escape(str(value)).replace("|", "&#124;").replace("\n", " ").replace("\r", " ")

    lines = ["# Waiver revalidation", "", f"Status: **{report['status']}**", "",
             f"Baseline: {escape(report['baseline_run_id'])}; current: {escape(report['current_run_id'])}.", "",
             report["meaning"], "", "| Waiver | Status | Added | Absent/unmapped |", "|---|---|---:|---:|"]
    for waiver in report["waivers"]:
        lines.append(f"| {escape(waiver['id'])} | {waiver['status']} | {len(waiver['added'])} | {len(waiver['removed'])} |")
    for issue in report["global_issues"]:
        lines += ["", f"- {escape(issue['code'])}: {escape(issue['message'])}"]
    for waiver in report["waivers"]:
        lines += ["", f"## {escape(waiver['id'])}"]
        for issue in waiver["issues"]:
            lines += ["", f"- {escape(issue['code'])}: {escape(issue['message'])}"]
        for category in ("added", "removed"):
            for finding in waiver[category]:
                lines += ["", f"- {category}: {escape(finding['object'])} / {escape(finding['rule'])}: "
                          f"{escape(finding['message'])} (evidence: {escape(finding['evidence_ref'])})"]
        for premise in waiver["premises"]:
            lines += ["", f"- Premise {escape(premise['key'])}: {premise['outcome']}; "
                      f"expected {escape(canonical(premise['equals']))}, observed {escape(canonical(premise['observed']))}; "
                      f"evidence {escape(premise['configuration_ref'])}, {escape(premise['evidence_ref'])}."]
        for mapping in waiver["mappings"]:
            lines += ["", f"- Explicit correspondence: {escape(mapping['from'])} -> {escape(mapping['to'])}; "
                      f"basis: {escape(mapping['evidence_ref'])}."]
    return "\n".join(lines) + "\n"
