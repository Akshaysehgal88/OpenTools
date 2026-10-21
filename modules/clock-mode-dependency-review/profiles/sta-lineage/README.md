# STA clock lineage and mode coverage

Use this activity during STA clock setup, before interpreting timing results for a
selected operating mode. It checks whether native clock objects, generated-clock
relationships, case values and register clock-pin coverage correspond to the
**original mode/consumer contract**.

The users are STA, clock/reset and integration engineers. Run it after changing
SDC, divider/mux selection, case analysis, propagation state or clock consumers.
A root clock can be present while downstream registers lack their required
generated clock. A clock count or a timing report alone can miss that gap.

This supplements the timing engine's setup diagnostics and your SDC review. It
replaces manual reconciliation of the selected native clock population with
required consumers and lineage. It does not establish physical clock availability,
waveform safety, CDC/RDC closure or timing signoff.

## First review

Saved-data use requires Python 3.10+ and the standard library. Run from
`modules/clock-mode-dependency-review`. Use a complete retained example at
`.local/sta-lineage`, or generate one on Linux with an existing
**OpenROAD v2.0-17598-ga008522d8** executable:

```sh
python profiles/sta-lineage/examples/run_native.py .local/sta-lineage --openroad /path/to/openroad
```

The recipe installs nothing. It collects two owned timing trees—boot
divide-by-two and wake divide-by-four—under nine setup variants each, then
creates source-bound policies and reviews. The output directory must be new.
Saved-data capture/review can run on Windows or Linux without OpenROAD.

Inspect the original consumer population and review the missing definition:

```sh
python profiles/sta-lineage/sta_review.py capture .local/sta-lineage boot-divider-complete --output .local/sta-lineage/recaptured.json
python profiles/sta-lineage/sta_review.py review .local/sta-lineage .local/sta-lineage/reviews/boot-divider-missing-generated.policy.json --output .local/sta-lineage/missing-review.json
python profiles/sta-lineage/sta_review.py review .local/sta-lineage .local/sta-lineage/reviews/boot-divider-complete.policy.json --output .local/sta-lineage/complete-review.json
```

Capture exits **0** for a valid import. The missing-generated review exits **1**:
the required final generated clock and its consumer coverage are absent although
upstream clock setup remains. The complete review exits **0**,
`clock_contract_corresponds`. Open the output JSON for findings, gaps, clock
properties and consumer correspondence. New output paths are required.

The controls also exercise wrong mode, divide ratio, gate case and ideal versus
propagated clocks. `boot-divider-untraced` and `boot-divider-auto-master` remain
incomplete (exit 2): the required lineage history is not established by the final
collection alone.

## The three helpers

| Helper | Where it runs and what it does |
|---|---|
| `trace_clocks.tcl` | Inside the pinned native timing tool, before definitions. Retains successfully resolved generated-clock constructor arguments, including explicit master, reference and target. |
| `export_clocks.tcl` | Inside the loaded native design, after setup. Exports clocks, constraint waveforms, targets, complete register clock-pin census, clock associations, actual case values and a selected path observation, plus a database. |
| `sta_review.py capture ROOT RUN_REF` | Reads and validates the original retained source/tool/command/artifact package. It executes no archived SDC or Tcl. |
| `sta_review.py review ROOT POLICY` | Reimports the bound native evidence and compares it with the independently sourced mode, clock and consumer contract. |

`--output` saves JSON; omit it to print JSON. Capture's successful import is not a
clock-contract disposition. Review performs the additional intent comparison.

## Connect to your existing timing setup

For the pinned qualified loader, load the trace before **any** clock definition,
and end it before collecting final native objects:

```tcl
source trace_clocks.tcl
opentools_clock_trace_start
# Execute the reviewed native create_clock/create_generated_clock setup here.
opentools_clock_trace_end
source export_clocks.tcl
opentools_export_clocks run_ref {reset_n boot_sel clock_enable} capture/D clocks.jsonl clocks.odb
```

Replace the run ID, case ports and endpoint with the selected design objects.
Source paths must resolve in your native tool's working directory. This is the
export hook, not the entire evidence package: retain the consumed setup, sources,
context, native invocation and execution/artifact identities described in
[FORMAT.md](FORMAT.md). The bundled [loader](loader.tcl) demonstrates the full
single-pass sequence, including `consumed.sdc`.

The trace intercepts the pinned native 13-argument generated-clock constructor
after successful creation and forwards its return. It records resolved objects;
it is not an SDC text parser. Start it once before definitions. The qualified
lifecycle creates each clock once without deletion/redefinition and restores the
original command before final collection.

The exporter can inspect final collections without a trace, including a loaded
database, but cannot recover missing creation history. The pinned API does not
provide a general posthoc master/divide getter. An implicit master, unsupported
generation option, ambiguous trace or different clock lifecycle remains unresolved.

## Source the contract independently

The native context and execution records bind run, design, configuration, mode,
setup, original tool/command and artifact identities. The review policy binds a
specific original export to an `opentools.sta-lineage-contract.v1` contract.

Write the contract from the original mode/setup requirements, before selecting
passing native output. Include:

- Required mode-port cases, clock and consumer rosters, with completeness scoped
  to the reviewed design/mode.
- Expected period, waveform, definition targets and generated/propagated state.
- Explicit master, reference source and divider relationships. The timing
  reference source is distinct from the generated clock's definition target.
- Required clock associations at each register clock pin and any selected-path
  requirement.
- Original design/setup sources, ownership, reset/power/clock-availability bases
  and the strength of the intended claim.

All timing values use the pinned native **ns** UI. The comparison's `1e-6` ns
floating tolerance is representation tolerance, not a timing margin. Constraint
waveforms are model objects, not measurements of physical pulses. Removing an
observed consumer from the requirement roster is reported rather than silently
shrinking the reviewed population.

## Adoption, correction and revalidation

1. Give your file/tool-enabled assistant [WORKFLOW.md](WORKFLOW.md), the original
   mode contract, consumed SDC and native setup scripts. Ask it to trace required
   consumers from source rather than infer them from existing clock objects.
2. Confirm the installed tool version, object API and clock lifecycle. Use the
   pinned collector as supplied, or validate a tool-specific exporter against
   original native objects before relying on a different EDA flow.
3. Retain and import the complete native package. Review lineage, missing
   consumers and mode cases with the STA/clock owners.
4. Correct the original SDC, mode selection or sourced requirement, then recollect
   and review the resulting native objects. Do not edit the export to clear a
   finding.
5. Hand off the contract, retained native evidence, report and owner decision.
   Repeat after relevant setup, source, divider, case or consumer changes.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module
`clock-mode-dependency-review` / activity `sta-lineage`, for project-local
AI-host adoption. Optional DVIT intent/dependency evidence can help reveal stale
consumer or mode assumptions; local sources and your existing AI remain sufficient.

## Outcomes and support boundary

| Review exit | Meaning |
|---:|---|
| 0 | Clock contract corresponds within the selected native scope. |
| 1 | Known setup/contract differences require review; coexisting gaps remain visible. |
| 2 | Incomplete lineage, mode or other required evidence. |
| 3 | Invalid input, changed/missing native package or I/O. |

Argument errors use exit 2. Hashes bind declared correspondence; they do not
authenticate source authority or engineering approval.

Batch qualification covers the bundled loader, flat scalar primitives, one
mode/tree, one root and single-pass explicit-master integer dividers in the pinned
OpenROAD version. Other loaders, clock transformations, hierarchical/partial
mapping and commercial timing tools need separate qualification. The AI workflow
can still use broader team-native evidence without claiming this reader supports it.

Set `OPENTOOLS_STA_LINEAGE_NATIVE` to the retained collection to include its tests:

```sh
python -m unittest discover -s profiles/sta-lineage/tests -v
```

Native-fixture tests otherwise skip. Installing the module never installs native
tools or runs their scripts.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
