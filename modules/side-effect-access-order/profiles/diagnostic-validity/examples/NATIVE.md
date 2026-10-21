# Native recovery and capture controls

Qualified recipe: Linux, Verilator5.020 with its C++/make runtime and Python3.10+
standard library. From this profile directory:

```sh
python examples/run_native.py /tmp/diagnostic-proof --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_VERILATOR` and `OPENTOOLS_VERILATOR_ROOT` for the native unittest.
Nothing downloads/installs tools. A new output directory retains source, build
command/diagnostics, executable, raw columns, normalized records and reports.

The owned RTL latches a cause, returns actual accepted read data, applies read-clear
or reset effects and captures the last response into a separate saved record.
The saved value is the returned response, not the already-cleared live bank.
A path enable controls access; a blocked attempt produces an actual error and no
valid response. It is not a physical clock gate or power-aware simulation.
The `clock-unavailable` fixture uses this access-enable surrogate. Recovery is a
synchronous owned command that clears or retains the selected state; it does not
model an asynchronous reset tree.

| Control | Selected diagnostic evidence |
|---|---|
| Capture before recovery | Saved response retains cause1 and its source epoch. |
| Read zero after reset | Cannot establish absence in the cleared earlier epoch. |
| Explicit undetermined after reset | Unknown remains; no fault conclusion invented. |
| Monitor reads first | Read-clear consumes the cause before the consumer reads. |
| Access unavailable | Idle/stale response bits supply no diagnostic observation. |
| No-fault control | Complete clean observed prefix supports bounded absence. |
| Old valid crash record | Set bits alone supply no current capture provenance. |
| Capture bank reset too | Earlier response is not still present in the invalid slot. |
| Engine-local retained status | Different cause bit and nondestructive read remain valid across a reset that preserves the bank. |
| Engine-local status clear | A later zero loses the earlier epoch again. |
| Fault-free retained engine | Bounded negative control under the second contract. |

Eleven controls/47 state-action observations are compared against an independent
[cause-set and read-receipt reference](reference_model.py). The raw harness knows
which fault it injected; the selected consumer artifact may still be unknown.
Keep those evidence roles separate. These controls qualify no silicon root cause,
watchdog/crash subsystem, arbitrary reset tree, asynchronous/concurrent fault,
X/metastability, physical retention or complete firmware logging path.

OpenTitan's [reset information and recorded state](https://opentitan.org/book/hw/top_earlgrey/ip_autogen/rstmgr/doc/theory_of_operation.html)
and [register side-effect definitions](https://opentitan.org/book/util/reggen/index.html)
are review references. This owned recipe does not execute or qualify OpenTitan.
