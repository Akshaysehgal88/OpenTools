# Native focused-capture example

This opt-in Linux example uses Verilator **5.020**, GCC C++17, GNU Make and
**pyvcd==0.5.0**. Its flags belong to the supplied wrapper, not every Verilated
binary. Inspect existing native hooks before introducing another wrapper.

From the waveform-capture module directory, with the optional
[requirements](../../requirements-native-example.txt) already installed:

```sh
python3 examples/verilator/run_example.py --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator --directory native-example --timing-repeats 3
```

Choose a new output directory with an existing parent. Retained outputs include
sources/hashes, build commands, plain/instrumented binaries, capabilities, native
declarations and bound context, plans, literal recipes, VCD/GTKWave files, original/
replay observations and timings. Owned space-free temporary builds accommodate
GNU Make's path restrictions; output paths may contain spaces. No tools install
or build through the project-local installer.

## Investigation

The DMA timeout path depends on upstream quiesce control. The driver writes that
control at 120 ns, submits a request at 180 ns and observes timeout at 240 ns.

| Capture | Scope/window | Available observation |
|---|---|---|
| Full | All selectable declarations, 0-260 ns | Baseline trace |
| Initial | Local DMA plus clock/reset, 220-250 ns | Timeout, no acceptance history |
| Request window | Adds request/grant/upstream state, 170-250 ns | Acceptance; upstream state already active |
| Expanded | Adds upstream write/value, 110-250 ns | Earlier write/latch/grant removal, acceptance and timeout |

The script verifies emitted declaration sets and first/last timestamps, reads
values through PyVCD and compares all 261 selected functional frames to the original
uninstrumented run. Instrumented no-dump execution also checks correspondence.
Both exact binary identities remain. A counterfactual changes config_value to zero
and changes response/timeout; it is exploratory evidence, not reproduction.

## Native controls

`--capabilities` advertises the actual producer version, instrumentation, 1 ns tick
and this demonstration wrapper's 1,000,000-tick bound. `--inventory-vcd FILE`
exports initialization declarations. The renderer verifies current binary bytes
and the supplied declaration namespace.

The wrapper uses `dumpvars(1,full_leaf)` before opening, delays open until start
tick and dumps after eval through end tick inclusively. Simulation still begins
from reset. Runtime depth zero would reset selection to everything; it is never
emitted. Individual unpacked-array/escaped VCD names are not assumed valid native
selectors. Unsupported mappings are rejected instead of silently capturing nothing.

This profile supports VCD/basic leaf identifiers and packed buses, not FST/FSDB,
generic Tcl, dynamic reselection, trigger buffers, checkpoint restore or all tool
versions. A declaration export is not full RTL hierarchy. Literal workload args
follow `--`; this example supports `--request-cycle`, `--config-cycle`,
`--config-value` and rejects unknown workload/trace options.

GTKWave save files use PyVCD's formatter with selected names, window start and
failure marker. No viewer is installed/launched. Save-file preparation is exercised;
actual GUI loading/rendering is not qualified here.

## Measurement and tests

Reports retain plan/render time, compile/instrumentation, whole child wall and CPU,
VCD bytes/declaration count, tokenization time and viewer files. Optional rounds
alternate full/scoped dump, instrumented no-dump and plain no-dump with matching
selected behavior. Whole recipe timing includes those stages and temporary cleanup;
tool installation, Python startup, GUI viewing and engineer review are excluded.

Smaller files are a scoped storage observation. The inadequate first trace is not
the best engineering result. Replay/setup/inspection and instrumented code can
dominate this toy; no complete-workflow/SoC speedup or human productivity claim is
inferred. No pre-failure data is recovered retroactively.

```sh
OPENTOOLS_WAVEFORM_NATIVE=/path/to/verilator_bin VERILATOR_ROOT=/path/to/share/verilator python3 -m unittest discover -s tests -v
```

Qualified native execution uses Linux, Verilator 5.020, GCC 13.3, Make 4.3 and
PyVCD 0.5.0. Windows supports the portable helper/optional VCD import tests. Native
macOS/Windows, commercial simulators and actual GTKWave GUI loading are untested.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
