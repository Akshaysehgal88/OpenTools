# Low-power quiescence obligations

Use this module before accepting drain acknowledgement, clock stop or power
removal. It asks whether **every required work owner** is quiescent and the
required controls remain satisfied throughout the sampled protected interval.

This fits in shutdown-sequence design, low-power integration and DV review after
changes to admission, queues, responses, credits or isolation. Block, interconnect,
clock/reset and power-sequence owners can use it alongside native power-aware and
protocol verification.

Local idle can become true when work moves to another owner that still needs a
live receiver. Zero counts at acknowledgement can also be followed by new work.
This activity supplements idle/drain diagnostics and replaces manual reconciliation
of selected owner counts and shutdown prerequisites. It does not replace UPF,
power-aware simulation or electrical checks.

## First use

Python 3.10+ and the standard library suffice. From
`modules/low-power-quiescence-obligations`:

```sh
python examples/create_example.py .local/quiescence-local --case power-local-only
python quiescence_review.py review .local/quiescence-local/inventory.json .local/quiescence-local/journal.json .local/quiescence-local/policy.json --json-out .local/quiescence-local/review.json --markdown-out .local/quiescence-local/review.md
```

Expected exit: **1**, `review_required`. The local request has been handed off,
so local idle is true, but an external response is still pending when drain is
acknowledged and the domain shuts down. The report retains the remote owner's
violation witness rather than equating local occupancy with system drain.

Compare the complete owner drain:

```sh
python examples/create_example.py .local/quiescence-system --case power-system-drain
python quiescence_review.py review .local/quiescence-system/inventory.json .local/quiescence-system/journal.json .local/quiescence-system/policy.json --json-out .local/quiescence-system/review.json --markdown-out .local/quiescence-system/review.md
```

Expected exit: **0**, `within_sampled_quiescence_contract`. The external
response returns before acknowledgement. Open Markdown for the protected-milestone
disposition and JSON for typed owner summaries, findings, gaps and first witnesses.

Other cases cover credit return before clock stop, missing isolation and late
admission after acknowledgement. They are owned reference fixtures. Example
directories and report paths must be new; output parents must exist.

## Helper and input features

| Operation | Responsibility |
|---|---|
| `quiescence_review.py review INVENTORY JOURNAL POLICY` | Validates bindings and selected owner coverage, checks zero outstanding work and explicit predicates while each protected state remains active, and retains first violation witnesses. |
| `quiescence_review.py digest RECORD` | Prints canonical JSON SHA-256 for inventory/journal bindings. |
| `--json-out` / `--markdown-out` | Saves structured and readable handoff reports; Markdown is also printed. |

[FORMAT.md](FORMAT.md) defines the records:

- **Inventory:** selected owner IDs, actual owner references, units and counting
  bases. “Accepted but not handed off” and “handed off but not returned” are
  distinct intervals.
- **Journal:** a clean initial sample, closed isolated transition window, typed
  owner counts and actual observed controls: request, ingress closed, drain ack,
  isolation, clock/power availability and local idle.
- **Policy:** the independent required-owner roster, selected
  `drain_ack/clock_stop/power_remove` milestones, owner sets and prerequisite
  predicates for each check.

Counts are unsigned below `2^64` or null. Counts with different units/bases are
never added or substituted. Extra raw counters can be retained without certifying
their normalization. Unknown counts, control state, owner roles or coverage remain
gaps.

A check continues while its protected state is active: acknowledgement true,
clock unavailable or power unavailable. New work after the first zero-count sample
can therefore fail the contract. Missing milestones in complete closed coverage
require review; partial coverage cannot establish absence.

## Integrate into the shutdown flow

1. Establish the original shutdown/drain scope and receiving criteria. Identify
   every owner whose unfinished work can depend on the retiring domain, including
   external responses and credits.
2. Inspect native counter semantics and ownership boundaries. Confirm the remote
   count is actually observed, not copied from local occupancy or an idle flag.
3. Capture relevant owner/control changes from before request through the
   protected interval. Use observed clock/power/isolation evidence, not just
   software requests.
4. Maintain the required-owner roster independently of the exporter. Include each
   selected owner in the appropriate milestone checks, preserving units/bases.
5. Review findings with admission, protocol, isolation or power-sequence owners.
   Correct the original flow or sourced contract, then rerun and revalidate.
6. Hand off original intent, owner rationale, native observations, normalized
   records, report and receiving decision. Repeat after owner/control changes.

An owner omitted from both inventory and policy cannot be discovered by this
comparator; source/dependency review must establish coverage. Reopening an active
protected state is unreviewed reentry. Abort, restore and repeated transitions
need their own applicability and temporal method.

## AI-led adoption and native control

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), the shutdown contract,
actual counter definitions and transition evidence:

> Trace work ownership beyond local idle. Find every response, credit or queue
> owner still dependent on this domain, establish actual admission closure and
> inspect the whole protected interval. Ask for missing counters or owner coverage
> before interpreting drain acknowledgement.

Use [ONBOARDING.md](../../ONBOARDING.md), module
`low-power-quiescence-obligations` / activity `default`. Existing AI and
engineering tools suffice. Optional [context sources](../../CONTEXT_PORT.md),
including DVIT, can expose scoped ownership and dependent consumers without
being required.

The [native controls](examples/NATIVE.md) use Linux, Verilator 5.020 and a C++/Make
toolchain. An independent token ledger checks six cases/72 native rows, accounting
conservation and shutdown milestones. The owned digital fixture models response
and credit obligations; it is not an UPF, ICG, isolation-cell or power-cell model.

## Results and limits

| Exit | Meaning |
|---:|---|
| 0 | Within the supplied sampled quiescence contract. |
| 1 | Known outstanding-owner, prerequisite or protected-interval finding. |
| 2 | Incomplete scope, counter, observation or original requirement. |
| 3 | Invalid input or I/O. |

Argument errors use exit 2. Known findings retain coexisting gaps; later zero
counts do not erase earlier unsafe shutdown observations.

This profile does not infer complete owner coverage, prove absence between samples,
extract arbitrary UPF or qualify analog power loss, electrical isolation, X
propagation or physical timing. Use native methods for those claims.

```sh
python -m unittest discover -s tests -v
```

The native guide describes opt-in tool variables. Saved-data review needs no
simulator.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
