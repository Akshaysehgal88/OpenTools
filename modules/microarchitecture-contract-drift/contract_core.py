"""Review explicit integer capacity obligations and retain their evidence limits."""
import hashlib
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def shape(value, required, optional=()):
    require(isinstance(value, dict) and set(required) <= set(value)
            and set(value) <= set(required) | set(optional), "Unexpected or missing fields")


def text(value):
    return isinstance(value, str) and bool(value.strip())


def nullable(value):
    return value is None or text(value)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda value: require(False, "Non-finite JSON number"))


SCOPE = ("project_ref", "interface_ref", "configuration_ref", "mode_ref")


def validate_record(record):
    shape(record, ("format", "record_ref", "revision_ref", "scope", "inputs_complete", "facts"), ("provenance",))
    require(record["format"] == "opentools.capacity-record.v1" and text(record["record_ref"]), "Invalid capacity record")
    require(nullable(record["revision_ref"]), "Invalid revision reference")
    shape(record["scope"], SCOPE)
    require(all(nullable(v) for v in record["scope"].values()), "Invalid scope values")
    require(record["inputs_complete"] is None or type(record["inputs_complete"]) is bool, "Invalid input completeness")
    require(isinstance(record["facts"], list), "Facts must be a list")
    ids = set()
    for fact in record["facts"]:
        shape(fact, ("id", "value", "unit", "basis_ref", "value_ref", "meaning_ref"))
        require(text(fact["id"]) and fact["id"] not in ids, "Fact IDs must be unique")
        ids.add(fact["id"])
        require(fact["value"] is None or type(fact["value"]) is int and fact["value"] >= 0,
                "Capacity values must be nonnegative integers or null")
        require(all(nullable(fact[k]) for k in ("unit", "basis_ref", "value_ref", "meaning_ref")), "Invalid fact basis")
    canonical(record)


def validate_contract(contract):
    shape(contract, ("format", "scope", "record_sha256", "baseline_sha256", "population_complete", "evidence_ref", "checks"))
    require(contract["format"] == "opentools.capacity-contract.v1", "Invalid capacity contract")
    shape(contract["scope"], SCOPE)
    require(all(text(v) for v in contract["scope"].values()), "Declare the exact requested scope")
    for key in ("record_sha256", "baseline_sha256"):
        value = contract[key]
        require(value is None or isinstance(value, str) and len(value) == 64
                and all(c in "0123456789abcdef" for c in value), "Invalid record digest")
    require(contract["population_complete"] is None or type(contract["population_complete"]) is bool,
            "Invalid obligation completeness")
    require(nullable(contract["evidence_ref"]) and isinstance(contract["checks"], list) and contract["checks"],
            "An explicit obligation population is required")
    ids = set()
    for check in contract["checks"]:
        shape(check, ("id", "required_fact", "available_fact", "unit", "basis_ref", "evidence_ref", "premises"))
        require(all(text(check[k]) for k in ("id", "required_fact", "available_fact")) and check["id"] not in ids,
                "Checks need unique IDs and explicit fact roles")
        require(check["required_fact"] != check["available_fact"], "Demand and supply must be distinct facts")
        ids.add(check["id"])
        require(all(nullable(check[k]) for k in ("unit", "basis_ref", "evidence_ref")), "Invalid obligation basis")
        require(isinstance(check["premises"], list) and check["premises"], "Declare the interpretation premises")
        premises = set()
        for premise in check["premises"]:
            shape(premise, ("id", "holds", "evidence_ref"))
            require(text(premise["id"]) and premise["id"] not in premises, "Premise IDs must be unique")
            premises.add(premise["id"])
            require(premise["holds"] is None or type(premise["holds"]) is bool, "Invalid premise value")
            require(nullable(premise["evidence_ref"]), "Invalid premise evidence")
    canonical(contract)


def review(record, contract, baseline=None):
    validate_record(record)
    validate_contract(contract)
    if baseline is not None:
        validate_record(baseline)
    gaps, findings, outcomes, changes = [], [], [], []
    applicable = True
    if contract["record_sha256"] != digest(record):
        gaps.append("Current record binding is missing or stale")
        applicable = False
    for key in SCOPE:
        if record["scope"][key] != contract["scope"][key]:
            gaps.append("Requested scope is unresolved or different: " + key)
            applicable = False
    for key in ("revision_ref", "inputs_complete"):
        if not record[key]:
            gaps.append("Current record lacks " + key)
    if contract["population_complete"] is not True or not contract["evidence_ref"]:
        gaps.append("Obligation population or review basis is incomplete")
    facts = {f["id"]: f for f in record["facts"]}
    for check in contract["checks"]:
        missing, false = [], []
        refs = [check["evidence_ref"]] if check["evidence_ref"] else []
        required, available = facts.get(check["required_fact"]), facts.get(check["available_fact"])
        if not applicable:
            missing.append("Record does not bind the requested contract/scope")
        if not check["evidence_ref"] or not check["unit"] or not check["basis_ref"]:
            missing.append("Obligation meaning or unit basis is missing")
        for name, fact in (("required", required), ("available", available)):
            if fact is None:
                missing.append(name + " fact is absent")
                continue
            if any(fact[k] is None for k in ("value", "unit", "basis_ref", "value_ref", "meaning_ref")):
                missing.append(name + " value/semantic evidence is incomplete")
            if fact["unit"] != check["unit"] or fact["basis_ref"] != check["basis_ref"]:
                missing.append(name + " quantity has a different or unknown unit/basis")
            refs.extend(fact[k] for k in ("value_ref", "meaning_ref") if fact[k])
        for premise in check["premises"]:
            if premise["holds"] is False and premise["evidence_ref"] and applicable:
                false.append(premise["id"])
            elif premise["holds"] is not True or not premise["evidence_ref"]:
                missing.append("Premise is unresolved: " + premise["id"])
            if premise["evidence_ref"]:
                refs.append(premise["evidence_ref"])
        status = "needs_evidence"
        if false:
            status = "premise_false"
        elif not missing:
            status = "exceeds_capacity" if required["value"] > available["value"] else "within_bounds"
        if status in ("exceeds_capacity", "premise_false"):
            findings.append({"check_id": check["id"], "kind": status, "false_premises": false})
        gaps.extend(check["id"] + ": " + item for item in missing)
        outcomes.append({"id": check["id"], "status": status,
                         "required": required["value"] if required else None,
                         "available": available["value"] if available else None,
                         "unit": check["unit"], "basis_ref": check["basis_ref"],
                         "gaps": missing, "false_premises": false, "evidence": sorted(set(refs))})
    if baseline is not None:
        comparable = contract["baseline_sha256"] == digest(baseline)
        comparable = comparable and all(baseline["scope"][k] == record["scope"][k]
                                        and record["scope"][k] is not None
                                        for k in ("project_ref", "interface_ref", "mode_ref"))
        if not comparable:
            gaps.append("Baseline is unbound, stale or outside the interface/mode")
        else:
            old = {f["id"]: f for f in baseline["facts"]}
            for key, fact in facts.items():
                prior = old.get(key)
                if prior and all(prior[k] == fact[k] and fact[k] is not None for k in ("unit", "basis_ref")):
                    if prior["value"] is not None and fact["value"] is not None and prior["value"] != fact["value"]:
                        changes.append({"id": key, "before": prior["value"], "after": fact["value"],
                                        "delta": fact["value"] - prior["value"], "unit": fact["unit"]})
            if not baseline["inputs_complete"] or not baseline["revision_ref"]:
                gaps.append("Baseline input/revision basis is incomplete")
    elif contract["baseline_sha256"] is not None:
        gaps.append("Contract declares a baseline but none was supplied")
    status = "review_required" if findings else "incomplete" if gaps else "within_declared_bounds"
    return {"format": "opentools.capacity-review.v1", "status": status,
            "record_sha256": digest(record), "contract_sha256": digest(contract),
            "baseline_sha256": digest(baseline) if baseline is not None else None,
            "scope": contract["scope"], "checks": outcomes, "changes": changes,
            "findings": findings, "gaps": sorted(set(gaps)),
            "limits": ["Declared integer bounds and premises only; references and completeness are not authenticated.",
                       "Elaborated parameter values do not prove runtime enforcement or semantic mapping.",
                       "No latency, throughput, protocol correctness or release verdict is established."]}


def exit_code(report):
    return {"within_declared_bounds": 0, "review_required": 1, "incomplete": 2}[report["status"]]


def markdown(report):
    lines = ["# Capacity contract review", "", "Status: " + report["status"], ""]
    for check in report["checks"]:
        lines.append(f"- {check['id']}: {check['status']}; required={check['required']}, available={check['available']} {check['unit']}")
    for change in report["changes"]:
        lines.append(f"- Changed {change['id']}: {change['before']} -> {change['after']} ({change['unit']})")
    lines += ["", "Evidence gaps:"] + ["- " + gap for gap in report["gaps"]]
    lines += ["", "Limits:"] + ["- " + limit for limit in report["limits"]]
    return "\n".join(lines) + "\n"
