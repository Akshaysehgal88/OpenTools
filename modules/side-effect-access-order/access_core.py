"""Bounded review of sampled, quiescent register accesses and explicit intent."""
import hashlib
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON value")))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def integer(value, label, maximum=None, nullable=False):
    if value is None and nullable:
        return
    require(type(value) is int and value >= 0 and (maximum is None or value <= maximum), label + " must be a nonnegative integer in range")


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + " must be nonempty text")


def boolean(value, label, nullable=False):
    require(type(value) is bool or (nullable and value is None), label + " must be boolean" + (" or null" if nullable else ""))


def mask(field):
    return ((1 << field["width"]) - 1) << field["lsb"]


def validate(spec, trace, policy):
    for record, kind in ((spec, "spec"), (trace, "trace"), (policy, "policy")):
        require(isinstance(record, dict) and record.get("format") == "opentools.access." + kind + ".v1", "Unsupported " + kind + " format")
        require(isinstance(record.get("scope"), dict) and set(record["scope"]) == {"project", "configuration", "mode", "address_space_ref"}, "Exact scope fields required")
        for value in record["scope"].values():
            text(value, "scope")
        text(record.get("basis_ref"), "basis_ref")
        boolean(record.get("inputs_complete"), "inputs_complete")
    regs = {}
    addresses = set()
    require(isinstance(spec.get("registers"), list) and spec["registers"], "Selected registers required")
    for reg in spec["registers"]:
        text(reg.get("id"), "register id")
        require(reg["id"] not in regs, "Duplicate register id")
        integer(reg.get("address"), "register address")
        require(reg.get("width") in (8, 16, 32, 64) and type(reg["width"]) is int, "Supported register width required")
        require(reg.get("access_width") == reg["width"], "Split accesses are unsupported")
        require(reg["address"] % (reg["width"] // 8) == 0, "Unaligned register")
        occupied = set(range(reg["address"], reg["address"] + reg["width"] // 8))
        require(not addresses & occupied, "Overlapping register storage")
        addresses |= occupied
        text(reg.get("evidence_ref"), "register evidence")
        require(isinstance(reg.get("fields"), list) and reg["fields"], "Selected fields required")
        names, bits = set(), 0
        for field in reg["fields"]:
            text(field.get("name"), "field name")
            require(field["name"] not in names, "Duplicate field")
            names.add(field["name"])
            integer(field.get("lsb"), "lsb", reg["width"] - 1)
            integer(field.get("width"), "field width", reg["width"])
            require(field["width"] > 0 and field["width"] + field["lsb"] <= reg["width"], "Invalid field extent")
            require(not bits & mask(field), "Overlapping fields")
            bits |= mask(field)
            require(field.get("sw") in ("r", "w", "rw", None), "Unsupported access encoding")
            require(field.get("onread") in ("none", "clear", "unsupported", None), "Unsupported onread encoding")
            require(field.get("onwrite") in ("none", "assign", "one_clear", "unsupported", None), "Unsupported onwrite encoding")
            integer(field.get("reset"), "reset", (1 << field["width"]) - 1, True)
            text(field.get("evidence_ref"), "field evidence")
        regs[reg["id"]] = reg
    require(isinstance(trace.get("events"), list) and trace["events"], "Selected events required")
    events, previous = {}, -1
    for event in trace["events"]:
        integer(event.get("seq"), "event seq")
        require(event["seq"] > previous, "Trace sequence must increase strictly")
        previous = event["seq"]
        text(event.get("register_ref"), "event register_ref")
        require(event.get("kind") in ("read", "write"), "Expected read or write")
        text(event.get("evidence_ref"), "event evidence")
        text(event.get("operation_ref"), "operation_ref")
        for key in ("accepted", "error", "hardware_quiet", "reset_inactive"):
            boolean(event.get(key), key, True)
        reg = regs.get(event["register_ref"])
        maximum = (1 << reg["width"]) - 1 if reg else None
        for key in ("before", "after", "write_data", "read_data", "bit_enable"):
            integer(event.get(key), key, maximum, True)
        integer(event.get("byte_enable"), "byte_enable", (1 << (reg["width"] // 8)) - 1 if reg else None, True)
        events[event["seq"]] = event
    require(trace.get("state_basis") == "selected-field-storage", "Explicit pre/post field storage samples required")
    require(isinstance(policy.get("events"), list), "Policy events required")
    rules = {}
    for rule in policy["events"]:
        integer(rule.get("seq"), "policy seq")
        require(rule["seq"] not in rules, "Duplicate policy event")
        for key in ("allowed_clear_mask", "required_clear_mask"):
            integer(rule.get(key), key, nullable=True)
        if rule["allowed_clear_mask"] is not None and rule["required_clear_mask"] is not None:
            require(rule["required_clear_mask"] & ~rule["allowed_clear_mask"] == 0, "Required clear must be allowed")
        boolean(rule.get("observation_only"), "observation_only", True)
        require(isinstance(rule.get("after_seq"), list) and len(rule["after_seq"]) == len(set(rule["after_seq"])), "Unique prerequisite sequences required")
        for seq in rule["after_seq"]:
            integer(seq, "prerequisite seq")
        text(rule.get("evidence_ref"), "policy evidence")
        rules[rule["seq"]] = rule
    return regs, events, rules


def review(spec, trace, policy):
    regs, events, rules = validate(spec, trace, policy)
    report = {"format": "opentools.access.report.v1", "scope": spec["scope"],
              "bindings": {"spec_sha256": digest(spec), "trace_sha256": digest(trace), "policy_sha256": digest(policy)},
              "findings": [], "gaps": [], "observations": [],
              "limits": ["Selected sampled accesses only; no arbitrary driver-flow, concurrent hardware, split access, lock or shadow-write proof.",
                         "Bindings and declared completeness do not establish semantic correctness, ownership or approval."]}
    def gap(kind, seq=None, **details):
        report["gaps"].append(dict(kind=kind, seq=seq, **details))
    def finding(kind, seq, **details):
        report["findings"].append(dict(kind=kind, seq=seq, **details))
    bound = True
    for record, name in ((trace, "trace"), (policy, "policy")):
        if record["scope"] != spec["scope"] or record["basis_ref"] != spec["basis_ref"] or record.get("spec_sha256") != digest(spec):
            gap("scope_or_spec_binding", record=name)
            bound = False
    if policy.get("trace_sha256") != digest(trace):
        gap("trace_binding")
        bound = False
    for record, name in ((spec, "spec"), (trace, "trace"), (policy, "policy")):
        if not record["inputs_complete"]:
            gap("partial_inputs", record=name)
    if bound:
        for seq in rules.keys() - events.keys():
            gap("policy_event_absent", seq)
        last = {}
        for seq, event in events.items():
            reg = regs.get(event["register_ref"])
            rule = rules.get(seq)
            if reg is None:
                gap("register_absent", seq)
                continue
            if rule is None:
                gap("intent_absent", seq)
            if event["error"] is True:
                finding("native_access_error", seq, evidence_ref=event["evidence_ref"])
            if event["accepted"] is not True or event["error"] is not False:
                gap("acceptance_unestablished", seq)
                continue
            if event["hardware_quiet"] is not True or event["reset_inactive"] is not True:
                gap("concurrent_or_reset_effects_unresolved", seq)
                last.pop(reg["id"], None)
                continue
            if event["before"] is None or event["after"] is None:
                gap("state_sample_absent", seq)
                last.pop(reg["id"], None)
                continue
            bits = sum(mask(f) for f in reg["fields"])
            permitted = ("r", "rw") if event["kind"] == "read" else ("w", "rw")
            if all(f["sw"] is not None for f in reg["fields"]) and not any(f["sw"] in permitted for f in reg["fields"]):
                finding("no_accessible_selected_field", seq, kind_requested=event["kind"])
            if reg["id"] in last and trace["inputs_complete"] and (last[reg["id"]] ^ event["before"]) & bits:
                finding("state_discontinuity", seq)
            last[reg["id"]] = event["after"]
            expected, supported = event["before"], True
            if event["kind"] == "write":
                if any(event[k] is None for k in ("write_data", "byte_enable", "bit_enable")):
                    gap("write_operand_absent", seq)
                    supported = False
                else:
                    enabled = sum(255 << (8 * i) for i in range(reg["width"] // 8) if event["byte_enable"] & (1 << i))
                    if event["bit_enable"] != enabled:
                        gap("byte_lane_mapping_mismatch", seq)
                        supported = False
                    if event["write_data"] & event["bit_enable"] & ~bits:
                        gap("unmodeled_written_bits", seq)
            for field in reg["fields"]:
                fm = mask(field)
                effect = field["onread"] if event["kind"] == "read" else field["onwrite"]
                access = field["sw"]
                if access is None or effect in (None, "unsupported"):
                    gap("field_semantics_unresolved", seq, field=field["name"])
                    supported = False
                    continue
                if event["kind"] == "read":
                    if access in ("r", "rw"):
                        if event["read_data"] is None:
                            gap("read_sample_absent", seq)
                        elif (event["read_data"] ^ event["before"]) & fm:
                            finding("read_value_mismatch", seq, field=field["name"])
                        if effect == "clear":
                            expected &= ~fm
                elif supported and access in ("w", "rw"):
                    enabled = event["bit_enable"] & fm
                    if effect == "one_clear":
                        expected &= ~(event["write_data"] & enabled)
                    elif effect == "assign":
                        expected = (expected & ~enabled) | (event["write_data"] & enabled)
            if supported and (expected ^ event["after"]) & bits:
                finding("native_state_mismatch", seq, expected=expected & bits, observed=event["after"] & bits)
            cleared = event["before"] & ~event["after"] & bits
            if rule:
                maximum = (1 << reg["width"]) - 1
                for key in ("allowed_clear_mask", "required_clear_mask"):
                    integer(rule[key], key, maximum, True)
                if any(rule[k] is None for k in ("allowed_clear_mask", "required_clear_mask", "observation_only")):
                    gap("intent_unresolved", seq)
                else:
                    if cleared & ~rule["allowed_clear_mask"]:
                        finding("unexpected_clear", seq, mask=cleared & ~rule["allowed_clear_mask"], intent_ref=rule["evidence_ref"])
                    if event["before"] & event["after"] & rule["required_clear_mask"]:
                        finding("required_clear_not_observed", seq, mask=event["before"] & event["after"] & rule["required_clear_mask"])
                    if rule["observation_only"] and (event["before"] ^ event["after"]) & bits:
                        finding("destructive_observation", seq)
                for predecessor in rule["after_seq"]:
                    prior = events.get(predecessor)
                    if prior is None and not trace["inputs_complete"]:
                        gap("required_order_unobserved", seq, after_seq=predecessor)
                    elif prior is None or predecessor >= seq:
                        finding("required_order_absent", seq, after_seq=predecessor)
                    elif prior["accepted"] is not True or prior["error"] is not False:
                        gap("required_order_acceptance_unresolved", seq, after_seq=predecessor)
            report["observations"].append({"seq": seq, "register_ref": reg["id"], "kind": event["kind"],
                                           "cleared_mask": cleared, "evidence_ref": event["evidence_ref"]})
    report["status"] = "review_required" if report["findings"] else "incomplete" if report["gaps"] else "within_observed_contract"
    return report


def exit_code(report):
    return {"within_observed_contract": 0, "review_required": 1, "incomplete": 2}[report["status"]]


def markdown(report):
    rows = ["# Register access review", "", "Status: " + report["status"], ""]
    for label in ("findings", "gaps", "observations"):
        rows += [label.capitalize() + ":", ""]
        rows += ["- " + json.dumps(row, ensure_ascii=False) for row in report[label]] or ["- None"]
        rows += [""]
    rows += report["limits"]
    return "\n".join(rows) + "\n"
