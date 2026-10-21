"""Reference event-route fixtures; native observations use run_native.py."""
import argparse
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from event_core import CONTROLS, STAGES, digest, require

CASES = ("clear-before-wake", "retain-before-service", "pulse-irq-required", "held-irq-required", "wake-only", "service-without-source-clear")
COUNTERS = ("assertions", "irq_captures", "deliveries", "services", "source_clears", "wake_captures", "wake_requests", "functional_edges", "aon_edges")


def config(case):
    require(case in CASES, "Unknown example")
    return {"held": case not in ("pulse-irq-required", "wake-only"), "clear_source": case != "service-without-source-clear",
            "gated": case in ("pulse-irq-required", "held-irq-required", "wake-only"), "late_aon": case == "clear-before-wake"}


def topology_for(case):
    return {"format": "opentools.event.topology.v1", "scope": {"project": "event-example", "configuration": case, "mode": "sleep-boundary", "event_ref": "isolated-cause-1"},
        "basis_ref": "settled-one-event-route-v1", "inputs_complete": True,
        "source": {"id": "source-cause", "owner_ref": "source-owner", "persistence": "held-until-clear" if config(case)["held"] else "pulse", "evidence_ref": "event_path.sv:source-status"},
        "routes": {"interrupt": {"id": "functional-gateway", "consumer_ref": "event-handler", "profile_ref": "owned-sampled-high-once-v1", "evidence_ref": "event_path.sv:functional-gateway"},
                   "wake": {"id": "aon-wake", "consumer_ref": "sleep-sequencer", "profile_ref": "owned-sticky-wake-v1", "evidence_ref": "event_path.sv:aon-capture"}}}


def journal_for(topology, samples):
    return {"format": "opentools.event.journal.v1", "scope": copy.deepcopy(topology["scope"]), "basis_ref": topology["basis_ref"],
            "inputs_complete": True, "topology_sha256": digest(topology), "event_isolated": True, "window_closed": True,
            "window_ref": "root-ticks-0-through-11", "samples": samples}


def policy_for(topology, journal, case):
    # Caller intent is independent of whether the actual route succeeded.
    required = ["asserted", "wake_retained", "wake_requested"]
    if case != "wake-only": required += ["interrupt_retained", "interrupt_delivered", "serviced"]
    if config(case)["held"]: required.append("source_cleared")
    orders = [("interrupt_retained", "interrupt_delivered"), ("interrupt_delivered", "serviced"), ("wake_retained", "wake_requested")]
    if config(case)["held"]: orders.append(("wake_retained", "source_cleared"))
    return {"format": "opentools.event.policy.v1", "scope": copy.deepcopy(topology["scope"]), "basis_ref": topology["basis_ref"], "inputs_complete": True,
        "topology_sha256": digest(topology), "journal_sha256": digest(journal), "window_ref": journal["window_ref"],
        "required_stages": [{"stage": s, "evidence_ref": "caller:" + ("wake-only" if case == "wake-only" else "wake-and-service") + ":" + s} for s in required],
        "orders": [{"before": a, "after": b, "evidence_ref": "caller:route-order:" + a + ":" + b} for a, b in orders],
        "stage_prerequisites": [{"stage": s, "controls": controls, "evidence_ref": "event_path.sv:stage-availability"} for s, controls in (
            ("interrupt_retained", ["functional_clock", "power_available", "interrupt_enable", "route_selected"]),
            ("interrupt_delivered", ["functional_clock", "power_available", "interrupt_enable", "route_selected"]),
            ("serviced", ["functional_clock", "power_available"]), ("wake_retained", ["aon_clock", "wake_enable"]),
            ("wake_requested", ["aon_clock", "sleep_window"]))]}


def reference(case):
    """Independent old-state event schedule for the owned clocked fixture."""
    cfg = config(case)
    state = dict.fromkeys(COUNTERS, 0)
    state.update(source_status=0, interrupt_pending=0, wake_pending=0, seen=0, in_service=0, clear_request=0, wake_sent=0)
    rows = []
    for step in range(12):
        old = dict(state)
        func = not (cfg["gated"] and 2 <= step <= 4)
        aon = not cfg["late_aon"] or step >= 9
        if step == 2:
            state["source_status"] = 1;state["assertions"] += 1
        elif not cfg["held"]: state["source_status"] = 0
        elif old["clear_request"] and old["source_status"]:
            state["source_status"] = 0;state["source_clears"] += 1
        if func:
            state["functional_edges"] += 1;state["clear_request"] = 0
            if not old["source_status"]: state["seen"] = 0
            if old["source_status"] and not old["seen"]:
                state["interrupt_pending"] = 1;state["seen"] = 1;state["irq_captures"] += 1
            if old["interrupt_pending"] and not old["in_service"]:
                state["interrupt_pending"] = 0;state["in_service"] = 1;state["deliveries"] += 1
            if old["in_service"]:
                state["in_service"] = 0;state["services"] += 1;state["clear_request"] = int(cfg["clear_source"])
        if aon:
            state["aon_edges"] += 1
            if old["source_status"] and not old["wake_pending"]:
                state["wake_pending"] = 1;state["wake_captures"] += 1
            if old["wake_pending"] and step <= 10 and not old["wake_sent"]:
                state["wake_sent"] = 1;state["wake_requests"] += 1
        rows.append({"step": step, "state": dict(state), "functional_enable": int(func), "aon_enable": int(aon), "sleep_window": int(step <= 10)})
    return rows


def normalize(row, previous, evidence_ref):
    state = row["state"]
    deltas = {k: state[k] - previous[k] for k in COUNTERS}
    require(all(value in (0, 1) for value in deltas.values()), "Owned counter delta must be zero or one")
    return {"seq": row["step"], "time_tick": row.get("time_tick", row["step"]), "stages": dict(zip(STAGES, [bool(deltas[k]) for k in COUNTERS[:7]])),
        "controls": dict(zip(CONTROLS, (bool(deltas["functional_edges"]), bool(deltas["aon_edges"]), True, True, True, True, bool(row["sleep_window"])))),
        "source_status": bool(state["source_status"]), "interrupt_pending_state": bool(state["interrupt_pending"]), "wake_pending_state": bool(state["wake_pending"]),
        "native_counters": {k: state[k] for k in COUNTERS}, "evidence_ref": evidence_ref}


def example(case="clear-before-wake"):
    topology = topology_for(case);previous = dict.fromkeys(COUNTERS, 0);samples = []
    for row in reference(case):
        samples.append(normalize(row, previous, "owned-reference:step-" + str(row["step"])));previous = row["state"]
    journal = journal_for(topology, samples)
    return topology, journal, policy_for(topology, journal, case)


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream: json.dump(value, stream, indent=2);stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument("directory");parser.add_argument("--case", choices=CASES, default="clear-before-wake");args = parser.parse_args()
    output = Path(args.directory);output.mkdir(parents=True, exist_ok=False)
    for name, value in zip(("topology", "journal", "policy"), example(args.case)): save(output / (name + ".json"), value)


if __name__ == "__main__": main()
