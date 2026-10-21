"""Review one isolated event's observed routes and explicit bounded obligations."""
import hashlib
import json
from pathlib import Path

STAGES = ("asserted", "interrupt_retained", "interrupt_delivered", "serviced", "source_cleared", "wake_retained", "wake_requested")
CONTROLS = ("functional_clock", "aon_clock", "power_available", "interrupt_enable", "route_selected", "wake_enable", "sleep_window")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + " required")


def boolean(value, label):
    require(type(value) is bool or value is None, label + " must be boolean or null")


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


def review(topology, journal, policy):
    for record, kind in ((topology, "topology"), (journal, "journal"), (policy, "policy")):
        require(isinstance(record, dict) and record.get("format") == "opentools.event." + kind + ".v1", "Unsupported " + kind + " format")
        require(isinstance(record.get("scope"), dict) and set(record["scope"]) == {"project", "configuration", "mode", "event_ref"}, "Exact event scope required")
        for value in record["scope"].values(): text(value, "scope")
        text(record.get("basis_ref"), "basis_ref")
        require(type(record.get("inputs_complete")) is bool, "Boolean inputs_complete required")
    require(isinstance(topology.get("source"), dict), "Source mapping required")
    for key in ("id", "owner_ref", "evidence_ref"): text(topology["source"].get(key), "source " + key)
    require(topology["source"].get("persistence") in ("held-until-clear", "pulse", "unknown"), "Explicit source persistence required")
    require(isinstance(topology.get("routes"), dict) and set(topology["routes"]) == {"interrupt", "wake"}, "Distinct interrupt and wake route mappings required")
    for name, route in topology["routes"].items():
        require(isinstance(route, dict), "Route object required")
        for key in ("id", "consumer_ref", "profile_ref", "evidence_ref"): text(route.get(key), name + " " + key)
    for key in ("event_isolated", "window_closed"): boolean(journal.get(key), key)
    for record in (journal, policy): text(record.get("window_ref"), "window_ref")
    report = {"format": "opentools.event.report.v1", "scope": topology["scope"],
              "bindings": {"topology_sha256": digest(topology), "journal_sha256": digest(journal), "policy_sha256": digest(policy)},
              "findings": [], "gaps": [], "stage_observations": [], "order_observations": [],
              "limits": ["One isolated event in a declared bounded window; no universal controller, physical CDC, pulse-width or unbounded delivery proof.",
                         "Wake and interrupt routes, stage roles, ownership and sampling coverage require source review. Hashes do not establish them or grant approval."]}
    def gap(kind, **details): report["gaps"].append(dict(kind=kind, **details))
    def finding(kind, **details): report["findings"].append(dict(kind=kind, **details))
    bound = True
    for record, name in ((journal, "journal"), (policy, "policy")):
        if record["scope"] != topology["scope"] or record["basis_ref"] != topology["basis_ref"] or record.get("topology_sha256") != digest(topology):
            gap("scope_or_topology_binding", record=name)
            bound = False
    if policy.get("journal_sha256") != digest(journal) or policy["window_ref"] != journal["window_ref"]:
        gap("journal_or_window_binding")
        bound = False
    for record, name in ((topology, "topology"), (journal, "journal"), (policy, "policy")):
        if not record["inputs_complete"]: gap("partial_inputs", record=name)
    if topology["source"]["persistence"] == "unknown": gap("source_persistence_unknown")
    if journal["event_isolated"] is not True: gap("event_isolation_unestablished")
    if journal["window_closed"] is not True: gap("observation_window_open")
    require(isinstance(journal.get("samples"), list) and journal["samples"], "Ordered samples required")
    last_seq, last_time = -1, -1
    for sample in journal["samples"]:
        for key in ("seq", "time_tick"):
            require(type(sample.get(key)) is int and sample[key] >= 0, "Unsigned sequence/time required")
        require(sample["seq"] > last_seq and sample["time_tick"] >= last_time, "Samples must be ordered")
        last_seq, last_time = sample["seq"], sample["time_tick"]
        text(sample.get("evidence_ref"), "sample evidence")
        require(isinstance(sample.get("stages"), dict) and set(sample["stages"]) == set(STAGES), "Exact stage marker mapping required")
        require(isinstance(sample.get("controls"), dict) and set(sample["controls"]) == set(CONTROLS), "Exact control mapping required")
        for value in list(sample["stages"].values()) + list(sample["controls"].values()): boolean(value, "observation")
        for key in ("source_status", "interrupt_pending_state", "wake_pending_state"):
            require(key in sample, "Explicit pending/source samples required")
            boolean(sample[key], key)
    require(isinstance(policy.get("required_stages"), list) and policy["required_stages"], "Required stage obligations needed")
    required = set()
    for rule in policy["required_stages"]:
        require(rule.get("stage") in STAGES and rule["stage"] not in required, "Unique supported required stage")
        required.add(rule["stage"])
        text(rule.get("evidence_ref"), "required stage evidence")
    require(isinstance(policy.get("orders"), list), "Explicit stage order list required")
    pairs = set()
    for rule in policy["orders"]:
        require(rule.get("before") in STAGES and rule.get("after") in STAGES and rule["before"] != rule["after"], "Distinct supported order endpoints required")
        pair = (rule["before"], rule["after"])
        require(pair not in pairs, "Duplicate stage order")
        pairs.add(pair)
        text(rule.get("evidence_ref"), "order evidence")
    require(isinstance(policy.get("stage_prerequisites"), list), "Explicit stage prerequisites required")
    stages_checked = set()
    for rule in policy["stage_prerequisites"]:
        require(rule.get("stage") in STAGES and rule["stage"] not in stages_checked, "Unique supported prerequisite stage")
        stages_checked.add(rule["stage"])
        require(isinstance(rule.get("controls"), list) and rule["controls"] and len(rule["controls"]) == len(set(rule["controls"])) and set(rule["controls"]) <= set(CONTROLS), "Unique supported controls required")
        text(rule.get("evidence_ref"), "prerequisite evidence")
    if not policy["orders"]: gap("stage_order_unreviewed")
    if not policy["stage_prerequisites"]: gap("stage_availability_unreviewed")
    if not bound:
        report["status"] = "incomplete"
        return report
    samples = journal["samples"]
    first = samples[0]
    prefix_known = all(first["stages"][s] is False for s in STAGES) and all(first[k] is False for k in ("source_status", "interrupt_pending_state", "wake_pending_state"))
    if not prefix_known: gap("clean_event_prefix_unestablished")
    assertion_rows = [s["seq"] for s in samples if s["stages"]["asserted"] is True]
    if len(assertion_rows) > 1: gap("multiple_source_events", sequences=assertion_rows)
    attribution = prefix_known and journal["event_isolated"] is True and len(assertion_rows) <= 1
    complete = attribution and all(r["inputs_complete"] for r in (topology, journal, policy)) and journal["window_closed"] is True
    for stage in STAGES:
        observations = [s for s in samples if s["stages"][stage] is True]
        unknown = [s["seq"] for s in samples if s["stages"][stage] is None]
        state = "observed" if observations and attribution else "observed_without_established_attribution" if observations else "unknown" if unknown or not complete else "not_observed_in_window"
        report["stage_observations"].append({"stage": stage, "state": state, "sequences": [s["seq"] for s in observations], "evidence_refs": [s["evidence_ref"] for s in observations]})
        if unknown: gap("stage_sample_unknown", stage=stage, sequences=unknown)
        if stage in required and not observations:
            if complete and not unknown: finding("required_stage_not_observed_in_window", stage=stage)
            else: gap("required_stage_unresolved", stage=stage)
    # Every stage in this single-event profile must be attributable to the
    # selected assertion; a populated old route is not a newly delivered event.
    seen = set()
    unknown_seen = set()
    for sample in samples:
        seq = sample["seq"]
        seen |= {stage for stage, value in sample["stages"].items() if value is True}
        unknown_seen |= {stage for stage, value in sample["stages"].items() if value is None}
        for stage, value in sample["stages"].items():
            if stage != "asserted" and value is True and "asserted" not in seen:
                if attribution and journal["inputs_complete"] and "asserted" not in unknown_seen: finding("stage_precedes_selected_assertion", stage=stage, seq=seq)
                else: gap("stage_event_attribution_unresolved", stage=stage, seq=seq)
        for rule in policy["orders"]:
            if sample["stages"][rule["after"]] is True:
                if rule["before"] in seen:
                    report["order_observations"].append({"before": rule["before"], "after": rule["after"], "seq": seq})
                elif attribution and journal["inputs_complete"] and rule["before"] not in unknown_seen:
                    finding("required_stage_order_not_observed", before=rule["before"], after=rule["after"], seq=seq, evidence_ref=rule["evidence_ref"])
                else: gap("stage_order_unresolved", before=rule["before"], after=rule["after"], seq=seq)
        for rule in policy["stage_prerequisites"]:
            if sample["stages"][rule["stage"]] is True:
                for control in rule["controls"]:
                    value = sample["controls"][control]
                    if value is None: gap("stage_prerequisite_unknown", stage=rule["stage"], control=control, seq=seq)
                    elif value is False: finding("stage_prerequisite_not_met", stage=rule["stage"], control=control, seq=seq, evidence_ref=rule["evidence_ref"])
    report["status"] = "review_required" if report["findings"] else "incomplete" if report["gaps"] else "within_observed_event_contract"
    return report


def exit_code(report):
    return {"within_observed_event_contract": 0, "review_required": 1, "incomplete": 2}[report["status"]]


def markdown(report):
    lines = ["# Event delivery review", "", "Status: " + report["status"], ""]
    for key in ("stage_observations", "findings", "gaps"):
        lines += [key.replace("_", " ").capitalize() + ":", ""]
        lines += ["- " + json.dumps(item, ensure_ascii=False) for item in report[key]] or ["- None"]
        lines += [""]
    return "\n".join(lines + report["limits"]) + "\n"
