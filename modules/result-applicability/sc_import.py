"""Read a qualified SiliconCompiler Project JSON profile without loading code."""
from __future__ import annotations

import os
import hashlib
import json
from pathlib import Path
import re

from applicability_core import (file_hash, read_json, pairs, require, shape, text,
                                validate_fields, validate_snapshot)

PROFILE = "SiliconCompiler.0.38.11.schema-0.57.2.Project.v1"


def read_native(path):
    data = Path(path).read_bytes()
    document = json.loads(data.decode("utf-8-sig"), object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"Invalid number: {value}")))
    return document, hashlib.sha256(data).hexdigest()


def pointer(document, path):
    require(isinstance(path, str) and path.startswith("/") and not re.search(r"~(?![01])", path),
            "Selector must be an absolute JSON pointer with valid escapes")
    value = document
    try:
        for part in path[1:].split("/"):
            key = part.replace("~1", "/").replace("~0", "~")
            if isinstance(value, list):
                require(key == "0" or (key.isdigit() and not key.startswith("0")), "Invalid array pointer index")
                value = value[int(key)]
            else:
                value = value[key]
        return value
    except (KeyError, IndexError, TypeError):
        return None


def escape(value):
    return value.replace("~", "~0").replace("/", "~1")


def global_value(document, keypath):
    prefix = "/" + "/".join(escape(v) for v in keypath)
    leaf = pointer(document, prefix)
    require(isinstance(leaf, dict) and leaf.get("pernode") == "never", "Expected a global native parameter")
    explicit = pointer(document, prefix + "/node/*/*")
    if isinstance(explicit, dict) and "value" in explicit:
        suffix = "/node/*/*/value"
    else:
        suffix = "/node/default/default/value"
    return pointer(document, prefix + suffix), prefix + suffix


def inspect_manifest(path, step, index):
    require(text(step) and text(index) and step not in ("default", "*") and index not in ("default", "*"),
            "Select an explicit native step and index")
    path = Path(path).resolve()
    document, manifest_sha256 = read_native(path)
    require(isinstance(document, dict) and isinstance(document.get("__meta__"), dict)
            and document["__meta__"].get("class") == "siliconcompiler.project/Project",
            "Expected a SiliconCompiler Project manifest, not a nested history or another schema class")
    version, _ = global_value(document, ["schemaversion"])
    require(version == "0.57.2", "Only schema 0.57.2 is qualified")
    source = "sha256:" + manifest_sha256
    fields = {}
    for key in ("design", "jobname", "flow"):
        value, location = global_value(document, ["option", key])
        fields["sc." + key] = {"value": value, "evidence_ref": source + "#" + location}
    for key in ("status", "toolexitcode", "toolpath", "toolargs", "toolversion", "scversion", "starttime", "endtime"):
        location = f"/record/{key}/node/{escape(step)}/{escape(index)}/value"
        fields["sc." + key] = {"value": pointer(document, location), "evidence_ref": source + "#" + location}
    for name, item in fields.items():
        if name != "sc.toolexitcode":
            require(item["value"] is None or isinstance(item["value"], str), f"Native field must be a string or null: {name}")
    require(fields["sc.toolexitcode"]["value"] is None or type(fields["sc.toolexitcode"]["value"]) is int,
            "Native exit code must be an integer or null")
    producer = fields["sc.scversion"]["value"]
    require(producer in (None, "0.38.11"), "Only producer 0.38.11 is qualified")
    fields["sc.step"] = {"value": step, "evidence_ref": source + "#selected-node"}
    fields["sc.index"] = {"value": index, "evidence_ref": source + "#selected-node"}
    validate_fields(fields)
    return {"profile": PROFILE, "manifest_sha256": source[7:], "manifest_path": str(path),
            "step": step, "index": index, "fields": fields,
            "limits": "Explicit selected-node records only. No history search, inferred pass, schema-code loading, current checkout substitution or dependency-completeness inference."}


def context_template(inventory):
    return {"format": "opentools.sc-result-context.v1", "manifest_sha256": inventory["manifest_sha256"],
            "step": inventory["step"], "index": inventory["index"],
            "run_ref": f"sc:{inventory['manifest_sha256']}/{inventory['step']}/{inventory['index']}",
            "selectors": {}, "fields": {},
            "execution": {"command": None, "executable_ref": None, "dependency_capture_complete": None, "dependency_evidence_ref": None},
            "result": {"outcome": "unknown", "native_status": None, "complete": None, "producer_run_ref": None,
                       "evidence_ref": None, "artifact": None}}


def import_manifest(manifest_path, context_path, output_path):
    context = read_json(context_path)
    shape(context, {"format", "manifest_sha256", "step", "index", "run_ref", "selectors", "fields", "execution", "result"})
    require(context["format"] == "opentools.sc-result-context.v1", "Unsupported context format")
    inventory = inspect_manifest(manifest_path, context["step"], context["index"])
    require(context["manifest_sha256"] == inventory["manifest_sha256"], "Context does not bind these manifest bytes")
    require(text(context["run_ref"]), "Explicit run reference required")
    fields = dict(inventory["fields"])
    require(isinstance(context["selectors"], dict), "selectors must be an object")
    validate_fields(context["fields"])
    require(not (set(fields) & (set(context["fields"]) | set(context["selectors"])))
            and not (set(context["fields"]) & set(context["selectors"])), "Cannot override or duplicate native/selective fields")
    document, second_sha256 = read_native(manifest_path)
    require(second_sha256 == inventory["manifest_sha256"], "Manifest changed during import")
    origins = {}
    for name, location in context["selectors"].items():
        require(text(name), "Selector field name required")
        fields[name] = {"value": pointer(document, location), "evidence_ref": "sha256:" + inventory["manifest_sha256"] + "#" + location}
        origins[name] = {"kind": "native_json_pointer", "pointer": location}
    fields.update(context["fields"])
    for name in context["fields"]:
        origins[name] = {"kind": "context_declaration"}
    execution = dict(context["execution"])
    shape(execution, {"command", "executable_ref", "dependency_capture_complete", "dependency_evidence_ref"})
    status = fields["sc.status"]["value"]
    code = fields["sc.toolexitcode"]["value"]
    ended = fields["sc.starttime"]["value"] and fields["sc.endtime"]["value"]
    require(code is None or type(code) is int, "Native tool exit code must be an integer or null")
    state = "completed" if producer_known(fields) and status == "success" and code == 0 and ended else "failed" if status == "error" else "unknown"
    execution.update(state=state, evidence_ref=fields["sc.status"]["evidence_ref"])
    result = dict(context["result"])
    # These are caller declarations, never derived from a successful tool exit.
    shape(result, {"outcome", "native_status", "complete", "producer_run_ref", "evidence_ref", "artifact"})
    if result["artifact"] is not None:
        shape(result["artifact"], {"path", "sha256"})
        require(text(result["artifact"]["path"]), "Artifact path required")
        artifact_path = (Path(context_path).resolve().parent / result["artifact"]["path"]).resolve()
        require(file_hash(artifact_path) == result["artifact"]["sha256"], "Result artifact differs from context identity")
        result["artifact"] = {"path": os.path.relpath(artifact_path, Path(output_path).resolve().parent), "sha256": result["artifact"]["sha256"]}
    snapshot = {"format": "opentools.result-snapshot.v1", "run_ref": context["run_ref"],
                "manifest_ref": "sha256:" + inventory["manifest_sha256"], "execution": execution,
                "result": result, "fields": fields,
                "provenance": {"profile": PROFILE, "manifest_path": str(Path(manifest_path).resolve()),
                               "context_sha256": file_hash(context_path), "field_origins": origins,
                               "context_fields_are_declarations": True}}
    validate_snapshot(snapshot)
    return snapshot


def producer_known(fields):
    return fields["sc.scversion"]["value"] == "0.38.11"
