"""Layer ECO/mode/mapping applicability over the existing result comparator."""
from __future__ import annotations
import html
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from applicability_core import InputError, audit, digest, require, shape, text, validate_fields
from yosys_equivalence import REQUIRED_FIELDS, revalidate


def review(intent, snapshot, root="."):
    shape(intent, {"format", "claim_id", "claim", "scope_ref", "eco_ref", "eco_intent_ref", "owner_ref", "run_ref",
                   "required_fields", "mode_input", "required_modes", "mode_basis_ref", "mapping_review"})
    require(intent["format"] == "opentools.equivalence-intent.v1", "Unsupported equivalence intent")
    require(all(text(intent[k]) for k in ("claim_id", "claim", "scope_ref", "eco_ref")), "Claim/ECO scope required")
    require(all(intent[k] is None or text(intent[k]) for k in ("eco_intent_ref", "owner_ref", "run_ref", "mode_input", "mode_basis_ref")), "Invalid intent reference")
    validate_fields(intent["required_fields"])
    require(set(intent["required_fields"]) == REQUIRED_FIELDS, "Select all required design/mapping/model/engine/partition facts")
    modes = intent["required_modes"]
    require(modes is None or (isinstance(modes, list) and modes and all(type(v) is int and v in (0, 1) for v in modes) and modes == sorted(set(modes))), "Required modes must be sorted unique0/1 or null")
    mapping = intent["mapping_review"];shape(mapping, {"status", "reviewer_ref", "basis_ref"})
    require(mapping["status"] in ("approved", "proposed", "unknown") and all(mapping[k] is None or text(mapping[k]) for k in ("reviewer_ref", "basis_ref")), "Invalid mapping review evidence")
    findings, gaps = [], []
    report = {"format": "opentools.equivalence-review.v1", "claim_id": intent["claim_id"], "claim": intent["claim"], "scope_ref": intent["scope_ref"],
              "eco_ref": intent["eco_ref"], "comparison": None, "native": None, "findings": findings, "gaps": gaps,
              "fingerprints": {"intent": digest(intent), "snapshot": digest(snapshot)},
              "limits": "Applicability of one original native whole-miter combinational equivalence result to the declared ECO, reviewed mapping and required modes. References/approvals/dependency completeness are supplied, not authenticated. No new engine, automatic matching, sequential/reset/memory refinement, ECO acceptance or signoff."}
    def finish():
        report["status"] = "review_required" if findings else "incomplete" if gaps else "native_result_supports_declared_equivalence_scope"
        return report
    if not text(intent["owner_ref"]) or not text(intent["eco_intent_ref"]):gaps.append("Independent ECO intent or receiving owner missing")
    if mapping["status"] != "approved" or not text(mapping["reviewer_ref"]) or not text(mapping["basis_ref"]):
        gaps.append("Existing approved compare-point/input mapping evidence is not established; do not invent approval")
    try:
        revalidate(snapshot, root)
        request = {"format": "opentools.result-request.v1", "claim_id": intent["claim_id"], "claim": intent["claim"], "scope_ref": intent["scope_ref"],
                   "required_fields": intent["required_fields"], "required_outcome": "any_observed"}
        compared = audit(snapshot, request, base_dir=root);report["comparison"] = compared
    except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
        gaps.append("Original native evidence/reader unresolved: " + str(exc));return finish()
    context = snapshot["provenance"]["context"]
    if not text(intent["run_ref"]):gaps.append("Original requested run identity missing");return finish()
    if intent["run_ref"] != snapshot["run_ref"] or intent["eco_ref"] != context["eco_ref"]:
        findings.append("Native run/ECO identity is foreign to the request; native conclusions quarantined");return finish()
    if compared["mismatches"]:
        findings.extend(v + "; native conclusions quarantined" for v in compared["mismatches"])
        gaps.extend(compared["unknowns"]);return finish()
    if compared["unknowns"]:gaps.extend(compared["unknowns"]);return finish()
    if not text(context["scope_basis_ref"]):gaps.append("Original compared-model scope basis missing")
    restriction = snapshot["fields"]["mode_constraint"]["value"]
    if not text(intent["mode_input"]):gaps.append("Independent requested mode input missing");return finish()
    if intent["mode_input"] != restriction["signal"]:gaps.append("Requested mode input differs from the original capture selector; no scope mapping is inferred");return finish()
    allowed = restriction["allowed_values"]
    native = {"outcome": snapshot["result"]["outcome"], "status": snapshot["result"]["native_status"],
              "partition": snapshot["fields"]["partition"]["value"], "allowed_modes": allowed,
              "proof_kind": snapshot["fields"]["engine_profile"]["value"]["proof_kind"],
              "counterexample": snapshot["provenance"]["native_counterexample"]}
    report["native"] = native
    if modes is None or not text(intent["mode_basis_ref"]):
        gaps.append("Independent required mode/constraint basis missing");return finish()
    missing = sorted(set(modes) - set(allowed));native["required_modes"] = modes;native["excluded_required_modes"] = missing
    if missing:findings.append("Native restriction excludes required functional modes: " + ", ".join(map(str, missing)))
    if native["outcome"] == "fail":
        cex = native["counterexample"]
        if cex is None:gaps.append("Native failure counterexample missing")
        elif cex[intent["mode_input"]] in modes:
            findings.append("Native equivalence counterexample is within the requested mode scope")
        else:gaps.append("Native failure witness is outside the requested modes; it neither refutes nor proves their equivalence")
    elif native["outcome"] != "pass":gaps.append("Native equivalence is not established")
    return finish()


def exit_code(report):return {"native_result_supports_declared_equivalence_scope": 0, "review_required": 1, "incomplete": 2}[report["status"]]


def markdown(report):
    def esc(v):return html.escape(str(v)).replace("|", "&#124;").replace("\n", "<br>")
    lines = ["# Equivalence comparison boundary", "", "Status: **" + report["status"] + "**", "", esc(report["claim"]), ""]
    if report["native"]:
        n = report["native"];lines += ["Original native outcome: **" + n["status"] + "**; partition " + esc(n["partition"]["id"]) + ".", "",
                                      "Native allowed modes: " + esc(n["allowed_modes"]) + ". Required modes: " + esc(n.get("required_modes", "unknown")) + ".", ""]
    for title, key in (("Findings", "findings"), ("Missing evidence", "gaps")):
        lines += ["## " + title, ""] + (["- " + esc(v) for v in report[key]] or ["None within this profile."]) + [""]
    return "\n".join(lines + [esc(report["limits"]), ""])
