#!/usr/bin/env python3
"""Add bounded observed crossing premises to an existing selected waiver snapshot."""
import argparse
import copy
import json
from pathlib import Path
import sys

MODULE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MODULE))
from waiver_core import digest, read_json, require, text_field, validate_snapshot


def capture(population, journal):
    waivers = validate_snapshot(population)
    require(isinstance(journal, dict) and journal.get("format") == "opentools.crossing-premise-journal.v1", "Unsupported crossing journal")
    require(type(journal.get("inputs_complete")) is bool, "Explicit journal completeness required")
    require(journal.get("sampling_basis") == "settled-events-closed-window-v1", "Unsupported sampling basis")
    require(journal.get("population_sha256") == digest(population), "Journal is bound to another population")
    for key in ("run_id", "scope", "configuration_ref", "identity_basis"):
        require(journal.get(key) == population[key], "Journal population context differs: " + key)
    waiver_id, finding_id = text_field(journal, "waiver_id", "journal"), text_field(journal, "finding_id", "journal")
    require(waiver_id in waivers, "Selected waiver absent")
    findings = {f["id"]: f for f in waivers[waiver_id]["findings"]}
    require(finding_id in findings, "Selected crossing finding absent")
    crossing = findings[finding_id].get("crossing")
    require(isinstance(crossing, dict) and journal.get("crossing") == crossing, "Explicit matching crossing mapping required")
    for key in ("source", "destination", "source_clock", "destination_clock", "source_reset", "destination_reset", "evidence_ref"):
        text_field(crossing, key, "crossing")
    width = crossing.get("width")
    require(type(width) is int and 1 <= width <= 64, "Selected crossing width must be 1 to 64")
    require(isinstance(journal.get("events"), list) and journal["events"], "Settled event journal required")
    gaps, stability_witnesses, reset_witnesses = [], [], []
    previous, last_seq, last_time = None, -1, -1
    active = False
    opened, closed, destination_samples = 0, 0, 0
    for event in journal["events"]:
        for key in ("seq", "time_tick"):
            require(type(event.get(key)) is int and event[key] >= 0, "Unsigned sequence/time required")
        require(event["seq"] > last_seq and event["time_tick"] >= last_time, "Event sequence/time must be ordered")
        last_seq, last_time = event["seq"], event["time_tick"]
        text_field(event, "evidence_ref", "event")
        for key in ("window", "source_reset", "destination_active", "source_ready", "destination_sample"):
            require(key in event and (type(event[key]) is bool or event[key] is None), "Boolean/null observed control required: " + key)
        value = event.get("source_value")
        require(value is None or type(value) is int and 0 <= value < 1 << width, "Unsigned source value or null required")
        window = event["window"]
        if window is None:
            gaps.append({"kind": "window_state_unknown", "seq": event["seq"]})
        else:
            if window and not active:
                if previous is None or previous["window"] is not False:
                    gaps.append({"kind": "window_prefix_unknown", "seq": event["seq"]})
                opened += 1
            if not window and active:
                closed += 1
            active = window
        in_window = window is True or previous is not None and previous["window"] is True
        if in_window:
            if window is None or previous is not None and previous["window"] is None:
                gaps.append({"kind": "window_boundary_unknown", "seq": event["seq"]})
            elif value is None or previous is None or previous["source_value"] is None:
                gaps.append({"kind": "window_value_unknown", "seq": event["seq"]})
            elif value != previous["source_value"]:
                stability_witnesses.append({"seq": event["seq"], "before": previous["source_value"], "after": value, "evidence_ref": event["evidence_ref"]})
            if event["destination_sample"] is True:
                destination_samples += 1
            elif event["destination_sample"] is None:
                gaps.append({"kind": "destination_sample_unknown", "seq": event["seq"]})
        destination_active = event["destination_active"]
        if event["destination_sample"] is True and destination_active is not True:
            gaps.append({"kind": "destination_sample_without_established_activity", "seq": event["seq"]})
        if destination_active is True:
            if event["source_reset"] is True or event["source_ready"] is False:
                reset_witnesses.append({"seq": event["seq"], "source_reset": event["source_reset"], "source_ready": event["source_ready"], "evidence_ref": event["evidence_ref"]})
            elif event["source_reset"] is None or event["source_ready"] is None:
                gaps.append({"kind": "source_readiness_unknown", "seq": event["seq"]})
        elif destination_active is None:
            gaps.append({"kind": "destination_activity_unknown", "seq": event["seq"]})
        previous = event
    if active or previous["window"] is None:
        gaps.append({"kind": "window_suffix_unknown"})
    if not opened or opened != closed or not destination_samples:
        gaps.append({"kind": "window_or_destination_observation_missing"})
    if not journal["inputs_complete"]:
        gaps.append({"kind": "partial_journal"})
    # Preserve known contrary observations alongside incomplete coverage. The
    # existing comparator retains its separate review_required flag under gaps.
    stable = False if stability_witnesses else None if gaps else True
    reset_order = False if reset_witnesses else None if gaps else True
    result = copy.deepcopy(population)
    prefix = "crossing:" + waiver_id + ":" + finding_id + ":"
    keys = [prefix + "stable_in_window", prefix + "source_ready_before_destination"]
    require(not any(key in result["configuration"] for key in keys), "Premise keys already exist; retain the original population input")
    result["configuration"].update(dict(zip(keys, (stable, reset_order))))
    original_basis = population.get("configuration_basis", "exporter-defined")
    result["configuration_basis"] = original_basis + "+crossing-journal-v1"
    if gaps:
        result["population_complete"] = False
        next(w for w in result["waivers"] if w["id"] == waiver_id)["complete"] = False
    result["crossing_premise_capture"] = {"profile": "crossing-premises-v1", "population_sha256": digest(population), "journal_sha256": digest(journal),
        "population_configuration_basis": original_basis, "crossing": crossing, "premise_keys": keys,
        "stable_in_window": stable, "source_ready_before_destination": reset_order,
        "stability_witnesses": stability_witnesses, "reset_witnesses": reset_witnesses, "gaps": gaps,
        "limits": ["Imported structural population remains its producer's evidence; no CDC/RDC engine or exception approval.",
                   "Settled event coverage is caller declared; no glitch, metastability, pulse-width or physical reset signoff."]}
    validate_snapshot(result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("population")
    parser.add_argument("journal")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        output = Path(args.out).resolve()
        require(not output.exists() and output.parent.is_dir(), "Choose a new output with an existing parent")
        result = capture(read_json(args.population), read_json(args.journal))
        with output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
        evidence = result["crossing_premise_capture"]
        print(json.dumps(evidence, indent=2))
        return 1 if evidence["stability_witnesses"] or evidence["reset_witnesses"] else 2 if evidence["gaps"] else 0
    except (ValueError, TypeError, KeyError, OSError, UnicodeError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__": sys.exit(main())
