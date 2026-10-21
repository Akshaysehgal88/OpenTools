# Campaign progress

Use this module during a regression or long simulation campaign to review
**what additional engineering evidence the completed work produced and which
original objectives remain open**. It is an offline review stage for DV,
simulation infrastructure and validation owners.

Coverage can plateau while useful checked work continues. Runs can also consume
cycles while the active path or checker contributes nothing. This module keeps
named coverage goals, effective events, required execution and resource
observations separate so that those situations are distinguishable.

## Choose the activity

| Activity | When to use it |
|---|---|
| Campaign progress, this guide | Compare cumulative campaign exports with the independent objective and run population |
| [Checker observation](profiles/checker-observation/README.md) | Establish whether completed transactions were actually observed by the intended checker |
| [Interaction obligations](profiles/interaction-obligations/README.md) | Review source-selected combined transitions that separate feature passes cannot close |

The module supplements existing regressions, dashboards and review meetings.
It replaces ad hoc count/percentage aggregation where its record definitions fit.
It provides no scheduler, job stopper, live monitor, test generator or automatic
release/stopping policy. Existing owners retain those decisions.

## First use: a coverage plateau with useful work

Python 3.10+ and its standard library suffice for saved-data use. From the clone
root, enter this folder; installed packages retain the same module layout.

```sh
cd modules/campaign-progress
python examples/create_example.py .local/campaign-first-use
python campaign_progress.py summarize .local/campaign-first-use/contract.json .local/campaign-first-use/before.json .local/campaign-first-use/after.json --output .local/campaign-first-use/review.json --markdown .local/campaign-first-use/review.md
python campaign_progress.py digest .local/campaign-first-use/contract.json
```

Expected summarize exit: **0**, `recorded_progress`. Two runs have passed and
the effective checked-handshake total rises from **64 to 128** against **192**.
The same three of four named goals are hit. The third required run and fourth
goal remain open. Exit 0 means the evidence was summarized consistently, not
that objectives were met or that a campaign can stop.

The example is synthetic; no job executes. Open `review.md` for the objective
values, targets, remaining run population and comparable changes. Use a fresh
directory and new report paths. Record the receiving decision in your normal
review system or [DECISION.md](DECISION.md).

## Helper: `campaign_progress.py`

| Operation / feature | Contribution |
|---|---|
| `summarize CONTRACT BEFORE AFTER` | Compare two cumulative snapshots under one independent objective contract |
| Required execution | Retain the full run population, native/normalized states and missing/not-run distinctions |
| Named coverage goals | Union qualified hit IDs only when the full selected population and definitions match |
| Effective exposure | Union source-qualified half-open event ranges per event space so overlap counts once |
| Resource observations | Preserve origin, scope, units and measured/estimated status separately from useful-event counts |
| `digest FILE` | Print a JSON `canonical_sha256` binding for the selected record |
| `--output` / `--markdown` | Save structured and human-readable review without replacing originals |

Cumulative snapshots are compared, never added together. Different labels do not
prove independent events; native exit 0 does not by itself establish checker pass.

## Define the campaign's intent before importing results

| Input | Source and meaning |
|---|---|
| Objective contract | Independently required runs, named goals, event target and permitted review recommendations |
| Before / after snapshots | Complete or explicitly partial cumulative exports with distinct identities and increasing known timestamps |
| Run records | Original state, configuration/model, qualified measurements and resource observations |
| Measurement basis | Native counter/checker definitions and the source evidence establishing what they count |

Use `opentools.campaign-contract.v1` and `opentools.campaign-snapshot.v1`.
The contract supports execution, named Boolean coverage, integer exposure and
manual objectives. Manual/statistical questions require a separately qualified
engineering method. Start from [record.template.json](record.template.json);
[FORMAT.md](FORMAT.md) defines the exact records and report.

Coverage populations/definitions and configuration/model identities must agree
before pooling. Queued or not-run work cannot contribute executed measurements.
A missing record is not assumed to be not-run. A failed prefix counts only under
explicit objective policy. Preserve unknown measurements rather than turning
them into zero. Resources are not substituted for useful exposure.

## Integrate with a regression or review flow

1. Select a campaign boundary and receiving decision. Enumerate the original
   applicable execution population and objectives independently of available logs.
2. Use the existing scheduler/runner exports. Translate each native state with its
   original value and source; establish checker verdict semantics from the runner.
3. Review the counters. Identify acceptance/completion/checker events, replay or
   reset behavior, event-space identity and objective eligibility. Use the
   checker-observation activity when that correspondence is uncertain.
4. Export two matching cumulative snapshots for a known interval. Mark partial
   collections explicitly and retain raw reports and source bindings.
5. Summarize and attach the output to the existing campaign review. Distinguish
   a useful coverage plateau, measured ineffective execution, missing evidence
   and an unmet independent requirement.
6. Let the campaign owner choose continue, inspect effectiveness, redirect or
   seek policy under the stated authority. Recheck after checker/model,
   configuration, goal population, counter definition or required-run changes.

The helper does not infer confidence, forecast a useful stopping time or turn
a stable percentage into a release criterion.

## Agent-assisted adoption

Give your agent the [workflow](SKILL.md), current campaign contract and exports:

> Review whether this interval added qualified evidence against our original
> campaign objectives. Inspect the runner's native pass and counter definitions,
> required run population and configuration. Identify unhit goals, outstanding
> execution, ineffective activity and missing measurements. Preserve the original
> targets and recommend a bounded next action under our existing policy.

The agent can adapt current company exports or validate another native method.
Use [shared onboarding](../../ONBOARDING.md), module `campaign-progress` and
workflow `default` for a reusable project profile. [AI_USAGE.md](AI_USAGE.md)
covers source interpretation; the helper does not authenticate supplied counters
or policy authority.

## Native example and interpretation

The [Verilator example](examples/verilator/README.md) executes an owned handshake
model and exports actual DUT counts, native checker verdicts, named payload goals
and process resource observations. Qualified native collection uses Linux,
Verilator **5.020**, GCC C++17 and GNU Make; no dependency is downloaded.

It includes productive work during a plateau, zero accepted work, a changed
configuration/denominator, a failed prefix and an incomplete export. This is a
source-defined Boolean goal set, not a general UCIS/UVM importer. Source review
is still needed when a structurally valid counter measures the wrong event.

| Exit | Interpretation |
|---|---|
| `0` | Recorded progress, possibly with unmet objectives or established zero effectiveness |
| `1` | Contradictions or execution findings; inspect the affected native records |
| `2` | Missing context prevents the requested summary |
| `3` | Invalid data or I/O failure |

Return the objective, interval, native observations, remaining obligations,
measurement gaps, receiving owner and next action. No output grants stopping or
signoff authority. Run `python -m unittest discover -s tests -v` for local checks.

[DVIT](../../DVIT.md) can maintain relationships between objectives, checker intent
and dependent decisions. Existing local/company evidence remains usable;
[context consumption](../../CONTEXT_PORT.md) is optional.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
