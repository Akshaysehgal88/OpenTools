# Native event-route controls

[event_path.sv](event_path.sv) has a root-clock source, sampled-high-once functional
gateway and independent sticky wake latch. Service acknowledges the gateway;
source clearing is a separate root-clock effect. The testbench changes gates while
the root is low and samples all state/counters after each root tick.

Qualified recipe: Linux, Python 3.10+, Verilator 5.020 and its GCC/Make toolchain.
No Python packages are required.

```sh
python examples/run_native.py /tmp/event-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Choose a new output directory. It retains source, command, build diagnostics,
executable, raw parameter/state/counter rows and normalized per-case records and
reports. A separate old-state reference and explicit expected per-stage counts
check 72 native rows. Source assertion and stage markers come from actual event
counter deltas; clock markers come from actual edge-counter deltas.

| Control | Observed distinction | Review |
|---|---|---|
| Clear before late wake capture | IRQ serviced and source cleared; no wake captured | Required wake and clear-order failure |
| Capture before service | Wake capture precedes source clearing | Within selected contract |
| Pulse, IRQ required | Wake occurs while stopped IRQ gateway misses pulse | Required interrupt stages absent in window |
| Held source, IRQ required | Cause survives stopped gateway and is serviced later | Within selected contract |
| Wake-only intent | Same pulse/wake behavior; no interrupt obligation | Within selected contract |
| Service without source clear | Service observed; source stays asserted | Required source clearing absent in window |

Sleep-window intent in this fixture requires retained wake, with no sleep-abort
alternative. A real implementation may have another valid entry path. This
digital observation fixture is not a PLIC, ICG or CDC reference circuit and does
not qualify glitches, X states, pulse widths or physical wakeup behavior.

```sh
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_VERILATOR` and `OPENTOOLS_VERILATOR_ROOT` to include the native test.
