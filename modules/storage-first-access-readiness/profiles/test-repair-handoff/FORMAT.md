# Owned observation profile

Python 3.10+ standard library is sufficient for saved-data review. Native example
generation uses Linux, a C++ compiler and Verilator 5.020:

```sh
python examples/run_native.py /tmp/repair-trials --verilator /path/to/verilator_bin --verilator-root /path/to/verilator/runtime
python handoff.py review /tmp/repair-trials/word-bank-good/run /tmp/repair-trials/word-bank-good/context.json /tmp/repair-trials/word-bank-good/receiving-policy.json
OPENTOOLS_REPAIR_NATIVE=/tmp/repair-trials python -m unittest discover -s tests
```

The collector builds once per geometry and runs twelve fixed stimulus plans per
build. Sources and plans are frozen before execution; original XML, ELF, selected
command, exit status, stdout and stderr are retained. `create_example.py` derives
receiving records from the independent owned contracts and binds the selected
source/plan/command/binary identities. Example hashes are local integrity bindings,
not proof of trusted execution or acceptance by a production owner.

## Context and retained native files

`context.json` uses `opentools.repair-context.v1`. Identity fields are `run_ref`,
`scope_ref`, `design_ref`, `configuration_ref`, `memory_ref`, `init_epoch_ref` and
`transition_ref`. Include the selected direct `unit_instance`, `unit_type`,
`memory_variable`, exact distinct `role_map`, `reset_asserted` and `ecc_profile_ref`.
Basis references identify mapping, macro view, wrapper, repair, test, initializer,
instrumentation and owner. Missing basis references remain gaps.

The reader follows the selected instance's actual XML definition, including
parameter specializations. It checks native port directions/widths, direct role
connections, unpacked physical array and logical readiness width. One command
interface does not imply a one-port foundry macro. Byte order is the owned model's
qualified behavior, not a fact inferred from array dimensions.

The native directory contains the five sources (`ecc_profile.sv`, `memory_bank.sv`,
`top.sv`, `main.cpp`, `plans.hpp`), `model.xml`, `Vtop`, `version.txt`, `plan.json`,
`execution.json`, and build/xml/run command JSON and stdout/stderr text. Commands
are argument arrays. The reader pins the owned bank, logger and parent SECDED
package; other implementations require qualification. No retained command is run.

`TIME_UNITS` records native timeunit/precision, both 1 ns. `CONFIG` binds selected
plan, flags, geometry, reset polarity, expected payload and step count. `INIT`
records actual initial state. Each `TX` contains sequence, actual tick, event ID,
pre-transaction state, driven inputs, observed outputs and assertion counters.
The ordered numeric field list is `repair_common.FIELDS`; state uses
`repair_common.STATE`. `NATIVE_RESULT` closes the exact window. The reader checks
state continuity, widths, stimulus against the compiled selected plan, original
assertion counts and exit status. These checks do not turn driver expectations
into receiving requirements.

## Receiving contract

`receiving-policy.json` uses `opentools.repair-policy.v1` with:

- `identity`: independently selected context identities; `source_sha256`,
  `plan_sha256`, `run_command_sha256`, `binary_sha256`: accepted artifact bindings.
- `source_ref`, `owner_ref`, `inputs_complete`: scope and receiving basis.
- `geometry`: logical/physical words, data/codeword bits, byte lanes, command ports,
  little-endian byte order and base address.
- `repair`: owned ABI, explicit `required` and `expected_payload`.
- `required_init_words`, `required_init_data` (`word`, `data`),
  `required_test_physical_words`, `release_event_ref` and `required_accesses`
  (`event_ref`, `operation` 7, `word`, `expected_data`). Keep these rosters independent
  of observed coverage. The helper currently accepts read obligations; the AI
  workflow retains additional consumer requirements outside that profile.

Owned repair payload: 12 bits, valid bit 11, bad logical row bits 9:6, spare physical
row bits 4:1, reserved mask `0x421`. An accepted valid-format load sets loaded;
remapping is active only when valid is set. Every accepted load advances an epoch.
This ABI is an example, not a foundry fuse specification.

Operations: 0/1 raw test write/read; 2 limited test completion; 3 repair load;
4 enable ECC; 5 full-codeword initialization; 6 release request; 7 functional read;
8 functional write; 10 disable ECC. Raw test access provides no initialization
credit. Only admitted initialization under the current mapping epoch supplies
release credit. A full functional write can initialize without an old-data read.
Partial nonzero writes read and merge old data; zero-mask writes do neither.

## Output

The report keeps native PASS/FAIL, findings, gaps, admitted initialization,
handoffs, accesses, owner and recheck triggers. Foreign/stale scope or artifact
bindings quarantine receiving attribution while retaining the native result.
Known failures remain visible alongside missing evidence. Aligned means only
that this selected, supplied contract is satisfied; it is not production approval.

`examples/reference_model.py` independently replays physical memory, ownership,
mapping epochs and byte-vector updates using the parent's Python SECDED oracle.
The native package implements encoding/decoding separately. Qualification covers
controlled two-state words; it does not model physical uninitialized memory.
