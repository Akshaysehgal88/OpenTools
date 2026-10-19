"""Compare a recorded result with a bounded claim, preserving evidence limits."""
from __future__ import annotations

import hashlib
import html
import json
import math
from pathlib import Path


class InputError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InputError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_hash(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


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
            f"Expected fields {sorted(required)} with optional {sorted(optional)}")


def json_value(value):
    if value is None or type(value) in (bool, int, str):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if isinstance(value, list):
        return all(json_value(v) for v in value)
    if isinstance(value, dict):
        return all(text(k) and json_value(v) for k, v in value.items())
    return False


def validate_fields(fields):
    require(isinstance(fields, dict), "fields must be an object")
    for key, item in fields.items():
        require(text(key), "Field names must be nonempty")
        shape(item, {"value", "evidence_ref"})
        require(json_value(item["value"]), f"Invalid field value: {key}")
        require(item["evidence_ref"] is None or text(item["evidence_ref"]), "Invalid evidence reference")


def known(item):
    # Null anywhere in a structured value means that its full identity is unknown.
    def complete(value):
        if value is None or (isinstance(value, str) and not text(value)):
            return False
        if isinstance(value, list):
            return all(complete(v) for v in value)
        if isinstance(value, dict):
            return all(complete(v) for v in value.values())
        return True
    return item is not None and complete(item["value"]) and text(item["evidence_ref"])


def validate_snapshot(record):
    shape(record, {"format", "run_ref", "manifest_ref", "execution", "result", "fields"}, {"provenance"})
    require(record["format"] == "opentools.result-snapshot.v1", "Unsupported snapshot format")
    require(text(record["run_ref"]) and text(record["manifest_ref"]), "Run and manifest references required")
    execution = record["execution"]
    shape(execution, {"state", "evidence_ref", "command", "executable_ref", "dependency_capture_complete", "dependency_evidence_ref"})
    require(execution["state"] in ("completed", "failed", "not_run", "unknown"), "Invalid execution state")
    require(execution["command"] is None or (isinstance(execution["command"], list) and execution["command"] and
            all(text(v) for v in execution["command"])), "Command must be a nonempty argument list or null")
    for key in ("evidence_ref", "executable_ref", "dependency_evidence_ref"):
        require(execution[key] is None or text(execution[key]), f"Invalid execution {key}")
    require(execution["dependency_capture_complete"] is None or type(execution["dependency_capture_complete"]) is bool,
            "Dependency completeness must be a boolean or null")
    result = record["result"]
    shape(result, {"outcome", "native_status", "complete", "producer_run_ref", "evidence_ref", "artifact"})
    require(result["outcome"] in ("pass", "fail", "not_run", "unknown"), "Invalid result outcome")
    require(result["complete"] is None or type(result["complete"]) is bool, "Result completeness must be boolean or null")
    for key in ("native_status", "producer_run_ref", "evidence_ref"):
        require(result[key] is None or text(result[key]), f"Invalid result {key}")
    artifact = result["artifact"]
    if artifact is not None:
        shape(artifact, {"path", "sha256"})
        require(text(artifact["path"]) and isinstance(artifact["sha256"], str) and len(artifact["sha256"]) == 64
                and all(c in "0123456789abcdef" for c in artifact["sha256"]), "Invalid result artifact identity")
    validate_fields(record["fields"])


def validate_request(request):
    shape(request, {"format", "claim_id", "claim", "scope_ref", "required_fields", "required_outcome"})
    require(request["format"] == "opentools.result-request.v1", "Unsupported request format")
    require(all(text(request[k]) for k in ("claim_id", "claim", "scope_ref")), "Claim and scope required")
    require(request["required_outcome"] in ("pass", "fail", "any_observed"), "Invalid required outcome")
    validate_fields(request["required_fields"])
    require(request["required_fields"], "Select at least one claim-relevant field")


def validate_rules(rules, record, request):
    if rules is None:
        return {}
    shape(rules, {"format", "claim_id", "run_ref", "exceptions"})
    require(rules["format"] == "opentools.result-reuse.v1" and rules["claim_id"] == request["claim_id"]
            and rules["run_ref"] == record["run_ref"], "Reuse rules must bind this run and claim")
    require(isinstance(rules["exceptions"], list), "exceptions must be a list")
    mapped = {}
    for item in rules["exceptions"]:
        shape(item, {"field", "observed", "requested", "rule_ref", "approved_by", "basis_ref", "reason"})
        name = item["field"]
        require(text(name) and name in request["required_fields"] and name not in mapped, "Duplicate or unselected reuse field")
        require(all(text(item[k]) for k in ("rule_ref", "approved_by", "basis_ref", "reason")), "Reviewed reuse basis required")
        require(json_value(item["observed"]) and json_value(item["requested"]), "Invalid reuse values")
        before, after = record["fields"].get(name), request["required_fields"][name]
        require(known(before) and known(after), "Reuse rule cannot fill missing evidence")
        require(canonical(before["value"]) == canonical(item["observed"]) and canonical(after["value"]) == canonical(item["requested"]),
                "Stale reuse rule values")
        require(canonical(item["observed"]) != canonical(item["requested"]), "Reuse rule must describe a difference")
        mapped[name] = item
    return mapped


def audit(record, request, rules=None, base_dir="."):
    validate_snapshot(record)
    validate_request(request)
    exceptions = validate_rules(rules, record, request)
    unknowns, mismatches, rows = [], [], []
    execution, result = record["execution"], record["result"]
    if execution["state"] != "completed" or not text(execution["evidence_ref"]):
        unknowns.append("Completed execution is not established")
    if not execution["command"] or not text(execution["executable_ref"]):
        unknowns.append("Original command or executable identity is missing")
    if execution["dependency_capture_complete"] is not True or not text(execution["dependency_evidence_ref"]):
        unknowns.append("Dependency capture is not declared complete with evidence")
    if result["complete"] is not True or not text(result["evidence_ref"]) or not text(result["native_status"]):
        unknowns.append("A complete native result is not established")
    if result["producer_run_ref"] != record["run_ref"]:
        unknowns.append("Result producer does not bind the selected run")
    if result["outcome"] not in ("pass", "fail"):
        unknowns.append("No executed pass/fail outcome is established")
    elif request["required_outcome"] != "any_observed" and result["outcome"] != request["required_outcome"]:
        mismatches.append(f"Observed outcome {result['outcome']} differs from requested {request['required_outcome']}")
    artifact = result["artifact"]
    integrity = {"status": "missing", "path": None, "expected_sha256": None, "actual_sha256": None}
    if artifact is not None:
        integrity.update(path=artifact["path"], expected_sha256=artifact["sha256"])
        try:
            integrity["actual_sha256"] = file_hash(Path(base_dir) / artifact["path"])
            integrity["status"] = "matched" if integrity["actual_sha256"] == artifact["sha256"] else "changed"
        except OSError as exc:
            integrity["error"] = str(exc)
    if integrity["status"] != "matched":
        unknowns.append("Result artifact is missing or differs from the recorded bytes")
    for name, wanted in sorted(request["required_fields"].items()):
        observed = record["fields"].get(name)
        row = {"field": name, "observed": observed, "requested": wanted, "reuse_rule": exceptions.get(name)}
        if not known(observed) or not known(wanted):
            row["status"] = "unknown"
            unknowns.append(f"Missing observed or requested evidence: {name}")
        elif canonical(observed["value"]) == canonical(wanted["value"]):
            row["status"] = "equal"
        elif name in exceptions:
            row["status"] = "reviewed_reuse"
        else:
            row["status"] = "mismatch"
            mismatches.append(f"Claim-relevant field differs: {name}")
        rows.append(row)
    status = "inapplicable" if mismatches else "unresolved" if unknowns else "applicable_with_reviewed_reuse" if exceptions else "directly_applicable_within_scope"
    return {"format": "opentools.result-audit.v1", "status": status, "claim_id": request["claim_id"],
            "claim": request["claim"], "scope_ref": request["scope_ref"], "run_ref": record["run_ref"],
            "manifest_ref": record["manifest_ref"], "execution": execution, "native_result": result,
            "fields": rows, "mismatches": mismatches, "unknowns": unknowns, "result_integrity": integrity,
            "unselected_fields": sorted(set(record["fields"]) - set(request["required_fields"])),
            "fingerprints": {"snapshot": digest(record), "request": digest(request), "reuse": digest(rules) if rules else None},
            "limits": "Correspondence within the declared capture and claim boundary; no checker-sufficiency, design-correctness or signoff decision. Reuse approval and evidence references are supplied, not authenticated."}


def exit_code(report):
    return 1 if report["status"] == "inapplicable" else 2 if report["status"] == "unresolved" else 0


def markdown(report):
    def esc(value):
        return html.escape(str(value)).replace("|", "&#124;").replace("\n", "<br>")
    def field(item):
        return "unknown" if item is None else esc(canonical(item["value"])) + " (" + esc(item["evidence_ref"]) + ")"
    lines = ["# Result applicability", "", f"Status: **{report['status']}**", "", esc(report["claim"]), "",
             f"Run: {esc(report['run_ref'])}. Scope: {esc(report['scope_ref'])}.", "",
             f"Native outcome: **{esc(report['native_result']['outcome'])}**; native status: {esc(report['native_result']['native_status'])}.", "",
             f"Result artifact: {esc(report['result_integrity']['status'])}.", "",
             "| Field | Observed / source | Requested / source | Finding | Reuse basis |", "|---|---|---|---|---|"]
    for row in report["fields"]:
        rule = row["reuse_rule"]
        basis = "; ".join(str(rule[k]) for k in ("rule_ref", "approved_by", "basis_ref", "reason")) if rule else ""
        lines.append(f"| {esc(row['field'])} | {field(row['observed'])} | {field(row['requested'])} | {row['status']} | {esc(basis)} |")
    for label, key in (("Mismatches", "mismatches"), ("Unknowns", "unknowns")):
        lines.extend(["", f"## {label}", ""] + [f"- {esc(v)}" for v in report[key]] if report[key] else ["", f"{label}: none."])
    lines.extend(["", "Unselected fields: " + esc(", ".join(report["unselected_fields"]) or "none") + ".", "", esc(report["limits"]), ""])
    return "\n".join(lines)
