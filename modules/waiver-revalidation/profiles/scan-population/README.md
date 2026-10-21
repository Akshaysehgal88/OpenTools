# Scan population and exclusion audit

Use this activity after scan insertion, reordering or an exclusion change.
It reconciles **independently required functional state with actual native chain
membership and current non-scan rationale**.

This fits in DFT insertion/closure and exclusion revalidation. DFT, state/clock
and receiving owners can use it alongside native scan reports. Successful
insertion does not mean every required state element entered scan; non-required
intent alone does not justify an unscanned element.

The activity supplements native DFT and the parent waiver review. It replaces
manual state/membership/exclusion reconciliation, not ATPG or fault-coverage
analysis. Historical exclusion drift is separate from the current membership
decision.

## First use

Saved-data review needs Python 3.10+ and the standard library. Run from
`modules/waiver-revalidation/profiles/scan-population`. Use a complete retained
collection at `.local/scan-native`, or collect one on Linux with existing
**OpenROAD v2.0-17598-ga008522d8** and its runtime:

```sh
python examples/run_native.py .local/scan-native --openroad /path/to/openroad
```

Replace the executable path. The recipe installs nothing and needs a new output.
Owned four-element single-clock and eight-element mixed-clock partitions exercise
complete membership, omitted required state and changing exclusion premises.

Capture and review the complete population:

```sh
python scan_population.py capture .local/scan-native control-bank-complete/run .local/scan-native/control-bank-complete/context.json --output .local/scan-native/control-bank-complete/recaptured.json
python scan_population.py review .local/scan-native .local/scan-native/control-bank-complete/contract.json .local/scan-native/control-bank-complete/recaptured.json --json-out .local/scan-native/control-bank-complete/new-review.json --markdown-out .local/scan-native/control-bank-complete/new-review.md
```

Expected review exit: **0**, `BOUNDED_POPULATION_ACCOUNTED`. Native census,
required roster and chain membership account for all four state elements.

Compare a missing required flop:

```sh
python scan_population.py review .local/scan-native .local/scan-native/control-bank-missing-required/contract.json .local/scan-native/control-bank-missing-required/evidence.json --json-out .local/scan-native/control-bank-missing-required/new-review.json --markdown-out .local/scan-native/control-bank-missing-required/new-review.md
```

Expected exit: **1**, `MEMBERSHIP_REVIEW_REQUIRED`, although native insertion
completed. The `control-bank-allowed-exclusion` control accounts for three scan
members plus one explicitly admitted unscanned state, retaining all four in the
denominator.

Review historical exclusion drift separately:

```sh
python scan_population.py drift .local/scan-native .local/scan-native/control-bank-allowed-exclusion/evidence.json .local/scan-native/control-bank-obsolete-role/evidence.json --output .local/scan-native/exclusion-drift-new.json
```

Expected exit: **1**: the old exclusion's role premise no longer applies.
Open Markdown for membership/exclusion rows and JSON for original insertion status,
counts, findings/gaps and the embedded parent drift audit.

Both membership report flags are required. Outputs must be distinct new files.
Capture exit 0 means a completed readable insertion, not all-state acceptance.
Original commands/Tcl/databases are read as data, never executed.

## Helper and independent records

| Operation | Contribution |
|---|---|
| `scan_population.py capture ROOT WORKDIR CONTEXT --output FILE` | Checks native sequential census, ODB pin/serialized-netlist correspondence and actual stitched plan paths. |
| `scan_population.py review ROOT CONTRACT EVIDENCE` | Revalidates originals, compares independent required-state roster and admits only applicable current exclusions. |
| `scan_population.py drift ROOT BASELINE CURRENT --output FILE` | Normalizes selected unscanned-state observations into the existing waiver comparator, retaining definition/premise changes and missing rationale. |

Start with [context](templates/context.json), [contract](templates/contract.json),
[population](templates/population.json) and
[exclusions](templates/exclusions.json). [FORMAT.md](FORMAT.md) defines the full
artifact package.

The independent population maps each required state one-to-one to a native
instance and records scan requirement, role, mapped clock, logical power group
and basis. A “complete” roster omitting a native sequential element remains
incomplete.

Exclusions separately retain instance, reason/rationale revision, approval/source
and required role/clock/power-group premises. Required state cannot be exempted
by a contradictory record. Non-required state needs a matching current exclusion
and supported premises before admission. Stale scope admits none.

Context/contract bind original run/native sources/command and independent
intent identities. Unknowns remain gaps; contrary native identity quarantines
attribution. Hashes identify content, not source authority or production approval.

## Integrate into scan closure

1. Establish original required functional state and receiving scope independently
   of scan output, with design/DFT owners.
2. Retain pre/post native census, netlist/ODB connectivity and actual DFT plan.
   Confirm functional pin connections survive insertion.
3. Source current exclusions and role/clock/logical-power premises separately.
   Keep unscanned state visible in the full population.
4. Capture and review membership first. Use historical drift as additional
   evidence, not a substitute for the current intent comparison.
5. Correct native setup, exclusion rationale or sourced requirement with owners,
   rerun/reassociate evidence and revalidate.
6. Hand off original population, native artifacts, exclusions, reports, gaps and
   receiving decisions. Repeat after insertion, mapping, clock or role changes.

A derived packet can pair unchanged native artifacts with newer independently
applicable intent while preserving the original packet/source identities.
Record that association; it is not a new insertion run or automatic approval.
Do not replace native inputs while keeping stale output.

## AI-first adoption and outcomes

Give a file/tool-enabled assistant [WORKFLOW.md](WORKFLOW.md),
[GUIDE.md](GUIDE.md), original required-state source and native scan/exclusion data:

> Reconcile required functional state with actual chain membership. Inspect
> current role/clock/group premises for every unscanned element, preserve missing
> roster entries and distinguish insertion completion from receiving acceptance.
> Review historical exclusion drift without dropping current obligations.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module `waiver-revalidation` /
activity `scan-population`. Existing AI/native tools suffice. Optional DVIT
intent/dependency context can connect state roles and exclusion rationale to
current product/test intent; independent use requires none.

| Membership exit | Meaning |
|---:|---|
| 0 | Bounded selected population accounted. |
| 1 | Known membership or premise finding. |
| 2 | Incomplete/quarantined evidence. |
| 3 | Invalid/changed input or I/O. |

Argument errors use exit 2. Drift uses the parent's 0/1/2 unchanged/review/
incomplete outcomes. Neither command approves an exclusion.

The reader supports flat scalar reset-capable mapped cells, rising-edge chains
and explicit clock roots, with the pinned loader/tool/library. Its 1–256-element
reader bound is not production qualification of every design. Multibit/multiedge,
ambiguous serial branches and other cells/loaders need another native method.
Logical power groups are source intent, not UPF or supply-network evidence.

Set `OPENTOOLS_SCAN_POPULATION_EXAMPLE` to the retained collection and run:

```sh
python -m unittest discover -s tests -v
```

Saved-data review works on Windows/Linux. Native-corpus tests otherwise skip.
Membership establishes no ATPG observability, fault coverage, defect detection
or production signoff.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
