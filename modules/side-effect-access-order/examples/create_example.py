"""Owned W1C and read-clear fixtures with independent intent rules."""
import argparse
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from access_core import digest, require

SCOPE = {"project": "register-example", "configuration": "two-causes", "mode": "functional", "address_space_ref": "register-offsets"}
CASES = ("rmw", "direct-mask", "disabled-low-byte", "diagnostic-peek", "diagnostic-consume")


def spec():
    result = {"format": "opentools.access.spec.v1", "scope": copy.deepcopy(SCOPE), "basis_ref": "unbuffered-effects-v1", "inputs_complete": True, "registers": []}
    for name, address, sw, onread, onwrite in (("pending", 0, "rw", "none", "one_clear"), ("diagnostic", 4, "r", "clear", "none")):
        result["registers"].append({"id": "effects." + name, "address": address, "width": 32, "access_width": 32,
            "evidence_ref": "effects.rdl:" + name, "fields": [{"name": "causes", "lsb": 0, "width": 2, "sw": sw,
            "onread": onread, "onwrite": onwrite, "reset": 0, "evidence_ref": "effects.rdl:" + name + ".causes"}]})
    return result


def event(seq, name, kind, before, after, data=0, be=0, read=0):
    return {"seq": seq, "register_ref": "effects." + name, "kind": kind, "accepted": True, "error": False,
            "hardware_quiet": True, "reset_inactive": True, "before": before, "after": after,
            "write_data": data if kind == "write" else None, "byte_enable": be if kind == "write" else None,
            "bit_enable": sum(255 << (i * 8) for i in range(4) if be & (1 << i)) if kind == "write" else None,
            "read_data": read if kind == "read" else None, "evidence_ref": "access_tb.sv:sampled-access",
            "operation_ref": "caller-intent:" + name}


def trace_for(record, events):
    return {"format": "opentools.access.trace.v1", "scope": copy.deepcopy(record["scope"]), "basis_ref": record["basis_ref"],
            "inputs_complete": True, "spec_sha256": digest(record), "state_basis": "selected-field-storage", "events": events}


def policy_for(record, trace, case):
    # Intent is independent of observed state: acknowledge only cause 0, or explicitly consume diagnostics.
    rules = []
    for item in trace["events"]:
        destructive_consume = case == "diagnostic-consume"
        acknowledgement = item["kind"] == "write"
        allowed = 3 if destructive_consume else 1 if acknowledgement else 0
        rules.append({"seq": item["seq"], "allowed_clear_mask": allowed, "required_clear_mask": allowed,
                      "observation_only": not acknowledgement and not destructive_consume,
                      "after_seq": [1] if case == "rmw" and item["seq"] == 2 else [],
                      "evidence_ref": "create_example.py:policy_for:caller-requests-cause-0-or-diagnostic-consume"})
    return {"format": "opentools.access.policy.v1", "scope": copy.deepcopy(record["scope"]), "basis_ref": record["basis_ref"],
            "inputs_complete": True, "spec_sha256": digest(record), "trace_sha256": digest(trace), "events": rules}


def example(case="direct-mask"):
    require(case in CASES, "Unknown example case")
    record = spec()
    if case == "rmw":
        events = [event(1, "pending", "read", 3, 3, read=3), event(2, "pending", "write", 3, 0, data=3, be=1)]
    elif case in ("direct-mask", "disabled-low-byte"):
        events = [event(1, "pending", "write", 3, 2 if case == "direct-mask" else 3, data=1, be=1 if case == "direct-mask" else 2)]
    else:
        events = [event(1, "diagnostic", "read", 3, 0, read=3)]
    trace = trace_for(record, events)
    return record, trace, policy_for(record, trace, case)


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--case", choices=CASES, default="direct-mask")
    args = parser.parse_args()
    output = Path(args.directory)
    output.mkdir(parents=True, exist_ok=False)
    for name, value in zip(("spec", "trace", "policy"), example(args.case)):
        save(output / (name + ".json"), value)


if __name__ == "__main__":
    main()
