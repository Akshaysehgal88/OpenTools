"""Read a qualified flat ORFS metadata profile; never execute Tcl or infer units."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

from ppa_core import COMMON, digest, index, number, pairs, require, text, validate_conditions, validate_snapshot

PROFILE = "ORFS.Metrics_2.1.2.finish.v1"
METRICS = {"finish__design__instance__area": "instance_area", "finish__design__instance__area__stdcell": "stdcell_area",
           "finish__design__die__area": "die_area", "finish__timing__setup__ws": "setup_slack"}
NATIVE = {"design_name": "run__flow__design", "platform_name": "run__flow__platform", "tool_ref": "run__flow__openroad_version",
          "flow_ref": "run__flow__scripts_commit", "reported_clocks": "constraints__clocks__details"}


def safe(value):
    if type(value) is float and not math.isfinite(value): return str(value)
    if isinstance(value, dict): return {k: safe(v) for k, v in value.items()}
    if isinstance(value, list): return [safe(v) for v in value]
    return value


def inspect(path):
    path = Path(path)
    if path.is_dir(): path = path / "metadata.json"
    raw = path.read_bytes()
    data = safe(json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=lambda value: value))
    require(isinstance(data, dict) and data.get("run__flow__metrics_version") == "Metrics_2.1.2", "Qualified ORFS reader requires flat Metrics_2.1.2 metadata")
    fingerprint = hashlib.sha256(raw).hexdigest()
    ref = "sha256:" + fingerprint
    conditions = {}
    for field, key in NATIVE.items():
        value = data.get(key)
        if value is None or (isinstance(value, str) and value in ("", "N/A", "ERR", "git not on PATH", "not a git repo")):
            value = None
        conditions[field] = {"value": value, "evidence_ref": ref + "#" + key if value is not None else None}
    validate_conditions(conditions)
    metrics = [{"id": kind, "key": key, "kind": kind, "raw_value": data.get(key),
                "numeric_value": data.get(key) if number(data.get(key)) else None, "evidence_ref": ref + "#" + key}
               for key, kind in METRICS.items() if key in data]
    require(metrics, "No supported finish-stage metric keys were found")
    return {"format": "opentools.orfs-inventory.v1", "profile": PROFILE, "metadata_sha256": fingerprint,
            "native_run_id": data.get("run__flow__uuid"), "conditions": conditions, "metrics": metrics,
            "platform_unit_labels": {k: v for k, v in data.items() if k.startswith("run__flow__platform__") and k.endswith("_units")},
            "limits": ["Unit labels are retained as metadata, not assumed to be the unit of every metric.",
                       "Clock details are not a complete interpretation of Tcl/SDC.",
                       "Synthesis hashes do not identify the final measured netlist."]}


def context_template(inventory):
    return {"format": "opentools.orfs-context.v1", "metadata_sha256": inventory["metadata_sha256"],
            "run_id": inventory["native_run_id"],
            "conditions": {key: {"value": None, "evidence_ref": None} for key in sorted(COMMON - {"stage", "tool_ref", "flow_ref"})},
            "artifacts": {}, "metrics": [{"id": m["id"], "key": m["key"], "scope_ref": None,
                                          "unit": None, "unit_evidence": None, "measurement_complete": False} for m in inventory["metrics"]]}


def import_metadata(path, context, context_dir):
    inventory = inspect(path)
    require(isinstance(context, dict) and set(context) == {"format", "metadata_sha256", "run_id", "conditions", "artifacts", "metrics"}, "Unexpected or missing ORFS context property")
    require(context["format"] == "opentools.orfs-context.v1" and context["metadata_sha256"] == inventory["metadata_sha256"], "ORFS context format/digest binding differs")
    validate_conditions(context["conditions"])
    require(isinstance(context["artifacts"], dict), "artifacts must map condition names to local files")
    reserved = set(NATIVE) | {"stage"}
    require(not (set(context["conditions"]) | set(context["artifacts"])) & reserved, "Context cannot override native metadata conditions or finish stage")
    require(not set(context["conditions"]) & set(context["artifacts"]), "Condition and artifact names must not overlap")
    conditions = {**inventory["conditions"], **context["conditions"]}
    artifact_sources = {}
    for name, filename in context["artifacts"].items():
        require(text(name) and text(filename), "Artifact names/paths must be nonempty")
        source = (Path(context_dir) / filename).resolve()
        fingerprint = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
        conditions[name] = {"value": fingerprint, "evidence_ref": fingerprint + "#declared-file"}
        artifact_sources[name] = {"path": str(source), "sha256": fingerprint}
    ref = "sha256:" + inventory["metadata_sha256"]
    conditions["stage"] = {"value": "finish", "evidence_ref": ref + "#finish-prefix"}
    selected = index(context["metrics"], "context metrics")
    require(selected, "Select at least one metric")
    metrics = []
    available = {m["key"]: m for m in inventory["metrics"]}
    for metric_id, entry in selected.items():
        require(set(entry) == {"id", "key", "scope_ref", "unit", "unit_evidence", "measurement_complete"}, "Unexpected metric context property")
        key = entry["key"]
        require(key in METRICS, "Native reader supports only the documented finish area/setup-slack keys; power needs an explicit normalized activity basis")
        native = available.get(key)
        metrics.append({"id": metric_id, "kind": METRICS[key], "definition_ref": PROFILE + ":" + key,
                        "scope_ref": entry["scope_ref"], "value": native["numeric_value"] if native else None,
                        "unit": entry["unit"], "unit_evidence": entry["unit_evidence"], "evidence_ref": ref + "#" + key,
                        "measurement_complete": entry["measurement_complete"], "conditions": conditions})
    snapshot = {"format": "opentools.ppa-snapshot.v1", "run_id": context["run_id"], "source_ref": ref, "context_ref": "sha256:" + digest(context),
                "metrics": metrics, "provenance": {"profile": PROFILE, "native_run_id": inventory["native_run_id"],
                    "artifact_sources": artifact_sources, "platform_unit_labels": inventory["platform_unit_labels"],
                    "raw_metrics": inventory["metrics"], "limits": inventory["limits"] + ["File hashes identify declared artifacts; they do not prove those files were consumed by the measured run."]}}
    validate_snapshot(snapshot)
    return snapshot
