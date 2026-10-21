"""Review one proof's premises, required activation and producer support."""
from __future__ import annotations

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from applicability_core import InputError, audit, canonical, digest, require, shape, text
from sby_capture import SCOPE_KEYS, revalidate


def fields(model):
    return {name: {"value": model[name], "evidence_ref": model["basis_ref"]}
            for name in ("sources", "top", "scope", "cells")}


def validate_model(model, consumer=False):
    required = {"sources", "top", "scope", "cells", "basis_ref"}
    required |= {"property_ref", "activation_ref", "assumptions"} if consumer else {"condition_ref", "owner_ref", "port_binding_ref"}
    shape(model, required)
    require(text(model["basis_ref"]), "Independent model basis reference required")
    require(model["top"] is None or text(model["top"]), "Invalid top")
    if model["scope"] is not None:
        shape(model["scope"], SCOPE_KEYS)
        require(all(v is None or text(v) for v in model["scope"].values()), "Invalid model scope")
    if model["sources"] is not None:
        require(isinstance(model["sources"], dict) and model["sources"], "Invalid source inventory")
        for name, checksum in model["sources"].items():
            require(text(name) and (checksum is None or (isinstance(checksum, str) and len(checksum) == 64 and
                    all(c in "0123456789abcdef" for c in checksum))), "Invalid source digest")
    if model["cells"] is not None:
        require(isinstance(model["cells"], list), "Invalid cell inventory")
        ids = []
        for cell in model["cells"]:
            shape(cell, {"id", "type", "source"})
            require(text(cell["id"]) and text(cell["source"]) and cell["type"] in ("$assert", "$assume", "$cover"), "Invalid formal cell")
            ids.append(cell["id"])
        require(len(ids) == len(set(ids)), "Duplicate formal cell")
        require(model["cells"] == sorted(model["cells"], key=lambda c: c["id"]), "Sort cells by native id")
    if consumer:
        require(all(model[k] is None or text(model[k]) for k in ("property_ref", "activation_ref")), "Invalid obligation reference")
        if model["assumptions"] is not None:
            require(isinstance(model["assumptions"], list), "Invalid assumption mapping")
            ids = []
            for item in model["assumptions"]:
                shape(item, {"cell_id", "condition_ref", "owner_ref", "support_ref"})
                require(text(item["cell_id"]) and all(item[k] is None or text(item[k]) for k in ("condition_ref", "owner_ref", "support_ref")),
                        "Invalid assumption link")
                ids.append(item["cell_id"])
            require(len(ids) == len(set(ids)), "Duplicate assumption link")
    else:
        require(all(model[k] is None or text(model[k]) for k in ("condition_ref", "owner_ref", "port_binding_ref")), "Invalid guarantee basis")


def review(spec, evidence, root="."):
    shape(spec, {"format", "scope_ref", "claim_ref", "claim", "owner_ref", "consumer", "guarantees", "run_refs"})
    require(spec["format"] == "opentools.formal-assumption-scope.v1", "Unsupported review scope")
    require(all(text(spec[k]) for k in ("scope_ref", "claim_ref", "claim")), "Claim/scope required")
    require(spec["owner_ref"] is None or text(spec["owner_ref"]), "Invalid claim owner")
    validate_model(spec["consumer"], True)
    require(isinstance(spec["guarantees"], dict) and all(text(k) for k in spec["guarantees"]), "Invalid guarantee inventory")
    for model in spec["guarantees"].values():
        validate_model(model)
    shape(spec["run_refs"], {"proof", "cover", "guarantees"})
    require(all(spec["run_refs"][k] is None or text(spec["run_refs"][k]) for k in ("proof", "cover")), "Invalid run reference")
    require(isinstance(spec["run_refs"]["guarantees"], dict) and set(spec["run_refs"]["guarantees"]) == set(spec["guarantees"]) and
            all(v is None or text(v) for v in spec["run_refs"]["guarantees"].values()), "Guarantee run references must match inventory")
    shape(evidence, {"format", "scope_sha256", "proof", "cover", "guarantees"})
    require(evidence["format"] == "opentools.formal-assumption-evidence.v1", "Unsupported evidence bundle")
    require(isinstance(evidence["guarantees"], dict) and set(evidence["guarantees"]) <= set(spec["guarantees"]), "Undeclared guarantee run")
    findings, gaps, rows, comparisons = [], [], [], {}
    if evidence["scope_sha256"] != digest(spec):
        gaps.append("Evidence bundle is stale or foreign to this scope; native conclusions quarantined")
        return result(spec, evidence, findings, gaps, rows, comparisons)
    if not text(spec["owner_ref"]):
        gaps.append("Claim owner is missing")

    def inspect(name, snapshot, model, wanted_run, role):
        if snapshot is None:
            gaps.append(name + ": retained native evidence missing")
            return None
        try:
            revalidate(snapshot, root)
            request = {"format": "opentools.result-request.v1", "claim_id": spec["claim_ref"] + ":" + name,
                       "claim": spec["claim"], "scope_ref": spec["scope_ref"], "required_fields": fields(model),
                       "required_outcome": "any_observed"}
            compared = audit(snapshot, request, base_dir=root)
        except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
            gaps.append(name + ": native integrity/reader unresolved: " + str(exc))
            return None
        comparisons[name] = compared
        if not text(wanted_run):
            gaps.append(name + ": original requested run identity missing")
            return None
        if wanted_run != snapshot["run_ref"]:
            findings.append(name + ": foreign run identity; native conclusions quarantined")
            return None
        if compared["mismatches"]:
            findings.extend(name + ": " + v + "; native conclusions quarantined" for v in compared["mismatches"])
            gaps.extend(name + ": " + v for v in compared["unknowns"])
            return None
        if compared["unknowns"]:
            gaps.extend(name + ": " + v for v in compared["unknowns"])
            return None
        f = {k: v["value"] for k, v in snapshot["fields"].items()}
        counts = {kind: sum(c["type"] == kind for c in f["cells"]) for kind in ("$assert", "$cover", "$assume")}
        required = {"$assert": 1, "$cover": 1} if role == "consumer" else {"$assert": 1, "$cover": 0, "$assume": 0}
        if any(counts[k] != v for k, v in required.items()):
            gaps.append(name + ": outside the one-property/one-activation or assumption-free producer profile")
            return None
        rows.append({"run": name, "run_ref": snapshot["run_ref"], "mode": f["mode"], "depth": f["depth"],
                     "native_status": snapshot["result"]["native_status"], "semantics": f["semantics"],
                     "formal_cells": counts, "witnesses": snapshot["provenance"]["witnesses"]})
        return f

    model = spec["consumer"]
    for key in ("property_ref", "activation_ref"):
        if not text(model[key]):
            gaps.append("Required consumer " + key + " is missing")
    proof = inspect("proof", evidence["proof"], model, spec["run_refs"]["proof"], "consumer")
    cover = inspect("cover", evidence["cover"], model, spec["run_refs"]["cover"], "consumer")
    if proof:
        if proof["mode"] not in ("prove", "bmc"):
            findings.append("Selected proof run is a cover task")
        elif proof["semantics"] == "counterexample":
            findings.append("Consumer property has a native counterexample within the matched formal model")
        elif proof["semantics"] != "proved_within_model":
            gaps.append("Unbounded safety proof is not established; a BMC pass is bounded only")
    if cover:
        if cover["mode"] != "cover":
            findings.append("Selected activation run is not a cover task")
        elif cover["semantics"] != "activation_witness":
            gaps.append(f"Required activation has no witness through {cover['depth']} checked states; this does not establish universal unreachability")
    expected_assumptions = {c["id"] for c in model["cells"] or [] if c["type"] == "$assume"}
    links = model["assumptions"]
    if links is None:
        gaps.append("Assumption ownership/support inventory is missing")
        links = []
    if {item["cell_id"] for item in links} != expected_assumptions:
        findings.append("Assumption mapping does not match the complete selected formal-cell population")
    used = set()
    for item in links:
        label = item["cell_id"]
        if not text(item["owner_ref"]) or not text(item["condition_ref"]):
            gaps.append(label + ": assumption owner/condition basis missing")
        support = item["support_ref"]
        if support is None or support not in spec["guarantees"]:
            gaps.append(label + ": producer guarantee support is not established")
            continue
        used.add(support)
        guarantee = spec["guarantees"][support]
        if not text(guarantee["condition_ref"]) or guarantee["condition_ref"] != item["condition_ref"]:
            findings.append(label + ": linked guarantee condition differs or is missing")
        for key in ("owner_ref", "port_binding_ref"):
            if not text(guarantee[key]):
                gaps.append(support + ": producer " + key + " missing")
        for key in ("clock_ref", "reset_ref", "integration_mode_ref"):
            left, right = (model["scope"] or {}).get(key), (guarantee["scope"] or {}).get(key)
            if not text(left) or not text(right):
                gaps.append(support + ": clock/reset/mode correspondence missing: " + key)
            elif left != right:
                findings.append(support + ": producer clock/reset/mode differs: " + key)
        native = inspect("guarantee:" + support, evidence["guarantees"].get(support), guarantee,
                         spec["run_refs"]["guarantees"][support], "producer")
        if native:
            if native["mode"] != "prove" or native["semantics"] != "proved_within_model":
                if native["semantics"] == "counterexample":
                    findings.append(support + ": producer guarantee has a matched native counterexample")
                else:
                    gaps.append(support + ": an assumption-free producer safety proof is not established")
    return result(spec, evidence, findings, gaps, rows, comparisons, sorted(set(spec["guarantees"]) - used))


def result(spec, evidence, findings, gaps, rows, comparisons, unused=None):
    return {"format": "opentools.formal-assumption-review.v1", "status": "review_required" if findings else "incomplete" if gaps else "supported_within_declared_model",
            "claim": spec["claim"], "claim_ref": spec["claim_ref"], "scope_ref": spec["scope_ref"],
            "runs": rows, "findings": findings, "gaps": gaps, "comparisons": comparisons,
            "unselected_guarantees": unused or [], "fingerprints": {"scope": digest(spec), "evidence": digest(evidence)},
            "limits": "Advisory review of one conditional safety property and one required activation. Scope/owner/predicate/port links and dependency/tool declarations are supplied, not authenticated. Native source correspondence is not proof of composition, property sufficiency, physical clocks/resets, liveness or signoff. Never automatically remove assumptions or accept a proof."}


def exit_code(report):
    return {"supported_within_declared_model": 0, "review_required": 1, "incomplete": 2}[report["status"]]


def markdown(report):
    def esc(v):
        return html.escape(str(v)).replace("|", "&#124;").replace("\n", "<br>")
    lines = ["# Formal assumption applicability", "", "Status: **" + report["status"] + "**", "", esc(report["claim"]), "",
             "| Run | Mode | Depth (states) | Native status | Meaning |", "|---|---|---:|---|---|"]
    for row in report["runs"]:
        lines.append("| " + " | ".join(esc(row[k]) for k in ("run", "mode", "depth", "native_status", "semantics")) + " |")
    for title, key in (("Findings", "findings"), ("Missing evidence", "gaps")):
        lines.extend(["", "## " + title, ""] + (["- " + esc(v) for v in report[key]] or ["None within this profile."]))
    lines.extend(["", esc(report["limits"]), ""])
    return "\n".join(lines)
