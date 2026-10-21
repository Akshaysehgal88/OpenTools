"""Review selected property bindings and actual activation at required sample slots."""
from __future__ import annotations
import hashlib
import html
import json
from pathlib import Path, PurePosixPath


class InputError(ValueError):
    pass


def require(condition, message):
    if not condition:raise InputError(message)


def text(value):return isinstance(value, str) and bool(value.strip())


def shape(value, required, optional=()):
    require(isinstance(value, dict) and set(required) <= set(value) <= set(required) | set(optional), "Unexpected record fields")


def canonical(value):return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):h.update(block)
    return h.hexdigest()


def read_json(path):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key: " + key);result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(InputError("Invalid JSON number")))


def contained(root, relative):
    require(text(relative) and "\\" not in relative and ":" not in relative, "Use relative POSIX evidence paths")
    path = PurePosixPath(relative)
    require(not path.is_absolute() and all(p not in ("", ".", "..") for p in relative.split("/")), "Evidence path escapes root")
    root = Path(root).resolve();target = (root / relative).resolve()
    require(target.is_relative_to(root), "Evidence path escapes root")
    current = root
    for part in path.parts:
        current /= part;require(not current.is_symlink(), "Linked evidence is unsupported")
    return target


def known(value):
    if value is None or (isinstance(value, str) and not text(value)):return False
    if isinstance(value, dict):return all(known(v) for v in value.values())
    if isinstance(value, list):return all(known(v) for v in value)
    return True


SCOPE = {"design_ref", "configuration_ref", "window_ref", "mode_ref"}


def scope(value):
    shape(value, SCOPE);require(all(v is None or text(v) for v in value.values()), "Invalid scope reference")


def references(value, keys):require(all(value[k] is None or text(value[k]) for k in keys), "Invalid evidence/reference value")


def review(roster, bindings, evidence, root="."):
    shape(roster, {"format", "scope_ref", "scope", "claim", "claim_kind", "owner_ref", "basis_ref", "inventory_complete", "property_ref", "obligations"})
    require(roster["format"] == "opentools.property-obligations.v1", "Unsupported obligation roster")
    require(all(text(roster[k]) for k in ("scope_ref", "claim", "claim_kind", "property_ref")), "Claim/property required")
    references(roster, ("owner_ref", "basis_ref"));scope(roster["scope"])
    require(roster["inventory_complete"] is None or type(roster["inventory_complete"]) is bool, "Invalid inventory completeness")
    require(isinstance(roster["obligations"], list) and 1 <= len(roster["obligations"]) <= 8, "Select one to eight required sample obligations")
    ids, slots = [], []
    for obligation in roster["obligations"]:
        shape(obligation, {"id", "requirement_ref", "owner_ref", "target_ref", "clock_ref", "edge", "mode", "tick", "condition_ref"})
        require(text(obligation["id"]), "Obligation ID required")
        references(obligation, ("requirement_ref", "owner_ref", "target_ref", "clock_ref", "edge", "condition_ref"))
        require(obligation["mode"] is None or (type(obligation["mode"]) is int and obligation["mode"] in (0, 1)), "Mode must be0/1 or null")
        require(obligation["tick"] is None or (type(obligation["tick"]) is int and 0 <= obligation["tick"] <= 1000000), "Invalid sample tick")
        ids.append(obligation["id"])
        if known({k: obligation[k] for k in ("target_ref", "clock_ref", "edge", "tick")}):slots.append(tuple(obligation[k] for k in ("target_ref", "clock_ref", "edge", "tick")))
    require(len(ids) == len(set(ids)) and len(slots) == len(set(slots)), "Duplicate obligation ID or required sample slot")
    shape(bindings, {"format", "scope", "basis_ref", "roster_sha256", "run_ref", "sources", "bindings"})
    require(bindings["format"] == "opentools.property-bindings.v1", "Unsupported binding model")
    scope(bindings["scope"]);references(bindings, ("basis_ref", "run_ref"))
    require(bindings["sources"] is None or isinstance(bindings["sources"], dict), "Invalid expected input inventory")
    for name, checksum in (bindings["sources"] or {}).items():
        require(text(name) and (checksum is None or (isinstance(checksum, str) and len(checksum) == 64 and all(c in "0123456789abcdef" for c in checksum))), "Invalid input digest")
    require(isinstance(bindings["bindings"], list), "Binding entries required")
    mapping = {}
    for item in bindings["bindings"]:
        shape(item, {"obligation_id", "checker_ref", "property_name", "activation_cover", "basis_ref"})
        require(text(item["obligation_id"]) and item["obligation_id"] not in mapping, "Duplicate/invalid binding entry")
        references(item, ("checker_ref", "property_name", "activation_cover", "basis_ref"));mapping[item["obligation_id"]] = item
    report = {"format": "opentools.property-activation-review.v1", "claim": roster["claim"], "scope_ref": roster["scope_ref"],
              "property_ref": roster["property_ref"], "findings": [], "gaps": [], "obligations": [], "native": {},
              "unselected_observer_events": [], "unselected_native_failures": [],
              "fingerprints": {"roster": digest(roster), "bindings": digest(bindings), "evidence": digest(evidence)},
              "limits": "Activation/binding correspondence in the selected bounded sampled window only. Presence, cover hits and activation do not establish property adequacy or unbounded proof. Intent/ownership/family/dependency references are supplied, not authenticated. No automatic binding/guard edits, proof acceptance or signoff."}
    def issue(kind, **details):report["findings"].append({"kind": kind, **details})
    def gap(kind, **details):report["gaps"].append({"kind": kind, **details})
    def finish():
        report["status"] = "review_required" if report["findings"] else "incomplete" if report["gaps"] else "within_observed_activation_contract"
        return report
    if bindings["roster_sha256"] != digest(roster):
        gap("stale_or_foreign_obligation_binding");return finish()
    if roster["inventory_complete"] is not True or not text(roster["basis_ref"]):gap("independent_obligation_completeness_unestablished")
    if not text(roster["owner_ref"]) or not text(bindings["basis_ref"]):gap("review_or_binding_owner_basis_missing")
    if roster["claim_kind"] != "observed_activation":gap("native_window_does_not_establish_requested_claim_kind", requested=roster["claim_kind"], observed="bounded_simulation")
    for name in set(mapping) - set(ids):gap("binding_entry_outside_required_roster", obligation_id=name)
    try:
        from native_capture import revalidate
        revalidate(evidence, root)
    except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
        gap("native_integrity_or_reader_unresolved", detail=str(exc));return finish()
    unknown, differences = [], []
    for name, observed, wanted in (("roster_scope", evidence["scope"], roster["scope"]), ("binding_scope", evidence["scope"], bindings["scope"]),
                                   ("run", evidence["run_ref"], bindings["run_ref"]), ("sources", evidence["sources"], bindings["sources"])):
        if not known(observed) or not known(wanted):unknown.append(name)
        elif canonical(observed) != canonical(wanted):differences.append(name)
    if unknown:gap("native_correspondence_unknown", fields=unknown)
    if differences:issue("native_evidence_foreign_or_different", fields=differences, action="quarantine")
    if unknown or differences:return finish()
    if evidence["dependencies_complete"] is not True or not text(evidence["dependency_basis_ref"]) or not text(evidence["family_basis_ref"]):
        gap("native_dependency_or_property_family_basis_missing");return finish()
    checker, observer = evidence["checker"], evidence["observer"]
    report["native"] = {"method": evidence["method"], "window": evidence["window"], "outcome": evidence["native_outcome"],
                        "checker": checker, "observer": observer, "covers": evidence["covers"], "assertion_failures": evidence["assertion_failures"]}
    selected_ticks, selected_failures = set(), set()
    for obligation in roster["obligations"]:
        name = obligation["id"];entry = mapping.get(name)
        row = {"obligation_id": name, "tick": obligation["tick"], "required_target": obligation["target_ref"], "required_mode": obligation["mode"],
               "checker_ref": entry["checker_ref"] if entry else None, "activation_observed": False, "condition_observed": None}
        report["obligations"].append(row)
        if not text(obligation["owner_ref"]):gap("required_obligation_owner_unknown", obligation_id=name)
        if not known({k: v for k, v in obligation.items() if k != "owner_ref"}):gap("required_obligation_basis_unknown", obligation_id=name);continue
        if entry is None:gap("required_property_mapping_missing", obligation_id=name);continue
        if not known(entry):gap("property_mapping_basis_unknown", obligation_id=name);continue
        if observer["target"] != obligation["target_ref"]:
            gap("independent_observer_does_not_measure_required_target", obligation_id=name);continue
        expected_clock = {"op": "signal", "ref": obligation["clock_ref"]}
        if observer["pins"]["observer_clk"] != expected_clock or observer["edge"] != obligation["edge"]:
            gap("independent_observer_clock_does_not_match_required_slot", obligation_id=name);continue
        candidate = next((r for r in evidence["required_samples"] if r["tick"] == obligation["tick"]), None)
        if candidate is None:gap("required_sample_not_observed", obligation_id=name);continue
        selected_ticks.add(obligation["tick"])
        if candidate["reset"] or not candidate["event_req"]:
            gap("required_event_not_exercised_at_selected_slot", obligation_id=name);continue
        if candidate["mode"] != obligation["mode"]:
            issue("observed_event_mode_differs_required_mode", obligation_id=name, observed=candidate["mode"]);continue
        row["condition_observed"] = bool(candidate["condition_ok"])
        if not candidate["condition_ok"]:issue("independent_required_condition_observed_false", obligation_id=name, tick=obligation["tick"])
        if checker is None or checker["hier"] != entry["checker_ref"]:
            issue("required_bound_checker_absent", obligation_id=name, actual_checker=checker["hier"] if checker else None);continue
        if checker["target"] != obligation["target_ref"]:
            issue("checker_target_differs_required_target", obligation_id=name);continue
        if checker["property_name"] != entry["property_name"]:
            issue("selected_property_absent_from_binding", obligation_id=name);continue
        if checker["pins"]["checker_clk"] != expected_clock or checker["edge"] != obligation["edge"]:
            issue("checker_clock_differs_required_clock", obligation_id=name, actual=checker["pins"]["checker_clk"])
        expected_cover = "c_active_risk" if obligation["mode"] else "c_active_normal"
        if entry["activation_cover"] != expected_cover:
            issue("activation_cover_does_not_select_required_mode", obligation_id=name, expected=expected_cover)
        drive = next(r for r in evidence["drive"] if r["tick"] == obligation["tick"])
        if not drive["assertions_enabled"]:
            issue("native_assertions_disabled_at_required_slot", obligation_id=name);continue
        sampled = next((r for r in evidence["checker_samples"] if r["tick"] == obligation["tick"]), None)
        if sampled is None:issue("no_checker_sample_at_required_slot", obligation_id=name);continue
        if sampled["reset"] or sampled["extra_disable"]:
            issue("checker_disabled_during_required_event", obligation_id=name, reset=sampled["reset"], extra_disable=sampled["extra_disable"]);continue
        if sampled["mode"] != candidate["mode"] or sampled["event_req"] != candidate["event_req"]:
            issue("checker_does_not_sample_required_event", obligation_id=name);continue
        if sampled["condition_ok"] != candidate["condition_ok"]:
            gap("checker_condition_correspondence_unestablished", obligation_id=name);continue
        row["activation_observed"] = True
        failure = {"hier": checker["hier"] + "." + entry["property_name"], "tick": obligation["tick"]}
        if failure in evidence["assertion_failures"]:
            issue("native_assertion_failure_observed", obligation_id=name, tick=obligation["tick"]);selected_failures.add((failure["hier"], failure["tick"]))
    report["unselected_observer_events"] = [r for r in evidence["required_samples"] if not r["reset"] and r["event_req"] and r["tick"] not in selected_ticks]
    report["unselected_native_failures"] = [r for r in evidence["assertion_failures"] if (r["hier"], r["tick"]) not in selected_failures]
    return finish()


def exit_code(report):return {"within_observed_activation_contract": 0, "review_required": 1, "incomplete": 2}[report["status"]]


def markdown(report):
    def esc(v):return html.escape(str(v)).replace("|", "&#124;").replace("\n", "<br>")
    lines = ["# Property activation review", "", "Status: **" + report["status"] + "**", "", esc(report["claim"]), "",
             "| Obligation | Tick | Target | Mode | Activation observed | Condition observed |", "|---|---:|---|---:|---|---|"]
    for row in report["obligations"]:lines.append("| " + " | ".join(esc(row[k]) for k in ("obligation_id", "tick", "required_target", "required_mode", "activation_observed", "condition_observed")) + " |")
    for title, key in (("Findings", "findings"), ("Missing evidence", "gaps")):
        lines += ["", "## " + title, ""] + (["- " + esc(canonical(v)) for v in report[key]] or ["None within the selected window."])
    return "\n".join(lines + ["", esc(report["limits"]), ""])
