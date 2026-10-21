# Endpoint records

`opentools.sta-endpoint-context.v1` binds run, scope, design, configuration, mode
and power references. Its setup declares the root clock, binary/null case ports
and explicit input/output delay maps. Original sources and context are frozen
before native execution. Review never executes archived Tcl.

`opentools.sta-endpoint-contract.v1` contains original expected identities,
source/command hashes, requirements/owner references, clock intent, required
case values, input-delay assumptions, an independent endpoint roster and explicit
exemptions. `examples/fixture.py` constructs complete records before execution.

Each endpoint entry identifies `endpoint`, `kind` (`output` or `data`), current
`role`, `timing_required`, `source_clock`, `target_clock`, `output_delay_ns`,
`constant_value` and `basis_ref`. Unknown values use null. Required output timing
needs a sourced delay and clock roles. Register check margins cannot serve as
output-delay requirements.

Each exemption identifies the endpoint, permitted current role, mode/power scope,
reason, approval/source references and optional constant premise. A non-timed
role alone does not grant an exemption. Missing conditions remain unresolved;
native known contrary values and changed roles remain findings. References do
not authenticate approval; inspect the actual source and authority.

`opentools.sta-endpoint-evidence.v1` retains the original execution, command,
source/file hashes and native data. Intake checks the pinned exporter/loader,
version, original context/contract, native artifacts and completion marker.
Edited review contracts remain distinguishable from the captured original.
Foreign identities/hashes are quarantined; missing expected bases stay open.
Changed or missing original artifacts reject intake.

The native JSON-lines export contains clock definitions/associations and register
clock-pin census, case ports, every output/register-data endpoint, separate native
forced/case/simulated logic values, and all returned selected maximum-setup path
records. Path records preserve actual unconstrained/output-delay/check classes,
source/target clocks, native slack string and native margin. `INF` is not a finite
slack. Six-decimal native margin formatting is representation precision, not an
engineering acceptance tolerance.

`unconstrained.txt` is the actual pinned native unconstrained-only verbose report.
Its declared population/count is checked against the complete exported census.
Constants and unclocked sources may appear in the report with no returned path;
they remain in the population. The unconstrained-inclusive path query also returns
constrained paths, so its flag/count never substitutes for native classification.

The report preserves the complete native denominator, independent intent,
exemption admission, native classes and findings/gaps/quarantine separately.
Known mode conditions are needed before a scoped exemption is admitted.
Simulated propagation is distinct from case assumptions and physical tie integrity.
The example approval/ownership references are owned fixture premises, not real
production approvals. Byte/ref binding establishes identity, not authenticity,
freshness, full dependency sufficiency or complete timing/signoff.
