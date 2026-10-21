# Fault-coverage denominator review

Use this activity during DFT test-coverage closure after a change to fault
definitions, legal modes/constraints, selected patterns, classification rules,
collapse policy or exclusions. It asks whether a higher score reflects
**additional fault detection or a changed measurement population**.

The users are DFT, ATPG and test-coverage owners reviewing a handoff or an
exclusion change. This supplements native fault reports, pattern analysis and
exclusion approval. It replaces manual reconciliation of the selected original
fault population, collapse map, classifications and denominator changes. It does
not replace ATPG, fault simulation or the receiving team's signoff process.

The AI workflow applies to your team's native evidence. The bundled Python
reader is a deliberately bounded, executable example: retained Verilator 5.020
campaigns for an owned finite single-site stuck-at model. It does not claim to
read arbitrary commercial ATPG databases. Fault classes are never translated into
the parent module's functional-coverage bins.

## Run the example

Saved-data review requires Python 3.10+ and the standard library. From
`modules/coverage-change-audit/profiles/fault-denominator`, use a complete
retained example at `.local/fault-native`, or generate one on Linux with an
existing Verilator 5.020, C++ compiler and Make:

```sh
python examples/run_native.py .local/fault-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Replace the native tool/runtime paths. The recipe installs nothing. Two different
owned logic networks each have one build and ten selected plans. Output paths
must be new; retain the complete directory for later data-only review.

Compare a denominator-only change:

```sh
python fault_audit.py compare .local/fault-native/select-network-baseline/run .local/fault-native/select-network-baseline/context.json .local/fault-native/select-network-denominator-only/run .local/fault-native/select-network-denominator-only/context.json .local/fault-native/select-network-denominator-only/policy.json --output .local/fault-native/denominator-review.json
```

Expected exit: **1**, `review_required`. The reported fraction rises from
**3/10 to 3/8**, with no newly detected faults. The original ten obligations
remain visible; two exclusions change the denominator and lack a supplied
reviewed basis. Inspect `findings`, `gaps` and `newly_detected_faults` in the JSON.

For an unchanged control:

```sh
python fault_audit.py compare .local/fault-native/select-network-baseline/run .local/fault-native/select-network-baseline/context.json .local/fault-native/select-network-same/run .local/fault-native/select-network-same/context.json .local/fault-native/select-network-same/policy.json --output .local/fault-native/unchanged-review.json
```

Expected exit: **0**, `aligned`. Other controls add selected patterns, supply a
reviewed exclusion, change legal mode/metric, use collapsed scoring, abort a
campaign or retain an unknown class. A justified exclusion can explain an increase
without creating new fault detection.

## Helper features

| Operation | Contribution |
|---|---|
| `fault_audit.py capture NATIVE_DIRECTORY CONTEXT --output FILE` | Reconstructs the owned campaign from original native artifacts; retains the site census, healthy/fault responses, classes, collapse correspondence and measurement definition. |
| `fault_audit.py compare BASE_DIR BASE_CONTEXT CURRENT_DIR CURRENT_CONTEXT POLICY` | Recaptures both sides, checks the independent objective/bindings and reports population, classification, exclusion and detection changes. |
| `--output` | Saves JSON to a new path. Omit it to print the structured record. |

For a standalone import:

```sh
python fault_audit.py capture .local/fault-native/select-network-baseline/run .local/fault-native/select-network-baseline/context.json --output .local/fault-native/captured.json
```

Capture exits 0 for valid intake, not coverage closure. Imported commands and
executables are never run by capture/compare.

## Inputs and measurement semantics

[FORMAT.md](FORMAT.md) describes the exact retained files and records. Keep the
owned RTL, top, driver, compiled plans, native XML, original executable, version,
plan, command/stdout/stderr and execution records. The context supplies original
run/design/configuration/fault-model/objective identities, selected instance and
port roles, model/constraint/pattern/exclusion bases and owner.

The independent policy contains the complete **original** fault roster, accepted
baseline/current source/plan/command/binary identities and reviewed current
exclusion decisions. Source it from the objective and original execution evidence;
do not reconstruct the required roster from a smaller reported denominator.
Review references are declarations, not authenticated approvals.

For this owned model:

- Original fault ID `2*site + stuck_value` names one SA0/SA1 obligation. Native
  XML establishes the declared output-vector injection sites, not all RTL pins.
- `DT` has a selected-pattern observable output difference. `UD` is finitely
  detectable but missed by the selected tests. `UT` has no possible difference
  in the completed, exact legal input space.
- `AB` has no observed detection before the selected budget expired.
  `UNKNOWN` retains an explicitly unresolved class, even if a score is available.
- Collapse groups have identical complete output responses over that exact legal
  mode/input space. A different legal space can change the collapse map.
- Metric 0 counts DT/nonexcluded; metric 1 additionally removes UT from the
  denominator. Original-fault and collapsed-group bases stay separate. A zero
  denominator is null; unlike definitions receive no percentage delta.

The native recipe records every legal healthy/fault response for finite
detectability and collapse checking. Those full-space audit vectors are **not**
credited as selected-pattern detections. A later DT after AB/UNKNOWN is resolved
classification, not proof that the earlier campaign conclusively missed it.

## Integrate with a DFT closure review

1. Give your AI assistant [WORKFLOW.md](WORKFLOW.md), the original coverage
   objective and native reports. Ask it to establish the fault model, legal
   constraints, complete population, collapse rules and exact reported metric.
2. Retain the original census and collapsed correspondence on both sides. Keep
   native class names and meanings; do not map another ATPG tool's labels by
   spelling alone.
3. Establish exclusions independently with their source, reason and receiving
   owner. Keep excluded obligations in the original review population.
4. Use the supplied helper only for its qualified owned format, or validate an
   exporter for your native producer against its original evidence. The assistant
   can still perform the broader workflow review without this reader.
5. Inspect new selected-test detections separately from denominator/class changes,
   unresolved classifications and changed legal space.
6. Return a population/change table, source-backed interpretation, missing
   evidence and rerun/revalidation actions to the test-coverage owner. Repeat
   after pattern, constraint, classification, collapse or exclusion changes.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module `coverage-change-audit` /
activity `fault-denominator`, for project-local setup. Existing AI subscriptions
and native tools suffice. Optional DVIT intent/context can relate exclusions and
measurement scope to original product/test obligations; the review remains
independent without it. The [review record](review-record.json) captures the
interpretation beyond the numeric comparison.

## Outcome and qualification

| Compare exit | Meaning |
|---:|---|
| 0 | Aligned within the supplied objective. |
| 1 | Changes requiring review; inspect coexisting gaps as well. |
| 2 | Incomplete evidence without a stronger known finding. |
| 3 | Invalid input/artifact or I/O. |

Argument errors use exit 2. Every comparison rechecks original native artifacts.
The owned reference model independently checks native gate responses and collapse
signatures. Set `OPENTOOLS_FAULT_NATIVE` to the retained collection and run:

```sh
python -m unittest discover -s tests -v
```

Qualification covers the declared injection sites and exact finite legal space.
Commercial ATPG, production collapse rules, transition/delay faults, scan protocols
and signoff require their actual native evidence and separate qualification.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
