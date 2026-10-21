# Native buffered-publication controls

The owned RTL has separate pending payload/publication queues and an ordered
observer. Commit events make each single-bit sentinel visible. A captured matching
domain control gates publication until payload commits. It is a concrete bounded
implementation example, not a new ISA memory model.

Run from this profile directory on Linux with Verilator 5.020, C++, make and
Python 3.10+:

```sh
python examples/run_native.py /tmp/ordering-proof --verilator /path/to/verilator_bin --verilator-root /path/to/verilator/share/verilator
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_VERILATOR` and `OPENTOOLS_VERILATOR_ROOT` for the native unittest.
The runner creates a new directory and retains sources, commands, diagnostics,
executable, raw steps, outcome enumeration, normalized records and reports. Nothing
downloads or installs tools.

Ten configurations exercise 55 schedules/372 observations. Nine configurations
try all six permutations of payload commit, publication commit and consumer poll.
Matching controls reject three premature publication attempts; three successful
linearizations remain. Unordered paths permit all six, including publication,
poll, payload commit: observed flag1/payload0. A separate favorable selected run
observes only flag1/payload1 while its complete model still permits stale data.

| Control | Owned-path result |
|---|---|
| RAM without control | Stale observation permitted and observed. |
| RAM W→W | Publication gated until payload commit. |
| MMIO without control or with W→W | Output is not covered; stale remains permitted. |
| MMIO W→O or full mask | Domain-specific gate prevents stale publication. |
| Wrong predecessor | Control does not cover the normal-memory payload write. |
| Control too early or too late | Actual issue placement prevents ordering credit. |
| Favorable selected schedule | Observation alone does not establish exclusion. |

[reference_model.py](reference_model.py) independently enumerates legal topological
orders and maintains queue/consumer state. Every native action/state field and
outcome is compared. Consumer read registers persist even after final memory
becomes1; final memory is never substituted for an earlier response.

The model has no caches, compiler/ISA execution, speculation, device protocol,
atomics, architectural access widths or translation maintenance. Sentinels are
single bits; this does not establish atomicity of a hardware word access. The
mask labels illustrate the declared owned-domain contract and are not a universal
fence recipe or RVWMO/MMIO platform qualification.

RISC-V documents [FENCE predecessor/successor domains and platform classification](https://docs.riscv.org/reference/isa/unpriv/rv32).
Its [RVWMO specification](https://docs.riscv.org/reference/isa/unpriv/rvwmo.html)
has a defined scope that must not be silently extended to I/O. These are references
for review; this recipe executes neither RISC-V instructions nor a formal ISA model.
