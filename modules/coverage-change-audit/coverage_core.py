"""Explain changes in declared, per-instance functional coverpoint populations."""
from __future__ import annotations

import json
from pathlib import Path


class InputError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InputError(message)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(InputError(f"Invalid number: {value}")))


def text(value):
    return isinstance(value, str) and bool(value.strip())


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def indexed(items, label):
    require(isinstance(items, list), f"{label} must be a list")
    result = {}
    for item in items:
        require(isinstance(item, dict) and text(item.get("id")), f"{label}: missing id")
        require(item["id"] not in result, f"{label}: duplicate id {item['id']}")
        result[item["id"]] = item
    return result


def definition(item):
    value = item.get("definition")
    require(value is None or text(value), "Definition must be a nonempty string or null")
    if value is not None:
        require(text(item.get("definition_evidence")), "Definition requires definition_evidence")
    return value


def validate(snapshot):
    require(isinstance(snapshot, dict), "Snapshot must be an object")
    require(snapshot.get("format") == "opentools.coverage-snapshot.v1", "Unsupported snapshot format")
    require(snapshot.get("metric") == "coverpoint-instance-bin-fraction", "Unsupported metric")
    require(set(snapshot) <= {"format", "metric", "run_id", "scope", "configuration_ref", "model_ref", "tool_ref", "source_ref", "population_complete", "points"}, "Unsupported snapshot field")
    for key in ("run_id", "scope", "configuration_ref", "model_ref", "tool_ref", "source_ref"):
        require(text(snapshot.get(key)), f"Missing {key}")
    require(type(snapshot.get("population_complete")) is bool, "population_complete must be boolean")
    points = indexed(snapshot.get("points"), "points")
    require(points, "At least one coverpoint instance is required")
    for point in points.values():
        require(set(point) <= {"id", "definition", "definition_evidence", "at_least", "weight", "goal", "bins", "evidence_ref"}, "Unsupported point field")
        definition(point)
        for key, minimum in (("at_least", 1), ("weight", 0), ("goal", 0)):
            require(integer(point.get(key), minimum), f"Point {key} must be an integer >= {minimum}")
        require(point["goal"] <= 100, "Point goal must be <= 100")
        require(text(point.get("evidence_ref")), "Point requires evidence_ref")
        for bin_ in indexed(point.get("bins"), "bins").values():
            require(set(bin_) <= {"id", "kind", "count", "definition", "definition_evidence", "evidence_ref"}, "Unsupported bin field (per-bin weights/external exclusions are outside this metric)")
            require(bin_.get("kind") in ("regular", "ignore", "illegal"), "Unsupported bin kind")
            require(integer(bin_.get("count")), "Bin count must be a nonnegative integer")
            require(text(bin_.get("evidence_ref")), "Bin requires evidence_ref")
            definition(bin_)
    return points


def summary(point):
    bins = point["bins"]
    regular = [b for b in bins if b["kind"] == "regular"]
    descriptive = [b for b in bins if b["kind"] != "illegal"]
    hit = lambda b: b["count"] >= point["at_least"]
    covered = sum(hit(b) for b in regular)
    return {"applicable_bins": len(regular), "covered_bins": covered,
            "bin_fraction_percent": 100 * covered / len(regular) if regular else None,
            "descriptive_population_bins": len(descriptive),
            "descriptive_satisfied_bins": sum(hit(b) for b in descriptive),
            "ignored_bins": sum(b["kind"] == "ignore" for b in bins),
            "illegal_bins": sum(b["kind"] == "illegal" for b in bins),
            "illegal_hits": sum(b["count"] for b in bins if b["kind"] == "illegal"),
            "at_least": point["at_least"], "weight": point["weight"], "goal": point["goal"]}


def _mapping(mapping, baseline, current, before, after):
    result = {}
    if mapping is None:
        return result
    require(isinstance(mapping, dict) and mapping.get("format") == "opentools.coverage-map.v1", "Unsupported mapping format")
    require(mapping.get("baseline_run_id") == baseline["run_id"] and
            mapping.get("current_run_id") == current["run_id"], "Mapping run binding differs")
    require(isinstance(mapping.get("mappings"), list), "mappings must be a list")
    for entry in mapping["mappings"]:
        require(isinstance(entry, dict), "Mapping entry must be an object")
        p, old, new = (entry.get(k) for k in ("point_id", "from", "to"))
        require(all(text(k) for k in (p, old, new)) and text(entry.get("evidence_ref")), "Mapping requires point_id, from, to and evidence_ref")
        require(p in before and p in after, "Mapping point must exist in both snapshots")
        require(old in indexed(before[p]["bins"], "bins") and new in indexed(after[p]["bins"], "bins"), "Mapping bin is absent")
        require((p, old) not in result, "Repeated mapping source")
        result[p, old] = entry
    # Include implicit unchanged IDs in the injectivity check.
    for p in before.keys() & after.keys():
        targets = []
        new_bins = indexed(after[p]["bins"], "bins")
        for old in indexed(before[p]["bins"], "bins"):
            new = result[p, old]["to"] if (p, old) in result else old
            if new in new_bins:
                targets.append(new)
        require(len(targets) == len(set(targets)), "Mapping is not one-to-one, including unchanged IDs")
    return result


def compare(baseline, current, mapping=None):
    before, after = validate(baseline), validate(current)
    mapping = _mapping(mapping, baseline, current, before, after)
    issues, rows, changes = [], [], []
    for key in ("scope", "configuration_ref", "tool_ref"):
        if baseline[key] != current[key]:
            issues.append(f"{key} differs; cross-context hit progress is not established")
    for name, snapshot in (("baseline", baseline), ("current", current)):
        if not snapshot["population_complete"]:
            issues.append(f"{name} population is incomplete for the declared scope")
        for point in snapshot["points"]:
            if point.get("definition") is None:
                issues.append(f"{name} {point['id']}: coverpoint expression/sampling definition is unknown")
            for bin_ in point["bins"]:
                if bin_.get("definition") is None:
                    issues.append(f"{name} {point['id']}/{bin_['id']}: bin definition is unknown")

    def change(category, point_id, bin_id=None, old=None, new=None, evidence=None):
        changes.append({"category": category, "point_id": point_id, "bin_id": bin_id,
                        "before": old, "after": new, "evidence": evidence or []})

    if baseline["model_ref"] != current["model_ref"]:
        change("model_revision_changed", "*", old=baseline["model_ref"], new=current["model_ref"])
    compatible_context = all(baseline[k] == current[k] for k in ("scope", "configuration_ref", "tool_ref"))
    for p in sorted(before.keys() | after.keys()):
        a, b = before.get(p), after.get(p)
        rows.append({"point_id": p, "baseline": summary(a) if a else None, "current": summary(b) if b else None})
        if b:
            for bin_ in b["bins"]:
                if bin_["kind"] == "illegal" and bin_["count"]:
                    change("illegal_bin_hit", p, bin_["id"], new=bin_["count"], evidence=[bin_["evidence_ref"]])
        if a is None or b is None:
            category = ("point_added" if a is None else "point_removed") if (
                baseline["population_complete"] and current["population_complete"]) else (
                "point_not_observed_in_baseline" if a is None else "point_not_observed_in_current")
            change(category, p, evidence=[(a or b)["evidence_ref"]])
            continue
        cp_known = a.get("definition") is not None and b.get("definition") is not None
        cp_equal = cp_known and a["definition"] == b["definition"]
        if not cp_known:
            change("definition_unknown", p)
        elif not cp_equal:
            change("point_definition_changed", p, old=a["definition"], new=b["definition"],
                   evidence=[a["definition_evidence"], b["definition_evidence"]])
        for key in ("at_least", "weight", "goal"):
            if a[key] != b[key]:
                change(f"{key}_changed", p, old=a[key], new=b[key], evidence=[a["evidence_ref"], b["evidence_ref"]])
        ab, bb = indexed(a["bins"], "bins"), indexed(b["bins"], "bins")
        used = set()
        for old_id in sorted(ab):
            entry = mapping.get((p, old_id))
            new_id = entry["to"] if entry else old_id
            old, new = ab[old_id], bb.get(new_id)
            if new is None:
                change("bin_removed" if current["population_complete"] else "bin_not_observed_in_current", p, old_id,
                       old=old, evidence=[old["evidence_ref"]])
                continue
            used.add(new_id)
            evidence = [old["evidence_ref"], new["evidence_ref"]]
            if entry:
                evidence.append(entry["evidence_ref"])
            if old_id != new_id:
                change("bin_renamed", p, old_id, old=old_id, new=new_id, evidence=evidence)
            known = old.get("definition") is not None and new.get("definition") is not None
            equal = known and old["definition"] == new["definition"]
            if not known:
                change("definition_unknown", p, old_id, evidence=evidence)
            elif not equal:
                change("bin_definition_changed", p, old_id, old=old["definition"], new=new["definition"],
                       evidence=[old["definition_evidence"], new["definition_evidence"]])
            if old["kind"] != new["kind"]:
                change("bin_kind_changed", p, old_id, old=old["kind"], new=new["kind"], evidence=evidence)
            if old["count"] != new["count"]:
                change("count_changed", p, old_id, old=old["count"], new=new["count"], evidence=evidence)
            # Progress claims require known unchanged semantics, context and native kind.
            if compatible_context and cp_equal and equal and old["kind"] == new["kind"] == "regular":
                if old["count"] == 0 < new["count"]:
                    change("newly_hit", p, old_id, old=old["count"], new=new["count"], evidence=evidence)
                if new["count"] == 0 < old["count"]:
                    change("hit_lost", p, old_id, old=old["count"], new=new["count"], evidence=evidence)
                old_sat, new_sat = old["count"] >= a["at_least"], new["count"] >= b["at_least"]
                if old_sat != new_sat:
                    change("newly_satisfied" if new_sat else "no_longer_satisfied", p, old_id,
                           old={"count": old["count"], "at_least": a["at_least"]},
                           new={"count": new["count"], "at_least": b["at_least"]}, evidence=evidence)
        for new_id in sorted(bb.keys() - used):
            change("bin_added" if baseline["population_complete"] else "bin_not_observed_in_baseline", p, new_id,
                   new=bb[new_id], evidence=[bb[new_id]["evidence_ref"]])
    return {"format": "opentools.coverage-audit.v1", "baseline_run_id": baseline["run_id"],
            "current_run_id": current["run_id"], "metric": baseline["metric"],
            "inputs": {name: {key: snapshot[key] for key in ("run_id", "scope", "configuration_ref", "model_ref", "tool_ref", "source_ref", "population_complete")}
                       for name, snapshot in (("baseline", baseline), ("current", current))},
            "status": "incomplete" if issues else "review_required" if changes else "unchanged_within_scope",
            "review_required": bool(changes or issues), "issues": issues, "points": rows, "changes": changes,
            "progress": {k: sum(c["category"] == k for c in changes)
                         for k in ("newly_hit", "hit_lost", "newly_satisfied", "no_longer_satisfied")},
            "limits": ["Fractions are equal-bin, per-instance, thresholded fractions, not native aggregate scores.",
                       "Descriptive population includes regular and ignore bins; illegal bins are separate.",
                       "Definition equality is exact equality of supplied semantic keys, not expression equivalence.",
                       "Newly satisfied can result from changed thresholds; consult scoring and count changes."]}


def _cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def markdown(report):
    lines = ["# Coverage change audit", "", f"Status: **{report['status']}**", "",
             f"Runs: `{_cell(report['baseline_run_id'])}` → `{_cell(report['current_run_id'])}`", "",
             "## Per-instance populations", "",
             "| Point | Baseline covered/applicable | Current covered/applicable | Baseline % | Current % |",
             "|---|---:|---:|---:|---:|"]
    for row in report["points"]:
        cells = []
        for s in (row["baseline"], row["current"]):
            cells.append(f"{s['covered_bins']}/{s['applicable_bins']}" if s else "absent")
        scores = [str(round(s["bin_fraction_percent"], 4)) if s and s["bin_fraction_percent"] is not None else "n/a"
                  for s in (row["baseline"], row["current"])]
        lines.append("| " + " | ".join([_cell(row["point_id"]), *cells, *scores]) + " |")
    sections = {"Population and definition changes": lambda c: c["category"].startswith(("bin_", "point_", "model_")),
                "Hit and satisfaction changes": lambda c: c["category"] in ("count_changed", "newly_hit", "hit_lost", "newly_satisfied", "no_longer_satisfied", "illegal_bin_hit"),
                "Scoring changes": lambda c: c["category"] in ("at_least_changed", "weight_changed", "goal_changed"),
                "Unresolved correspondence": lambda c: c["category"] == "definition_unknown" or "not_observed" in c["category"]}
    for title, include in sections.items():
        lines += ["", f"## {title}", ""]
        matches = [c for c in report["changes"] if include(c)]
        if not matches:
            lines.append("None observed within the declared scope.")
            continue
        lines += ["| Change | Point / bin | Before | After | Evidence |", "|---|---|---|---|---|"]
        for c in matches:
            lines.append("| " + " | ".join(_cell(v) for v in (c["category"], c["point_id"] + (" / " + c["bin_id"] if c["bin_id"] else ""),
                         json.dumps(c["before"], ensure_ascii=False), json.dumps(c["after"], ensure_ascii=False), "; ".join(c["evidence"]))) + " |")
    lines += ["", "## Evidence limits", ""]
    lines += [f"- {_cell(issue)}" for issue in report["issues"] + report["limits"]]
    return "\n".join(lines) + "\n"
