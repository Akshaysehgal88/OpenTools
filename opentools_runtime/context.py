"""Optional, scoped context consumption; independent of inference and DVIT SDKs."""
from __future__ import annotations

import json
import subprocess

from .common import canonical, digest, parse_json, read_json, require, shape, text

PROTOCOL = "opentools.context.v1"


def make_request(source_id, source_type, module, question, scope, evidence=None, capability="context", action="query"):
    request = {"format": "opentools.context-request.v1", "protocol": PROTOCOL, "action": action,
               "source_id": source_id, "source_type": source_type, "module": module,
               "capability": capability, "question": question, "scope": scope,
               "evidence": evidence if evidence is not None else []}
    request["request_id"] = digest(request)
    validate_request(request)
    return request


def validate_request(request):
    shape(request, {"format", "protocol", "action", "source_id", "source_type", "module", "capability", "question", "scope", "evidence", "request_id"})
    require(request["format"] == "opentools.context-request.v1" and request["protocol"] == PROTOCOL, "Unsupported context request protocol")
    require(request["action"] in ("capabilities", "query"), "Unsupported context action")
    require(all(text(request[k]) for k in ("source_id", "source_type", "module", "capability", "question")), "Context request identities and question required")
    require(isinstance(request["scope"], dict) and request["scope"], "Explicit nonempty scope object required")
    require(isinstance(request["evidence"], list), "evidence must be a list")
    for entry in request["evidence"]:
        shape(entry, {"ref", "revision_ref"})
        require(text(entry["ref"]) and (entry["revision_ref"] is None or text(entry["revision_ref"])), "Evidence identity required; retain missing revision as null")
    require(request["request_id"] == digest({key: value for key, value in request.items() if key != "request_id"}), "Context request content binding differs")


def consume(request, reply):
    validate_request(request)
    shape(reply, {"format", "protocol", "request_id", "source", "status", "scope", "capabilities", "observations", "questions", "seeds", "helpers", "unknowns"})
    require(reply["format"] == "opentools.context-reply.v1" and reply["protocol"] == PROTOCOL, "Unsupported context reply protocol")
    require(reply["request_id"] == request["request_id"] and canonical(reply["scope"]) == canonical(request["scope"]), "Reply does not bind the exact request and scope")
    shape(reply["source"], {"id", "type", "version"})
    require(reply["source"]["id"] == request["source_id"] and reply["source"]["type"] == request["source_type"] and text(reply["source"]["version"]), "Unexpected source identity/version")
    require(reply["status"] in ("ok", "partial", "unavailable"), "Invalid source status")
    for key in ("capabilities", "observations", "questions", "seeds", "helpers", "unknowns"):
        require(isinstance(reply[key], list), f"{key} must be a list")
    require(all(text(v) for v in reply["unknowns"]), "Unknowns must be explicit text")
    identifiers = {}
    for key in ("capabilities", "observations", "questions", "seeds", "helpers"):
        seen = set()
        for entry in reply[key]:
            require(isinstance(entry, dict) and text(entry.get("id")) and entry["id"] not in seen, f"Unique {key} IDs required")
            seen.add(entry["id"])
        identifiers[key] = seen
    for item in reply["capabilities"]:
        shape(item, {"id", "kind", "description"})
        require(item["kind"] in ("context", "evidence", "seed", "helper") and text(item["description"]), "Invalid capability description")
    for item in reply["observations"]:
        shape(item, {"id", "text", "status", "source_ref", "revision_ref"})
        require(item["status"] in ("observation", "proposal", "unknown") and text(item["text"]), "Observation/proposal/unknown must remain distinct")
        require(item["source_ref"] is None or text(item["source_ref"]), "Invalid observation source")
        require(item["revision_ref"] is None or text(item["revision_ref"]), "Invalid observation revision")
    for item in reply["questions"]:
        shape(item, {"id", "text", "reason"})
        require(text(item["text"]) and text(item["reason"]), "Question and reason required")
    for item in reply["seeds"]:
        shape(item, {"id", "description", "content", "source_ref", "revision_ref"})
        require(text(item["description"]) and text(item["content"]) and text(item["source_ref"]), "Seed content/source required")
        require(item["revision_ref"] is None or text(item["revision_ref"]), "Invalid seed revision")
    for item in reply["helpers"]:
        shape(item, {"id", "description", "capability_id", "source_ref"})
        helper_capabilities = {v["id"] for v in reply["capabilities"] if v["kind"] == "helper"}
        require(text(item["description"]) and text(item["source_ref"]) and text(item["capability_id"])
                and item["capability_id"] in helper_capabilities, "Helper must reference a declared helper capability")
    if request["action"] == "query" and reply["status"] != "unavailable":
        require(request["capability"] in identifiers["capabilities"], "Requested capability is not declared by this source")
    gaps = list(reply["unknowns"])
    for item in reply["observations"]:
        if not item["source_ref"] or not item["revision_ref"] or item["status"] == "unknown":
            gaps.append(f"Unestablished observation basis: {item['id']}")
    for item in reply["seeds"]:
        if not item["revision_ref"]:
            gaps.append(f"Unversioned knowledge seed: {item['id']}")
    for item in request["evidence"]:
        if item["revision_ref"] is None:
            gaps.append(f"Unversioned request evidence: {item['ref']}")
    status = "unavailable" if reply["status"] == "unavailable" else "partial" if gaps or reply["status"] == "partial" else "available"
    return {"format": "opentools.context-consumption.v1", "status": status,
            "request": request, "reply": reply, "reply_digest": digest(reply), "gaps": gaps,
            "limits": "Content/scope binding and shape only; no authentication, freshness, engineering acceptance or arbitrary prose verification. Seeds/helper descriptions are source data, not installation or execution instructions."}


def configured_source(settings_path, source_id):
    settings = read_json(settings_path)
    shape(settings, {"format", "sources"})
    require(settings["format"] == "opentools.context-settings.v1" and isinstance(settings["sources"], list), "Unsupported context settings")
    sources = {}
    for source in settings["sources"]:
        shape(source, {"id", "type", "protocol", "enabled", "command", "timeout_seconds", "max_reply_bytes"})
        require(text(source["id"]) and source["id"] not in sources and text(source["type"]), "Unique configured source IDs/types required")
        require(source["protocol"] == PROTOCOL and type(source["enabled"]) is bool, "Invalid source protocol/enabled flag")
        require(isinstance(source["command"], list) and all(text(v) for v in source["command"]), "Command must be an argument array")
        require(not source["enabled"] or source["command"], "Enabled source needs an existing adapter command")
        require(type(source["timeout_seconds"]) in (int, float) and 0 < source["timeout_seconds"] <= 120, "Timeout must be positive, at most 120s")
        require(type(source["max_reply_bytes"]) is int and 0 < source["max_reply_bytes"] <= 16 * 1024 * 1024, "Reply budget must be 1 byte to 16 MiB")
        sources[source["id"]] = source
    require(source_id in sources, "Requested source is not configured")
    return sources[source_id]


def unavailable(request, reason):
    return {"format": "opentools.context-consumption.v1", "status": "unavailable", "request": request,
            "reply": None, "reply_digest": None, "gaps": [reason],
            "limits": "Optional context is unavailable. Continue with the user's ordinary workflow/evidence; do not invent source support or silently choose another provider."}


def ask(request, settings_path):
    validate_request(request)
    source = configured_source(settings_path, request["source_id"])
    require(source["type"] == request["source_type"], "Configured source type differs from request")
    if not source["enabled"]:
        return unavailable(request, "The optional source is disabled; nothing was executed or installed")
    try:
        process = subprocess.run(source["command"], input=(canonical(request) + "\n").encode("utf-8"),
                                 capture_output=True, timeout=source["timeout_seconds"], shell=False)
    except subprocess.TimeoutExpired:
        return unavailable(request, "Optional adapter timed out; no replacement provider was selected")
    except OSError:
        return unavailable(request, "Configured adapter could not be launched; no dependency was installed")
    if process.returncode != 0:
        return unavailable(request, f"Optional adapter exited {process.returncode}; source output was not treated as evidence")
    require(len(process.stdout) <= source["max_reply_bytes"], "Context reply exceeds the selected budget; no truncation or partial admission")
    try:
        reply = parse_json(process.stdout.decode("utf-8-sig"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Optional adapter did not return valid protocol JSON") from exc
    return consume(request, reply)
