"""Read selected node timing/resource records from a pinned SC Project JSON profile."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from cost_core import (CONTEXT, number, pairs, require, shape, text,
                       validate_run)

PROFILE = "SiliconCompiler.0.38.11.schema-0.57.2.cost.v1"
NATIVE_METRICS = {"exetime": ("elapsed_time", "executable"), "tasktime": ("elapsed_time", "task"),
                  "totaltime": ("elapsed_time", "native-recorded-total"), "memory": ("peak_memory", "program")}


def get(document, *keys):
    value = document
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def source_pointer(sha, *keys):
    return "sha256:" + sha + "#/" + "/".join(str(k).replace("~", "~0").replace("/", "~1") for k in keys)


def global_value(document, *keys):
    leaf = get(document, *keys)
    require(isinstance(leaf, dict) and leaf.get("pernode") == "never", "Expected a global native parameter")
    explicit = get(leaf, "node", "*", "*")
    return explicit["value"] if isinstance(explicit, dict) and "value" in explicit else get(leaf, "node", "default", "default", "value")


def native_value(document, section, name, step, index):
    return get(document, section, name, "node", step, index, "value")


def read_native(path):
    raw = Path(path).read_bytes()
    document = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"Invalid native number: {value}")))
    return document, hashlib.sha256(raw).hexdigest()


def timestamp(value):
    if value is None:
        return None
    require(text(value), "Native time must be a string or null")
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)


def inventory(document, sha, path):
    require(isinstance(document, dict) and get(document, "__meta__", "class") == "siliconcompiler.project/Project", "Expected Project JSON, not a history/schema object")
    require(global_value(document, "schemaversion") == "0.57.2", "Only native schema 0.57.2 is qualified")
    ids = set()
    for name in ("status", "starttime", "endtime"):
        nodes = get(document, "record", name, "node")
        require(isinstance(nodes, dict), "Native record node map required")
        for step, indices in nodes.items():
            if step in ("default", "*"):
                continue
            require(text(step) and isinstance(indices, dict), "Invalid native step map")
            for index in indices:
                if index not in ("default", "*"):
                    ids.add((step, index))
    nodes = []
    for step, index in sorted(ids):
        record = {name: native_value(document, "record", name, step, index) for name in
                  ("starttime", "endtime", "status", "scversion", "toolversion", "toolpath", "toolexitcode", "machine")}
        require(record["scversion"] in (None, "0.38.11"), "Only producer 0.38.11 is qualified")
        require(all(record[k] is None or isinstance(record[k], str) for k in record if k != "toolexitcode"), "Invalid native string record")
        require(record["toolexitcode"] is None or type(record["toolexitcode"]) is int, "Invalid native exit code")
        start, end = timestamp(record["starttime"]), timestamp(record["endtime"])
        require(start is None or end is None or end >= start, "Native end precedes start on recorded UTC clock")
        metrics = {}
        for name in NATIVE_METRICS:
            value = native_value(document, "metric", name, step, index)
            require(value is None or (number(value) and value >= 0), "Invalid native metric value")
            unit = get(document, "metric", name, "unit")
            require(unit is None or text(unit), "Invalid native metric unit")
            metrics[name] = {"value": value, "unit": unit,
                             "evidence_ref": source_pointer(sha, "metric", name, "node", step, index, "value")}
        nodes.append({"step": step, "index": index, "record": record, "metrics": metrics,
                      "evidence_ref": source_pointer(sha, "record", "starttime", "node", step, index)})
    return {"profile": PROFILE, "manifest_sha256": sha, "manifest_path": str(Path(path).resolve()),
            "design": global_value(document, "option", "design"), "jobname": global_value(document, "option", "jobname"),
            "flow": global_value(document, "option", "flow"), "nodes": nodes,
            "limits": "Root node records only; no history search, CPU inference or complete outer-workflow/clock-synchronization claim. Native metrics remain separate observations."}


def inspect_manifest(path):
    document, sha = read_native(path)
    return inventory(document, sha, path)


def context_template(info):
    return {"format": "opentools.sc-cost-context.v1", "manifest_sha256": info["manifest_sha256"],
            "run_ref": "sc:" + info["manifest_sha256"], "task": "Audit the explicitly selected native node window",
            "clock_ref": None, "clock_evidence_ref": None, "scope_ref": None,
            "nodes": [{"step": n["step"], "index": n["index"], "stage": "native:" + n["step"] + "/" + n["index"], "accounting": "stage"} for n in info["nodes"]],
            "collection": {"complete": None, "evidence_ref": None},
            "completion": {"required_evidence_complete": None, "evidence_ref": None},
            "context": {key: {"value": None, "evidence_ref": None} for key in sorted(CONTEXT)}}


def import_manifest(manifest_path, context_path):
    document, sha = read_native(manifest_path)
    info = inventory(document, sha, manifest_path)
    context, context_sha = read_native(context_path)
    shape(context, {"format", "manifest_sha256", "run_ref", "task", "clock_ref", "clock_evidence_ref", "scope_ref", "nodes", "collection", "completion", "context"})
    require(context["format"] == "opentools.sc-cost-context.v1" and context["manifest_sha256"] == sha, "Context must bind these exact native manifest bytes")
    require(all(context[k] is None or text(context[k]) for k in ("clock_ref", "clock_evidence_ref", "scope_ref")), "Invalid clock/scope reference")
    shape(context["completion"], {"required_evidence_complete", "evidence_ref"})
    require(isinstance(context["nodes"], list), "Select an explicit node list")
    selected, seen = [], set()
    native = {(n["step"], n["index"]): n for n in info["nodes"]}
    for node in context["nodes"]:
        shape(node, {"step", "index", "stage", "accounting"})
        require(all(text(node[k]) for k in ("step", "index", "stage")) and node["step"] not in ("*", "default") and node["index"] not in ("*", "default"), "Explicit node/stage required")
        key = (node["step"], node["index"])
        require(key not in seen, "Duplicate selected node")
        seen.add(key)
        entry = native.get(key)
        if entry is None:
            entry = {"step": node["step"], "index": node["index"], "record": {}, "metrics": {}}
        selected.append((node, entry))
    starts = [timestamp(n["record"].get("starttime")) for _, n in selected]
    ends = [timestamp(n["record"].get("endtime")) for _, n in selected]
    points = [p for p in starts + ends if p is not None]
    origin = min(points) if points else None
    def relative(value):
        return (value - origin).total_seconds() if value is not None and origin is not None else None
    phases, resources, states = [], [], []
    for (node, entry), start, end in zip(selected, starts, ends):
        step, index = node["step"], node["index"]
        supported = entry["record"].get("scversion") == "0.38.11"
        phases.append({"id": step + "/" + index, "stage": node["stage"], "accounting": node["accounting"],
                       "start_s": relative(start), "end_s": relative(end), "basis": "measured" if supported else "unknown",
                       "evidence_ref": source_pointer(sha, "record", "starttime", "node", step, index) + ";" + source_pointer(sha, "record", "endtime", "node", step, index)})
        status, code = entry["record"].get("status"), entry["record"].get("toolexitcode")
        states.append("completed" if supported and status == "success" and code == 0 and start is not None and end is not None
                      else "failed" if status == "error" or (type(code) is int and code != 0) else "unknown")
        for name, (kind, scope) in NATIVE_METRICS.items():
            metric = entry["metrics"].get(name, {"value": None, "unit": None, "evidence_ref": source_pointer(sha, "metric", name, "node", step, index)})
            resources.append({"id": f"{step}/{index}:{name}", "kind": kind, "value": metric["value"], "unit": metric["unit"],
                              "definition_ref": "SiliconCompiler0.38.11:schema_support/metric.py:" + name,
                              "scope_ref": f"sc:{info['jobname']}:{step}/{index}:{scope}", "basis": "measured" if supported else "unknown",
                              "evidence_ref": metric["evidence_ref"]})
    outcome = "failed" if "failed" in states else "completed" if states and all(s == "completed" for s in states) else "unknown"
    clock = context["clock_ref"] if text(context["clock_evidence_ref"]) else None
    run = {"format": "opentools.cost-run.v1", "run_ref": context["run_ref"], "task": context["task"],
           "window": {"start_s": 0 if starts and all(p is not None for p in starts) else None,
                      "end_s": relative(max(ends)) if ends and all(p is not None for p in ends) else None,
                      "basis": "measured" if selected and all(n["record"].get("scversion") == "0.38.11" for _, n in selected) else "unknown",
                      "clock_ref": clock, "scope_ref": context["scope_ref"],
                      "evidence_ref": "sha256:" + sha + "#record;sha256:" + context_sha + "#clock-and-scope"},
           "collection": context["collection"], "completion": {"outcome": outcome, **context["completion"]},
           "phases": phases, "resources": resources, "simulation_progress": {"amount": None, "unit": None, "definition_ref": None, "scope_ref": None, "basis": "unknown", "evidence_ref": None},
           "context": context["context"], "provenance": {"profile": PROFILE, "manifest_sha256": sha, "context_sha256": context_sha,
            "origin_utc": origin.isoformat() if origin else None, "clock_evidence_ref": context["clock_evidence_ref"], "selected_native_nodes": [n for _, n in selected],
            "window_basis": "Minimum selected start to maximum selected end, only when all selected boundaries are present. Excludes outer preparation/queue/review; UTC coherence is supplied, not established by this reader."}}
    validate_run(run)
    return run
