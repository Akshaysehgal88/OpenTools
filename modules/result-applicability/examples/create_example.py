#!/usr/bin/env python3
"""Create a self-contained synthetic passing result and ECC-enabled request."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def fact(value, ref="synthetic:retained-run-manifest"):
    return {"value": value, "evidence_ref": ref}


def records(result_path="result.txt"):
    result = b"SYNTHETIC run:A data-integrity regression PASS; ECC_EN=0\n"
    fields = {"design.ref": fact("rtl:source-A"), "configuration.ECC_EN": fact(0),
              "build.executable_ref": fact("sha256:synthetic-simulator-A"),
              "checker.ref": fact("checker:data-integrity-v2"),
              "runtime.inputs_ref": fact({"seed": 17, "firmware": "sha256:synthetic-fw-A"}),
              "scope.ref": fact("regression:selected-data-integrity"),
              "runtime.trace_level": fact("off")}
    snapshot = {"format": "opentools.result-snapshot.v1", "run_ref": "run:A", "manifest_ref": "synthetic:manifest-A",
                "execution": {"state": "completed", "evidence_ref": "synthetic:runner-A#completed",
                              "command": ["simulator-A", "+seed=17"], "executable_ref": "sha256:synthetic-simulator-A",
                              "dependency_capture_complete": True, "dependency_evidence_ref": "synthetic:input-inventory-A"},
                "result": {"outcome": "pass", "native_status": "PASS", "complete": True, "producer_run_ref": "run:A",
                           "evidence_ref": "synthetic:checker-result-A", "artifact": {"path": result_path,
                           "sha256": hashlib.sha256(result).hexdigest()}}, "fields": fields}
    requested = {key: fact(copy.deepcopy(value["value"]), "synthetic:handoff-request") for key, value in fields.items() if key != "runtime.trace_level"}
    requested["configuration.ECC_EN"] = fact(1, "synthetic:handoff-request")
    request = {"format": "opentools.result-request.v1", "claim_id": "ecc-enabled-regression", "scope_ref": "handoff:ECC-enabled",
               "claim": "The ECC-enabled configuration passed the selected data-integrity regression.",
               "required_fields": requested, "required_outcome": "pass"}
    return snapshot, request, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    args = parser.parse_args()
    target = Path(args.directory)
    target.mkdir(parents=True, exist_ok=False)
    snapshot, request, result = records()
    (target / "result.txt").write_bytes(result)
    for name, value in (("snapshot", snapshot), ("request", request)):
        (target / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
