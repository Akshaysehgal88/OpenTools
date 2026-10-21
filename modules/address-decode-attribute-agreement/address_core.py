"""Compare explicit byte-addressed maps without inferring hidden translations."""
import hashlib
import json
from pathlib import Path

SCOPE = ("project_ref", "configuration_ref", "mode_ref")
PERMISSIONS = ("read", "write", "execute")
ATTRIBUTES = ("cacheable", "shareable", "secure_only")
ATTR_PATHS = tuple("permissions." + k for k in PERMISSIONS) + tuple("attributes." + k for k in ATTRIBUTES)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def nullable(value):
    return value is None or text(value)


def shape(value, fields, optional=()):
    require(isinstance(value, dict) and set(fields) <= set(value)
            and set(value) <= set(fields) | set(optional), "Unexpected or missing fields")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


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
                      parse_constant=lambda value: require(False, "Non-finite JSON value"))


def integer(value, positive=False):
    return value is None or type(value) is int and value >= (1 if positive else 0)


def validate_map(record):
    shape(record, ("format", "view_ref", "revision_ref", "scope", "address_unit", "basis_ref", "inputs_complete", "windows"), ("provenance",))
    require(record["format"] == "opentools.address-map.v1" and text(record["view_ref"]), "Invalid map identity")
    require(nullable(record["revision_ref"]) and nullable(record["basis_ref"]), "Invalid map basis")
    require(record["address_unit"] == "bytes", "Only explicitly byte-addressed maps are supported")
    shape(record["scope"], SCOPE)
    require(all(nullable(v) for v in record["scope"].values()), "Invalid scope")
    require(record["inputs_complete"] is None or type(record["inputs_complete"]) is bool, "Invalid map completeness")
    require(isinstance(record["windows"], list), "Windows must be a list")
    ids = set()
    for window in record["windows"]:
        shape(window, ("id", "initiator_ref", "base", "size", "target_ref", "target_base", "permissions", "attributes", "evidence_ref"))
        require(text(window["id"]) and window["id"] not in ids, "Unique window IDs required")
        ids.add(window["id"])
        require(all(nullable(window[k]) for k in ("initiator_ref", "target_ref", "evidence_ref")), "Invalid window identity/basis")
        require(integer(window["base"]) and integer(window["size"], positive=True) and integer(window["target_base"]), "Invalid byte interval")
        shape(window["permissions"], PERMISSIONS)
        shape(window["attributes"], ATTRIBUTES)
        require(all(v is None or type(v) is bool for key in ("permissions", "attributes") for v in window[key].values()), "Attributes must be boolean or null")
    canonical(record)


def validate_policy(policy):
    shape(policy, ("format", "scope", "hardware_sha256", "software_sha256", "basis_ref", "population_complete", "evidence_ref", "pairs", "aliases", "required_decode"))
    require(policy["format"] == "opentools.address-policy.v1", "Invalid address policy")
    shape(policy["scope"], SCOPE)
    require(all(text(v) for v in policy["scope"].values()) and nullable(policy["basis_ref"]) and nullable(policy["evidence_ref"]), "Declare the exact requested map scope")
    for key in ("hardware_sha256", "software_sha256"):
        value = policy[key]
        require(value is None or isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value), "Invalid map digest")
    require(policy["population_complete"] is None or type(policy["population_complete"]) is bool, "Invalid population completeness")
    require(isinstance(policy["pairs"], list) and policy["pairs"], "Select explicit window correspondence")
    left, right = set(), set()
    for pair in policy["pairs"]:
        shape(pair, ("hardware", "software", "evidence_ref"))
        require(text(pair["hardware"]) and text(pair["software"]) and nullable(pair["evidence_ref"])
                and pair["hardware"] not in left and pair["software"] not in right, "Correspondence must be one-to-one")
        left.add(pair["hardware"])
        right.add(pair["software"])
    require(isinstance(policy["aliases"], list) and isinstance(policy["required_decode"], list), "Invalid alias/range lists")
    seen = set()
    for alias in policy["aliases"]:
        shape(alias, ("initiator_ref", "windows", "allow_differences", "evidence_ref"))
        require(text(alias["initiator_ref"]) and isinstance(alias["windows"], list) and len(alias["windows"]) == 2
                and all(text(v) for v in alias["windows"]) and len(set(alias["windows"])) == 2, "Declare an exact alias pair")
        key = (alias["initiator_ref"], tuple(sorted(alias["windows"])))
        require(key not in seen, "Duplicate alias rule")
        seen.add(key)
        require(isinstance(alias["allow_differences"], list) and len(set(alias["allow_differences"])) == len(alias["allow_differences"])
                and set(alias["allow_differences"]) <= set(ATTR_PATHS) and nullable(alias["evidence_ref"]), "Invalid alias attribute policy")
    for interval in policy["required_decode"]:
        shape(interval, ("initiator_ref", "base", "size", "evidence_ref"))
        require(text(interval["initiator_ref"]) and type(interval["base"]) is int and interval["base"] >= 0
                and type(interval["size"]) is int and interval["size"] > 0 and nullable(interval["evidence_ref"]), "Invalid required decode range")
    canonical(policy)


def flatten(window):
    values = {key: window[key] for key in ("initiator_ref", "base", "size", "target_ref", "target_base")}
    values.update({key + "." + name: value for key in ("permissions", "attributes") for name, value in window[key].items()})
    return values


def intersection(a, b, start="base"):
    if any(w[k] is None for w in (a, b) for k in (start, "size")):
        return None
    first, last = max(a[start], b[start]), min(a[start] + a["size"], b[start] + b["size"])
    return [first, last] if first < last else []


def uncovered(base, size, windows):
    cursor, end, result = base, base + size, []
    for first, last in sorted((w["base"], w["base"] + w["size"]) for w in windows if w["base"] is not None and w["size"] is not None):
        if last <= cursor or first >= end:
            continue
        if first > cursor:
            result.append([cursor, min(first, end)])
        cursor = max(cursor, min(last, end))
    if cursor < end:
        result.append([cursor, end])
    return result


def compare(hardware, software, policy):
    validate_map(hardware)
    validate_map(software)
    validate_policy(policy)
    findings, gaps, aliases, holes = [], [], [], []
    result = {"format": "opentools.address-review.v1", "scope": policy["scope"],
              "hardware_sha256": digest(hardware), "software_sha256": digest(software), "policy_sha256": digest(policy),
              "findings": findings, "gaps": gaps, "aliases": aliases, "required_ranges": holes,
              "limits": ["Declared effective byte maps and explicit correspondence only.",
                         "No inferred translation, native decode priority, interconnect security or coherency proof.",
                         "References, map roles and completeness declarations are not authenticated."]}

    def finish():
        result["status"] = "review_required" if findings else "incomplete" if gaps else "agrees_within_declared_scope"
        return result

    applicable = True
    for name, record in (("hardware", hardware), ("software", software)):
        if policy[name + "_sha256"] != digest(record) or record["scope"] != policy["scope"]:
            gaps.append(name + " binding/scope is missing, stale or foreign")
            applicable = False
        if record["basis_ref"] != policy["basis_ref"] or not policy["basis_ref"]:
            gaps.append(name + " effective-map semantic basis is unknown or different")
            applicable = False
        if record["inputs_complete"] is not True or not record["revision_ref"]:
            gaps.append(name + " input/revision basis is incomplete")
        for window in record["windows"]:
            if any(v is None for v in flatten(window).values()) or not window["evidence_ref"]:
                gaps.append(name + ": incomplete window " + window["id"])
    if policy["population_complete"] is not True or not policy["evidence_ref"]:
        gaps.append("Compared obligation population/review basis is incomplete")
    if not applicable:
        return finish()
    hw = {w["id"]: w for w in hardware["windows"]}
    sw = {w["id"]: w for w in software["windows"]}
    for rule in policy["aliases"]:
        if any(name not in hw or hw[name]["initiator_ref"] != rule["initiator_ref"] for name in rule["windows"]):
            gaps.append("Alias rule has absent or foreign-initiator windows")
    for pair in policy["pairs"]:
        a, b = hw.get(pair["hardware"]), sw.get(pair["software"])
        if a is None or b is None or not pair["evidence_ref"]:
            gaps.append("Window correspondence is absent/unreviewed: " + pair["hardware"])
            continue
        for path, value in flatten(a).items():
            other = flatten(b)[path]
            if value is not None and other is not None and value != other:
                findings.append({"kind": "view_difference", "hardware": a["id"], "software": b["id"],
                                 "path": path, "hardware_value": value, "software_value": other,
                                 "evidence": [a["evidence_ref"], b["evidence_ref"], pair["evidence_ref"]]})
    if set(hw) != {p["hardware"] for p in policy["pairs"]} or set(sw) != {p["software"] for p in policy["pairs"]}:
        gaps.append("The selected maps contain unmapped windows or missing selected IDs")
    for name, record in (("hardware", hardware), ("software", software)):
        windows = record["windows"]
        for i, a in enumerate(windows):
            for b in windows[i + 1:]:
                if a["initiator_ref"] is None or a["initiator_ref"] != b["initiator_ref"]:
                    continue
                overlap = intersection(a, b)
                if overlap:
                    findings.append({"kind": "address_overlap", "view": name, "windows": [a["id"], b["id"]],
                                     "interval": overlap, "initiator_ref": a["initiator_ref"]})
                if name != "hardware" or a["target_ref"] is None or a["target_ref"] != b["target_ref"]:
                    continue
                target_overlap = intersection(a, b, "target_base")
                if not target_overlap or overlap:
                    continue
                rule = next((r for r in policy["aliases"] if r["initiator_ref"] == a["initiator_ref"]
                             and set(r["windows"]) == {a["id"], b["id"]}), None)
                if rule is None or not rule["evidence_ref"]:
                    findings.append({"kind": "unreviewed_target_alias", "windows": [a["id"], b["id"]],
                                     "initiator_ref": a["initiator_ref"], "target_interval": target_overlap})
                    continue
                if a["target_base"] != b["target_base"] or a["size"] != b["size"]:
                    gaps.append("Partial target alias needs another qualified interpretation: " + a["id"])
                    continue
                left, right = flatten(a), flatten(b)
                differences = [p for p in ATTR_PATHS if left[p] is not None and right[p] is not None and left[p] != right[p]]
                disallowed = sorted(set(differences) - set(rule["allow_differences"]))
                aliases.append({"windows": [a["id"], b["id"]], "initiator_ref": a["initiator_ref"],
                                "status": "attribute_review" if disallowed else "allowed_under_supplied_policy",
                                "attribute_differences": differences, "evidence_ref": rule["evidence_ref"]})
                if disallowed:
                    findings.append({"kind": "alias_attribute_difference", "windows": [a["id"], b["id"]], "paths": disallowed})
    for interval in policy["required_decode"]:
        if not interval["evidence_ref"]:
            gaps.append("Required range has no independent evidence")
            continue
        windows = [w for w in hardware["windows"] if w["initiator_ref"] == interval["initiator_ref"]]
        unknown = any(w["base"] is None or w["size"] is None for w in windows) or any(w["initiator_ref"] is None for w in hardware["windows"])
        missing = uncovered(interval["base"], interval["size"], windows)
        holes.append({"initiator_ref": interval["initiator_ref"], "base": interval["base"], "size": interval["size"],
                      "not_observed": missing, "evidence_ref": interval["evidence_ref"]})
        if missing:
            if hardware["inputs_complete"] is True and not unknown:
                findings.append({"kind": "required_decode_gap", "initiator_ref": interval["initiator_ref"], "intervals": missing})
            else:
                gaps.append("Required decode is not observed in an incomplete population")
    return finish()


def exit_code(report):
    return {"agrees_within_declared_scope": 0, "review_required": 1, "incomplete": 2}[report["status"]]


def markdown(report):
    lines = ["# Address map review", "", "Status: " + report["status"], ""]
    lines += ["- " + json.dumps(item, ensure_ascii=False) for item in report["findings"]]
    lines += ["", "Gaps:"] + ["- " + item for item in report["gaps"]]
    lines += ["", "Limits:"] + ["- " + item for item in report["limits"]]
    return "\n".join(lines) + "\n"
