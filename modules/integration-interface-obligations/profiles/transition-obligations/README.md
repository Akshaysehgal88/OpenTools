# Protocol transition obligations

Use this activity to review one transaction from request through **accepted
ownership/completion token and actual consumer use**. It keeps an explicit ledger
of which source still owes a release or data receipt in the selected transaction
and epoch.

This belongs in coherence/ownership integration, reclamation/completion review
and revalidation after acknowledgement, transient-state or backpressure changes.
Design and DV owners can use it alongside native protocol checkers and the parent
[interface activity](../../README.md). Stable-state labels and numerical pending
counts do not establish that the correct sources discharged their obligations.

The review supplements the original protocol contract and native observations.
It replaces manual distinct-source receipt/permission reconciliation for the
selected exclusive-handoff profile. It does not infer a protocol from an industry
name or implement a general coherence engine.

## First use

Python 3.10+ and the standard library suffice; Slang is not required. Run from
`modules/integration-interface-obligations/profiles/transition-obligations`:

```sh
python examples/create_example.py .local/transition-early --case directory-premature-grant
python transition_review.py .local/transition-early/model.json .local/transition-early/journal.json .local/transition-early/policy.json --output .local/transition-early/review.json
```

Expected exit: **1**, `review_required`. A new exclusive user receives usable
permission while an old reader still holds rights. Later acknowledgements and a
good final state do not erase earlier grant/use conflicts. Inspect grants,
remaining obligations, actual reads, event ledger, findings and gaps in the JSON.

Compare a completed handoff:

```sh
python examples/create_example.py .local/transition-complete --case directory-complete
python transition_review.py .local/transition-complete/model.json .local/transition-complete/journal.json .local/transition-complete/policy.json --output .local/transition-complete/review.json
```

Expected exit: **0**, `within_observed_contract`. Both distinct old-holder
releases and returned data precede accepted grant and consumer use.

Other controls cover late data, duplicate/stale acknowledgements, offered grants
under backpressure, and a two-worker ring's reclaim frontier. Example directories
and report files must be new; the generator also writes `report.json`.

## Helper and typed evidence

`transition_review.py MODEL JOURNAL POLICY` replays the selected event ledger,
checks grant/finish prerequisites, actual permission overlap and consumer data,
and compares reported counters with distinct-source release obligations.
`--output` saves JSON to a new file; omit it to print JSON. It executes no native
commands.

[FORMAT.md](FORMAT.md) defines the inputs:

| Record | What it contributes |
|---|---|
| Model | Resource, grantor/requestor, request/grant/completion classes, selected transaction/epoch, participants, original holders and typed release/data obligations. |
| Journal | Original accepted/offered messages, source/class/resource/ID/epoch, actual old/new rights, data/read/write effects, pending masks/counts and closed isolated window. |
| Policy | Independent required participants/holders/obligations, intended frontier, returned-data requirement, original expected value and accepted consumer milestones. |

The required population comes from the source contract, not the smaller observed
receipt set. Scope includes project/configuration/mode/protocol/transaction/epoch.
Canonical model/journal bindings preserve correspondence; unknown acceptance,
rights or identity stay explicit gaps.

Receipt credit requires the current resource, transaction, epoch, source and
message class. A release also needs observed permission revocation; data needs
observed availability. Unknown bytes remain a data gap without converting a known
receipt into an absent message. Duplicate credit from one source cannot discharge
another source's obligation. Foreign replies remain visible as ignored.

Only **accepted** grants cross the usable-permission frontier. An offered token
under backpressure does not authorize use. Permission revocation before its later
acknowledgement is allowed, but does not discharge that acknowledgement.
Pending counts cover distinct releases, not combined data/message traffic.
Actual conflicting permissions are checked independently of debug state labels.

## Integrate into a transition review

1. State the original ownership/completion frontier and consumer authority with
   the protocol owner. Identify the old holders and separately required data.
2. Inspect source rules for transaction/epoch identity, message classes, release
   effects and accepted grant. Keep these independent of the received log labels.
3. Retain native messages and actual permission/data/consumer observations across
   a clean isolated epoch, including backpressure and required terminal activity.
4. Normalize into the documented profile or use another validated method for your
   native protocol. Preserve simultaneous messages and asynchronous grant
   acceptance; do not hide them behind one aggregate operation.
5. Review outstanding and uncertain obligations at accepted grant/finish, duplicate
   or foreign receipts, counter discrepancies and actual consumer conflicts.
6. Correct the implementation, instrumentation or sourced contract, rerun and
   revalidate. Keep earlier violations even when later receipts complete the ledger.
   Hand off original sources, records, report and owner decision together.

An uncertain receipt cannot prove a premature completion by itself. Known
permission conflicts or other findings retain coexisting gaps. Stale/foreign scope
bindings provide no valid current ledger.

## AI-first adoption

Give a file/tool-enabled assistant [WORKFLOW.md](WORKFLOW.md), the original
protocol version, transient-state rules and native observations:

> Establish what must finish before this token permits exclusive use or reuse.
> Track each required source and message class by transaction and epoch. Check
> actual revocation, grant acceptance and consumer effects, rather than stable
> labels or zero pending counts. Ask for missing identity/permission evidence.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module
`integration-interface-obligations` / activity `transition-obligations`.
Existing AI hosts can review broader company-native evidence. Optional
[context sources](../../../../CONTEXT_PORT.md), including DVIT, can connect scoped
protocol, ownership and dependent-consumer obligations; they are not required.

## Native controls, outcome and limits

The [native controls](examples/NATIVE.md) use Linux, Verilator 5.020 and a C++/Make
toolchain. Eight cases produce 84 observations checked by an independent set-based
ledger. Directory mode needs two distinct releases and data; ring mode needs both
worker completions before reclaim/rewrite, with no returned-data property.
These are two applications of the same workflow frontier.

| Exit | Meaning |
|---:|---|
| 0 | Within the selected observed contract. |
| 1 | Known receipt, prerequisite, permission or consumer finding. |
| 2 | Incomplete identity, observation, scope or original requirement. |
| 3 | Invalid input or I/O. |

Argument errors use exit 2. Findings retain gaps. Favorable selected observations
do not establish complete MSI/CHI/AXI behavior, arbitrary descriptor translation
or unbounded liveness.

The owned model serializes selected command events and backpressures grant. Retry,
cancellation, eviction, reset overlap, multi-channel ordering and fairness require
their own source rules and native qualification.

```sh
python -m unittest discover -s tests -v
```

The native guide explains opt-in tool variables. Run these tests separately from
the parent's selected-port tests.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
