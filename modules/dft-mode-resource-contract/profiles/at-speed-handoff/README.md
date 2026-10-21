# At-speed recipe and STA handoff

Use this activity when an OCC recipe, launch/capture mode, selected timing
scenario or exception changes. It reconciles the **required source edges and
control setup** with observed pulses and the native STA clock/path interpretation.

This fits between test-clock recipe definition, DFX verification and DFT/STA
handoff. DFT, OCC, STA and verification owners can use it to check that their
artifacts describe the same launch/capture operation. A shift-only false path must
not hide the selected LOC capture path; a native checker pass does not necessarily
meet the independent recipe's stronger control guard.

It supplements OCC verification, STA setup diagnostics and pattern/ATPG review.
It replaces manual cross-checking of this selected recipe, pulse journal and
timing scenario. It does not replace ATPG, physical pulse-quality characterization
or production timing signoff.

## First use

Saved-data review needs Python 3.10+ and the standard library. Run from
`modules/dft-mode-resource-contract/profiles/at-speed-handoff`. Use a complete
retained collection at `.local/occ-native`, or collect one on Linux with existing
**Verilator 5.020**, **OpenROAD v2.0-17598-ga008522d8**, C++/Make and the required
native runtime libraries:

```sh
python examples/run_native.py .local/occ-native --openroad /path/to/openroad --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Replace the tool/runtime paths. The recipe installs nothing. Its two owned paths
use different names, 10/16 ns source periods and opposite reset polarities.
Two native builds serve 14 STA scenarios and 28 behavior controls. The output
directory must be new.

Reimport the good capture pairing and review it:

```sh
python occ_handoff.py capture .local/occ-native scan-window-capture-good/run sta/scan-window-capture/run .local/occ-native/scan-window-capture-good/context.json --output .local/occ-native/scan-window-capture-good/recaptured.json
python occ_handoff.py review .local/occ-native .local/occ-native/scan-window-capture-good/contract.json .local/occ-native/scan-window-capture-good/recaptured.json --json-out .local/occ-native/scan-window-capture-good/new-review.json --markdown-out .local/occ-native/scan-window-capture-good/new-review.md
```

Expected review exit: **0**, `BOUNDED_RECIPE_ALIGNED`. Inspect Markdown for the
disposition and JSON for native behavior status/counts, timing completion, pulse
and guard observations, selected path probes, findings and gaps.

Now review capture using a shift exemption:

```sh
python occ_handoff.py review .local/occ-native .local/occ-native/scan-window-capture-shift-exception/contract.json .local/occ-native/scan-window-capture-shift-exception/evidence.json --json-out .local/occ-native/scan-window-capture-shift-exception/new-review.json --markdown-out .local/occ-native/scan-window-capture-shift-exception/new-review.md
```

Expected exit: **1**, `ALIGNMENT_REVIEW_REQUIRED`. The selected capture path
cannot receive a shift-only exemption. Other controls include missing, extra and
gapped pulses, wrong period, scan-enable setup, held reset, unknown native cases
and valid shift with/without an exception.

Both report flags are required, with distinct new files and existing parents.
Keep the entire native collection, including shared `sta/` directories. A receipt
alone is insufficient: review rechecks original artifacts under the explicit root.

## Helper and independent recipe

| Operation | What it does |
|---|---|
| `occ_handoff.py capture ROOT BEHAVIOR_DIR STA_DIR CONTEXT --output RECEIPT` | Imports the original behavior and STA packages, checks shared-unit/source/role identity, and retains measured pulses, controls, native outcomes and path evidence. |
| `occ_handoff.py review ROOT CONTRACT RECEIPT --json-out JSON --markdown-out MD` | Revalidates artifacts/normalized fields and compares them with the original recipe and claim. It executes no received command, Tcl or executable. |

Complete [templates/context.json](templates/context.json) from the original
mapping/run/scenario and [templates/contract.json](templates/contract.json) from
the independent recipe. [FORMAT.md](FORMAT.md) defines the artifact set and
supported writer/logger formats.

Context identifies scope/design/configuration/domain/phase/recipe, behavior and STA
run/scenario, selected unit/gate/launch/capture cells, clocks, reset polarity and
fourteen observed signal roles. The contract binds the original source and command
identities and separately states:

- LOC capture or shift phase, source period in integer nanoseconds and increasing
  required source-edge indices.
- Required control guard, reset and scan levels, selected path and exception
  applicability, with source/owner basis.
- Any stronger required claim, including native ATPG evidence.

Edge index zero is the first observed root rise, avoiding an invented absolute
phase relationship between simulator initialization and STA time origin.
Generated rises must coincide with selected root rises. Capture requires two
consecutive source edges and a visible selected timed path.

The independent guard is not copied from the native checker's guard. Correct
values at an edge can still fail when a known recent change violates setup;
missing earlier history remains unknown. Required edges beyond the retained window
remain gaps. A matching pulse prefix cannot qualify a longer recipe.

## Integrate into the OCC/STA handoff

1. Establish the original capture/shift recipe and receiving claim with DFT and
   STA owners. Keep pattern/ATPG expectations distinct from available clock data.
2. Retain original behavior sources, XML, executable, commands, sampled journal and
   outcomes, plus native STA sources/setup, consumed SDC, resource export and
   execution evidence.
3. Confirm behavior and timing use the same selected unit/source and scenario.
   Map logger signals through native ports to the intended gate and cell pins.
4. Capture and review. Inspect pulses, guards, reset/scan cases and path visibility
   separately from process exits and native checker verdicts.
5. Correct the original recipe/controller, timing setup or sourced requirement.
   Recollect the affected native evidence and revalidate the pairing.
6. Hand off recipe rationale, original artifacts, reports, unresolved claims and
   owner decision. Repeat after relevant clock, control, path, exception or scenario
   changes.

A compatible retained STA scenario can pair with another behavior run only when
shared source and scenario/input identities match. A new pairing is not a new
timing execution. Supplied scenario labels do not authenticate native intent.

## AI-led adoption

Give a file/tool-enabled assistant [WORKFLOW.md](WORKFLOW.md), the original recipe,
OCC/control sources, consumed timing setup and native observations:

> Reconcile this selected launch/capture operation across DFT, behavior and STA.
> Check source-edge selection, independent control guard, reset/scan cases,
> generated-clock interpretation and exception applicability. Preserve missing
> ATPG or stronger physical/timing evidence rather than inferring it from labels.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module
`dft-mode-resource-contract` / activity `at-speed-handoff`. Existing AI hosts can
review your company-native artifacts beyond the supplied reader. Optional DVIT
intent/dependency context can expose stale recipe/scenario assumptions; local
operation requires no connection. [GUIDE.md](GUIDE.md) provides the compact
command reference.

## Outcomes and qualification

| Review exit | Meaning |
|---:|---|
| 0 | Bounded recipe alignment. |
| 1 | Known pulse, guard, mode, clock or path/exception alignment finding. |
| 2 | Incomplete or quarantined evidence; resolve missing scope/identity before attribution. |
| 3 | Invalid input/artifact or I/O. |

Argument errors use exit 2. Capture exit 0 means a valid import, including native
behavior FAIL. Known findings retain accompanying gaps.

The qualified owned profile uses one AND gate, two scalar `SCANR_CELL` instances
and the documented reset alias/inverter mapping. Behavior uses contiguous 1 ns
samples; STA uses a pinned 1 ns Liberty unit and limited native `write_sdc`
format parsed as data. Other cells, loaders, formats and EDA tools need separate
native qualification.

Ideal library timing makes the selected path visible; it does not characterize
production setup/hold or physical pulses between samples. This reader has no
qualified ATPG artifact path, so `require_native_atpg: true` stays an explicit
gap. It establishes no fault coverage, electrical timing or owner approval.

Set `OPENTOOLS_OCC_EXAMPLE` to the retained collection to include its tests:

```sh
python -m unittest discover -s tests -v
```

Native-corpus tests otherwise skip. Saved-data review also runs on Windows.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
