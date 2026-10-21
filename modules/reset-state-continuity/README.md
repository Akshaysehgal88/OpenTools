# Reset sequencing and state continuity

Use this module when reviewing a warm, local or watchdog reset and its restart
path. It asks **what clears, what survives and who owns any surviving work**
before normal activity resumes.

This fits in reset-domain integration, restart/firmware review and DV after reset
scope or initialization changes. Reset, RTL, firmware and verification owners can
use it alongside reset-tree/RDC analysis and native transition traces.

A reset can clear a consumer's context while leaving its producer pending.
Deassertion alone does not establish initialized software or permission to replay
old work. This activity supplements native reset diagnostics and replaces manual
state-by-owner continuity reconciliation for one sampled event.

## First use

Python 3.10+ and the standard library suffice. From
`modules/reset-state-continuity`:

```sh
python examples/create_example.py .local/reset-partial --case warm-partial
python reset_review.py review .local/reset-partial/inventory.json .local/reset-partial/journal.json .local/reset-partial/policy.json --json-out .local/reset-partial/review.json --markdown-out .local/reset-partial/review.md
```

Expected exit: **1**, `review_required`. The producer retains pending work while
the consumer loses context; an orphan effect is observed after release. The report
keeps continuity risk separate from the actual post-reset effect.

Compare resetting both owners:

```sh
python examples/create_example.py .local/reset-both --case warm-reset-both
python reset_review.py review .local/reset-both/inventory.json .local/reset-both/journal.json .local/reset-both/policy.json --json-out .local/reset-both/review.json --markdown-out .local/reset-both/review.md
```

Expected exit: **0**, `within_sampled_reset_contract`. `warm-drain` is another
control: work completes before consumer reset. `watchdog-fresh-start` rejects
retained old work, while `watchdog-replay` explicitly permits and observes replay
under its own readiness contract.

These are owned reference fixtures, not a universal reset policy. Example and
report paths must be new with existing report parents. Open Markdown for the
state-by-owner table and JSON for four-phase values, findings, gaps and replay
permission.

## Helper and records

| Operation | Responsibility |
|---|---|
| `reset_review.py review INVENTORY JOURNAL POLICY` | Checks intended clear/preserve effects, actual reset application, release prerequisites, pending/context continuity and selected post-release expectations. |
| `reset_review.py digest RECORD` | Prints canonical JSON SHA-256 for inventory/journal binding. |
| `--json-out` / `--markdown-out` | Saves structured and readable reports; Markdown is also printed. |

[FORMAT.md](FORMAT.md) defines the inputs:

- **Inventory:** selected scalar state IDs, widths, owners, reset domains and actual
  reset values. Widths are 1–64 bits; unknown values/domains are null.
- **Journal:** original scope/event and four ordered sampled phases:
  `before`, `held`, `released` and `post`. Each retains state values, actual
  asserted reset domains, prerequisites and hardware-quiescence evidence.
- **Policy:** independently sourced clear/preserve/unconstrained expectations,
  required reset application, restart prerequisites, producer-pending/consumer-
  context relationships, identity comparison, explicit replay authority and
  expected post effects.

Preservation is attributed across before/held only with quiescence. The release
sample is before new work changes state; post is a defined bounded observation
window, not every later cycle. Unknown or missing phases remain gaps.

A surviving producer with cleared consumer context is a continuity risk unless
replay is explicitly permitted. Permission alone does not establish readiness;
retain required initialization/clock/replay prerequisites and actual post
expectations. When both contexts survive, supplied identities can expose mismatch.
Do not normalize a reset value to zero merely because it is unknown.

## Integrate into reset/restart review

1. Establish the original reset event, affected mode and restart objective.
   Do not treat warm/local reset as power-on reset because both restart software.
2. Identify selected state owners and the actual reset-domain application.
   Trace producer/consumer context and pending work across that boundary.
3. Retain native reset/state observations at the four defined phases, with
   quiescence and initialization/readiness sources.
4. Source clearing, retention and replay expectations independently of observed
   outcomes. Bind inventory/journal and review the selected contract.
5. Route state effect, missing initialization, identity or orphan findings to
   reset, producer, consumer or firmware owners. Correct the original sequence/
   scope or sourced requirement, rerun and revalidate.
6. Hand off original intent, state mapping, native artifacts, report and receiving
   decision. Repeat after reset scope, retention, initialization or replay changes.

Wrong state normalization or a policy permitting unowned completion can manufacture
agreement; source review remains necessary after a favorable report.

## AI-first adoption and native controls

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), reset/state exports,
restart source and the original transition question:

> Trace what this selected reset clears and preserves for each owner. Establish
> readiness at release and the identity/authority of surviving work. Separate
> continuity risk from an observed orphan, and require explicit intent for replay.
> Ask for missing state, initialization or observation-boundary evidence.

Use [ONBOARDING.md](../../ONBOARDING.md), module `reset-state-continuity` /
activity `default`. Existing AI/native tools suffice. Optional
[context sources](../../CONTEXT_PORT.md), including DVIT, can add scoped state
ownership, retention intent and dependent restart assumptions; local use needs none.

The [native controls](examples/NATIVE.md) use Linux, Verilator 5.020 and a C++/Make
toolchain. Five owned instances with independent producer/consumer resets supply
twenty phase rows, checked by an independent reset/delivery reference.
Initialization behavior in that fixture is not a general firmware assumption.

## Outcome and limits

| Exit | Meaning |
|---:|---|
| 0 | Within the supplied sampled reset contract. |
| 1 | Known state, reset, readiness, continuity or post-effect finding. |
| 2 | Incomplete scope, phase or original requirement. |
| 3 | Invalid input or I/O. |

Argument errors use exit 2. Findings retain coexisting gaps; continuity risk alone
is not proof of an actual stale completion.

The helper covers four sampled phases and explicit scalar pending/context
relationships. Arbitrary reset trees, synchronizers, transaction ownership,
analog recovery/removal, X behavior, physical RDC and exhaustive restart/replay
need their own native methods and qualification.

```sh
python -m unittest discover -s tests -v
```

The native guide explains opt-in tool variables. Ordinary saved-data review needs
no simulator.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
