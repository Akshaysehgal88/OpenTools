"""Owned warm reset and watchdog event-replay records with independent intent."""
import argparse
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reset_core import digest, require

CASES = ("warm-partial", "warm-reset-both", "warm-drain", "watchdog-fresh-start", "watchdog-replay")
STATE_NAMES = ("producer_pending", "consumer_context", "producer_id", "consumer_id", "orphan", "replay")


def inventory_for(case):
    require(case in CASES, "Unknown example")
    scope = {"project": "reset-example", "configuration": "two-state-owners", "mode": "functional", "reset_event_ref": "watchdog" if case.startswith("watchdog") else "warm"}
    result = {"format": "opentools.reset.inventory.v1", "scope": scope, "basis_ref": "reviewed-reset-boundary-v1", "inputs_complete": True, "states": []}
    for name in STATE_NAMES:
        owner = "producer" if name.startswith("producer") else "consumer"
        result["states"].append({"id": name, "width": 4 if name.endswith("_id") else 1, "owner_ref": owner,
                                "reset_domain_ref": owner + "-reset", "reset_value": 0, "evidence_ref": "reset_path.sv:" + name})
    return result


def journal_for(inventory, phases):
    return {"format": "opentools.reset.journal.v1", "scope": copy.deepcopy(inventory["scope"]), "basis_ref": inventory["basis_ref"],
            "inputs_complete": True, "inventory_sha256": digest(inventory), "phases": phases}


def policy_for(inventory, journal, case):
    result = {"format": "opentools.reset.policy.v1", "scope": copy.deepcopy(inventory["scope"]), "basis_ref": inventory["basis_ref"],
        "inputs_complete": True, "inventory_sha256": digest(inventory), "journal_sha256": digest(journal), "state_expectations": [],
        "release_requires": [{"id": k, "evidence_ref": "caller:restart-prerequisite:" + k} for k in ("clock_available", "consumer_initialized")],
        "continuity": [{"producer_pending_ref": "producer_pending", "consumer_context_ref": "consumer_context", "allow_replay": case == "watchdog-replay",
                        "producer_identity_ref": "producer_id", "consumer_identity_ref": "consumer_id", "evidence_ref": "caller:explicit-event-replay-only"}],
        "post_expectations": [{"state_ref": "orphan", "equals": 0, "evidence_ref": "caller:no-unowned-post-reset-completion"}]}
    # Reset scope and replay authority are intent, independent of observed values.
    for state in inventory["states"]:
        reset = state["owner_ref"] == "consumer" or case == "warm-reset-both"
        result["state_expectations"].append({"state_ref": state["id"], "effect": "clear" if reset else "preserve", "required_reset": reset, "evidence_ref": "caller:reset-owner-policy"})
    if case == "watchdog-replay":
        result["release_requires"].append({"id": "replay_ready", "evidence_ref": "caller:retained-event-replay-ready"})
        result["post_expectations"].append({"state_ref": "replay", "equals": 1, "evidence_ref": "caller:consume-retained-event"})
    return result


def reference_rows(case):
    # Independent snapshot reference for the owned testbench event schedule.
    before = dict(zip(STATE_NAMES, [0 if case == "warm-drain" else 1, 0 if case == "warm-drain" else 1, 5, 5, 0, 0]))
    held = dict(before, consumer_context=0, consumer_id=0, orphan=0, replay=0)
    if case == "warm-reset-both": held.update(producer_pending=0, producer_id=0)
    post = dict(held)
    if held["producer_pending"]:
        post["producer_pending"] = 0
        post["replay" if case == "watchdog-replay" else "orphan"] = 1
    return [before, held, dict(held), post]


def example(case="warm-partial"):
    inventory = inventory_for(case)
    phases = []
    for index, (name, values) in enumerate(zip(("before", "held", "released", "post"), reference_rows(case))):
        phases.append({"phase": name, "values": values, "reset_active": {"producer-reset": index == 1 and case == "warm-reset-both", "consumer-reset": index == 1},
            "hardware_quiet": True, "prerequisites": {"clock_available": True, "consumer_initialized": index != 1, "replay_ready": case == "watchdog-replay" and index != 1},
            "evidence_ref": "reset_path.sv:phase-" + name})
    journal = journal_for(inventory, phases)
    return inventory, journal, policy_for(inventory, journal, case)


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--case", choices=CASES, default="warm-partial")
    args = parser.parse_args()
    output = Path(args.directory)
    output.mkdir(parents=True, exist_ok=False)
    for name, value in zip(("inventory", "journal", "policy"), example(args.case)): save(output / (name + ".json"), value)


if __name__ == "__main__": main()
