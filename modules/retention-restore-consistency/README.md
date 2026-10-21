# Retention and restore consistency

Use this module when accepting a retained structure or a wake/restore sequence.
It asks whether the **state bundle required by the consumer** is coherent before
exposure, and whether actual post-wake reads return the intended result.

This fits in low-power integration, state-retention review and DV after selection,
restore or initialization changes. Design, power-sequence and consumer owners can
use it alongside retention selection reports and native power-aware methods.
Preserved valid/identity metadata with lost payload can produce a hit on wrong
data; correct final state can also conceal an earlier invalid access.

The activity supplements retention and restore verification. It replaces manual
bundle/exposure/read reconciliation for one selected logical window. It does not
validate retention cells or infer the intended bundle from the selection list.

## First use

Python 3.10+ and the standard library suffice. From
`modules/retention-restore-consistency`:

```sh
python examples/create_example.py .local/restore-metadata --case cache-metadata-only
python restore_review.py review .local/restore-metadata/inventory.json .local/restore-metadata/journal.json .local/restore-metadata/policy.json --json-out .local/restore-metadata/review.json --markdown-out .local/restore-metadata/review.md
```

Expected exit: **1**, `review_required`. Metadata survives while payload is
lost; the owned consumer read hits but returns the wrong value. Open Markdown
for member/exposure findings and JSON for expected values, selections, actual
reads, first mismatch witnesses and gaps.

Compare paired retention:

```sh
python examples/create_example.py .local/restore-paired --case cache-paired
python restore_review.py review .local/restore-paired/inventory.json .local/restore-paired/journal.json .local/restore-paired/policy.json --json-out .local/restore-paired/review.json --markdown-out .local/restore-paired/review.md
```

Expected exit: **0**, `within_observed_restore_contract`. Other cases cover
payload-only selection, dirty-metadata loss, valid-before-initialization,
initialization before valid publication, explicit cold rebuild and a context/
owner bundle. These are applications of the same review activity.

Examples and report paths must be new with existing report parents. The fixtures
are source-defined reference data; no native tool is executed.

## Helper and records

| Operation | Responsibility |
|---|---|
| `restore_review.py review INVENTORY JOURNAL POLICY` | Checks selected bundle members at ready/exposure, prerequisites, actual request/response attribution and expected hit/error/data across one observed loss/wake window. |
| `restore_review.py digest RECORD` | Prints canonical JSON SHA-256 for inventory/journal bindings. |
| `--json-out` / `--markdown-out` | Saves structured/readable handoff reports; Markdown is also printed. |

[FORMAT.md](FORMAT.md) defines:

- **Inventory:** state identity, width, role/owner, power/reset domain, observed/
  reviewed `retained/lost/unknown` selection and its source basis.
- **Journal:** pre-loss snapshot and complete isolated window, actual selected
  loss and wake, state values, consumer/restore controls and attributed read
  requests/responses.
- **Policy:** independent consumer bundles, eligibility, ready requirement,
  required members/roles, preserve-before or explicit constant expectation,
  prerequisites and expected read hit/error/data source.

Selection says what survives; obligation says what the consumer needs.
Lost members can be rebuilt before exposure, and cold restart can legitimately
have a different contract from warm resume. Source the original before image and
reinitialized values independently; never substitute reset values for unknown
saved state.

Members are checked when ready is declared or the powered enabled consumer is
eligible. Preserve early exposure history even if a later ready/final snapshot
matches. A required unobserved read remains incomplete. Actual response data is
compared with the expected bundle member, not with today's live field or a
software buffer.

Scalars are unsigned 1–4096 bits with explicit nulls for unknowns. Use lossless
integer handling. Separate read request/response samples retain the same identity;
unattributed responses cannot become invented reads or a liveness conclusion.

## Integrate into retention/wake review

1. Establish the original consumer obligation and warm/cold contract. Include
   payload, identity/owner, validity, dirty/status and initialization dependencies.
2. Inspect retention selection and restore source with the relevant owners.
   Maintain required members independently of the observed selection export.
3. Capture pre-loss state and the actual loss/wake/exposure sequence, including
   early accesses and native read responses.
4. Bind records and review selection, restored member values, readiness and
   consumer outcome separately.
5. Correct the original selection/restore/initialization or sourced requirement,
   then rerun and revalidate. A later correct state does not erase an earlier fault.
6. Hand off original intent, source mapping, native evidence, report and receiving
   decision. Repeat after bundle, selection, restore or exposure changes.

Cold discard needs explicit authority and dirty-state handling. It is not a
universal repair for lost retention. Dirty metadata loss can violate the bundle
even when read data is correct; that alone does not prove an observed writeback
failure.

## AI-first adoption and native controls

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), consumer requirements,
selection/restore source and native observations:

> Identify the state bundle this consumer needs after wake. Compare payload with
> identity/valid/owner/status and initialization dependencies. Trace actual loss,
> rebuild, exposure and reads; distinguish legitimate cold restart from warm
> preservation. Ask for missing before-state or early-access evidence.

Use [ONBOARDING.md](../../ONBOARDING.md), module
`retention-restore-consistency` / activity `default`. Existing AI/native methods
suffice. Optional [context sources](../../CONTEXT_PORT.md), including DVIT, can
connect scoped bundle, restore-order and consumer intent; local operation requires none.

The [native controls](examples/NATIVE.md) use Linux, Verilator 5.020 and a C++/Make
toolchain. Nine cases/108 rows are checked by an independent image/loss/rebuild
reference and actual reads. The fixture uses an 8-bit payload; the wider scalar
comparison is separately tested.

## Outcome and limits

| Exit | Meaning |
|---:|---|
| 0 | Within the supplied observed restore contract. |
| 1 | Known member, exposure, prerequisite or read finding. |
| 2 | Incomplete source, window, expectation or consumer observation. |
| 3 | Invalid input or I/O. |

Argument errors use exit 2. Findings retain coexisting gaps.

Selective logical assignment-to-zero is not power-aware simulation or retention-cell
validation. Arbitrary UPF/vendor extraction, ECC encoding, X propagation, analog
power, physical timing and multiple loss cycles need their own native methods.
A logical initialization-ready bit does not establish a real ECC implementation.

```sh
python -m unittest discover -s tests -v
```

The native guide explains opt-in tool variables. Saved-data review needs no
simulator or DVIT installation.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
