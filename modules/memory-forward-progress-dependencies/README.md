# Memory forward-progress dependencies

Use this module when a transaction class retains resources while requesting more,
and an integration review needs to distinguish a **candidate wait cycle from
observed blocking**. It follows resource allocation, release and escape paths
through one finite episode.

This fits in microarchitecture resource/deadlock review, credit/queue integration
and validation of a stalled transaction path. Design, interconnect, memory and DV
owners can use it alongside native protocol analysis and formal methods.
A cyclic graph or a flat waveform alone is not a deadlock proof.

The workflow supplements allocation/credit analysis and native observations.
It replaces manual reconciliation of selected holds, requests, capacities and
release enables. It does not infer dependencies from arbitrary RTL or implement
a general liveness engine.

## First use

Python 3.10+ and the standard library suffice. From
`modules/memory-forward-progress-dependencies`:

```sh
python examples/create_example.py .local/progress-opposite --case coherence-opposite
python progress_review.py .local/progress-opposite/model.json .local/progress-opposite/journal.json .local/progress-opposite/policy.json --output .local/progress-opposite/review.json
```

Expected exit: **1**, `review_required`. Both owned transactions retain their
first single-slot resource and request the other's. The report separates the
static `candidate_cycles` from conditional `blocking_witnesses` backed by
observed holdings, capacities/enables and the declared closed-model premises.

Compare an escape:

```sh
python examples/create_example.py .local/progress-escape --case coherence-escape
python progress_review.py .local/progress-escape/model.json .local/progress-escape/journal.json .local/progress-escape/policy.json --output .local/progress-escape/review.json
```

Expected exit: **0**, `within_observed_contract`. A separate resource permits
progress. `coherence-release-before-wait` is another control; it drops the first
resource before requesting the next.

The `coherence-serialized` case completes in the observed trace but retains a
static candidate cycle. `coherence-starved-escape` has an enabled action left
unscheduled: finite completion fails without establishing terminal blocking.
External reclaim and unknown environment closure are also distinct cases.
Example/report paths must be new. The generator saves its own `report.json`;
use `review.json` for the fresh CLI result.

## Helper and records

`progress_review.py MODEL JOURNAL POLICY` computes static retained-wait cycles,
available quantities, derived/observed enables, actual wait edges, conditional
blocking and the selected finite completion obligation. `--output` writes JSON
to a new file; omit it to print JSON. No native command is executed.

[FORMAT.md](FORMAT.md) defines:

| Input | Original source needed |
|---|---|
| Model | Resource/actor roster, capacities and units, mode-active retained waits, release conditions, internal/external update assumptions and explicit external release actions. |
| Journal | Reachable-prefix basis, closed observation window, each actor's actual holdings/requests, pending/completion and release/advance enables, plus external enables. |
| Policy | Independent required resource/actor populations, role/unit identities, selected consecutive samples and whether completion is required at the end. |

The helper supports 1–64 resources and actors, capacities 1–4096 and explicit
nonnegative counts. Only known active waits that retain resources enter the
static graph. Unknown guards or retention meanings remain gaps.

Free capacity is total capacity minus all observed holdings. A request must fit
the available quantities; observed advance enables are checked against that
derived condition. Negative free capacity or conflicting enables cannot qualify
a blocking snapshot.

A conditional blocking witness needs pending work, no enabled internal progress,
an actual retained-wait cycle, no enabled external release, complete observations
and reviewed reachability/closure premises. Those premises include complete
resource/release coverage and absence of autonomous/external updates.
Fair scheduling is separate and is never inferred from a finite trace.

## Integrate into resource review

1. Select the original traffic/transaction class and completion obligation.
   Identify every owner and resource unit, including shared queues and credits.
2. Inspect allocation and release source. Record what is retained while waiting,
   which mode activates it, and completion/early release/cancel/timeout/escape
   paths relevant to the selected episode.
3. Retain an actual reachable prefix and observations of quantities and enables.
   Do not manufacture reachability or fairness from a stalled snapshot.
4. Maintain the required resource/actor roster independently of the observed list.
   State closure assumptions with source evidence; list legal external reclaim.
5. Review static cycles, observed blocking, enabled-but-unscheduled work and
   finite noncompletion separately with the owning designer.
6. Correct the original allocation/release path or sourced model, rerun and
   revalidate. Hand off intent, source mapping, native evidence, records, report
   and receiving decision.

An omitted owner, timer or release path can invalidate a closed-model conclusion.
Source review must establish coverage. A complete label or hash cannot establish
the truth of those assumptions.

## AI-first adoption and native controls

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), allocation/credit source,
arbitration premises and original observations:

> Trace what each pending actor retains and requests, and every legal release or
> escape path. Establish resource units, capacity and reachable prefix. Separate
> candidate cycles, observed conditional blocking and enabled work not scheduled.
> Ask for missing external/autonomous behavior before making a deadlock claim.

Use [ONBOARDING.md](../../ONBOARDING.md), module
`memory-forward-progress-dependencies` / activity `default`. Your existing AI
and native methods suffice. Optional [context sources](../../CONTEXT_PORT.md),
including DVIT, can reveal scoped ownership/release/dependency relationships
without being required.

The [native controls](examples/NATIVE.md) use Linux, Verilator 5.020 and a C++/Make
toolchain. Nine cases/117 samples exercise coherence-like and accelerator-like
contexts with two fixed actors and single-slot resources. A separate exhaustive
state model checks reachable transitions and replays native actions; it qualifies
only that finite abstraction.

## Outcome and limits

| Exit | Meaning |
|---:|---|
| 0 | Within the supplied observed contract. |
| 1 | Known findings or static candidate cycles requiring review. |
| 2 | Incomplete scope, observation, closure or original requirement. |
| 3 | Invalid input or I/O. |

Argument errors use exit 2. A successful serialized trace can still return 1 for
its static candidate cycle, without an observed blocking witness. Findings retain
coexisting gaps.

Production coherence protocols, arbitrary RTL equivalence, new arrivals, hidden
owners, autonomous timers, simultaneous transitions and reset overlap require
broader qualified methods. This establishes neither unbounded liveness/livelock
nor fairness or production signoff.

```sh
python -m unittest discover -s tests -v
```

The native guide explains opt-in tool variables. Saved-data review needs no
simulator.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
