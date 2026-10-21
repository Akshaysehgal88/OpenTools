# Native register controls

The owned [SystemRDL source](effects.rdl) defines two pending causes in a W1C
register and a read-clear diagnostic register. PeakRDL-regblock generates the
actual storage and passthrough bus implementation. The
[testbench](access_tb.sv) resets and primes state before each scenario, then samples
native acknowledgement, errors, readback, byte/bit enables and hardware field
storage. It does not use a second software read for pre/post state.

Qualified recipe: Linux, Python 3.10+, systemrdl-compiler 1.32.2,
peakrdl-regblock 1.3.1, Verilator 5.020 and its normal GCC/Make toolchain.

```sh
python -m pip install -r requirements-example.txt
python examples/run_native.py /tmp/register-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Choose a new output directory. It retains source, generated RTL, commands, build
diagnostics, executable, raw native observations, normalized records and reports.
A temporary space-free build directory avoids Make path limitations.

| Control | Observed effect | Expected review |
|---|---|---|
| RMW acknowledges cause 0 | Read 3, write 3, both causes clear | Unintended cause-1 clear |
| Direct mask | Write 1, cause 1 remains pending | Within supplied contract |
| Low byte disabled | Write 1, both causes remain pending | Required acknowledgement missing |
| Diagnostic peek | Read 3, both causes clear | Destructive observation |
| Diagnostic consume | Same read, deliberate consumption | Within supplied contract |

An independent cause-ID set model checks six native accesses. Intent is supplied
separately from those transitions. This fixture qualifies these supported effects,
not arbitrary generated blocks, silicon behavior or concurrent hardware timing.

```sh
python -m unittest discover -s tests -v
```

Optional SDK tests skip without SystemRDL. Set `OPENTOOLS_VERILATOR` and
`OPENTOOLS_VERILATOR_ROOT` to include the generated native simulation test.
