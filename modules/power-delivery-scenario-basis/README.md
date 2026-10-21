# Power-delivery scenario basis

Use this module before applying a saved static IR result to a new decision.
It asks whether the retained analysis covers the **requested supply, sources,
corner, topology and loading assumptions**, preserving native voltages and failures.

This fits in PD/EMIR scenario setup, result reuse and power-delivery handoff.
Power-integrity, PD and scenario owners can use it alongside their existing
solver and load-model review. Matching logical supply names or successful process
completion does not establish physical connectivity or scenario applicability.

The activity supplements native static analysis and electrical acceptance review.
It replaces manual reconciliation of retained results with an independent scenario
request. It does not solve IR, validate the load model or approve voltage limits.

## First use

Saved-data review needs Python 3.10+ and the standard library. From
`modules/power-delivery-scenario-basis`, use a complete retained collection at
`.local/supply-native`, or generate one on Linux with existing
**OpenROAD v2.0-17598-ga008522d8**:

```sh
python examples/run_native.py .local/supply-native --openroad /path/to/openroad
```

Replace the executable path and configure its runtime libraries. The recipe
installs nothing. Two owned networks exercise baseline/unchanged, load, source,
corner and physical-disconnection scenarios. Output must be new.

Inspect the baseline and review it against its original request:

```sh
python supply_review.py capture .local/supply-native series-base --output .local/supply-native/recaptured-base.json
python supply_review.py review .local/supply-native .local/supply-native/reviews/series-base.policy.json --output .local/supply-native/base-review.json
```

Expected review exit: **0**, `static_scenario_corresponds`. This establishes
scenario correspondence, not electrical acceptance.

Now apply the old result to a changed load request:

```sh
python supply_review.py review .local/supply-native .local/supply-native/reviews/series-old-loads.policy.json --output .local/supply-native/old-loads-review.json
```

Expected exit: **1**, `scenario_mismatch_or_native_failure`. The selected
baseline result does not cover the changed loading. This prepared policy also
names a retained exact-load candidate; its separate `cached_review` corresponds,
so the next actions can suggest that existing result. It is not a new IR run.

The `series-exact-cut` control retains a native disconnected-grid failure even
with matching requested identity. `series-dynamic` exits **2** for the requested
dynamic/wake evidence that this static profile cannot supply. Open the JSON for
original native status/voltages, requested fields, findings, gaps and next actions.

Capture exit 0 means a valid import. Outputs require new names. Keep complete
original run directories; review reimports them rather than trusting a cached
normalized receipt.

## Helpers and native hook

| Helper | Responsibility |
|---|---|
| `export_supply.tcl` | Reads native physical supply terminals/shapes and selected library operating point, and saves an export/database copy. |
| `supply_review.py capture ROOT RUN_REF` | Validates the retained source/tool/command/artifact package and reads static analysis evidence without executing saved commands. |
| `supply_review.py review ROOT POLICY` | Reviews a selected result and optional retained candidate independently against the original request, keeping native failure and missing numerical facts. |
| `--output FILE` | Saves JSON to a new path; omit it to print JSON. |

For an existing loaded native flow:

```tcl
source export_supply.tcl
opentools_export_supply run_ref VDD owned_supply/LOAD supply.jsonl supply.odb
```

Replace selected run, net and library/cell. This object export is only part of
the evidence: native static reports, consumed sources/loads and original execution
records are separate. The generic export can support AI review; automatic batch
intake requires the pinned loader/package in [FORMAT.md](FORMAT.md).

## Record the independent scenario

Context identifies run/scope/design/configuration/scenario, explicit supply
voltage, steady power overrides, resistance arguments, source rows, selected
library/corner and activity/state/concurrency assumptions. Execution records retain
original sources/tool/command, artifacts, native stage return/catch codes and
process exit.

The request independently states claim/owner, complete required-field roster,
source basis, scenario/setup/configuration/tool/operating-point identity and
stronger required claims. The policy selects and binds the original run, optionally
a retained candidate. A target simulation need not exist to review a prospective
request.

Units remain explicit:

- Source coordinates/bump size are micrometres; source and terminal voltage are
  volts. Native resolved source nodes retain grid discretization separately.
- Native SPICE resistors are ohms, DC currents amperes and ideal sources volts.
  The profile's explicit power overrides use watts.
- Resistance command arguments follow the pinned native library units.
  Operating-point float tolerance is representation tolerance, not a permitted
  engineering corner range.

The reader checks effective-current correspondence against native sources; it
does not compute voltage from inputs. The example's independent DC solver is for
fixture validation only.

A zero process exit can coexist with a caught native connectivity/analysis failure.
Successful analysis means a static solution was produced, not accepted.
Missing voltage/network reports stay unknown; no zero drop or electrical failure
is invented from absence.

## Integrate into EMIR review

1. State the original electrical/scenario decision and required claim with the
   power-integrity owner, including activity, state and concurrency assumptions.
2. Retain the consumed topology, sources, loads, corner/library, native commands,
   stage outcomes and numerical reports.
3. Define the new request independently of the available passing result. Preserve
   required fields and unknown load/scenario bases.
4. Review selected evidence. Inspect mismatch, native physical-grid failure and
   incomplete numerical evidence as separate conditions.
5. Check any retained candidate against the same request. Use it only within its
   established scenario; otherwise run the appropriate native analysis.
6. Correct setup/load/request sources as needed and revalidate. Hand off original
   request, retained results, reports, remaining analyses and owner decision.

Required dynamic IR, wake sequencing, EM lifetime, load-model validation and
full-chip claims remain open in this static reader.

## AI-first adoption, results and support

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), original supply/scenario
request, load rationale and native evidence:

> Establish whether this static result applies to the requested decision.
> Reconcile physical topology, sources, loads, corner and concurrency assumptions.
> Preserve native failures and unavailable voltages, and distinguish static
> correspondence from dynamic/EM/load-model acceptance.

Use [ONBOARDING.md](../../ONBOARDING.md), module
`power-delivery-scenario-basis` / activity `default`. Your existing AI and native
tools suffice. Optional DVIT intent/dependency context can reveal changed scenario
assumptions or dependent consumers; independent operation requires no connection.

| Review exit | Meaning |
|---:|---|
| 0 | Static scenario correspondence. |
| 1 | Known scenario mismatch or native physical-grid failure; gaps remain visible. |
| 2 | Incomplete source/scenario or stronger required analysis. |
| 3 | Invalid/changed native package or I/O. |

Argument errors use exit 2. Source/topology/fixed-stage changes reject intake.
Hashes identify declared bytes, not freshness, authenticity or approval.

Batch qualification covers one flat power net, one selected library cell, explicit
steady power, one known PG terminal per instance and the pinned loader/version.
Multiple PG pins, broader bump mapping, other load models/loaders, ground analysis,
transients and commercial tools need separate native qualification. The AI workflow
can still use team-native evidence beyond this reader.

Set `OPENTOOLS_SUPPLY_NATIVE` to the retained collection and run:

```sh
python -m unittest discover -s tests -v
```

Native-fixture tests otherwise skip. Saved-data review also runs on Windows.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
