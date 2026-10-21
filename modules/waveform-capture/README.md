# Waveform capture

Plan a focused waveform around an engineering question, validate that the required signals and time controls are actually supported, and expand the capture when the initial history is insufficient.

Use this activity between a simulation observation and a diagnostic rerun: timeout investigation, protocol acceptance/progress review, reset or clock sequencing, or an upstream control dependency. It helps DV engineers and their existing AI agents choose what to record and why. It supplements the simulator, native trace APIs and waveform viewer; it can replace repeated manual signal/window recipe preparation within the supported profile.

A smaller dump is useful only if it contains the evidence needed. This module connects the question, actual trace visibility, original run, causal history and replay limits rather than treating waveform size as the result.

## Start with your existing AI agent

Give a file/tool-enabled agent this request from the clone:

> Use waveform-capture to investigate this simulation observation. Find the original run and native trace capabilities, resolve the required signal objects, and propose a capture window with clock/reset and upstream context. Explain the time basis, inspect the recipe before running it, check emitted data and reproduction, and expand the scope if history is missing.

Follow [SKILL.md](SKILL.md) and [AI_USAGE.md](AI_USAGE.md); use [shared onboarding](../../ONBOARDING.md) to select/install the activity in a project. Your agent uses its existing model subscription and native runner. These scripts neither call a model nor install a simulator.

## First use: preview a capture without EDA tools

Python 3.10+ standard library is sufficient for this path. From this module directory:

```sh
python examples/create_example.py demo
python waveform_capture.py assess demo/plan.json demo/inventory.json \
  --binary demo/sim.bin --output demo/assessment.json
python waveform_capture.py render demo/plan.json demo/inventory.json \
  --binary demo/sim.bin --waveform demo/capture.vcd \
  --output demo/recipe.json
```

Use a new `demo` directory. Both checks return **0**, `renderable`. The supplied clock relation maps the requested 55–125 cycles to **110–250 ns**, with a 240 ns failure marker and a run stop of 260 ns.

Inspect `assessment.json` for resolved objects, aliases, exact tick controls, warnings and the replay label. Inspect `recipe.json` for the literal argument array and expected trace declarations. The demonstration binary is non-executable identity data; neither command executes it or creates a waveform. Unknown correspondence remains explicitly unqualified even when a recipe can be rendered.

## What is provided

| Helper or record | Responsibility |
|---|---|
| `waveform_capture.py assess` | Bind the plan, declaration inventory and current binary; check visibility, aliases, time conversion, history and supported controls. |
| `waveform_capture.py render` | Produce a literal wrapper invocation and viewer instructions after readiness checks. Optional `--viewer` writes a GTKWave save file. |
| `inspect-vcd` / `import-vcd` | Inspect native VCD declarations and create a source-bound inventory using separately supplied producer context. |
| `examples/create_example.py` | Create synthetic preview inputs without requiring a simulator. |
| `examples/verilator/run_example.py` | Exercise a real owned timeout investigation, progressively expanded captures, replay checks and scoped measurements. |
| [record.template.json](record.template.json) | Record a manual engineering investigation when an existing native tool is more appropriate than the bundled renderer. |

## Use your actual trace evidence

VCD inspection/import and optional GTKWave save generation require the pinned [native requirements](requirements-native-example.txt), `pyvcd==0.5.0`:

```sh
python -m pip install -r requirements-native-example.txt
python waveform_capture.py inspect-vcd existing.vcd \
  --output header.json --context-template context.json
```

Inspect the producer's original source/invocation/capabilities and fill the unknown fields in `context.json`. Then import:

```sh
python waveform_capture.py import-vcd existing.vcd context.json \
  --output inventory.json
```

The bundled importer accepts the qualified Verilator 5.020 VCD producer profile. It reads declarations through `$enddefinitions $end` and binds the exact header prefix; it does not verify the waveform body or discover the full RTL hierarchy. A signal existing in HDL does not establish visibility in the instrumented executable.

Prepare the plan from [FORMAT.md](FORMAT.md) and the preview example:

| Input | Establish before use |
|---|---|
| Engineering question and original run | Failure/observation reference, workload/configuration and what behavior must be distinguished. |
| Inventory and binary | Actual declarations, supported selectors, native aliases, instrumentation and exact executable digest. |
| Window and failure marker | Simulation quantities with units and the source of each boundary. Wall time is a separate measurement. |
| Clock relation | Evidenced period and edge origin for cycle conversion; use physical/native edge evidence when the clock is gated or variable. |
| Objects | Native path or evidenced alias, role, selection rationale and source reference for each group. |
| History and correspondence | How history before the failure will exist, earliest available time, and whether replay matches selected original behavior. |
| Run and expansion | Actual stop/workload arguments; a trigger and next action if the first scope/window cannot answer the question. |

Unknown producer facts stay unknown. Do not invent a binary identity, alias, complete visibility or matched replay status to make a plan renderable.

## Integrate into a simulation flow

1. Start from the failing observation and original runner arguments. Preserve seed, configuration, source/build identities and relevant transactions.
2. Use actual native visibility to select clock/reset, acceptance, progress and upstream control context. A local module cone is an initial hypothesis.
3. Establish how pre-failure history will be recorded. Use an existing trace, supported buffer or a new/qualified replay beginning early enough.
4. Assess and render only supported controls. Review literal arguments before execution through the existing runner.
5. Check emitted declarations, timestamps, values and replay correspondence. A value already active at the first dump does not reveal when it changed.
6. Expand earlier or add the relevant chain when evidence is insufficient. Retain each attempt, its question and why the next capture changed.

Capture-time signal/window restriction can avoid some dump work. Filtering a completed trace can reduce transfer or inspection work; its original simulation and dump cost has already been paid. An error trigger cannot recover unrecorded past history.

The [native worked guide](examples/verilator/README.md) demonstrates this cycle with upstream configuration, request acceptance and a later timeout. The example is a fixture; the activity applies to the investigation stage rather than one IP type.

## Results and supported controls

| Exit | Result | Action |
|---|---|---|
| 0 | `renderable` | Inspect the preview, then run the supported wrapper and inspect its actual output. |
| 1 | `rejected` | Fix a known incompatible binary, object, control, bound or history method. |
| 2 | `incomplete` | Obtain missing evidence; do not treat readiness as established. |
| 3 | Invalid input or I/O | Correct records/paths and retry with new destinations. |

Outputs must be new and distinct from inputs, binary and requested waveform. `render` writes a JSON recipe, not a simulation result. The recipe uses `shell=false` and preserves literal workload arguments after `--`; their engineering meaning still comes from your original invocation.

The qualified renderer supports `verilator-5.020-vcd-wrapper.v1`: VCD, basic dot-separated leaf identifiers/packed buses, scheduled new/reset runs, and inclusive dump ticks after evaluation. Native selection can include additional declarations under the documented prefix/depth semantics; inspect them in the assessment.

The supplied wrapper's 1,000,000-tick bound is its own declared limit. Escaped/unpacked-array selections, FST/FSDB, dynamic reselection, trigger buffers, checkpoint restore and other versions require a separately qualified native method. The workflow can use commercial or internal tools; the bundled parser/flags do not imply support for all of them.

`renderable` establishes command readiness, not sufficient causal history, faithful reproduction or efficiency. Known replay divergence blocks a reproduction plan; an exploratory branch must retain that label.

## Handoff and tests

Deliver the question, original run, plan, inventory/context, literal recipe, emitted trace, correspondence checks, unresolved premises and expansion rationale. Revalidate after changes to the binary, trace instrumentation, hierarchy/aliases, workload, time basis or native wrapper.

Measure planning, build/instrumentation, replay, dump cost, parsing/loading and review where available. Delayed dumping still simulates earlier time. File-size reduction alone does not establish end-to-end speedup.

```sh
python -m unittest discover -s tests -v
```

Optional dependencies enable VCD/viewer tests. The native example has a separate Linux/tool opt-in described in its guide; a skipped native test is not native qualification on the current machine.

An AI agent may use existing company tools or an independently checked method beyond this renderer. Preserve the helper's result and cite the additional evidence. Optional [context sources](../../CONTEXT_PORT.md), including DVIT, can supply intent, questions and evidence across the chain; standalone adoption requires no DVIT connection and never installs it automatically.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
