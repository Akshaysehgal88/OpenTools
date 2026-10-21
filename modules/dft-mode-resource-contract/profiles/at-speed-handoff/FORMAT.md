# LOC/shift evidence profile

## Context and independent recipe

`opentools.occ-context.v1` selects run, scope, design, configuration, domain, phase,
recipe, STA run/scenario and source-basis references. Its mapping selects the unit,
gate target, launch/capture cells, root/generated clocks, reset polarity and 14
observed signal roles. Native ATPG scenario/basis references may be retained as
declarations. This reader does not qualify an ATPG artifact from those labels.

`opentools.occ-contract.v1` contains `expected` identities, mapping, original native
source/command SHA256 values and an independent `recipe`. Missing hashes remain
gaps; different identities quarantine evidence before attribution. The recipe names
LOC capture or shift control, source period in integer nanoseconds, increasing
source-edge indices, required control guard, reset/scan levels, selected path,
exception applicability and source/owner references. Capture requires two consecutive
source edges and a visible selected timed path; its selected path cannot be marked
shift-exempt. Shift may retain conservative timing without an exception.

Source-edge indices use the first observed root rise as index zero. This avoids
inventing an absolute phase relationship between simulator initialization and the
STA clock's time origin. Generated rises must coincide with selected root rises.
Sampled high spans and native half-period waveforms are checked in the owned
profile; that is a logical comparison, not physical pulse certification.

The guard is independent of the native checker's guard. Correct values at the edge
with a known recent change are mismatches. Missing earlier history stays unknown.
Required source edges beyond the recorded window remain gaps; matching a prefix
cannot close a longer recipe. `require_native_atpg=true` retains an explicit gap
because this profile has no qualified native ATPG reader.

## Original directories

Capture takes separate relative behavior and STA directories within an artifact
root. Shared `unit.v` identities must match. Retain:

- Behavior inputs: `unit.v`, `top.sv`, `models.sv`, `ports.hpp`, `main.cpp`.
- Behavior outputs: build/XML command, stdout and stderr files, `model.xml`,
  original `Vtop` ELF, `run.command.json`, `run.stdout.txt`, `run.stderr.txt`,
  `execution.json`, `version.txt`.
- STA inputs: `unit.v`, `cells.lib`, `cells.lef`, `sta.tcl`.
- STA outputs: `command.json`, `stdout.txt`, `stderr.txt`, `execution.json`,
  `version.txt`, `resources.txt`, native `consumed.sdc`.

The [collector](examples/run_native.py) defines the qualified commands. It hashes
inputs before/after execution. The source unit uses one AND gate, two scalar
`SCANR_CELL` instances and either a direct active-low reset alias or one `INV_CELL`
for an active-high input. XML binds logger roles through unit ports to selected
primitive pins. Other native interfaces/cells require another qualified method;
the broader AI workflow can use the team's existing artifacts.

The native STA export contains explicit supplied job/scenario labels, native clock
properties/source pins, root case values, resolved from/to cells and selected
path counts without/under the selected exception. Labels are not engine-generated
attestations. Native `write_sdc` supplies the consumed root/generated clock,
case-analysis and false-path statements. This reader parses that limited writer
format as data. It does not evaluate Tcl or assume `report_exceptions` exists.
The pinned profile requires a 1ns Liberty unit; native waveform updates and user
unit conversion are performed by its export script. Unknown cases remain `X`.

Behavior records use `TIME_UNITS -9 -9`, native `CONFIG`, contiguous 1ns `SAMPLE`
observations, a measured `PULSES` list and `NATIVE_RESULT`. Native comparison actions
and totals are recounted. Capture windows cover 18 source cycles, including quiet
time after the owned controller stops; shift controls cover nine cycles. The
independent [reference model](examples/reference_model.py) checks owned fixture
semantics separately. Source/oracle references still need review.

## Review boundary

Rehashing/recapture rejects edited originals or normalized fields. Duplicate keys,
unsafe paths, symlinks and unsupported native formats are rejected. Received
commands, Tcl and executables are never executed. Artifacts and supplied references
are not authenticated execution, freshness or acceptance proofs.

Reports retain STA completion, native behavior pass/fail, path probes, pulse/control
observations, findings and gaps separately. Known mismatches take precedence over
gaps while retaining both. Cached STA is reusable only with matching input/scenario
and shared-unit identities; a new pairing is not a new timing run. No report grants
ATPG coverage, pulse-quality certification, production timing or owner approval.
