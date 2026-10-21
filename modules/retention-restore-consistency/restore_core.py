"""Review selected scalar restore bundles and their first post-wake consumers."""
import hashlib
import json
from pathlib import Path

CONTROLS = ("transition_active", "power_available", "consumer_enabled", "restore_ready")
MAX_BITS = 4096


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + " required")


def boolean(value, label):
    require(type(value) is bool or value is None, label + " must be boolean or null")


def unsigned(value, maximum, label, nullable=True):
    require(nullable and value is None or type(value) is int and 0 <= value <= maximum, label + " must be an unsigned integer in range" + (" or null" if nullable else ""))


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


def review(inventory, journal, policy):
    for record, kind in ((inventory, "inventory"), (journal, "journal"), (policy, "policy")):
        require(isinstance(record, dict) and record.get("format") == "opentools.restore." + kind + ".v1", "Unsupported " + kind + " format")
        require(isinstance(record.get("scope"), dict) and set(record["scope"]) == {"project", "configuration", "mode", "transition_ref"}, "Exact restore scope required")
        for value in record["scope"].values(): text(value, "scope")
        text(record.get("basis_ref"), "basis_ref")
        require(type(record.get("inputs_complete")) is bool, "Boolean inputs_complete required")
    for record in (journal, policy): text(record.get("window_ref"), "window_ref")
    for key in ("transition_isolated", "window_closed"): boolean(journal.get(key), key)
    unsigned(journal.get("before_seq"), (1 << 64) - 1, "before_seq", False)
    report = {"format": "opentools.restore.report.v1", "scope": inventory["scope"],
        "bindings": {"inventory_sha256": digest(inventory), "journal_sha256": digest(journal), "policy_sha256": digest(policy)},
        "findings": [], "gaps": [], "bundles": [], "reads": [],
        "limits": ["Selected scalar bundle in one isolated restore window; no automatic bundle discovery or exhaustive consumer proof.",
                   "Logical observations do not validate retention cells, UPF, ECC encoding, analog power loss or physical timing. Source roles and coverage require review."]}
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
    if journal["window_closed"] is not True: gap("observation_window_open")
    if journal["transition_isolated"] is not True: gap("restore_window_not_isolated")
    text(inventory.get("selection_basis_ref"), "selection_basis_ref")
    require(isinstance(inventory.get("states"), list) and inventory["states"], "Selected state inventory required")
    states = {}
    for state in inventory["states"]:
        text(state.get("id"), "state id");require(state["id"] not in states, "Duplicate state")
        unsigned(state.get("width"), MAX_BITS, "state width", False);require(state["width"] > 0, "Positive state width required")
        require(state.get("selection") in ("retained", "lost", "unknown"), "Explicit selection required")
        if state["selection"] == "unknown": gap("retention_selection_unknown", state=state["id"])
        for key in ("role_ref", "owner_ref", "power_domain_ref", "reset_domain_ref"):
            if state.get(key) is None: gap("state_definition_unresolved", state=state["id"], role=key)
            else: text(state[key], key)
        text(state.get("evidence_ref"), "state evidence");states[state["id"]] = state
    require(isinstance(journal.get("samples"), list) and journal["samples"], "Ordered restore samples required")
    samples, previous_seq, previous_time = {}, -1, -1
    for sample in journal["samples"]:
        for key in ("seq", "time_tick"): unsigned(sample.get(key), (1 << 64) - 1, key, False)
        require(sample["seq"] > previous_seq and sample["time_tick"] >= previous_time, "Samples must be ordered")
        previous_seq, previous_time = sample["seq"], sample["time_tick"]
        text(sample.get("evidence_ref"), "sample evidence")
        require(isinstance(sample.get("controls"), dict) and set(sample["controls"]) == set(CONTROLS), "Exact restore controls required")
        for value in sample["controls"].values(): boolean(value, "restore control")
        require(isinstance(sample.get("values"), dict), "State values required")
        for state_id, value in sample["values"].items():
            if state_id in states: unsigned(value, (1 << states[state_id]["width"]) - 1, "state value")
            else: gap("observed_state_definition_absent", state=state_id, seq=sample["seq"])
        require(isinstance(sample.get("reads"), list), "Explicit read event list required")
        seen_reads = set()
        for event in sample["reads"]:
            for key in ("read_ref", "bundle_ref", "evidence_ref"): text(event.get(key), key)
            require(event["read_ref"] not in seen_reads, "Duplicate read within sample");seen_reads.add(event["read_ref"])
            for key in ("requested", "response_valid", "hit", "error"):
                require(key in event, "Explicit read flags required");boolean(event[key], key)
            unsigned(event.get("data"), (1 << MAX_BITS) - 1, "read data")
        samples[sample["seq"]] = sample
    require(isinstance(policy.get("bundles"), list) and policy["bundles"], "Independent consumer bundle obligations required")
    bundles, used = {}, set()
    for bundle in policy["bundles"]:
        text(bundle.get("id"), "bundle id");require(bundle["id"] not in bundles, "Duplicate bundle")
        for key in ("consumer_ref", "eligible_ref", "evidence_ref"): text(bundle.get(key), key)
        if bundle["eligible_ref"] in states: require(states[bundle["eligible_ref"]]["width"] == 1, "Eligible state must be one bit")
        used.add(bundle["eligible_ref"])
        require(type(bundle.get("require_ready")) is bool, "Explicit require_ready required")
        require(isinstance(bundle.get("members"), list) and bundle["members"], "Bundle member obligations required")
        members = {}
        for member in bundle["members"]:
            for key in ("state_ref", "role_ref", "evidence_ref"): text(member.get(key), key)
            state_id = member["state_ref"];require(state_id not in members, "Duplicate bundle member")
            require(member.get("expected") in ("preserve_before", "constant", "unknown"), "Supported restore expectation required")
            if member["expected"] == "constant": unsigned(member.get("value"), (1 << states[state_id]["width"]) - 1 if state_id in states else (1 << MAX_BITS) - 1, "expected value", False)
            members[state_id] = member;used.add(state_id)
        require(isinstance(bundle.get("prerequisites"), list) and bundle["prerequisites"], "Exposure prerequisites required")
        prerequisites = set()
        for predicate in bundle["prerequisites"]:
            text(predicate.get("state_ref"), "prerequisite state");text(predicate.get("evidence_ref"), "prerequisite evidence")
            state_id = predicate["state_ref"];require(state_id not in prerequisites, "Duplicate exposure prerequisite")
            unsigned(predicate.get("equals"), (1 << states[state_id]["width"]) - 1 if state_id in states else (1 << MAX_BITS) - 1, "prerequisite expected value", False)
            prerequisites.add(state_id);used.add(state_id)
        read = bundle.get("read")
        require(isinstance(read, dict) and type(read.get("required")) is bool, "Explicit consumer read contract required")
        text(read.get("evidence_ref"), "read intent evidence")
        for key in ("expected_hit", "expected_error"): boolean(read.get(key), key)
        require("data_state_ref" in read and (read["data_state_ref"] is None or read["data_state_ref"] in members), "Read data must refer to an expected bundle member or explicit null")
        require(read["expected_hit"] is not True or read["data_state_ref"] is not None, "A required hit needs an expected data member")
        require(isinstance(read.get("prerequisites"), list) and read["prerequisites"], "Explicit read prerequisites required")
        read_controls = set()
        for predicate in read["prerequisites"]:
            require(predicate.get("control") in CONTROLS and predicate["control"] not in read_controls and type(predicate.get("equals")) is bool, "Unique read control with boolean expectation required")
            read_controls.add(predicate["control"]);text(predicate.get("evidence_ref"), "read prerequisite evidence")
        bundles[bundle["id"]] = bundle
    for state_id in states.keys() - used: gap("selected_state_unreviewed", state=state_id)
    for state_id in used - states.keys(): gap("required_state_absent", state=state_id)
    if not bound or journal["transition_isolated"] is not True:
        report["status"] = "incomplete";return report
    before = samples.get(journal["before_seq"])
    if before is None or before["controls"]["power_available"] is not True or before["controls"]["transition_active"] is not False:
        gap("before_snapshot_unestablished");report["status"] = "incomplete";return report
    after = [s for seq, s in samples.items() if seq > journal["before_seq"]]
    for sample in after:
        if sample["controls"]["power_available"] is None or sample["controls"]["transition_active"] is None:
            gap("transition_boundary_unknown", seq=sample["seq"])
    loss = next((s for s in after if s["controls"]["transition_active"] is True and s["controls"]["power_available"] is False), None)
    if loss is None:
        complete = journal["window_closed"] is True and all(r["inputs_complete"] for r in (inventory, journal, policy))
        if complete and all(s["controls"]["power_available"] is not None and s["controls"]["transition_active"] is not None for s in after): finding("selected_loss_transition_not_observed")
        else: gap("loss_transition_unresolved")
        report["status"] = "review_required" if report["findings"] else "incomplete";return report
    wake = next((s for s in after if s["seq"] > loss["seq"] and s["controls"]["power_available"] is True), None)
    if wake is None:
        gap("post_loss_wake_unobserved");report["status"] = "incomplete";return report
    end = next((s["seq"] for s in after if s["seq"] > wake["seq"] and s["controls"]["power_available"] is False), None)
    if end is not None: gap("multiple_transitions_unreviewed", seq=end)
    window = [s for s in after if s["seq"] >= wake["seq"] and (end is None or s["seq"] < end)]
    def value(sample, state_id): return sample["values"].get(state_id) if state_id in states else None
    for bundle_id, bundle in bundles.items():
        expected, members = {}, {m["state_ref"]: m for m in bundle["members"]}
        for state_id, member in members.items():
            definition = states.get(state_id)
            if definition is None: continue
            if definition.get("role_ref") != member["role_ref"]:
                gap("member_role_mismatch", bundle=bundle_id, state=state_id);continue
            expected[state_id] = value(before, state_id) if member["expected"] == "preserve_before" else member.get("value") if member["expected"] == "constant" else None
            if expected[state_id] is None: gap("expected_member_value_unknown", bundle=bundle_id, state=state_id)
        ready_sequences, exposed_sequences = [], []
        mismatch_seen, unknown_seen, bad_prerequisite, missing_prerequisite = set(), set(), set(), set()
        for sample in window:
            seq, controls = sample["seq"], sample["controls"]
            if controls["power_available"] is not True:
                gap("power_observation_unresolved", seq=seq);continue
            eligible = value(sample, bundle["eligible_ref"])
            ready = controls["restore_ready"]
            exposed = eligible == 1 and controls["consumer_enabled"] is True
            if ready is None and bundle["require_ready"]: gap("restore_ready_unknown", bundle=bundle_id, seq=seq)
            if eligible is None or controls["consumer_enabled"] is None: gap("consumer_exposure_unresolved", bundle=bundle_id, seq=seq)
            if ready is True: ready_sequences.append(seq)
            if exposed: exposed_sequences.append(seq)
            if ready is True or exposed:
                for state_id, target in expected.items():
                    observed = value(sample, state_id)
                    if observed is None and state_id not in unknown_seen:
                        gap("member_sample_unknown", bundle=bundle_id, state=state_id, seq=seq);unknown_seen.add(state_id)
                    elif target is not None and observed is not None and observed != target and state_id not in mismatch_seen:
                        finding("bundle_member_not_restored", bundle=bundle_id, state=state_id, expected=target, observed=observed, seq=seq,
                                evidence_ref=sample["evidence_ref"], intent_ref=members[state_id]["evidence_ref"]);mismatch_seen.add(state_id)
            if exposed:
                for predicate in bundle["prerequisites"]:
                    state_id = predicate["state_ref"];observed = value(sample, state_id)
                    if observed is None and state_id not in missing_prerequisite:
                        gap("exposure_prerequisite_unknown", bundle=bundle_id, state=state_id, seq=seq);missing_prerequisite.add(state_id)
                    elif observed is not None and observed != predicate["equals"] and state_id not in bad_prerequisite:
                        finding("consumer_exposed_before_prerequisite", bundle=bundle_id, state=state_id, expected=predicate["equals"], observed=observed, seq=seq,
                                evidence_ref=sample["evidence_ref"], intent_ref=predicate["evidence_ref"]);bad_prerequisite.add(state_id)
        if bundle["require_ready"] and not ready_sequences:
            if journal["window_closed"] is True and journal["inputs_complete"] and all(s["controls"]["restore_ready"] is not None for s in window): finding("required_restore_ready_not_observed", bundle=bundle_id)
            else: gap("restore_ready_unresolved", bundle=bundle_id)
        if not ready_sequences and not exposed_sequences:
            gap("bundle_members_never_observed_at_ready_or_exposure", bundle=bundle_id)
        read_rule, read_events = bundle["read"], {}
        for sample in window:
            for event in sample["reads"]:
                if event["bundle_ref"] != bundle_id: continue
                entry = read_events.setdefault(event["read_ref"], {"requests": [], "responses": [], "unknown": False})
                if event["requested"] is True: entry["requests"].append(sample["seq"])
                if event["response_valid"] is True: entry["responses"].append((sample, event))
                if event["requested"] is None or event["response_valid"] is None: entry["unknown"] = True;gap("read_event_unresolved", bundle=bundle_id, read=event["read_ref"])
        responses = 0
        for read_id, entry in read_events.items():
            require(len(entry["requests"]) <= 1 and len(entry["responses"]) <= 1, "One request/response per selected read identity required")
            if not entry["responses"]:
                if entry["requests"]: gap("read_response_unobserved", bundle=bundle_id, read=read_id)
                continue
            sample, event = entry["responses"][0];responses += 1
            if not entry["requests"] or entry["requests"][0] > sample["seq"]:
                gap("read_request_attribution_unresolved", bundle=bundle_id, read=read_id)
                continue
            for predicate in read_rule["prerequisites"]:
                key = predicate["control"];observed = sample["controls"][key]
                if observed is None: gap("read_prerequisite_unknown", bundle=bundle_id, read=read_id, control=key)
                elif observed != predicate["equals"]: finding("read_prerequisite_not_met", bundle=bundle_id, read=read_id, control=key, expected=predicate["equals"], observed=observed, seq=sample["seq"])
            for key in ("hit", "error"):
                target = read_rule["expected_" + key]
                if target is None or event[key] is None: gap("read_outcome_unresolved", bundle=bundle_id, read=read_id, field=key)
                elif event[key] != target: finding("unexpected_post_wake_read_outcome", bundle=bundle_id, read=read_id, field=key, expected=target, observed=event[key], seq=sample["seq"], evidence_ref=event["evidence_ref"])
            state_id = read_rule["data_state_ref"]
            if event["hit"] is True and state_id is not None:
                target = expected.get(state_id)
                if state_id in states: unsigned(event["data"], (1 << states[state_id]["width"]) - 1, "selected read data")
                if target is None or event["data"] is None: gap("read_data_unresolved", bundle=bundle_id, read=read_id)
                elif event["data"] != target: finding("post_wake_read_data_mismatch", bundle=bundle_id, read=read_id, expected=target, observed=event["data"], seq=sample["seq"], evidence_ref=event["evidence_ref"])
            report["reads"].append({"bundle": bundle_id, "read": read_id, "seq": sample["seq"], "hit": event["hit"], "error": event["error"], "data": event["data"], "evidence_ref": event["evidence_ref"]})
        if read_rule["required"] and not responses: gap("required_post_wake_read_unobserved", bundle=bundle_id)
        report["bundles"].append({"id": bundle_id, "consumer_ref": bundle["consumer_ref"], "before_seq": journal["before_seq"], "loss_seq": loss["seq"], "wake_seq": wake["seq"],
            "ready_sequences": ready_sequences, "exposed_sequences": exposed_sequences, "expected_members": expected,
            "selections": {state_id: states[state_id]["selection"] for state_id in members if state_id in states}})
    for sample in window:
        for event in sample["reads"]:
            if event["bundle_ref"] not in bundles: gap("observed_consumer_unreviewed", bundle=event["bundle_ref"], seq=sample["seq"])
    report["status"] = "review_required" if report["findings"] else "incomplete" if report["gaps"] else "within_observed_restore_contract"
    return report


def exit_code(report):
    return {"within_observed_restore_contract": 0, "review_required": 1, "incomplete": 2}[report["status"]]


def markdown(report):
    lines = ["# Retention and restore review", "", "Status: " + report["status"], ""]
    for key in ("bundles", "reads", "findings", "gaps"):
        lines += [key.capitalize() + ":", ""]
        lines += ["- " + json.dumps(item, ensure_ascii=False) for item in report[key]] or ["- None"]
        lines += [""]
    return "\n".join(lines + report["limits"]) + "\n"
