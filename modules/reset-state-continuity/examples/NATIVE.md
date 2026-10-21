# Native reset controls

[reset_path.sv](reset_path.sv) has producer pending state and consumer context on
independent reset inputs. Five instances cover warm partial reset, reset of both
owners, drain before reset, watchdog fresh start and explicit retained-event
replay. Reset-held and release samples occur before further delivery; the bounded
post sample follows delivery and one additional root tick.

Qualified recipe: Linux, Python 3.10+, Verilator 5.020 and its GCC/Make toolchain.
No Python packages are required.

```sh
python examples/run_native.py /tmp/reset-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Choose a new output directory. It retains source, command, build diagnostics,
executable, raw parameters/state/reset observations and per-case records/reports.
A temporary space-free build directory avoids Make path limits. The independent
reset/delivery reference checks 20 phase rows and observed reset/clock controls.

| Case | Native post-reset result | Review |
|---|---|---|
| Warm partial reset | Producer survives; unowned completion arrives | Continuity risk and observed orphan |
| Reset both owners | Pending work and consumer context clear | Within sampled contract |
| Drain first | Pending work consumed before consumer reset | Within sampled contract |
| Watchdog fresh start | Old retained event has no consumer context | Continuity risk and observed orphan |
| Watchdog replay | Restart explicitly consumes retained event | Within declared replay contract |

In this owned fixture, the consumer can accept new work as soon as reset releases;
that is not a general software-initialization assumption. Clock availability is a
testbench source control, with actual edge counts retained. These reset-primed
digital controls do not qualify analog reset behavior, X states, synchronizers,
physical RDC or exhaustive transaction replay.

```sh
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_VERILATOR` and `OPENTOOLS_VERILATOR_ROOT` to include the native test.
