# Native clock evidence boundary

The saved reader checks original source, command, tool, setup and native artifact
identity. It executes no retained Tcl or SDC. Byte hashes and reference labels do
not authenticate source authority, freshness, mode intent or receiving acceptance.

Native JSON lines retain clock period, generated/propagated state, resolved
constraint waveform, definition-target pins, complete register clock-pin census,
clock-to-pin associations, actual cases and a selected native path observation.
All timing values use the pinned native ns UI. Constraint waveforms are timing
model objects, not measured physical pulse quality.

The pinned STA exposes `all_registers -clock ... -clock_pins`; it does not expose
`get_clocks -of_objects` or clock master/divide properties. A trace at the native
generated-clock constructor boundary retains already resolved Pin/Clock objects
after successful creation, then forwards the original return unchanged. It is not
an SDC parser or a posthoc master-clock getter. The timing reference source is
separate from the generated clock's definition target.

The trace requires the pinned 13-argument native ABI and starts before definitions.
The bundled loader creates each clock once, with no deletion/redefinition, then
restores the native command before final collection. The reviewer checks one
creation record per generated clock, explicit master, final object correspondence
and matching targets. Implicit masters, absent/ambiguous journals, unsupported
generation options or changed object lifecycles remain unresolved. Generic traces
from other flows need their own lifecycle and producer qualification.

`opentools.sta-lineage-context.v1` binds run/design/configuration/mode, setup and
relationship sources. `opentools.sta-lineage-execution.v1` retains original tool,
source, command and artifact hashes. Missing/changed native files reject intake;
missing metadata in a retained export remains a review gap, not a hardware failure.

`opentools.sta-lineage-contract.v1` supplies independent source identities, complete
mode-port/clock/consumer rosters, required clock fields, explicit lineage, selected
path requirement, owner and claim strength. The example contracts are written
before native execution. A policy binds one original export to that contract.
Dropping a native consumer from the contract is reported. Native floating timing
representation uses `1e-6` ns comparison tolerance, not an engineering margin.

Batch qualification covers one mode/tree, flat scalar primitives, one root and
single-pass explicit-master integer dividers, with the bundled loader/pinned
OpenROAD version. Generic final collection can inspect an existing loaded flow or
saved-database replay without recovering original creation history. Other loaders,
clock transformations, hierarchical/partial-tree mapping and full signoff need
separate qualification. The AI workflow can use broader team-native evidence.
