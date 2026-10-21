# At-speed recipe and STA handoff

Use when an OCC recipe, launch/capture mode or timing scenario changes. Compare
the required pulses and control setup with observed behavior and the selected
native clocks, mode cases and exceptions. Start with [WORKFLOW.md](WORKFLOW.md).
The AI workflow accepts your existing engineering artifacts and tools.

## Saved-data helper

Python 3.10+, standard library only. This profile reads the owned LOC/shift logger
from Verilator 5.020 and OpenROAD `v2.0-17598-ga008522d8` STA exports. It checks the
shared path source, observed pin roles, measured nanoseconds and original run
identities before comparing the independent recipe. See [FORMAT.md](FORMAT.md).

From this profile directory:

```sh
python occ_handoff.py capture artifacts behavior/run sta/run context.json --output evidence.json
python occ_handoff.py review artifacts contract.json evidence.json \
  --json-out review.json --markdown-out review.md
```

Fill the [context](templates/context.json) and [contract](templates/contract.json)
from the original request, native mappings and independent recipe. Keep the original
inputs and outputs. A compatible retained STA scenario can be paired with another
behavior run when their shared source and scenario identities match; that pairing
is not a new STA execution. Outputs must be distinct new files. Capture and review
never execute received Tcl, commands or executables.

Review exits: `0` bounded alignment, `1` review required, `2` incomplete or quarantined
evidence, `3` invalid input. A complete native behavior failure can be captured
with exit `0`; its failure remains in the evidence and review.

## Qualification

The owned examples use two differently named clock paths, 10/16ns source periods
and opposite reset polarities. Controls cover valid capture, a shift-only exception
in capture, gap/missing/extra pulses, scan-enable setup, reset held, clock-period
disagreement, unknown native cases and valid shift with/without an exception.
A native checker pass can still fail the independent recipe's stronger guard.

The collector runs two native builds, 14 STA scenarios and 28 behavior controls:

```sh
python examples/run_native.py out --openroad /path/to/openroad \
  --verilator /path/to/verilator_bin --verilator-root /path/to/verilator-runtime
OPENTOOLS_OCC_EXAMPLE="$PWD/out" python -m unittest discover -s tests -v
```

Native generation is qualified on Linux with the pinned tools already configured;
it downloads nothing. Saved-data review also runs on Windows. Native-corpus tests
skip when the environment variable is absent.

The library and gate models are owned ideal fixtures. Setup/hold numbers establish
native path visibility, without characterizing timing. This reader does not qualify
native ATPG artifacts, fault coverage, physical pulse quality or behavior between
sampled instants. Preserve stronger requested claims and use the relevant native
tools and owner evidence. Install the parent module with the
[project-local installer](../../../../INSTALL.md); DVIT is optional.
