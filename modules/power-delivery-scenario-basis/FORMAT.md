# Evidence and support boundary

The batch profile reads original OpenROAD/PDNSim static evidence. It executes no
retained Tcl, commands or binaries. Original source, command, tool and artifact
hashes identify bytes; they do not authenticate consumption, freshness or authority.

`opentools.supply-context.v1` declares run/scope/design/configuration/scenario,
relationship sources, explicit net voltage, power overrides, resistance arguments,
source rows, selected library/corner and activity/state/concurrency assumptions.
Source CSV coordinates and bump size use micrometres; voltages use volts. Resolved
native source nodes are retained separately, including native grid discretization.

`opentools.supply-execution.v1` retains consumed source and original tool/command
identities, output hashes and process exit. Native stage records preserve Tcl
catch codes and returned values for connectivity, analysis and SPICE export.
Process exit zero can coexist with a failed native analysis. Successful analysis
means a static solution was produced; it is not electrical acceptance.

Native exports retain physical supply terminals/shapes and the selected library
operating point. Voltage CSV retains original per-terminal volts and locations.
Native SPICE retains actual resistors in ohms, DC current sources in amperes and
ideal voltage sources in volts. Explicit power overrides are watts in this pinned
profile; effective current correspondence is checked against the native sources.
Resistance command arguments follow native library units. The reader does not
compute voltage from those inputs. The independent DC solver in examples is for
validation only.

Missing or changed original voltage/network reports leave those facts unknown
while preserving original native status. Source, topology, command or fixed-stage
artifact changes reject intake. Native failure can coexist with missing numerical
results. No zero drop, electrical violation or successful solution is invented.

`opentools.supply-request.v1` states the independent claim, owner, required field
roster, source basis and required-claim flags. Fields include source identities,
setup, scenario, configuration, tool identity and selected operating point. Missing
values remain unknown. The operating-point comparison allows `1e-6` native floating
representation error, not an engineering corner range. Required dynamic IR, wake
sequence, EM lifetime, load-model validation and full-chip claims remain open.

`opentools.supply-policy.v1` selects an original run and binds its context/source/
artifact identities. An optional cached run has its own binding and is reviewed
against the same request. It is suggested only when that review corresponds.
Read original request sources before treating a prepared policy as authoritative.

Batch qualification covers one flat power net, one selected library cell,
explicit steady power overrides, one known PG terminal per instance, and the
bundled loader/pinned native version. It checks complete current/voltage population
and a native source population matching the source rows. Broader bump mapping,
multiple PG pins, other load models, loaders, ground analysis and transient solvers
need separate qualification. The generic exporter also works after a loaded native
database reopen; it does not automatically admit other flows to the batch reader.
Use the AI workflow with the team's native evidence beyond these helper limits.
