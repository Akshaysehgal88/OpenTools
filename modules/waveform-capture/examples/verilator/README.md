# Focused waveform capture with Verilator

Run a complete owned investigation: begin with a late timeout capture, discover that acceptance history is missing, expand upstream and earlier, and compare the instrumented reruns with the original selected behavior.

This example exercises the [waveform-capture activity](../../README.md). It demonstrates native trace controls and an engineering expansion loop; use your existing runner and trace hooks when adapting the activity to a project.

## Prerequisites and first run

Use Linux with Verilator **5.020**, a GCC C++17 toolchain, GNU Make, Python 3.10+ and **pyvcd==0.5.0**. The qualified native environment used GCC 13.3 and Make 4.3. Install the optional Python dependency in your chosen environment from the waveform-capture module directory:

```sh
python3 -m pip install -r requirements-native-example.txt
python3 examples/verilator/run_example.py \
  --verilator /path/to/verilator_bin \
  --verilator-root /path/to/share/verilator \
  --directory native-example --timing-repeats 3
```

Choose a new output directory whose parent exists. The script uses already installed tools; it does not download or install a simulator. It creates owned sources, builds plain and instrumented binaries, runs the captures, inspects the VCDs and retains checks and measurements.

The supplied flags belong to this explicit C++ wrapper. An arbitrary Verilated binary will not accept them automatically. GNU Make builds use owned space-free temporary paths; retained output paths may contain spaces.

## What the investigation shows

The fixture uses a request/timeout path affected by upstream quiesce control. The driver writes the control at **120 ns**, submits a request at **180 ns**, and observes timeout at **240 ns**.

| Attempt | Captured scope and window | What you can learn |
|---|---|---|
| Full reference | All selectable declarations, 0–260 ns | Baseline behavior and trace population. |
| Initial | Local request state plus clock/reset, 220–250 ns | Timeout is visible; acceptance history is absent. |
| Request window | Adds request/grant/upstream state, 170–250 ns | Acceptance is visible, but upstream state is already active. |
| Expanded | Adds upstream write/value, 110–250 ns | Earlier write, latch, grant removal, acceptance and timeout are visible. |

The useful result is the evidence chain that answers the question. The smallest initial file cannot explain the earlier cause.

The runner checks actual emitted declarations, first/last timestamps and values with PyVCD. It compares **261 selected functional frames** with the original uninstrumented execution and also checks instrumented execution without dumping. It retains both binary identities. This is correspondence of selected observations, not proof that every internal state is identical.

A separate counterfactual changes `config_value` to zero and changes response/timeout. That is exploratory evidence with altered input; it is not presented as reproduction of the original run.

## Inspect the retained outputs

| Output | Use |
|---|---|
| `sources/`, `source-manifest.json`, build invocation records | Inspect the wrapper, design, sources/hashes and actual native build commands. |
| `plain.bin` / `traced.bin` and capability records | Distinguish the original and trace-enabled executables and their instrumentation. |
| `inventory.vcd`, `header.json`, `context.json`, `inventory.json` | Check declaration namespace, header binding, producer facts and semantic aliases. |
| `full-`, `initial-`, `request-window-`, `expanded-` plan/recipe records | See the question, selections, exact time controls, workload and rendered literal command. |
| Corresponding `.vcd` and `.gtkw` files | Inspect emitted values; use the save file for selected viewer signals/window/marker. |
| `summary.json` and `recipe-timing.json` | Read scoped observations, capture sizes, correspondence and stage measurements. |
| `*.invocation.json` | Retain original arguments, exit status, output and timing for the relevant native operation. |

Do not overwrite the archive while comparing attempts. GTKWave save files are prepared with PyVCD's formatter; no viewer is installed or launched. Actual GUI loading/rendering has not been qualified here.

To inspect/import a retained header again, run from the module directory with new output names:

```sh
python3 waveform_capture.py inspect-vcd native-example/inventory.vcd \
  --output native-example/header-review.json
python3 waveform_capture.py import-vcd native-example/inventory.vcd \
  native-example/context.json --output native-example/inventory-review.json
```

Import checks the pinned header/context relationship. It does not validate the waveform body or re-run the simulation.

## Understand the native control boundary

The wrapper's `--capabilities` reports the actual producer version, instrumentation, **1 ns** tick and its own **1,000,000-tick** bound. `--inventory-vcd FILE` exports initialization declarations.

The rendered capture contract is:

```text
BINARY --capture-vcd FILE --start-tick N --end-tick N --stop-tick N --select LEAF [--select LEAF ...] -- WORKLOAD_ARGS
```

The wrapper applies `dumpvars(1,full_leaf)` before opening VCD, delays opening until the start tick, and dumps after evaluation through the end tick inclusively. Simulation begins from reset. The wrapper never emits depth zero, which would reset selection to everything.

Basic dot-separated leaf identifiers and packed buses are supported. Individual unpacked-array and escaped VCD names do not automatically map to native leaf selectors. The assessment exposes additional declarations introduced by prefix/depth semantics.

This example supports workload options `--request-cycle`, `--config-cycle` and `--config-value` after `--`, and rejects unknown workload/trace options. It does not provide FSDB/FST, generic Tcl, runtime reselection, trigger buffers or checkpoint restore.

## Adapt it to a project

1. Start with the original observation, native runner, source/build identity and actual visibility. Inspect existing trace hooks before introducing a wrapper.
2. Establish supported selector syntax, time resolution, window semantics, instrumentation and earliest available history from that producer.
3. Map original native declarations and evidenced aliases into the inventory. Do not infer runtime visibility from RTL names.
4. Build the first plan around a discriminating question, with explicit signal rationale and reasons to expand.
5. Inspect rendered arguments, run through the native workflow, check the trace and compare selected original behavior.
6. Preserve altered-input branches and replay uncertainty explicitly. Revalidate mappings and capabilities after a build/tool change.

Your AI agent can follow [SKILL.md](../../SKILL.md) and [AI_USAGE.md](../../AI_USAGE.md), using its existing tools/subscription. For another simulator, retain the investigation method and qualify its own native export/control mapping; do not reuse this wrapper's flags as a universal interface.

## Interpret the measurements

Reports keep plan/render time, compilation/instrumentation, whole-child wall and CPU time, VCD bytes/declaration count, tokenization and viewer-file preparation. Repeated rounds alternate full/scoped dump, instrumented no-dump and plain no-dump with matching selected behavior.

Whole recipe timing includes these stages and temporary cleanup. Tool installation, Python startup, GUI viewing and engineer review are excluded. Trace-enabled code and replay/setup can dominate this small fixture. Smaller VCD files support a scoped storage observation; they do not establish complete-workflow or SoC speedup. Delayed dumping does not avoid simulation before the dump window or recover unrecorded history.

## Tests and handoff

From the waveform-capture module directory:

```sh
OPENTOOLS_WAVEFORM_NATIVE=/path/to/verilator_bin \
  VERILATOR_ROOT=/path/to/share/verilator \
  python3 -m unittest discover -s tests -v
```

The native run is opt-in. Windows supports portable helper and optional VCD import tests; native Windows/macOS, commercial simulators and GTKWave GUI loading are untested by this recipe.

Hand off the original/capture identities, plans, trace evidence, correspondence scope, measured costs, unresolved observations and next expansion. Optional DVIT context is consumed through the shared mechanism described in the [module guide](../../README.md); this example runs independently.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
