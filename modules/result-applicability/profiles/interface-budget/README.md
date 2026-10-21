# Interface timing budget review

Use this activity after block-to-top timing allocations, reference edges, loads
or models change. It reconciles the **original allocation with both block views
and the integrated path**, retaining timing debt and its owning source.

This fits in hierarchical timing handoff between block and top STA owners.
It supplements native timing reports and allocation review. It replaces manual
three-view reconciliation for a selected scalar interface; it does not generate
SDC, schedule jobs or establish all-path closure.

Two permissive block budgets can each pass while their integrated path fails.
Conversely, coherent assumptions can agree yet retain a real timing deficit.
The review separates budget consistency from actual timing success.

## First use

Saved-data review needs Python 3.10+ and the standard library. Run from
`modules/result-applicability/profiles/interface-budget`. Use a complete retained
collection at `.local/budget-native`, or generate one on Linux with existing
**OpenROAD v2.0-17598-ga008522d8** and its runtime:

```sh
python examples/run_native.py .local/budget-native --openroad /path/to/openroad
```

Replace the executable path. The recipe installs nothing. Forty-two native views
cover full-cycle rising and opposite-edge contexts, each with upstream, downstream
and integrated-top evidence. Output must be new.

Review independently permissive block budgets:

```sh
python budget_review.py review .local/budget-native .local/budget-native/packets/rising-cycle-permissive.json --json-out .local/budget-native/permissive-review.json --markdown-out .local/budget-native/permissive-review.md
```

Expected exit: **1**, `BUDGET_REVIEW_REQUIRED`. The block views pass under their
permissive assumptions while the integrated path fails. Open Markdown for the
timeline/relationships and JSON for all three native outcomes, projection,
findings, gaps and recheck triggers.

Compare the shorter coherent control and inspect one view:

```sh
python budget_review.py review .local/budget-native .local/budget-native/packets/rising-cycle-coherent.json --json-out .local/budget-native/coherent-review.json --markdown-out .local/budget-native/coherent-review.md
python budget_review.py capture .local/budget-native rising-cycle-coherent-upstream --output .local/budget-native/recaptured-upstream.json
```

Expected review exit: **0**, `BOUNDED_INTERFACE_AGREEMENT`. Capture exit 0 means
a readable bound observation, not acceptance. The `rising-cycle-coherent-slow`
control keeps consistent budgets but returns 1 for actual timing debt.
Wrong load, reference edge, library/model and unknown mode have separate controls.

Both report flags are required. Choose distinct new paths and keep the complete
original run directories. Saved-data intake executes no archived Tcl.

## Helper and independent contract

| Operation | Contribution |
|---|---|
| `budget_review.py capture ROOT RUN_REF --output FILE` | Validates original native source/setup/report evidence and emits native facts plus a parent applicability snapshot. |
| `budget_review.py review ROOT CONTRACT --json-out JSON --markdown-out MD` | Checks each bound view, complete mapped cones and explicit timing/load relationships against the original interface allocation. |

[FORMAT.md](FORMAT.md) defines `opentools.interface-budget-contract.v1` and the
qualified native package. The contract independently records:

- Original scope, owner/requirements, upstream/downstream/top run and consumed
  source/invocation identities.
- Clock mapping, latency/projection basis, handoff deadline/load, capture
  requirement and launch arrival.
- One-to-one cell correspondence, actual boundary pins and requested result fields.

A null selected run or relationship remains unresolved. Stronger requested fields
are preserved as unknown, never silently removed.

The native export retains actual expanded-clock source/target edges, selected
arrivals/deadlines/margins, cases, operating conditions, waveform, port capacitance
and connectivity. Native `report_net` supplies integrated boundary capacitance
and driver/load counts. Time uses **ns** and capacitance **pF**. Output delay and
register setup margin retain different meanings.

The parent comparator uses `any_observed` per view, so a failed native observation
remains valid evidence with its failure preserved. Known model/identity differences
prevent cross-view composition; they cannot become an unexplained timing delta.

## Integrate into block/top handoff

1. Establish the original allocation and receiving requirement with upstream,
   downstream and top owners. Identify the actual source/capture edges.
2. Retain the consumed models, clock/case setup, native reports and source
   identities for all three views.
3. Review cell/boundary correspondence and actual load assumptions. Keep input/
   output delay, launch arrival, capture requirement and integrated margin distinct.
4. Run the review. Separate assumption mismatch, load/reference/model differences,
   missing premises and actual coherent timing debt.
5. Correct the owning allocation, model, setup or implementation through the
   existing timing flow, then regenerate and revalidate affected views.
6. Hand off the original contract, native artifacts, relationship/timeline report,
   remaining debt and owner decisions. Repeat after budget, edge, load or model changes.

The native process exit is insufficient by itself: completion markers, producer/
version/setup and artifact checks must also agree. Byte bindings do not establish
source authority or report sufficiency.

## AI-first adoption and outcomes

Give a file/tool-enabled assistant [WORKFLOW.md](WORKFLOW.md), the original budget,
block/top setup and native reports:

> Reconcile this interface allocation across both blocks and top. Trace actual
> reference edges, launch/capture requirements, boundary mapping and loads.
> Distinguish inconsistent assumptions from coherent timing debt, and identify
> the owning source of each required correction.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module `result-applicability` /
activity `interface-budget`. Existing AI/timing tools suffice. Optional DVIT
intent/dependency context can connect allocation changes to original performance
requirements and dependent consumers; it is not required.

| Review exit | Meaning |
|---:|---|
| 0 | Bounded agreement of selected views and allocation. |
| 1 | Actual timing debt or known budget/correspondence finding; gaps remain. |
| 2 | Missing/unresolved premises or quarantined evidence. |
| 3 | Invalid/changed native package or I/O. |

Argument errors use exit 2. A matching allocation does not grant signoff.

Qualification covers one fresh flat, single-library/single-clock mapped scalar
buffer interface, one max-setup path per view, one driver/load and zero annotated
wire capacitance at the boundary. Owned models and unannotated interconnect
illustrate correspondence, not characterized silicon timing. Hold, macro/multicycle,
mixed libraries, OCV/derates, extracted RC, functional equivalence and frequency/
all-path claims need separately qualified native evidence.

Set `OPENTOOLS_INTERFACE_BUDGET_NATIVE` to the retained collection and run:

```sh
python -m unittest discover -s tests -v
```

Native-corpus tests otherwise skip. Saved-data review needs no native engine or
DVIT connection.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
