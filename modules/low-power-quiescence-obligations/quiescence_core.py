"""Review owner quiescence and prerequisites throughout a sampled shutdown."""
import hashlib
import json
from pathlib import Path

CONTROLS = ("transition_requested", "ingress_closed", "drain_ack", "isolation_active", "clock_available", "power_available", "local_idle")
MILESTONES = ("drain_ack", "clock_stop", "power_remove")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + " required")


def boolean(value, label):
    require(type(value) is bool or value is None, label + " must be boolean or null")


def count(value, label):
    require(value is None or type(value) is int and 0 <= value < 1 << 64, label + " must be an unsigned 64-bit count or null")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                                     allow_nan=False).encode("utf-8")).hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON value")))


def active(controls, milestone):
    key = {"drain_ack": "drain_ack", "clock_stop": "clock_available", "power_remove": "power_available"}[milestone]
    value = controls[key]
    return value if value is None or milestone == "drain_ack" else not value


def review(inventory, journal, policy):
    for record, kind in ((inventory, "inventory"), (journal, "journal"), (policy, "policy")):
        require(isinstance(record, dict) and record.get("format") == "opentools.quiescence." + kind + ".v1", "Unsupported " + kind + " format")
        require(isinstance(record.get("scope"), dict) and set(record["scope"]) == {"project", "configuration", "mode", "transition_ref"}, "Exact transition scope required")
        for value in record["scope"].values(): text(value, "scope")
        text(record.get("basis_ref"), "basis_ref")
        require(type(record.get("inputs_complete")) is bool, "Boolean inputs_complete required")
    for key in ("transition_isolated", "window_closed"): boolean(journal.get(key), key)
    for record in (journal, policy): text(record.get("window_ref"), "window_ref")
    report = {"format": "opentools.quiescence.report.v1", "scope": inventory["scope"],
        "bindings": {"inventory_sha256": digest(inventory), "journal_sha256": digest(journal), "policy_sha256": digest(policy)},
        "findings": [], "gaps": [], "owners": [], "milestones": [],
        "limits": ["Selected owners and sampled shutdown interval only; no exhaustive quiescence, CDC, analog, UPF or electrical signoff.",
                   "Owner coverage, counter roles and isolation/clock/power meaning need native source review. Hashes and declared completeness do not establish them."]}
    def gap(kind, **details): report["gaps"].append(dict(kind=kind, **details))
    def finding(kind, **details): report["findings"].append(dict(kind=kind, **details))
    bound = True
    for record, name in ((journal, "journal"), (policy, "policy")):
        if record["scope"] != inventory["scope"] or record["basis_ref"] != inventory["basis_ref"] or record.get("inventory_sha256") != digest(inventory):
            gap("scope_or_inventory_binding", record=name);bound = False
    if policy.get("journal_sha256") != digest(journal) or policy["window_ref"] != journal["window_ref"]:
        gap("journal_or_window_binding");bound = False
    for record, name in ((inventory, "inventory"), (journal, "journal"), (policy, "policy")):
        if not record["inputs_complete"]: gap("partial_inputs", record=name)
    if journal["transition_isolated"] is not True: gap("transition_isolation_unestablished")
    if journal["window_closed"] is not True: gap("observation_window_open")
    owners = {}
    require(isinstance(inventory.get("owners"), list) and inventory["owners"], "Selected owner inventory required")
    for owner in inventory["owners"]:
        text(owner.get("id"), "owner id");require(owner["id"] not in owners, "Duplicate owner")
        text(owner.get("evidence_ref"), "owner evidence")
        for key in ("owner_ref", "unit", "counting_basis_ref"):
            if owner.get(key) is None: gap("owner_definition_unresolved", owner=owner["id"], role=key)
            else: text(owner[key], key)
        owners[owner["id"]] = owner
    roster = {}
    require(isinstance(policy.get("required_owners"), list) and policy["required_owners"], "Independent required-owner roster required")
    for owner in policy["required_owners"]:
        text(owner.get("id"), "required owner id");require(owner["id"] not in roster, "Duplicate required owner")
        for key in ("unit", "counting_basis_ref", "evidence_ref"): text(owner.get(key), "required " + key)
        roster[owner["id"]] = owner
    comparable = set()
    for owner_id, expected in roster.items():
        observed = owners.get(owner_id)
        if observed is None: gap("required_owner_absent", owner=owner_id)
        elif any(observed.get(k) != expected[k] for k in ("unit", "counting_basis_ref")):
            gap("owner_count_basis_mismatch", owner=owner_id)
        elif observed.get("owner_ref") is not None: comparable.add(owner_id)
    for owner_id in owners.keys() - roster.keys(): gap("observed_owner_unreviewed", owner=owner_id)
    require(isinstance(journal.get("samples"), list) and journal["samples"], "Ordered transition samples required")
    last_seq, last_time = -1, -1
    for sample in journal["samples"]:
        for key in ("seq", "time_tick"):
            require(type(sample.get(key)) is int and sample[key] >= 0, "Unsigned sequence/time required")
        require(sample["seq"] > last_seq and sample["time_tick"] >= last_time, "Samples must be ordered")
        last_seq, last_time = sample["seq"], sample["time_tick"]
        text(sample.get("evidence_ref"), "sample evidence")
        require(isinstance(sample.get("controls"), dict) and set(sample["controls"]) == set(CONTROLS), "Exact control mapping required")
        for value in sample["controls"].values(): boolean(value, "sample control")
        require(isinstance(sample.get("counts"), dict), "Owner count mapping required")
        for owner_id, value in sample["counts"].items():
            text(owner_id, "sample owner");count(value, "owner count")
            if owner_id not in owners: gap("observed_owner_definition_absent", owner=owner_id, seq=sample["seq"])
    require(isinstance(policy.get("checks"), list) and policy["checks"], "Milestone checks required")
    checks, used = {}, set()
    for check in policy["checks"]:
        milestone = check.get("milestone")
        require(milestone in MILESTONES and milestone not in checks, "Unique supported milestone required")
        text(check.get("evidence_ref"), "milestone evidence")
        require(isinstance(check.get("owners"), list) and check["owners"] and all(isinstance(v, str) for v in check["owners"]), "Required owners for milestone needed")
        require(len(check["owners"]) == len(set(check["owners"])) and set(check["owners"]) <= roster.keys(), "Unique declared roster owners required")
        used |= set(check["owners"])
        require(isinstance(check.get("predicates"), list) and check["predicates"], "Explicit milestone prerequisites required")
        controls = set()
        for predicate in check["predicates"]:
            control = predicate.get("control")
            require(control in CONTROLS and control not in controls and type(predicate.get("equals")) is bool, "Unique control with boolean expected value required")
            controls.add(control);text(predicate.get("evidence_ref"), "predicate evidence")
        checks[milestone] = check
    for owner_id in roster.keys() - used: gap("required_owner_obligation_unreviewed", owner=owner_id)
    if not bound:
        report["status"] = "incomplete";return report
    first = journal["samples"][0]["controls"]
    prefix = first["drain_ack"] is False and first["clock_available"] is True and first["power_available"] is True and first["transition_requested"] is False
    if not prefix: gap("shutdown_prefix_unestablished")
    complete = prefix and journal["transition_isolated"] is True and journal["window_closed"] is True and all(r["inputs_complete"] for r in (inventory, journal, policy))
    for owner_id, owner in owners.items():
        observations = [(s["seq"], s["counts"].get(owner_id)) for s in journal["samples"]]
        report["owners"].append({"id": owner_id, "owner_ref": owner.get("owner_ref"), "unit": owner.get("unit"), "counting_basis_ref": owner.get("counting_basis_ref"),
            "first_nonzero_seq": next((seq for seq, value in observations if value is not None and value > 0), None), "last_count": observations[-1][1]})
    for milestone, check in checks.items():
        occurrences, unknown, prior_active, state_reentry = [], [], False, False
        busy_seen, missing_seen, failed_controls, unknown_controls = set(), set(), set(), set()
        for sample in journal["samples"]:
            seq, controls = sample["seq"], sample["controls"]
            enabled = active(controls, milestone)
            if enabled is None:
                unknown.append(seq);continue
            if enabled is False:
                if prior_active and not state_reentry:
                    gap("transition_reentry_unreviewed", milestone=milestone, seq=seq);state_reentry = True
                continue
            prior_active = True;occurrences.append(seq)
            for owner_id in check["owners"]:
                if owner_id not in comparable: continue
                value = sample["counts"].get(owner_id)
                if value is None and owner_id not in missing_seen:
                    gap("owner_count_unknown_in_protected_interval", milestone=milestone, owner=owner_id, seq=seq);missing_seen.add(owner_id)
                elif value is not None and value > 0 and owner_id not in busy_seen:
                    finding("owner_not_quiescent_in_protected_interval", milestone=milestone, owner=owner_id, count=value, unit=owners[owner_id]["unit"], seq=seq,
                            evidence_ref=sample["evidence_ref"], intent_ref=check["evidence_ref"]);busy_seen.add(owner_id)
            for predicate in check["predicates"]:
                key = predicate["control"];observed = controls[key]
                if observed is None and key not in unknown_controls:
                    gap("milestone_prerequisite_unknown", milestone=milestone, control=key, seq=seq);unknown_controls.add(key)
                elif observed is not None and observed != predicate["equals"] and key not in failed_controls:
                    finding("milestone_prerequisite_not_met", milestone=milestone, control=key, expected=predicate["equals"], observed=observed, seq=seq,
                            evidence_ref=sample["evidence_ref"], intent_ref=predicate["evidence_ref"]);failed_controls.add(key)
        if unknown: gap("milestone_state_unknown", milestone=milestone, sequences=unknown)
        if not occurrences:
            if complete and not unknown: finding("required_milestone_not_observed_in_window", milestone=milestone)
            else: gap("required_milestone_unresolved", milestone=milestone)
        report["milestones"].append({"milestone": milestone, "first_active_seq": occurrences[0] if occurrences else None,
                                      "protected_samples": len(occurrences), "required_owners": check["owners"]})
    report["status"] = "review_required" if report["findings"] else "incomplete" if report["gaps"] else "within_sampled_quiescence_contract"
    return report


def exit_code(report):
    return {"within_sampled_quiescence_contract": 0, "review_required": 1, "incomplete": 2}[report["status"]]


def markdown(report):
    lines = ["# Quiescence review", "", "Status: " + report["status"], ""]
    for key in ("owners", "milestones", "findings", "gaps"):
        lines += [key.capitalize() + ":", ""]
        lines += ["- " + json.dumps(item, ensure_ascii=False) for item in report[key]] or ["- None"]
        lines += [""]
    return "\n".join(lines + report["limits"]) + "\n"
