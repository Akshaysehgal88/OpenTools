# Timing scenario coverage

Use this activity during STA run planning and coverage review to establish whether
the **independently required operating scenarios were actually analyzed** with
corresponding model, mode, clock, power-state and RC evidence.

This fits before timing-result handoff and after changes to the scenario matrix,
libraries, clock/mode setup or analysis scope. STA and scenario owners can use it
alongside their native run manager. Several clean runs can still cover the same
obligation and leave a required mode/corner unobserved.

The activity supplements native timing and scenario planning. It replaces manual
required-versus-observed scenario reconciliation. It does not generate a Cartesian
mode/corner product, schedule runs or establish signoff sufficiency.

## First use

Saved-data review needs Python 3.10+ and the standard library. Run from
`modules/result-applicability/profiles/timing-scenarios`. Use a complete retained
collection at `.local/scenarios-native`, or collect one on Linux with existing
**OpenROAD v2.0-17598-ga008522d8** and its configured runtime:

```sh
python examples/run_native.py .local/scenarios-native --openroad /path/to/openroad
```

Replace the tool path. The recipe installs nothing and needs a new output.
Original plans/corpora are written before native execution. Wake-sequence and
manufacturing-capture contexts exercise the same required-scenario review.

Inspect one saved run and the omitted-scenario corpus:

```sh
python scenario_review.py capture .local/scenarios-native wake-sequence-functional-nominal-normal --output .local/scenarios-native/recaptured.json
python scenario_review.py review .local/scenarios-native .local/scenarios-native/requirements/wake-sequence.plan.json .local/scenarios-native/requirements/wake-sequence.omitted.corpus.json --json-out .local/scenarios-native/omitted-review.json --markdown-out .local/scenarios-native/omitted-review.md
```

Expected review exit: **1**, `SCENARIO_REVIEW_REQUIRED`. Three passing runs cover
only two of three required obligations: repeating functional nominal analysis
does not supply the missing low-voltage wake scenario.

Compare the complete corpus:

```sh
python scenario_review.py review .local/scenarios-native .local/scenarios-native/requirements/wake-sequence.plan.json .local/scenarios-native/requirements/wake-sequence.complete.corpus.json --json-out .local/scenarios-native/complete-review.json --markdown-out .local/scenarios-native/complete-review.md
```

Expected exit: **0**, `DECLARED_SCENARIOS_ACCOUNTED`. This accounts for the
declared scenario population, not timing signoff. Open Markdown for obligations
and JSON for per-candidate applicability audits, native outcomes, covered counts,
findings, gaps and quarantined runs.

Both report flags are required. Outputs must be distinct new paths. Capture exit
0 means valid intake. Keep the original complete run directories; saved review
executes no retained Tcl or native command.

## Helper and records

| Operation | Responsibility |
|---|---|
| `scenario_review.py capture ROOT RUN_REF --output FILE` | Reads and validates native run artifacts, retaining original evidence plus a parent result snapshot. |
| `scenario_review.py review ROOT PLAN CORPUS --json-out JSON --markdown-out MD` | Composes result applicability per candidate, matches independent obligations and preserves timing failures separately from scenario accounting. |

[FORMAT.md](FORMAT.md) defines the plan, corpus and original native context/
execution package:

- **Plan:** original scope/design/configuration, requirements source/owner and
  independent obligations. Each is required, explicitly nonapplicable or unknown,
  with its own requested field values and evidence.
- **Corpus:** actual distinct archive run IDs selected for review. Another actual
  repeat may be retained, but cannot cover an unmatched obligation by count.
- **Native package:** original context/setup, model/library sources, invocation,
  actual tool/artifact identities, native clocks/cases/census/path and annotation
  report.

Required requested fields include source/library/physical-library identities,
selected min/max PVT, mode/corner/power role, native cases, clock definition,
RC view and reader profile. Missing foundation fields cannot be dropped to get
acceptance. Additional unsupported claims remain unresolved.

Model PVT values use process, volts and degrees C, normalized to six decimal
places for native representation consistency—not an engineering tolerance.
Clock/PVT values and case integers retain exact types through the parent audit.
Power/mode roles are supplied source declarations, not measured physical state.

Nonapplicability needs the identified combination, source decision, reason and
exclusion reference. A run missing from the collection is not automatically an
inapplicable scenario.

## Integrate into STA scenario review

1. Establish the original required scenario population with design/power/STA
   owners, including documented nonapplicable combinations.
2. Retain the native run inventory independently of that roster. Record actual
   consumed libraries/models, min/max operating conditions, clock/cases and RC basis.
3. Map each selected run to the documented evidence fields, preserving original
   IDs, native result and source/command/artifact identity.
4. Review required-versus-observed correspondence. Inspect missing/foreign runs
   and source/model/mode differences separately from a failed timing observation.
5. Run or locate the missing matching analysis, correct setup or revisit a sourced
   requirement with its owner. Reimport and revalidate after correction.
6. Hand off the original plan, native collection, report, remaining analyses and
   receiving decision. Repeat after scenario or model-basis changes.

An applicable failed observation can account for analysis coverage while retaining
the actual timing failure. The supplied snapshot classifies only a selected
maximum-setup representative, not a complete STA verdict. Clean sampled paths and
scenario counts cannot establish all-path sufficiency.

## AI-first adoption and native boundary

Give a file/tool-enabled assistant [WORKFLOW.md](WORKFLOW.md), original scenario
requirements, mode/power/clock sources and native run inventory:

> Reconcile required scenarios with actual analyses. Check consumed models,
> selected PVT, native clock/case coverage and RC evidence before counting a run.
> Preserve timing failures and sourced nonapplicability separately; ask for missing
> mode or analysis basis instead of inferring coverage from run counts.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module `result-applicability` /
activity `timing-scenarios`. Your current AI/company tools suffice. Optional DVIT
intent/dependency context can reveal omitted or stale scenario obligations;
independent operation requires no connection.

The native profile uses a fresh flat `top`, one library/clock, scalar register
pair, explicit operating conditions and case ports. The closed loader imports no
SDC, exceptions or parasitic files. The native annotation report is retained;
interconnect is unannotated.

Illustrative owned timing tables and PVT labels are model conditions, not
characterized silicon or physical supply/temperature measurements. Hold timing,
all structural paths, extracted RC, OCV/derates, mixed exceptions, other loaders/
commercial tools and signoff need separate qualification.

## Outcomes and tests

| Review exit | Meaning |
|---:|---|
| 0 | Declared obligations accounted within scope. |
| 1 | Missing/inapplicable required scenario or observed selected-path timing failure. |
| 2 | Unresolved evidence. |
| 3 | Invalid/changed native input or I/O. |

Argument errors use exit 2. Read findings, gaps and quarantined-run lists together.
Native outcomes remain visible even when applicability fails.

Set `OPENTOOLS_STA_SCENARIO_NATIVE` to the retained collection and run:

```sh
python -m unittest discover -s tests -v
```

Saved-data review works on Windows/Linux. Without an archive, input tests run and
native-corpus tests skip.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
