# Erratum and workaround review

Use this activity before applying, retaining, removing or carrying forward a
**supplied** workaround. It keeps underlying applicability, observed behavior,
mitigation efficacy, dependent premises and current approval correspondence
separate.

This fits in silicon/firmware maintenance and validation handoff. Erratum,
firmware, validation and receiving owners can use it alongside their existing
notice and change-control process. A passing mitigated run does not erase the
underlying vulnerable condition; a nominally fixed stepping can still use a
vulnerable producer path.

The activity supplements notice review and native validation. It replaces manual
reconciliation of selected notice conditions, current evidence and dependent
workaround premises. It does not discover real errata, authenticate approval or
authorize a software/release change.

## First use

Saved-data review needs Python 3.10+ and the standard library. Run from
`modules/result-applicability/profiles/erratum-workaround`. Use a complete
retained collection at `.local/erratum-native`, or generate one on Linux with
existing **Ubuntu GCC 13.3.0**:

```sh
python examples/run_native.py .local/erratum-native --cxx /usr/bin/g++
```

Replace the compiler path if needed. The recipe installs nothing and needs a new
output. Twenty-four owned C++ model runs cover two guard-interval contexts;
twelve additional reviews reuse them for approval/removal/stronger-claim questions.

Review an affected, unmitigated observation:

```sh
python erratum_review.py review .local/erratum-native .local/erratum-native/ordering-boundary-affected-unmitigated/capture-notice.json .local/erratum-native/ordering-boundary-affected-unmitigated/capture-request.json --json-out .local/erratum-native/unmitigated-review.json --markdown-out .local/erratum-native/unmitigated-review.md
```

Expected exit: **1**, `REVIEW_REQUIRED`. The synthetic notice applies and the
selected observation lacks the required mitigation.

Compare the mitigated control and inspect its retained run:

```sh
python erratum_review.py review .local/erratum-native .local/erratum-native/ordering-boundary-affected-mitigated/capture-notice.json .local/erratum-native/ordering-boundary-affected-mitigated/capture-request.json --json-out .local/erratum-native/mitigated-review.json --markdown-out .local/erratum-native/mitigated-review.md
python erratum_review.py capture .local/erratum-native ordering-boundary-affected-mitigated --output .local/erratum-native/recaptured-mitigated.json
```

Expected review exit: **0**, `REVIEW_PACKET_ACCOUNTED`. This accounts for the
stated bounded review inputs; it grants no authority to remove, deploy or release.
Open Markdown for interpretation and JSON for applicability truth, original native
outcome, mitigation/interaction/approval correspondence, findings and gaps.

The notice `OWNED-E001` and device are **synthetic**. These results are not
claims about a real vendor erratum. Outputs must be distinct new paths. Capture
reads artifacts without executing the archived binary or source.

## Helper and required inputs

| Operation | Responsibility |
|---|---|
| `erratum_review.py capture ROOT RUN_REF --output FILE` | Validates original source/context/invocation and retained native event evidence, producing facts plus a parent result snapshot. |
| `erratum_review.py review ROOT NOTICE REQUEST --json-out JSON --markdown-out MD` | Evaluates the supplied applicability predicate, composes source/result correspondence and checks mitigation, dependent premises, intent and approval scope separately. |

[FORMAT.md](FORMAT.md) and the [owned fixture](examples/fixture.py) define
the full records.

The notice identifies version/source/owner, one applicability predicate, scoped
guard intervals, ordering/clock mitigation premises and one dependent exception.
Supported predicate operations are typed equality, finite membership, `all`
and `any` within explicit bounds. No arbitrary expression or code executes.
Each relationship/leaf needs a source basis. Unknown readout or rule sources
remain unknown; a decisive false/true branch can determine the selected condition
without inventing unresolved sibling facts.

The independent request records original question/owner/scope, current review cut,
`apply/retain/remove` intent, selected notice profile/digest, native/source/
context/invocation bindings and required model/image/guard fields.

An optional existing approval must correspond to notice digest, scope, mode,
image, intent and review cut. Missing, pending, withdrawn and stale approval are
different conditions. Matching declarations do not authenticate authority.

## Integrate into workaround maintenance

1. Obtain the actual supplied notice and original maintenance question. Establish
   affected conditions, model/stepping/configuration and intended action.
2. Retain current consumer-visible readouts, consumed image/source identity and
   actual behavior. Do not substitute a private model value for an unreadable
   device fuse or status field.
3. Review underlying applicability separately from mitigation. A workaround label
   does not establish actual ordering or sufficient active guard ticks.
4. Inspect dependent exceptions/premises. A primary mitigation that forces a clock
   can invalidate a separate clock-idle assumption.
5. Compare current approval scope and review cut through your existing process.
   Route efficacy, interaction or authority gaps to their owners; do not infer
   removal permission from an apparently fixed revision.
6. Recollect/revalidate after source, image, condition, notice or premise changes.
   Keep the original captured notice/request immutable; create a new query for
   a changed question while preserving old source identities.
7. Hand off original notice, request, artifacts, findings/gaps and receiving
   decisions. The tool writes no firmware or device changes.

The owned producer interprets a bounded command image, not an ISA.
`BASE_FENCE` precedes workaround logic; `WA_FENCE` does not retroactively
repair the baseline-order condition. Guards use observed active-clock ticks,
not only the requested argument. Native checker PASS/FAIL remains separate from
process completion and applicability.

## AI-first adoption and outcome

Give a file/tool-enabled assistant [WORKFLOW.md](WORKFLOW.md), supplied notice,
original maintenance intent, current image/readouts and native observations:

> Determine whether this notice still applies and what evidence supports the
> intended apply/retain/remove decision. Separate underlying condition, observed
> efficacy, dependent premises and current approval. Ask for missing readouts or
> scope rather than inferring permission from a passing mitigated run.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module `result-applicability` /
activity `erratum-workaround`. Existing AI/native maintenance methods suffice.
Optional DVIT intent/dependency context can expose stale workaround assumptions
and dependent exceptions; local use requires none.

| Review exit | Meaning |
|---:|---|
| 0 | Review packet accounted within the stated bounded scope. |
| 1 | Known efficacy/timing/interaction/intent/approval finding or inapplicable evidence. |
| 2 | Missing or unknown condition, source or stronger-claim evidence. |
| 3 | Invalid/changed native input or I/O. |

Argument errors use exit 2. Findings retain gaps; contrary source/scope evidence
is quarantined rather than attributed to the requested configuration.

Qualification covers one supplied notice, one owned C++17 event path and dependent
premise per operating observation. Real silicon, firmware ISA execution, power,
all-mode verification, safety and approval authentication require their own
native evidence/process. No status authorizes removal or release.

Set `OPENTOOLS_ERRATUM_NATIVE` to the retained collection and run:

```sh
python -m unittest discover -s tests -v
```

Native-corpus tests otherwise skip. Ordinary saved-data review needs no compiler
or DVIT connection.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
