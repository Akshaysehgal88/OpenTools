# Checkpoint replay

Use this module before reusing a simulation checkpoint and when qualifying a
save/restore mechanism for a new testbench. Its first question is whether the
checkpoint belongs to the requested binary, configuration, prefix inputs and
capture point. Its second is whether a restored continuation matches a control
run over explicitly selected observations and a stated horizon.

This fits between a runner's checkpoint selection and native restore, and in the
qualification loop after changes to the simulator, driver or external state.
DV infrastructure engineers, testbench owners and debug engineers can use it to
avoid repeating a long initialization prefix without treating an unqualified
snapshot as interchangeable state.

It supplements the simulator's save/restore facility and your runner/cache
policy. It replaces ad hoc manifest comparison and selected-trajectory diffing.
It does not implement a checkpoint catalog, simulator restore API or scheduler.

## First use: inspect records without a simulator

Python 3.10+ and the standard library are sufficient. From
`modules/checkpoint-replay`:

```sh
python -c "from pathlib import Path; Path('.local').mkdir(exist_ok=True)"
python examples/create_example.py .local/replay-first-use
python checkpoint_replay.py check .local/replay-first-use/checkpoint.json .local/replay-first-use/request.json .local/replay-first-use/profile.json --artifact-root .local/replay-first-use --json-out .local/replay-first-use/check.json --markdown-out .local/replay-first-use/check.md
python checkpoint_replay.py qualify .local/replay-first-use/checkpoint.json .local/replay-first-use/request.json .local/replay-first-use/profile.json .local/replay-first-use/control.json .local/replay-first-use/restored.json --artifact-root .local/replay-first-use --json-out .local/replay-first-use/qualification.json --markdown-out .local/replay-first-use/qualification.md
```

Both checks exit **0**. `check` returns
`compatible_within_declared_scope`; `qualify` returns
`matched_selected_observables`. Open the Markdown files for the decision and
the JSON files for identities, file observations, selected channels and gaps.

The example is deliberately **synthetic**: its state and executable files are
plain demonstration bytes. No simulator or checkpoint is executed. Its five
selected channels are time, transaction, RNG, pending queue and checker state,
observed at capture step 4 and suffix steps 5–6.

Try a live-file negative control after the successful checks:

```sh
python -c "from pathlib import Path; Path('.local/replay-first-use/firmware.bin').write_bytes(b'changed prefix image')"
python checkpoint_replay.py check .local/replay-first-use/checkpoint.json .local/replay-first-use/request.json .local/replay-first-use/profile.json --artifact-root .local/replay-first-use --json-out .local/replay-first-use/changed-prefix.json
```

Expected exit: **1**, because the current prefix-file bytes no longer match the
request. Updating a filename or a record without establishing the original
consumed bytes cannot make the checkpoint compatible. Use a new example directory
to return to the original case. All report paths must be new with existing parents.

## Helpers and features

| Entry point | Responsibility |
|---|---|
| `checkpoint_replay.py check CHECKPOINT REQUEST PROFILE` | Compares captured/requested context, continuation and required-state obligations; verifies checkpoint artifacts, requested executable and prefix-file bytes under `--artifact-root`. |
| `checkpoint_replay.py qualify CHECKPOINT REQUEST PROFILE CONTROL RESTORED` | Runs the compatibility checks, validates distinct bound control/restored run records, then compares capture boundary, every selected suffix step/channel and the final boundary. |
| `--json-out` / `--markdown-out` | Saves structured and readable reports. The CLI prints a readable report even without output flags. |
| [examples/verilator/run_example.py](examples/verilator/run_example.py) | Opt-in Linux native save/restore qualification, negative controls and scoped cost observations for the owned fixture. It is separate from the data-only helper. |

The Python helper does not launch native commands. The native example does so
only when explicitly run with your existing tool paths. Its
[guide](examples/verilator/README.md) explains the inspected mechanism and outputs.

## Define inputs from the real testbench

Use [FORMAT.md](FORMAT.md) for exact schemas and digest conventions, and
[record.template.json](record.template.json) for the checkpoint record.

| Record | Source and meaning |
|---|---|
| Profile | Independently inspected state obligations, capture boundary and exact observable channel definitions. Mark a state component `not_used` only after inspecting its actual consumers. |
| Checkpoint | Original binary/configuration, ordered consumed prefix inputs, actual prefix seed, capture step/unit, continuation, complete state inventory, capture outcome, artifacts and boundary observation. |
| Request | The desired faithful or exploratory continuation, current executable/prefix files and selected horizon. It must not silently alter a faithful prefix or continuation. |
| Control/restored runs | Distinct original run identities, input-record bindings, completion status and all selected observations at the capture boundary and every suffix step. |

Inventory more than the DUT: simulation time, advanced RNG state, driver queues,
scoreboard/reference memory, DPI objects, open-file positions and external
interactions may affect continuation. A complete declaration is useful only if it
matches the inspected testbench. The helper cannot discover hidden unsaved state.

State units and sample boundaries are explicit; there is no automatic unit
conversion or cross-platform binary compatibility inference. Null means unknown.
A known absent seed can use an explicit value such as `{"state":"not_used"}`.
Record/profile bindings use canonical JSON SHA-256; file identities use raw
bytes. Artifact paths are relative POSIX paths below an explicit root. Missing,
changed or escaping files cannot pass verification.

## Integrate into the simulation flow

1. Inspect the installed simulator's save/restore mechanism and exact version.
   Choose a stable capture phase and document outstanding transactions.
2. Write the profile with the testbench owner. For each state component, record
   the capture/restore method or a sourced reason it is unused.
3. Have the existing runner retain the original consumed prefix bytes,
   configuration, executable, capture outcome, state files and boundary sample.
   Hashing today's file cannot reconstruct what an earlier run consumed.
4. Construct the new request independently from the intended continuation.
   Run `check` before asking the runner to restore the native state.
5. For mechanism qualification, retain a control and restored continuation with
   complete selected samples. Run `qualify` and include missing-state,
   changed-input and corrupt-file controls.
6. Review the implementation and state inventory alongside the results. Measure
   capture, restore, qualification and repeated-run costs before enabling reuse
   under your existing runner's storage/concurrency policy.
7. Requalify after simulator, ABI, model, wrapper, external-state or observation
   changes. Keep the request, records, journals, reports and owner decision together.

A changed stimulus is an exploratory branch unless correspondence to the original
continuation is established. A restored suffix is not an independently
initialized test. A match over selected channels and steps does not prove full
process-state equivalence.

## Use with an AI agent

Give your file/tool-enabled assistant [SKILL.md](SKILL.md),
[AI_USAGE.md](AI_USAGE.md) and the actual runner/testbench sources:

> Identify where initialization cost occurs and whether the installed simulator
> supports a useful save point. Inventory every state consumer outside the model,
> explain how it is captured, and ask for missing sources. Propose a bounded
> control/restore qualification and negative controls. Compare full repeated-task
> cost; do not infer useful speedup from a matching final checksum.

For project-local adoption use [ONBOARDING.md](../../ONBOARDING.md), module
`checkpoint-replay` / activity `default`. Your existing AI host can investigate
native evidence beyond the supplied record reader. Optional DVIT intent and
dependency context can help determine which state or observation changes require
requalification; independent local operation remains complete without it.

## Results and native support

| Exit | `check` / `qualify` interpretation |
|---:|---|
| 0 | Compatible within declared scope / matched selected observations. |
| 1 | Known incompatibility, unavailable/corrupt artifact or selected-observation divergence. |
| 2 | Unknown compatibility or an unqualified/incomplete/badly bound run pair. |
| 3 | Invalid input or I/O. Repair the records/package first. |

Syntax errors use exit 2. Reports preserve known differences and coexisting gaps.
The native recipe is qualified on Linux with **Verilator 5.020**, GCC 13.3 and
Make 4.3. It uses a synchronous 16-byte memory and explicit C++ state, comparing
128 suffix steps. Missing RNG and pending-queue controls demonstrate why a native
checker pass alone is insufficient.

UVM, cocotb, timed schedulers, DPI, other simulators, process checkpointing and
cross-host/ABI transfer need their own capability and state qualification.
Portable Python records do not make native state bytes platform independent.

```sh
python -m unittest discover -s tests -v
```

Portable tests run without native tools; native execution is enabled only by the
environment variables described in the native example guide.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
