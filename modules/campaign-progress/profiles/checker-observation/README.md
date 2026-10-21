# Checker observation validity

Use this activity when a simulation passes but you need to establish **what the
checker actually observed**. It follows checker integration or a change to event
mapping, enable logic, clock, reset or operating mode, and precedes campaign
progress accounting. The users are checker owners, DV engineers and regression
owners interpreting accepted, completed and checked work.

A stimulus counter or a count of checker calls can conceal a disabled interval,
a wrong transaction ID or a checker attached to the wrong event. This activity
relates native acceptance and completion events to actual comparison actions,
against an independently stated observation contract. It supplements the
scoreboard and campaign dashboard; it replaces manual reconciliation of these
selected event records. It does not replace the expected-data model or its review.

## Start with your AI assistant

Give a file/tool-enabled assistant this folder and [WORKFLOW.md](WORKFLOW.md):

> Establish whether our checker observes every required completion in the selected
> modes. Read the original interface contract, checker code, enable logic and run
> configuration before interpreting the logs. Identify the acceptance/completion
> boundary, clock/reset sampling, transaction identity and expected-data source.
> Map supported evidence, ask for missing requirements and report unobserved work
> separately from functional failures. Keep the original native verdict.

For installation and project-local onboarding, use the repository's
[ONBOARDING.md](../../../../ONBOARDING.md). Select module `campaign-progress`,
activity `checker-observation`. The assistant can adapt a company exporter or
inspect other evidence directly; this supplied reader has the precise native
boundary below. It requires Python 3.10+ and the standard library for saved data.
Your existing AI subscription supplies the reasoning; DVIT is optional.

## Run a first review

Run the following from `modules/campaign-progress/profiles/checker-observation`.
Use a new output directory. If a teammate has already generated the example,
retain its complete directory at `.local/checker-native` and skip the build.
Otherwise, on Linux with an existing Verilator 5.020, GCC C++17 and Make:

```sh
python examples/run_native.py .local/checker-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Replace both paths with your installed native executable and runtime. The recipe
builds two owned fixtures and performs 22 runs; it installs no tools. Saved-data
capture and review can subsequently run on another system without a simulator.

Reimport one retained run and review it:

```sh
python observation_check.py capture .local/checker-native/stream-gated-clean run .local/checker-native/stream-gated-clean/capture-context.json --output .local/checker-native/stream-gated-clean/recaptured.json
python observation_check.py review .local/checker-native/stream-gated-clean/intent.json .local/checker-native/stream-gated-clean/recaptured.json --json-out .local/checker-native/stream-gated-clean/new-review.json --markdown-out .local/checker-native/stream-gated-clean/new-review.md
```

Capture exits 0 because the import succeeds. Review exits **1**: the native run
passes, but only seven of eleven completions have comparison actions. Four
mode-1 completions occur while checking is disabled. Open `new-review.md` for the
finding and `new-review.json` for the per-mode accounting and witnesses.

For the complementary control:

```sh
python observation_check.py review .local/checker-native/stream-good-fault/intent.json .local/checker-native/stream-good-fault/evidence.json --json-out .local/checker-native/stream-good-fault/new-review.json --markdown-out .local/checker-native/stream-good-fault/new-review.md
```

This review exits **0** for observation correspondence, while preserving native
FAIL and four caught comparison failures. All eleven completions were checked.
Observation validity and functional correctness are separate questions. The
`mailbox-wrong-id` fixture also shows why equal aggregate counts are insufficient.

Outputs must be new paths; choose a fresh name for another review. Save a captured
receipt beside its retained `run/` directory: artifact paths are resolved from
the receipt's parent. Copying only the JSON receipt loses the evidence needed to
review it.

## Helper and records

| Helper operation | What it contributes |
|---|---|
| `observation_check.py capture ROOT WORKDIR CONTEXT --output RECEIPT` | Reads the original native artifacts, validates their consistency and retains source/port identities, events, comparison actions and native status. It executes no imported commands. |
| `observation_check.py review INTENT RECEIPT` | Rechecks artifact identity, matches accepted/completed work with actual comparisons, separates requested modes, and reports differences, missing evidence and qualified campaign exposure. |
| `--json-out` / `--markdown-out` | Writes a structured handoff record and a readable review. Without these, the review JSON is printed. |

Prepare the two independent records using
[capture-context.template.json](capture-context.template.json) and
[intent.template.json](intent.template.json):

- The capture context identifies the original run, configuration/model, clock,
  reset/polarity, checker, source files, window and eleven explicit port roles.
  It records the instrumentation and expected-data bases.
- Intent states the claim, owner and source, required modes and expected native
  identity. Obtain these from the original interface/checker contract and build
  evidence; do not derive required modes from whichever runs happened to pass.
- Retain sources, XML, executable, original commands, stdout/stderr and execution
  results. [FORMAT.md](FORMAT.md) lists the exact files and JSON schemas.

Acceptance and completion mean valid AND ready outside reset. IDs are unique
while pending; reuse after completion creates a new acceptance sequence. A sampled
reset cancels pending work and starts a new epoch. Work still pending at the end
of the observation window remains unresolved. Required modes apply at completion;
acceptance mode is also retained.

## Integrate into an existing flow

1. Select a single observation boundary and its original requirement. Ask the
   interface owner what must be checked in each mode, including reset cancellation
   and outstanding work.
2. Inspect the checker and instrumentation source. Establish what each sampled
   signal and expected value means. A hash binds a source file; it does not prove
   that the source implements the intended oracle.
3. Have the existing runner retain the native artifacts and settled event/action
   journal. Map native names explicitly, preserving reset polarity, widths and
   source identity. Never substitute aggregate counts for the journal.
4. Capture and review after the run. Keep simulator PASS/FAIL in the same handoff
   as observation validity, unresolved work and missing modes.
5. Route wrong-event, disabled-checker or identity findings to their owners, fix
   the original checker/instrumentation or requirement, then rerun and recapture.
6. Feed only the qualified, uniquely identified exposure to campaign accounting.
   Stimulus, raw checker calls and observed completions have different meanings.

This reader is qualified for retained **Verilator 5.020**, one flat top, one
positive-edge clock and stable pre-edge sampling. Controls are scalar; paired
unsigned IDs/data have matching widths of 1–32 bits. It excludes same-edge
zero-latency completion. Arbitrary UVM logs, other simulators and different
sampling models need a separately validated mapping/exporter. The workflow still
applies; portable JSON alone does not qualify an EDA adapter.

## Interpret and hand off the result

| Review exit | Meaning and next action |
|---:|---|
| 0 | `observation_consistent_with_declared_contract`. Retain the native functional result and review the oracle separately. |
| 1 | `review_required`. Inspect known mapping or observation differences and their event witnesses. |
| 2 | `incomplete`. Supply the missing scope, mode, source or window evidence before claiming qualified observation. |
| 3 | Invalid record or I/O. Repair the input/artifact package and rerun. |

Argument syntax errors use argparse's exit 2. Findings can coexist with missing
evidence. Capture's exit 0 means successful import, including native FAIL.
Neither observation correspondence nor passing examples establishes verification
completeness, statistical confidence or stopping authority.

The owned stream and mailbox examples vary port names, reset polarity and payload
relations. A separately expressed finite model qualifies their native samples and
actions. To test an existing retained collection, set
`OPENTOOLS_OBSERVATION_EXAMPLE` to its root and run:

```sh
python -m unittest discover -s tests -v
```

Keep the intent, native package, receipt, report and correction/revalidation
decision together. An optional DVIT connection can provide additional
requirement/dependency context through the shared intent layer; local sources
remain sufficient for independent use.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
