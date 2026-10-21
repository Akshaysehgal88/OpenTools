"""Create a synthetic capacity-change example in a new directory."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contract_core import digest


def record(required=8, available=8, profile="queue"):
    basis = "unretired-credit-window" if profile == "queue" else "unique-live-tag-window"
    scope = {"project_ref": "owned-example", "interface_ref": profile + "-channel",
             "configuration_ref": f"{profile}-capacity-{available}", "mode_ref": "no-retirement-window"}
    return {"format": "opentools.capacity-record.v1", "record_ref": f"{profile}-{required}-{available}",
            "revision_ref": "synthetic-v1", "scope": scope, "inputs_complete": True,
            "facts": [{"id": name, "value": value, "unit": "transactions", "basis_ref": basis,
                       "value_ref": "synthetic:" + name, "meaning_ref": "synthetic:reviewed-" + name}
                      for name, value in (("required", required), ("available", available))]}


def contract(current, baseline=None):
    fact = current["facts"][0]
    return {"format": "opentools.capacity-contract.v1", "scope": current["scope"].copy(),
            "record_sha256": digest(current), "baseline_sha256": digest(baseline) if baseline else None,
            "population_complete": True, "evidence_ref": "synthetic:interface-review",
            "checks": [{"id": "outstanding-capacity", "required_fact": "required", "available_fact": "available",
                        "unit": fact["unit"], "basis_ref": fact["basis_ref"], "evidence_ref": "synthetic:capacity-obligation",
                        "premises": [{"id": "maximum-unretired-demand", "holds": True,
                                      "evidence_ref": "synthetic:producer-limit"},
                                     {"id": "capacity-is-available-to-this-channel", "holds": True,
                                      "evidence_ref": "synthetic:consumer-reservation"}]}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    args = parser.parse_args()
    directory = Path(args.directory)
    directory.mkdir(exist_ok=False)
    baseline, current = record(), record(8, 4)
    for name, value in (("baseline.json", baseline), ("current.json", current),
                        ("contract.json", contract(current, baseline))):
        (directory / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
