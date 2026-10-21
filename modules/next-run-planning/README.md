# Next-run planning

Use this module before spending another simulation or investigation cycle.
It records **what the next step should establish, what evidence can answer it,
and how each possible outcome changes the decision**.

This fits in investigation triage, rerun review and handoff between engineers.
DV, simulation-infrastructure and validation owners can use it alongside their
issue tracker, existing artifacts and runner. It supplements technical judgment;
it replaces unstructured “rerun with more debug” notes and lost attempt history.
It does not dispatch jobs or claim that fewer runs always produce better evidence.

The primary workflow is AI-led. A short [RECORD.md](RECORD.md) is sufficient.
Structured JSON and the helper are optional when exact plan/result correspondence
and history checks help.

## First use

Python 3.10+ and the standard library suffice. From
`modules/next-run-planning`:

```sh
python -c "from pathlib import Path; Path('.local').mkdir(exist_ok=True)"
python examples/create_example.py .local/next-run-first-use
python experiment_ledger.py audit-plan .local/next-run-first-use/inspect-plan.json --output .local/next-run-first-use/plan-review.json
python experiment_ledger.py review-result .local/next-run-first-use/inspect-plan.json .local/next-run-first-use/inspect-result.json --output .local/next-run-first-use/inspect-review.json
```

Expected exits: **0**. The synthetic timeout question distinguishes “not accepted”
from “accepted but unfinished.” The original journal already covers the correlated
request/deadline window, so the plan inspects it before proposing another run.
The recorded result observes acceptance without completion; the underlying cause
remains unresolved.

Now review a proposed replay that has not run:

```sh
python experiment_ledger.py audit-plan .local/next-run-first-use/replay-plan.json --prior .local/next-run-first-use/inspect-plan.json --output .local/next-run-first-use/replay-plan-review.json
python experiment_ledger.py review-result .local/next-run-first-use/replay-plan.json .local/next-run-first-use/unexecuted-result.json --output .local/next-run-first-use/unexecuted-review.json
```

The plan audit exits **0**; the unexecuted result exits **2**. A structurally useful
proposal does not become execution evidence. No example launches a job.

The generator also supplies `late-plan.json` / `inconclusive-result.json` and
`divergent-plan.json` / `divergent-result.json`. A late trace cannot answer whether
a request predating it was accepted. A replay that differs despite fixed inputs
must preserve that divergence. Choose new directories/report files with existing
parents; original plans and results are never rewritten.

## Helper features and records

| Operation | Contribution |
|---|---|
| `experiment_ledger.py audit-plan PLAN --prior OLD_PLAN` | Checks declared controls, required observations, hypotheses, action/outcome map and prior exact plan correspondence. Repeat `--prior` for more history. |
| `experiment_ledger.py review-result PLAN RESULT` | Checks exact plan binding, actual route/variables, execution state, observation completeness, reproduction correspondence and mapped outcome. |
| `--output FILE` | Saves JSON to a new path; JSON is also printed. |

The [plan template](record.template.json), [result template](result.template.json)
and [FORMAT.md](FORMAT.md) define the optional structured records.

A plan retains the original observation/run, question, grounded explanations,
fixed/intended/uncontrolled variables, required attainable observations, outcome
decisions, next action, prior-search scope, stopping condition and unknowns.
Actions can inspect existing evidence, request context, propose a run or stop.
A new-run proposal includes a cheaper route considered and decisions for
inconclusive/failed execution; original reproduction also needs a divergence route.

A result retains its immutable original plan binding, actual execution/route,
variables, sourced observations, selected outcome, correspondence, interpretation,
remaining unknowns and cost observations. Keep unexecuted, failed, inconclusive
and divergent results; they are legitimate investigation history.

The helper validates structure and declared correspondence. It cannot prove
hypothesis plausibility, observation adequacy, semantic novelty or whether a
free-text outcome condition is true. A well-shaped but wrongly interpreted result
can pass structural review.

## Put it into the investigation loop

1. State the original question and decision, not only the failure symptom.
   Separate plausible explanations using their source basis.
2. Inspect the actual prior attempts and retained artifacts. Establish identity,
   window and sampling coverage before requesting recollection.
3. Choose the smallest **adequate** observation route. Existing counters/journals
   may suffice; if the required facts were never recorded, define an attainable
   collection using the installed native tool.
4. Record original binary/configuration/input basis, fixed controls, intended
   intervention and uncontrolled factors. Same seed alone does not establish
   reproduction.
5. Define how discriminating, inconclusive, failed and divergent outcomes affect
   the hypotheses and next action. Set the stopping condition for this step.
6. Use your existing runner for any approved native execution. Append actual
   evidence and interpretation to a new result bound to the original plan.
7. Review what changed in understanding. If the plan changes, give it a new
   identity; do not edit the old hypothesis to fit the result.

A failed loader run can inform an infrastructure explanation without answering the
original hardware question. Changed stimulus, forced signals or timeout settings
need an explicit relationship to the original execution. An exploratory branch can
inform the investigation without becoming a faithful replay or passing test.

Exact repeated-plan detection is advisory, not semantic duplicate detection.
Replication can be useful for nondeterminism. Repeating an inadequate trace
window without repairing it does not resolve the missing evidence.

## AI-first adoption

Give a file/tool-enabled assistant [SKILL.md](SKILL.md),
[AI_USAGE.md](AI_USAGE.md), the original issue and actual prior artifacts:

> Determine what this next step should establish. Inspect existing evidence and
> history, map grounded explanations to attainable observations and outcome
> decisions, and ask for missing identity/window/tool capability. Record failures
> and uncertainty; do not turn a proposed rerun into an observation.

Use [ONBOARDING.md](../../ONBOARDING.md), module `next-run-planning` / activity
`default`, for project-local integration. No provider SDK, native importer or
runner is imposed. Optional DVIT intent/dependency context can connect the local
question to affected requirements and earlier decisions; independent use needs
only your existing AI and engineering sources.

## Results and boundaries

| Exit | Meaning |
|---:|---|
| 0 | Structurally complete plan or recorded outcome. |
| 1 | Contradiction, failed execution or replay divergence. |
| 2 | Missing context, unexecuted or inconclusive evidence. |
| 3 | Invalid input or I/O. |

Argument errors use exit 2. A zero status does not establish interpretation truth,
usefulness, cheapest route or release acceptance.

Costs retain measured/estimated/unknown basis, unit and scope. They are not summed
or used to prove savings. Include full execution/collection/review work when
making an independent efficiency judgment.

See [representative investigations](examples/INVESTIGATIONS.md) for outcome
boundaries and run:

```sh
python -m unittest discover -s tests -v
```

Keep the original request, prior-search basis, immutable plans, actual results and
follow-up decisions together in your existing issue/evidence workflow.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
