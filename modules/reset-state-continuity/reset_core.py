"""Review a bounded reset journal against explicit state and continuity policy."""
import hashlib
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + " required")


def boolean(value, label):
    require(type(value) is bool or value is None, label + " must be boolean or null")


def integer(value, maximum, label, nullable=True):
    require(nullable and value is None or type(value) is int and 0 <= value <= maximum, label + " must be an unsigned integer in range" + (" or null" if nullable else ""))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


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
        require(isinstance(record, dict) and record.get("format") == "opentools.reset." + kind + ".v1", "Unsupported " + kind + " format")
        require(isinstance(record.get("scope"), dict) and set(record["scope"]) == {"project", "configuration", "mode", "reset_event_ref"}, "Exact reset scope required")
        for value in record["scope"].values(): text(value, "scope")
        text(record.get("basis_ref"), "basis_ref")
        require(type(record.get("inputs_complete")) is bool, "Boolean inputs_complete required")
    report = {"format": "opentools.reset.report.v1", "scope": inventory["scope"],
              "bindings": {"inventory_sha256": digest(inventory), "journal_sha256": digest(journal), "policy_sha256": digest(policy)},
              "findings": [], "gaps": [], "state_by_owner": [], "continuity": [],
              "limits": ["Selected sampled reset window only; no exhaustive restart, synchronizer, recovery/removal, analog or RDC signoff.",
                         "State identity, completeness, ownership and replay authority require source review; hashes do not establish them."]}
    def gap(kind, **details): report["gaps"].append(dict(kind=kind, **details))
    def finding(kind, **details): report["findings"].append(dict(kind=kind, **details))
    bound = True
    for record, name in ((journal, "journal"), (policy, "policy")):
        if record["scope"] != inventory["scope"] or record["basis_ref"] != inventory["basis_ref"] or record.get("inventory_sha256") != digest(inventory):
            gap("scope_or_inventory_binding", record=name)
            bound = False
    if policy.get("journal_sha256") != digest(journal):
        gap("journal_binding")
        bound = False
    for record, name in ((inventory, "inventory"), (journal, "journal"), (policy, "policy")):
        if not record["inputs_complete"]: gap("partial_inputs", record=name)
    states = {}
    require(isinstance(inventory.get("states"), list) and inventory["states"], "Selected state inventory required")
    for state in inventory["states"]:
        text(state.get("id"), "state id")
        require(state["id"] not in states, "Duplicate state")
        integer(state.get("width"), 64, "state width", False)
        require(state["width"] > 0, "Positive state width required")
        integer(state.get("reset_value"), (1 << state["width"]) - 1, "reset value")
        text(state.get("evidence_ref"), "state evidence")
        for key in ("owner_ref", "reset_domain_ref"):
            if state.get(key) is None: gap("state_ownership_unresolved", state=state["id"], role=key)
            else: text(state[key], key)
        states[state["id"]] = state
    require(isinstance(journal.get("phases"), list), "Ordered journal phases required")
    phases, last = {}, -1
    order = ("before", "held", "released", "post")
    for phase in journal["phases"]:
        require(phase.get("phase") in order and order.index(phase["phase"]) > last, "Phases must be unique and in before/held/released/post order")
        last = order.index(phase["phase"])
        text(phase.get("evidence_ref"), "phase evidence")
        for key in ("values", "reset_active", "prerequisites"):
            require(isinstance(phase.get(key), dict), key + " mapping required")
        boolean(phase.get("hardware_quiet"), "hardware_quiet")
        for key, value in phase["values"].items():
            if key not in states: gap("unmapped_observed_state", state=key)
            else: integer(value, (1 << states[key]["width"]) - 1, "state sample")
        for value in list(phase["reset_active"].values()) + list(phase["prerequisites"].values()): boolean(value, "sampled control")
        phases[phase["phase"]] = phase
    for name in order:
        if name not in phases: gap("phase_absent", phase=name)
    expectations = {}
    require(isinstance(policy.get("state_expectations"), list), "State expectations required")
    for rule in policy["state_expectations"]:
        text(rule.get("state_ref"), "expected state")
        require(rule["state_ref"] not in expectations, "Duplicate state expectation")
        require(rule.get("effect") in ("clear", "preserve", "unconstrained", None), "Supported state effect required")
        boolean(rule.get("required_reset"), "required_reset")
        text(rule.get("evidence_ref"), "expectation evidence")
        expectations[rule["state_ref"]] = rule
    for key in ("release_requires", "continuity", "post_expectations"):
        require(isinstance(policy.get(key), list), key + " list required")
        if not policy[key]: gap("selected_reset_contract_unreviewed", section=key)
    if not bound:
        report["status"] = "incomplete"
        return report
    before, held, released, post = (phases.get(p) for p in order)
    def sample(phase, state_id):
        if state_id not in states:
            gap("state_reference_absent", state=state_id)
            return None
        value = phase["values"].get(state_id) if phase else None
        if value is None: gap("state_sample_absent", state=state_id, phase=phase["phase"] if phase else None)
        return value
    for state_id in expectations.keys() - states.keys(): gap("policy_state_absent", state=state_id)
    for state_id, state in states.items():
        rule = expectations.get(state_id)
        old, during, after, final = sample(before, state_id), sample(held, state_id), sample(released, state_id), sample(post, state_id)
        report["state_by_owner"].append({"state_ref": state_id, "owner_ref": state.get("owner_ref"), "reset_domain_ref": state.get("reset_domain_ref"),
                                        "before": old, "held": during, "released": after, "post": final, "expected_effect": rule["effect"] if rule else None})
        if rule is None:
            gap("state_intent_absent", state=state_id)
            continue
        observed_reset = held["reset_active"].get(state.get("reset_domain_ref")) if held else None
        if rule["required_reset"] is None or observed_reset is None:
            gap("reset_application_unresolved", state=state_id)
        elif observed_reset != rule["required_reset"]:
            finding("reset_application_mismatch", state=state_id, expected=rule["required_reset"], observed=observed_reset)
        if released:
            active = released["reset_active"].get(state.get("reset_domain_ref"))
            if active is None: gap("reset_release_unresolved", state=state_id)
            elif active: finding("reset_still_active_at_release", state=state_id)
        effect = rule["effect"]
        if effect is None: gap("state_effect_unresolved", state=state_id)
        elif effect == "clear":
            if state["reset_value"] is None: gap("reset_value_unknown", state=state_id)
            elif during is not None and during != state["reset_value"]: finding("required_state_clear_missing", state=state_id, expected=state["reset_value"], observed=during)
        elif effect == "preserve":
            if not before or not held or before["hardware_quiet"] is not True or held["hardware_quiet"] is not True:
                gap("preservation_attribution_unresolved", state=state_id)
            elif old is not None and during is not None and old != during: finding("required_state_preservation_missing", state=state_id, before=old, held=during)
    names = set()
    for rule in policy["release_requires"]:
        text(rule.get("id"), "release prerequisite")
        text(rule.get("evidence_ref"), "release evidence")
        require(rule["id"] not in names, "Duplicate release prerequisite")
        names.add(rule["id"])
        observed = released["prerequisites"].get(rule["id"]) if released else None
        if observed is None: gap("release_prerequisite_unresolved", prerequisite=rule["id"])
        elif not observed: finding("release_prerequisite_not_met", prerequisite=rule["id"], evidence_ref=rule["evidence_ref"])
    pairs = set()
    for rule in policy["continuity"]:
        text(rule.get("evidence_ref"), "continuity evidence")
        for key in ("producer_pending_ref", "consumer_context_ref"): text(rule.get(key), key)
        boolean(rule.get("allow_replay"), "allow_replay")
        pending_id, context_id = rule["producer_pending_ref"], rule["consumer_context_ref"]
        require((pending_id, context_id) not in pairs, "Duplicate continuity pair")
        pairs.add((pending_id, context_id))
        for state_id in (pending_id, context_id):
            if state_id in states: require(states[state_id]["width"] == 1, "Continuity presence flags must be one bit")
        pending, context = sample(released, pending_id), sample(released, context_id)
        if rule["allow_replay"] is None: gap("replay_authority_unresolved", evidence_ref=rule["evidence_ref"])
        elif pending == 1 and context == 0 and not rule["allow_replay"]:
            finding("producer_survives_cleared_consumer", producer=pending_id, consumer=context_id, evidence_ref=rule["evidence_ref"])
        elif pending == 1 and context == 0:
            report["continuity"].append({"producer": pending_id, "status": "replay_permitted_by_supplied_policy", "evidence_ref": rule["evidence_ref"]})
        require("producer_identity_ref" in rule and "consumer_identity_ref" in rule, "Explicit identity references or nulls required")
        identity_ids = [rule["producer_identity_ref"], rule["consumer_identity_ref"]]
        require(all(v is None for v in identity_ids) or all(isinstance(v, str) and v.strip() for v in identity_ids), "Supply both identity references or explicit nulls")
        if all(identity_ids) and pending == 1 and context == 1:
            producer_id, consumer_id = (sample(released, value) for value in identity_ids)
            if all(v in states for v in identity_ids) and states[identity_ids[0]]["width"] != states[identity_ids[1]]["width"]:
                gap("identity_width_mismatch", evidence_ref=rule["evidence_ref"])
            elif producer_id is not None and consumer_id is not None and producer_id != consumer_id: finding("retained_identity_mismatch", producer=producer_id, consumer=consumer_id, evidence_ref=rule["evidence_ref"])
    checked = set()
    for rule in policy["post_expectations"]:
        text(rule.get("state_ref"), "post state")
        text(rule.get("evidence_ref"), "post evidence")
        require(rule["state_ref"] not in checked, "Duplicate post expectation")
        checked.add(rule["state_ref"])
        state = states.get(rule["state_ref"])
        if state:
            integer(rule.get("equals"), (1 << state["width"]) - 1, "post expectation", False)
        observed = sample(post, rule["state_ref"])
        if observed is not None and observed != rule["equals"]: finding("unexpected_post_release_effect", state=rule["state_ref"], expected=rule["equals"], observed=observed, evidence_ref=rule["evidence_ref"])
    report["status"] = "review_required" if report["findings"] else "incomplete" if report["gaps"] else "within_sampled_reset_contract"
    return report


def exit_code(report):
    return {"within_sampled_reset_contract": 0, "review_required": 1, "incomplete": 2}[report["status"]]


def markdown(report):
    lines = ["# Reset state review", "", "Status: " + report["status"], ""]
    for key in ("state_by_owner", "continuity", "findings", "gaps"):
        lines += [key.replace("_", " ").capitalize() + ":", ""]
        lines += ["- " + json.dumps(item, ensure_ascii=False) for item in report[key]] or ["- None"]
        lines += [""]
    return "\n".join(lines + report["limits"]) + "\n"
