# Native clock-transition controls

[clock_path.sv](clock_path.sv) defines a root-clock enable controller, a gated-clock
worker and a root-clock completion wait. Five instances cover bad/fixed boot,
bad/fixed wake and wake without restore. Wake readiness needs two worker edges;
boot readiness needs one. The testbench holds request/restore conditions stable
for eight sampled root edges after reset.

Qualified recipe: Linux, Python 3.10+, Verilator 5.020 and its GCC/Make toolchain.
No Python packages are required.

```sh
python examples/run_native.py /tmp/clock-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Choose a new output directory. Source, command, build diagnostics, executable,
raw native configuration/observations, normalized per-case records and reports
are retained. A temporary space-free build directory avoids Make path limits.
An independent rising/falling-edge schedule checks all 40 sampled rows.

| Case | Native observation | Static model |
|---|---|---|
| Boot cycle | No worker edges or completion observed | Circular prerequisite candidate |
| Boot fixed | Worker ready and wait released | Goal derivable |
| Wake cycle | No worker edges or completion observed | Circular prerequisite candidate |
| Wake fixed | Two worker edges establish ready; wait releases | Goal derivable |
| Wake without restore | No worker edges or completion observed | Missing prerequisite; no cycle |

The fixture's falling-edge gate update is not a qualified integrated clock-gate
cell. These controls check source mapping and bounded progress; they do not
establish glitch quality, X-state behavior, unbounded liveness or physical timing.
The JSON mapping is explicitly source-reviewed, not automatically extracted.

```sh
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_VERILATOR` and `OPENTOOLS_VERILATOR_ROOT` to include the native test.
