"""Independent expected clock edges, samples and obligations for owned examples."""
CONFIGS = {"disabled": ["BAD_GUARD"], "active": [], "gated-clock": ["CHECK_GATED"],
           "wrong-target": ["BIND_DECOY"], "reset-mask": ["MASK_RESET"], "absent": ["OMIT_BIND"]}
CASES = {"power-disabled-fault": ("power", "disabled", False), "power-active-fault": ("power", "active", False),
         "power-clean": ("power", "active", True), "power-gated-clock": ("power", "gated-clock", False),
         "power-wrong-target": ("power", "wrong-target", False), "power-reset-mask": ("power", "reset-mask", False),
         "power-absent": ("power", "absent", False), "power-disabled-clean": ("power", "disabled", True),
         "power-runtime-off": ("power", "active", False),
         "flush-disabled-fault": ("flush", "disabled", False),
         "flush-active-fault": ("flush", "active", False), "flush-clean": ("flush", "active", True)}


RUNTIME_OFF = {"power-runtime-off"}


def expected(config, clean, runtime_assertions=True):
    drive, required, samples, failures = [], [], [], []
    checker = "top.decoy.audit" if config == "wrong-target" else "top.dut.audit"
    for step in range(8):
        tick = 2 * step + 1
        mode = int(3 <= step <= 5)
        row = {"tick": tick, "aon_clk": 1, "functional_clk": 1 - mode, "reset": int(step == 0),
               "mode": mode, "event_req": int(step in (2, 4)), "condition_ok": int(clean or step != 4),
               "assertions_enabled": int(runtime_assertions)}
        drive.append(row)
        required.append({k: row[k] for k in ("tick", "reset", "mode", "event_req", "condition_ok")} | {"hier": "top.dut.observe"})
        if config == "absent" or (config == "gated-clock" and mode):continue
        observed = {k: row[k] for k in ("tick", "reset", "mode", "event_req", "condition_ok")}
        if config == "wrong-target":observed.update(event_req=0, condition_ok=1)
        if config == "reset-mask":observed["reset"] = int(bool(observed["reset"] or mode))
        observed.update(hier=checker, extra_disable=mode if config == "disabled" else 0)
        samples.append(observed)
        if runtime_assertions and not observed["reset"] and not observed["extra_disable"] and observed["event_req"] and not observed["condition_ok"]:
            failures.append({"hier": checker + ".p_transition", "tick": tick})
    active = [r for r in samples if not r["reset"] and not r["extra_disable"] and r["event_req"]]
    counts = {"top.dut.observe.c_required_normal": 1, "top.dut.observe.c_required_risk": 1}
    if config != "absent":
        counts.update({checker + ".c_active_any": len(active), checker + ".c_active_normal": sum(not r["mode"] for r in active),
                       checker + ".c_active_risk": sum(bool(r["mode"]) for r in active)})
    return {"drive": drive, "required_samples": required, "checker_samples": samples,
            "assertion_failures": failures, "coverage_counts": counts, "window": {"start_tick": 0, "end_tick": 16, "cycles": 8}}
