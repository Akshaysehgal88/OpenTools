"""Compare complete finite combinational boundary relations without signoff claims."""
from __future__ import annotations
import hashlib
import html
import json
from pathlib import Path, PurePosixPath


class InputError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InputError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def shape(value, required, optional=()):
    require(isinstance(value, dict) and set(required) <= set(value) <= set(required) | set(optional), "Unexpected record fields")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_hash(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def pairs(values):
    result = {}
    for name, value in values:
        require(name not in result, "Duplicate JSON key: " + name)
        result[name] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=pairs,
                      parse_constant=lambda v: (_ for _ in ()).throw(InputError("Invalid JSON number")))


def contained(root, relative):
    require(text(relative) and "\\" not in relative and ":" not in relative, "Use relative POSIX evidence paths")
    value = PurePosixPath(relative)
    require(not value.is_absolute() and all(p not in ("", ".", "..") for p in relative.split("/")), "Evidence path escapes root")
    root = Path(root).resolve()
    path = (root / relative).resolve()
    require(path.is_relative_to(root), "Evidence path escapes root")
    current = root
    for part in value.parts:
        current /= part
        require(not current.is_symlink(), "Linked evidence is unsupported")
    return path


def relation(value, widths):
    require(isinstance(value, list), "Relation must be a list")
    rows = []
    for row in value:
        require(isinstance(row, list) and len(row) == len(widths), "Relation row arity differs")
        require(all(type(v) is int and 0 <= v < 2 ** width for v, width in zip(row, widths)), "Relation value outside unsigned domain")
        rows.append(tuple(row))
    require(len(set(rows)) == len(rows), "Duplicate relation tuple")
    require(rows == sorted(rows), "Sort relation tuples")
    return set(rows)


def known(value):
    if value is None or (isinstance(value, str) and not text(value)):return False
    if isinstance(value, dict):return all(known(v) for v in value.values())
    if isinstance(value, list):return all(known(v) for v in value)
    return True


def review(contract, evidence, root="."):
    shape(contract, {"format", "review_ref", "claim", "owner_ref", "scope_ref", "scope", "domain", "property", "views", "obligations"})
    require(contract["format"] == "opentools.abstraction-boundary.v1", "Unsupported contract format")
    require(all(text(contract[k]) for k in ("review_ref", "claim", "scope_ref")), "Review claim/scope required")
    require(contract["owner_ref"] is None or text(contract["owner_ref"]), "Invalid owner")
    shape(contract["scope"], {"boundary_ref", "mode_ref", "model_class", "basis_ref"})
    require(contract["scope"]["model_class"] == "finite_combinational_relation", "Only finite combinational relations are qualified")
    require(all(v is None or text(v) for v in contract["scope"].values()), "Invalid scope basis")
    require(isinstance(contract["domain"], list) and 1 <= len(contract["domain"]) <= 8, "Invalid domain")
    names, widths = [], []
    for item in contract["domain"]:
        shape(item, {"name", "width"})
        require(text(item["name"]) and type(item["width"]) is int and 1 <= item["width"] <= 12, "Invalid domain item")
        names.append(item["name"]);widths.append(item["width"])
    require(len(names) == len(set(names)) and sum(widths) <= 12, "Duplicate domain names or domain exceeds4096 tuples")
    shape(contract["property"], {"ref", "basis_ref", "allowed_rows"})
    require(all(contract["property"][k] is None or text(contract["property"][k]) for k in ("ref", "basis_ref")), "Invalid property basis")
    allowed = relation(contract["property"]["allowed_rows"], widths) if contract["property"]["allowed_rows"] is not None else None
    shape(contract["views"], {"concrete", "abstract"})
    for expected in contract["views"].values():
        shape(expected, {"run_ref", "sources", "basis_ref"})
        require(all(expected[k] is None or text(expected[k]) for k in ("run_ref", "basis_ref")), "Invalid view basis")
        require(expected["sources"] is None or isinstance(expected["sources"], dict), "Invalid expected source inventory")
        for name, checksum in (expected["sources"] or {}).items():
            require(text(name) and (checksum is None or (isinstance(checksum, str) and len(checksum) == 64 and
                    all(c in "0123456789abcdef" for c in checksum))), "Invalid expected source digest")
    require(contract["obligations"] is None or isinstance(contract["obligations"], list), "Invalid invariant obligations")
    ids = []
    for item in contract["obligations"] or []:
        shape(item, {"cell_id", "owner_ref", "basis_ref"})
        require(text(item["cell_id"]) and all(item[k] is None or text(item[k]) for k in ("owner_ref", "basis_ref")), "Invalid invariant obligation")
        ids.append(item["cell_id"])
    require(len(set(ids)) == len(ids), "Duplicate invariant obligation")
    shape(evidence, {"format", "contract_sha256", "concrete", "abstract"})
    require(evidence["format"] == "opentools.abstraction-evidence.v1", "Unsupported evidence format")
    findings, gaps, observations, native = [], [], {}, {}
    if evidence["contract_sha256"] != digest(contract):
        gaps.append("Evidence is stale/foreign to the independent contract; conclusions quarantined")
        return result(contract, evidence, findings, gaps, observations, native)
    if not text(contract["owner_ref"]) or any(not text(v) for v in contract["scope"].values()):
        gaps.append("Review owner or independent scope basis missing")
    if allowed is None or not all(text(contract["property"][k]) for k in ("ref", "basis_ref")):
        gaps.append("Independent selected property truth relation/basis is missing")
    views = {}
    from yosys_capture import revalidate
    for name in ("concrete", "abstract"):
        snapshot = evidence[name]
        if snapshot is None:
            gaps.append(name + ": native evidence missing")
            continue
        try:
            revalidate(snapshot, root)
        except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
            gaps.append(name + ": native integrity/reader unresolved: " + str(exc))
            continue
        wanted = contract["views"][name]
        if not all(text(wanted[k]) for k in ("run_ref", "basis_ref")) or wanted["sources"] is None:
            gaps.append(name + ": independent original run/source basis missing")
            continue
        mismatches, unknown = [], []
        for key, observed, expected in (("run", snapshot["run_ref"], wanted["run_ref"]), ("sources", snapshot["sources"], wanted["sources"]),
                                        ("scope", snapshot["scope"], contract["scope"]), ("domain", snapshot["domain"], contract["domain"]),
                                        ("property", snapshot["property_ref"], contract["property"]["ref"])):
            if not known(observed) or not known(expected):unknown.append(key)
            elif canonical(observed) != canonical(expected):mismatches.append(key)
        if unknown:gaps.append(name + ": missing original correspondence: " + ", ".join(unknown))
        if mismatches:
            findings.append(name + ": foreign/different " + ", ".join(mismatches) + "; native conclusions quarantined")
            continue
        if unknown:continue
        if snapshot["dependency_capture_complete"] is not True or not text(snapshot["dependency_basis_ref"]) or not snapshot["original_command"]:
            gaps.append(name + ": original command/dependency capture is not established")
            continue
        rows = relation(snapshot["rows"], widths)
        if not rows:
            gaps.append(name + ": empty relation cannot establish an applicable environment")
        views[name] = rows
        native[name] = {k: snapshot[k] for k in ("run_ref", "outcome", "witness", "cutpoints", "assumption_cells", "cone_ports")}
        native[name]["rows"] = len(rows)
        if allowed is not None:
            failures = rows - allowed
            if snapshot["outcome"] == "pass" and failures:
                findings.append(name + ": native property PASS conflicts with the independent required property relation")
            if snapshot["outcome"] == "fail":
                witness = tuple(snapshot["witness"]) if snapshot["witness"] is not None else None
                if witness not in rows or witness not in failures:
                    gaps.append(name + ": native failure witness does not demonstrate the required property in its captured relation")
            if snapshot["outcome"] not in ("pass", "fail"):
                gaps.append(name + ": native property observation unresolved")
    if "concrete" in native and (native["concrete"]["cutpoints"] or native["concrete"]["assumption_cells"]):
        gaps.append("Concrete reference is outside the assumption-free/no-cut first profile")
    if "abstract" in native:
        if not native["abstract"]["cutpoints"]:
            gaps.append("Selected abstract view has no native cutpoint record in the first profile")
        actual_ids = {c["id"] for c in native["abstract"]["assumption_cells"]}
        if contract["obligations"] is None:
            gaps.append("Invariant ownership/correspondence obligation inventory is missing")
        elif set(ids) != actual_ids:
            findings.append("Invariant obligation inventory differs from native abstract assumption population")
        for item in contract["obligations"] or []:
            if not text(item["owner_ref"]) or not text(item["basis_ref"]):
                gaps.append(item["cell_id"] + ": invariant owner/correspondence basis missing")
    if set(views) == {"concrete", "abstract"}:
        c, a = views["concrete"], views["abstract"]
        missing, added = sorted(c - a), sorted(a - c)
        direction = "equal" if c == a else "conservative_expansion" if not missing else "restrictive_subset" if not added else "incomparable"
        observations.update(relation_direction=direction, excludes_concrete=[list(v) for v in missing], adds_abstract=[list(v) for v in added],
                            concrete_included=not missing, boundary_scope="Complete selected stateless finite tuples only; not a sequential simulation relation")
        if missing:findings.append("Abstract relation excludes concrete behavior at the selected finite boundary")
        if native["abstract"]["outcome"] == "fail":
            witness = tuple(native["abstract"]["witness"] or [])
            classification = "feasible_in_selected_concrete_relation" if witness in c else "absent_from_selected_concrete_relation" if witness in a else "unresolved"
            observations["abstract_witness_classification"] = classification
            findings.append("Abstract property has a native counterexample; " + classification + " (not an automatic concrete design failure)")
        elif native["abstract"]["outcome"] != "pass":
            gaps.append("Selected abstract property is not proved")
    return result(contract, evidence, findings, gaps, observations, native)


def result(contract, evidence, findings, gaps, observations, native):
    return {"format": "opentools.abstraction-review.v1", "status": "review_required" if findings else "incomplete" if gaps else "supported_within_finite_boundary",
            "review_ref": contract["review_ref"], "claim": contract["claim"], "scope_ref": contract["scope_ref"],
            "observations": observations, "native": native, "findings": findings, "gaps": gaps,
            "fingerprints": {"contract": digest(contract), "evidence": digest(evidence)},
            "limits": "Advisory pointwise inclusion for the complete declared combinational relation and selected property. Native cones are structural observations, not sufficiency. Sources, owners, semantic mappings and completeness declarations need review; no arbitrary abstraction soundness, sequential refinement, liveness, memory model, proof acceptance or signoff claim."}


def exit_code(report):
    return {"supported_within_finite_boundary": 0, "review_required": 1, "incomplete": 2}[report["status"]]


def markdown(report):
    def esc(value):return html.escape(str(value)).replace("|", "&#124;").replace("\n", "<br>")
    lines = ["# Abstraction boundary review", "", "Status: **" + report["status"] + "**", "", esc(report["claim"]), ""]
    if report["observations"]:lines += ["Relation: " + esc(report["observations"].get("relation_direction")) + ".", ""]
    lines += ["| View | Native property | Tuples | Cut outputs |", "|---|---|---:|---|"]
    for name, row in report["native"].items():lines.append("| " + " | ".join(map(esc, (name, row["outcome"], row["rows"], row["cutpoints"]))) + " |")
    for label, key in (("Findings", "findings"), ("Missing evidence", "gaps")):
        lines += ["", "## " + label, ""] + (["- " + esc(v) for v in report[key]] or ["None within this profile."])
    return "\n".join(lines + ["", esc(report["limits"]), ""])
