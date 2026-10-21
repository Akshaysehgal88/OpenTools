"""Create review records from the owned example's retained native data; no execution."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
from activation_core import digest, exit_code, file_hash, markdown, read_json, require, review
from native_capture import capture
from reference_model import CASES, CONFIGS, RUNTIME_OFF, expected


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:stream.write(json.dumps(value, indent=2) + "\n")


def context_for(name, family, config):
    return {"format": "opentools.activation-capture-context.v1", "run_ref": "owned:" + name,
            "scope": {"design_ref": "owned:" + family + ":boolean-transition-interface", "configuration_ref": "owned:" + config,
                      "window_ref": "owned:eight-cycles-two-events", "mode_ref": "owned:normal-and-risk"},
            "family_basis_ref": "owned:source-reviewed-same-cycle-implication-reset-and-extra-disable",
            "dependencies_complete": True, "dependency_basis_ref": "owned:fixed-five-source-inputs-and-recorded-pinned-native-build-runtime"}


def records(name, family, snapshot):
    condition = "drain-before-power-off" if family == "power" else "cancellation-before-flush"
    roster = {"format": "opentools.property-obligations.v1", "scope_ref": "owned:" + name + ":transition-checker-review",
              "scope": snapshot["scope"], "claim": "The selected transition property is bound and active at both required normal/risk sample events; retain observed condition failures separately.",
              "claim_kind": "observed_activation", "owner_ref": "owned-requirement-owner", "basis_ref": "owned:independent-two-event-obligation-roster",
              "inventory_complete": True, "property_ref": "owned:" + family + ":" + condition,
              "obligations": [{"id": "normal-event" if mode == 0 else "risk-event", "requirement_ref": "owned:" + family + ":" + ("normal-event" if mode == 0 else "risk-event"),
                               "owner_ref": "owned-requirement-owner", "target_ref": "top.dut", "clock_ref": "top.aon_clk", "edge": "posedge",
                               "mode": mode, "tick": tick, "condition_ref": "owned:" + condition} for mode, tick in ((0, 5), (1, 9))]}
    model = {"format": "opentools.property-bindings.v1", "scope": snapshot["scope"], "basis_ref": "owned:expected-checker-integration-map",
             "roster_sha256": digest(roster), "run_ref": snapshot["run_ref"], "sources": snapshot["sources"],
             "bindings": [{"obligation_id": o["id"], "checker_ref": "top.dut.audit", "property_name": "p_transition",
                           "activation_cover": "c_active_normal" if o["mode"] == 0 else "c_active_risk", "basis_ref": "owned:source-and-mode-cover-review"}
                          for o in roster["obligations"]]}
    return roster, model


def from_native(output):
    output = Path(output).resolve();collection = read_json(output / "collection.json")
    require(len(collection["cases"]) == len(CASES) and collection["native_builds"] == 8, "Owned native case population differs")
    results = []
    for name, (family, config, clean) in CASES.items():
        folder = output / name;ctx = context_for(name, family, config);snapshot = capture(folder, "run", ctx)
        for native_name, source in (("top.sv", MODULE / "examples" / (family + ".sv")),
                                    *[(n, MODULE / "examples" / n) for n in ("checker.sv", "composition.vh", "main.cpp")]):
            require(snapshot["sources"][native_name] == file_hash(source), "Retained model differs from current owned example")
        selection = "".join("`define " + flag + "\n" for flag in CONFIGS[config]) or "// Active binding\n"
        require((folder / "run/selection.vh").read_text(encoding="utf-8") == selection, "Retained selection differs")
        reference = expected(config, clean, name not in RUNTIME_OFF)
        for key in ("drive", "required_samples", "checker_samples", "assertion_failures", "window"):
            require(snapshot[key] == reference[key], "Native/reference differs: " + name + " " + key)
        require({p: v["count"] for p, v in snapshot["covers"].items()} == reference["coverage_counts"], "Native/reference cover counters differ")
        require(snapshot["observer"]["target_module"] == family + "_subject", "Independent observer targets the wrong module")
        roster, model = records(name, family, snapshot);report = review(roster, model, snapshot, folder)
        require(exit_code(report) == (0 if name in ("power-clean", "flush-clean") else 1), "Unexpected owned review result: " + name)
        save(folder / "capture-context.json", ctx);save(folder / "evidence.json", snapshot)
        save(folder / "obligations.json", roster);save(folder / "bindings.json", model);save(folder / "report.json", report)
        save(folder / "independent-reference.json", reference)
        (folder / "report.md").write_text(markdown(report), encoding="utf-8")
        results.append({"case": name, "status": report["status"], "native_outcome": snapshot["native_outcome"],
                        "required_rows": len(snapshot["required_samples"]), "checker_rows": len(snapshot["checker_samples"]),
                        "native_assertion_failures": len(snapshot["assertion_failures"]),
                        "activation_by_obligation": {r["obligation_id"]: r["activation_observed"] for r in report["obligations"]},
                        "cover_counts": reference["coverage_counts"]})
        print(name + ": " + report["status"], flush=True)
    summary = {"version": collection["version"], "native_builds": 8, "native_xml_exports": 8, "native_runs": len(results), "cases": results,
               "reference_method": "Independent clock-edge/Boolean interface recurrence and complete per-record comparison, native hierarchy/pins, per-mode cover counts and runtime assertion-enable facts.",
               "limits": "Bounded stable-before-edge same-cycle Boolean implication family. Cover hits and activation are not property adequacy or unbounded proof; no automatic edits/acceptance or physical-clock/reset qualification."}
    save(output / "summary.json", summary);return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument("retained_native_directory", type=Path);args = parser.parse_args()
    print(json.dumps(from_native(args.retained_native_directory), indent=2))


if __name__ == "__main__":main()
