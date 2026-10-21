# Native quiescence controls

[quiescence_path.sv](quiescence_path.sv) transfers one local request to an external
owner. That owner holds a response or credit return requiring a live receiver.
An always-on sequencer closes admission, acknowledges drain, applies isolation,
stops the domain clock and optionally removes logical power availability.

Qualified recipe: Linux, Python 3.10+, Verilator 5.020 and its GCC/Make toolchain.
No Python packages are required.

```sh
python examples/run_native.py /tmp/quiescence-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Choose a new output directory. Source, command, build diagnostics, executable,
raw parameters/state/counts and per-case records/reports are retained. A separate
token-ownership reference checks 72 native rows, accounting conservation and
explicit expected acknowledgement/stop/power milestones. Actual domain-edge counts
remain in the raw journal alongside digital gate/power flags.

| Control | Native observation | Review |
|---|---|---|
| Local-only power drain | Local idle; external response still pending at acknowledgement and shutdown | Owner not quiescent |
| System power drain | External response returns before acknowledgement | Within sampled contract |
| Local-only clock drain | Credit return remains outstanding after stop | Owner not quiescent |
| System clock drain | Credit returns before stop; power remains available | Within sampled contract |
| Power-down without isolation | Both owners drain; isolation stays inactive | Missing prerequisite |
| Late admission | Counts zero at acknowledgement; new local work accepted next cycle | Protected interval violated |

The reference also checks `accepted - handed == local_pending`,
`handed - returned == remote_pending` and `received == returned`. The required-owner
policy is authored independently of the observed inventory. It is not generated
by selecting whichever counters happened to be exported.

This is an owned digital observation fixture, not UPF or an ICG/isolation/power-cell
implementation. Flags do not simulate analog power loss, electrical isolation,
X propagation or physical timing. The two return profiles qualify these bounded
logical controls, not arbitrary response or credit protocols.

```sh
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_VERILATOR` and `OPENTOOLS_VERILATOR_ROOT` to include the native test.
