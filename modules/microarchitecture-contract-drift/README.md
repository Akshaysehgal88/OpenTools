# Microarchitecture contract drift

Use this module after changing a producer limit, consumer capacity, reservation or
configuration that affects an interface. It reviews the bounded obligation
**maximum required demand ≤ minimum available capacity**, with explicit units,
counting basis and source-backed premises.

This fits in microarchitecture change review and block/integration handoff.
Architecture, RTL and DV owners can use it alongside elaboration and native
behavioral checks. A parameter can remain syntactically valid while its consumer
no longer has enough guaranteed entries, tags or credits.

The activity supplements design calculations, parameter checks and simulation.
It replaces manual current/baseline capacity reconciliation for selected bounds.
It does not infer arbitrary inequalities, prove runtime admission behavior or
establish throughput/latency targets.

## First use without native tools

Python 3.10+ and the standard library suffice. From
`modules/microarchitecture-contract-drift`:

```sh
python -c "from pathlib import Path; Path('.local').mkdir(exist_ok=True)"
python examples/create_example.py .local/capacity-first-use
python contract_review.py review .local/capacity-first-use/current.json .local/capacity-first-use/contract.json --baseline .local/capacity-first-use/baseline.json --json-out .local/capacity-first-use/review.json --markdown-out .local/capacity-first-use/review.md
```

Expected exit: **1**, `review_required`. The synthetic consumer capacity falls
from eight to four while maximum producer demand remains eight. Open Markdown
for the bound and premise disposition; JSON retains exact bindings, per-check
findings, missing bases and descriptive baseline deltas.

The generator's parent must exist. Example directories and report files must be
new. This exercise compares supplied records; it does not execute RTL.
The [native example](examples/native/README.md) supplies actual elaboration/
simulation controls for matching, reduced-capacity and coordinated-demand cases.

## Helpers and features

| Entry point | Responsibility |
|---|---|
| `contract_review.py review RECORD CONTRACT --baseline BASELINE` | Checks scope/digest correspondence, required/available fact units and basis, explicit premises, the selected bound and optional descriptive changes. |
| `contract_review.py digest RECORD` | Prints canonical JSON SHA-256 used by the reviewed contract. |
| `contract_review.py capture-slang` | Captures selected known integral top-level parameter/local-parameter values from actual Slang elaboration, with verified overrides and retained diagnostics. |
| `slang_capacity.py` | The library behind `capture-slang`; use the public CLI rather than treating it as a separate command. |
| `--json-out` / `--markdown-out` | Saves structured and readable review reports; Markdown is also printed. |

## Source the numbers and their meaning

[FORMAT.md](FORMAT.md) defines `opentools.capacity-record.v1`,
`opentools.capacity-contract.v1` and the native mapping.

Each fact has an explicit value, unit, counting/population/interval basis,
numeric evidence and **meaning evidence**. A native `ISSUE_LIMIT=4` export
establishes a value; source review must establish what it bounds in the selected
runtime flow. Null is unknown, never zero.

The contract independently identifies the required/available facts, common unit
and basis, requested scope, current/baseline digests and nonempty premises.
Document maximum unretired demand, guaranteed usable capacity, sharing/reservations,
admission backpressure and retirement/credit-return behavior as applicable.

Per-bank capacity is not aggregate capacity. There is no automatic unit, population
or time-window conversion. A sourced false premise is a finding even when the
numbers fit; missing premise evidence blocks a numeric conclusion.

Baseline deltas describe matched fact IDs with equal units/bases. An absent fact
is not proven removed, and stable IDs do not establish semantic equivalence.

## Capture from a real elaboration

The optional adapter requires Python 3.11+ and **pyslang 12.0.0**:

```sh
python -m pip install -r requirements-native.txt
```

Prepare an integer override object, scope object and mapping from the format.
Each mapping fact names a plain top-level parameter symbol, semantic role ID,
unit, basis and meaning source. Then adapt the paths and identifiers:

```sh
python contract_review.py capture-slang --source design.sv --top selected_top --parameters parameters.json --mapping mapping.json --scope scope.json --record-ref run-1 --revision-ref retained-revision --complete-inputs --output snapshot.json
python contract_review.py digest snapshot.json
```

Use new output/evidence paths with existing parents. Repeat `--source` and
`--dependency` for the inspected input inventory. Top-module integer overrides
are verified; derived local parameters may be read but not overridden. Strings,
real/unknown/negative values and nonparameters are rejected.

Capture retains diagnostics and declared-file hashes before/after extraction.
It does not discover dependency closure. Bind the resulting snapshot only after
reviewing source meaning and applicability; updating a digest is not a correction
to a false premise. Other native tools can provide separately validated normalized
records.

## Integrate into design change review

1. Establish the original capacity obligation and selected interface/mode with
   producer and consumer owners.
2. Trace maximum live demand and minimum usable supply in consumed source/configuration.
   Identify reserved/shared entries and actual admission/retirement premises.
3. Capture resolved numeric facts where supported, preserving the meaning source
   separately from the numeric source.
4. Write the independent check population and premises; bind current/baseline
   records and run the review.
5. Route excess capacity demand, false premises or missing meaning to the owning
   architecture/RTL/configuration source. Confirm behavior in the existing
   native verification flow.
6. Correct and recapture/revalidate. Hand off original intent, source rationale,
   native evidence, reports and owner decisions after relevant limit, sharing,
   configuration or admission changes.

## AI-first adoption

Give a file/tool-enabled assistant [SKILL.md](SKILL.md),
[AI_USAGE.md](AI_USAGE.md), the original interface requirement and actual sources:

> Establish the maximum unretired demand and guaranteed usable capacity in this
> mode. Trace reservations, shared populations, admission and return behavior.
> Capture resolved parameters where supported, and ask for missing meaning or
> dependency evidence before interpreting the inequality.

Use [ONBOARDING.md](../../ONBOARDING.md), module
`microarchitecture-contract-drift` / activity `default`. Your existing AI host
can inspect broader design evidence. Optional DVIT intent/dependency context can
reveal which consumer assumptions a changed limit affects; local use requires none.

## Outcome and native qualification

| Exit | Meaning |
|---:|---|
| 0 | Within declared bounds with required premises/evidence. |
| 1 | Capacity excess or a sourced false premise; accompanying gaps remain. |
| 2 | Incomplete, unbound or inapplicable evidence. |
| 3 | Invalid input, capture or I/O. |

Argument errors use exit 2. A numeric match is not implementation correctness or
release approval.

The native recipe is qualified on Linux with Verilator **5.020**, GCC 13.3,
Make 4.3 and pinned Slang. Credit-window and live-tag profiles each test 8/8,
8/4 and coordinated 4/4 demand/capacity. Independent allocation checks compare
actual native observations. Other protocols, shared banks, return paths and
platforms need their own qualification.

```sh
python -m unittest discover -s tests -v
```

Slang tests skip without the optional package; the native guide describes opt-in
simulation variables. Nothing installs native tools or DVIT automatically.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
