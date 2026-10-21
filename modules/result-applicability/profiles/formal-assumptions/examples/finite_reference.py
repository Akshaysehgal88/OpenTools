"""Independent finite-state reference for the two owned logical examples."""
from itertools import product
from pathlib import Path


def consumer_step(context, mode, state, inputs):
    if context == "wake":
        age, asleep, ack, previous, older, previous_ack = state
        req, sleep, resume = inputs
        legal = True
        if mode == 1 and age > 0:
            legal = not req or not asleep
        if mode == 2 and age >= 2:
            legal = not (previous and not previous_ack) or bool(req)
        bad = age == 3 and older and not (ack or previous_ack)
        active = age > 0 and req and asleep
        nxt = (min(3, age + 1), 1 if not age else 0 if req or resume else 1 if sleep else asleep,
               0 if not age else int(req and not asleep), req, previous, ack)
    else:
        age, previous_valid, previous_ready, previous_data = state
        valid, ready, data = inputs
        held = not (previous_valid and not previous_ready) or (valid and data == previous_data)
        legal = True if not age or mode == 0 else bool(ready) if mode == 1 else age < 2 or held
        bad = age >= 2 and not held
        active = age > 0 and valid and not ready
        nxt = (min(3, age + 1), valid, ready, data)
    return bool(legal), bool(bad), bool(active), nxt


def finite_consumer(context, mode):
    initial = (0, 1, 0, 0, 0, 0) if context == "wake" else (0, 0, 0, 0)
    inputs = list(product((0, 1), (0, 1), (0, 1) if context == "wake" else range(4)))
    seen, frontier = {initial}, {initial}
    bad, activation, rounds, edges = False, False, 0, 0
    while frontier:
        following = set()
        for state in frontier:
            for values in inputs:
                legal, failure, hit, nxt = consumer_step(context, mode, state, values)
                if legal:
                    edges += 1
                    bad |= failure
                    activation |= hit
                    if nxt not in seen:
                        seen.add(nxt)
                        following.add(nxt)
        frontier = following
        rounds += 1
    return {"reachable_states": len(seen), "legal_edges": edges, "fixpoint_rounds": rounds,
            "safety_counterexample_exists": bool(bad), "activation_reachable": bool(activation)}


def finite_producer(context):
    # All legal incoming/ack/ready inputs are enumerated. No hold premise is used.
    initial = (0, 0, 0, 0) if context == "wake" else (0, 0, 0, 0, 0, 0)
    seen, frontier, failures = {initial}, {initial}, 0
    inputs = list(product((0, 1), (0, 1), range(4)))
    while frontier:
        following = set()
        for state in frontier:
            for incoming, response, value in inputs:
                if context == "wake":
                    age, req, prev_req, prev_ack = state
                    bad = age >= 2 and prev_req and not prev_ack and not req
                    nxt_req = 0 if not age else incoming if not req or response else req
                    nxt = (min(3, age + 1), nxt_req, req, response)
                else:
                    age, valid, data, pv, pr, pd = state
                    bad = age >= 2 and pv and not pr and not (valid and data == pd)
                    nv, nd = (0, 0) if not age else (incoming, value) if not valid or response else (valid, data)
                    nxt = (min(3, age + 1), nv, nd, valid, response, data)
                failures += int(bool(bad))
                if nxt not in seen:
                    seen.add(nxt)
                    following.add(nxt)
        frontier = following
    return {"reachable_states": len(seen), "violations": failures, "hold_assumed": False}


def frames(path, names):
    """Read qualified Yosys-SMTBMC full frames; ignore its final clock-only frame."""
    stack, ids, current, result = [], {}, {}, []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if line.startswith("$scope"):
            stack.append(parts[2])
        elif line.startswith("$upscope"):
            stack.pop()
        elif line.startswith("$var") and stack == ["consumer"] and parts[4] in names:
            ids[parts[3]] = parts[4]
        elif line.startswith("#"):
            if set(current) == set(names):
                result.append(current)
            current = {}
        elif line.startswith("b") and len(parts) == 2 and parts[1] in ids:
            assert set(parts[0][1:]) <= {"0", "1"}, "Unknown selected witness value"
            current[ids[parts[1]]] = int(parts[0][1:], 2)
    if set(current) == set(names):
        result.append(current)
    assert set(ids.values()) == set(names) and result, "Selected native witness population missing"
    return result


def check_trace(context, mode, path, kind):
    names = {"age", "asleep", "ack", "request", "sleep_cmd", "external_resume"} if context == "wake" else {"age", "valid", "ready", "data", "out_valid", "out_data"}
    rows = frames(path, names)
    state = (0, 1, 0, 0, 0, 0) if context == "wake" else (0, 0, 0, 0)
    bad, active = False, False
    for row in rows:
        if context == "wake":
            assert (row["age"], row["asleep"], row["ack"]) == state[:3], "Native wake recurrence differs"
            values = tuple(row[k] for k in ("request", "sleep_cmd", "external_resume"))
        else:
            assert row["age"] == state[0] and row["valid"] == row["out_valid"] and row["data"] == row["out_data"], "Native stream mapping differs"
            values = tuple(row[k] for k in ("valid", "ready", "data"))
        legal, failure, hit, state = consumer_step(context, mode, state, values)
        assert legal, "Native witness violates the selected premise"
        bad |= failure
        active |= hit
    assert bad if kind == "counterexample" else active, "Witness does not demonstrate the requested observation"
    return {"checked_frames": len(rows), "counterexample_observed": bool(bad), "activation_observed": bool(active)}
