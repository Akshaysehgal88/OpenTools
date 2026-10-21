"""Owned response/credit drain fixtures with an independent required-owner roster."""
import argparse
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quiescence_core import digest, require

CASES = ("power-local-only", "power-system-drain", "clock-local-only", "clock-system-drain", "power-no-isolation", "power-late-admission")
FIELDS = ("local_pending", "remote_pending", "ingress_closed", "drain_ack", "isolation_active", "clock_enable", "power_available", "accepted", "handed", "returned", "received", "domain_edges")


def config(case):
    require(case in CASES, "Unknown example")
    return {"local_only": case.endswith("local-only"), "power_mode": not case.startswith("clock"), "no_isolation": case == "power-no-isolation", "bad_admission": case == "power-late-admission"}


def inventory_for(case):
    # Observed resource definitions; policy roster below is maintained separately.
    power = config(case)["power_mode"]
    return {"format": "opentools.quiescence.inventory.v1", "scope": {"project": "quiescence-example", "configuration": case, "mode": "power-down" if power else "clock-stop", "transition_ref": "shutdown-1"},
        "basis_ref": "owned-settled-owner-census-v1", "inputs_complete": True, "owners": [
            {"id": "local-work", "owner_ref": "local-block", "unit": "request_slots", "counting_basis_ref": "accepted-not-handed-off", "evidence_ref": "quiescence_path.sv:local-pending"},
            {"id": "remote-work", "owner_ref": "response-owner" if power else "credit-owner", "unit": "response_slots" if power else "credit_returns", "counting_basis_ref": "handed-off-not-returned", "evidence_ref": "quiescence_path.sv:remote-pending"}]}


def required_owners(case):
    # Independent caller ownership contract. Do not derive this from an export.
    return [{"id": "local-work", "unit": "request_slots", "counting_basis_ref": "accepted-not-handed-off", "evidence_ref": "caller:admitted-local-work"},
            {"id": "remote-work", "unit": "credit_returns" if case.startswith("clock") else "response_slots", "counting_basis_ref": "handed-off-not-returned", "evidence_ref": "caller:external-return-obligation"}]


def journal_for(inventory, samples):
    return {"format": "opentools.quiescence.journal.v1", "scope": copy.deepcopy(inventory["scope"]), "basis_ref": inventory["basis_ref"], "inputs_complete": True,
        "inventory_sha256": digest(inventory), "window_ref": "root-ticks-0-through-11", "window_closed": True, "transition_isolated": True, "samples": samples}


def policy_for(inventory, journal, case):
    power = config(case)["power_mode"]
    stages = ["drain_ack", "clock_stop"] + (["power_remove"] if power else [])
    checks = []
    for stage in stages:
        predicates = [("transition_requested", True), ("ingress_closed", True)]
        if stage != "drain_ack": predicates.append(("drain_ack", True))
        if power and stage != "drain_ack": predicates.append(("isolation_active", True))
        if stage == "power_remove": predicates.append(("clock_available", False))
        checks.append({"milestone": stage, "owners": ["local-work", "remote-work"], "predicates": [
            {"control": key, "equals": value, "evidence_ref": "caller:shutdown-order:" + stage + ":" + key} for key, value in predicates], "evidence_ref": "caller:all-required-owners-drained:" + stage})
    return {"format": "opentools.quiescence.policy.v1", "scope": copy.deepcopy(inventory["scope"]), "basis_ref": inventory["basis_ref"], "inputs_complete": True,
        "inventory_sha256": digest(inventory), "journal_sha256": digest(journal), "window_ref": journal["window_ref"], "required_owners": required_owners(case), "checks": checks}


def reference(case):
    """Independent token ownership ledger and clock-controller phase schedule."""
    cfg = config(case);local, remote = [], []
    state = dict.fromkeys(FIELDS, 0);state.update(clock_enable=1, power_available=1)
    rows = []
    for step in range(12):
        old = dict(state);old_local, old_remote = list(local), list(remote)
        issue, transfer, request = step in (1, 8), step == 2, step >= 3
        return_ready = step >= (6 if cfg["power_mode"] else 7)
        edge = old["clock_enable"] and old["power_available"]
        if edge:
            state["domain_edges"] += 1
            if issue and (not request or cfg["bad_admission"]): local.append(step);state["accepted"] += 1
            if transfer and old_local:
                token = local.pop(0);remote.append(token);state["handed"] += 1
            if old_remote and return_ready:
                remote.pop(0);state["returned"] += 1;state["received"] += 1
        state["local_pending"], state["remote_pending"] = len(local), len(remote)
        state["ingress_closed"] = int(request)
        if request and not old["drain_ack"] and not old_local and (cfg["local_only"] or not old_remote and old["ingress_closed"]): state["drain_ack"] = 1
        if cfg["power_mode"] and not cfg["no_isolation"] and old["drain_ack"]: state["isolation_active"] = 1
        if old["drain_ack"] and (not cfg["power_mode"] or cfg["no_isolation"] or old["isolation_active"]): state["clock_enable"] = 0
        if cfg["power_mode"] and not old["clock_enable"]: state["power_available"] = 0
        rows.append({"step": step, "state": dict(state), "issue": int(issue), "transfer": int(transfer), "request": int(request), "return_ready": int(return_ready)})
    return rows


def normalize(row, evidence_ref):
    state = row["state"]
    return {"seq": row["step"], "time_tick": row.get("time_tick", row["step"]), "counts": {"local-work": state["local_pending"], "remote-work": state["remote_pending"]},
        "controls": {"transition_requested": bool(row["request"]), "ingress_closed": bool(state["ingress_closed"]), "drain_ack": bool(state["drain_ack"]),
            "isolation_active": bool(state["isolation_active"]), "clock_available": bool(state["clock_enable"] and state["power_available"]), "power_available": bool(state["power_available"]), "local_idle": not bool(state["local_pending"])},
        "native_counters": {k: state[k] for k in ("accepted", "handed", "returned", "received", "domain_edges")}, "evidence_ref": evidence_ref}


def example(case="power-local-only"):
    inventory = inventory_for(case)
    journal = journal_for(inventory, [normalize(row, "owned-reference:step-" + str(row["step"])) for row in reference(case)])
    return inventory, journal, policy_for(inventory, journal, case)


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream: json.dump(value, stream, indent=2);stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument("directory");parser.add_argument("--case", choices=CASES, default="power-local-only");args = parser.parse_args()
    output = Path(args.directory);output.mkdir(parents=True, exist_ok=False)
    for name, value in zip(("inventory", "journal", "policy"), example(args.case)): save(output / (name + ".json"), value)


if __name__ == "__main__": main()
