# Native logical-loss controls

[restore_path.sv](restore_path.sv) holds a scalar payload, identity, valid bit,
auxiliary metadata and an initialization-ready bit. KEEP_MASK selects which fields
survive one explicitly modeled logical loss. A read port returns actual hit/error/
data observations. Cache-like and context/owner profiles use different saved data
and identities; these are contexts for one bundle-review activity.

Qualified recipe: Linux, Python 3.10+, Verilator 5.020 and its GCC/Make toolchain.
No Python packages are required.

```sh
python examples/run_native.py /tmp/restore-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Choose a new output directory. Source, command, build diagnostics, executable,
raw selection/action/state/read rows and per-case records/reports are retained.
A separate image/loss/rebuild reference checks 108 native rows and explicit actual
read outcomes. The helper's wider scalar comparison is also tested with a 512-bit
value; the owned native fixture itself uses an 8-bit payload.

| Control | Native result | Review |
|---|---|---|
| Cache payload only | Metadata lost; read misses | Warm bundle not restored |
| Cache metadata only | Read hits with zero payload | Wrong restored data |
| Cache paired | Saved payload and metadata read correctly | Within observed contract |
| Dirty metadata lost | Read data correct; dirty bit cleared | Bundle metadata mismatch |
| Valid before initialization | Early read faults; final state later agrees | Exposure/order failure retained |
| Initialize before valid | Lost flags rebuilt before publication; read succeeds | Within observed contract |
| Explicit cold rebuild | Clean initial state discarded; new image/identity read | Within cold rebuild contract |
| Context metadata only | Owner retained; context data lost | Wrong restored data |
| Context paired | Owner and context payload agree | Within observed contract |

The cold control starts clean and explicitly permits discard/reinitialization.
The dirty-loss control observes a metadata violation, not an actual eviction or
writeback failure. The initialization fault is a logical guard, not ECC encoding.
Selective assignment-to-zero is not power-aware simulation or retention-cell
validation; physical loss, X propagation, analog behavior and timing remain outside
this fixture's qualification.

```sh
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_VERILATOR` and `OPENTOOLS_VERILATOR_ROOT` to include the native test.
