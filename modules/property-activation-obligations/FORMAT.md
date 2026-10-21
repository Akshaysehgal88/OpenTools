# Inputs and native boundary

Use strict JSON with explicit unknowns, source references and exact unsigned
sample ticks. Duplicate keys, non-finite numbers and Boolean-as-integer modes are
rejected. No inferred clock equivalence or time-unit conversion.

## Independent requirements and binding map

`opentools.property-obligations.v1` contains `scope_ref`, `scope`, `claim`,
`claim_kind`, `owner_ref`, `basis_ref`, `inventory_complete`, `property_ref` and
one to eight `obligations`. Scope records `design_ref`, `configuration_ref`,
`window_ref`, `mode_ref`.

Each obligation has `id`, `requirement_ref`, `owner_ref`, `target_ref`, `clock_ref`,
`edge`, `mode` (0/1), `tick` and `condition_ref`. The roster comes from independent
accepted intent. Unknown substantive references/ticks use `null`; they are not
filled from the report. Identical target/clock/edge/tick slots cannot be duplicated.
The helper supports `claim_kind=observed_activation`; stronger claims stay open.

`opentools.property-bindings.v1` has the same `scope`, `basis_ref`, canonical
`roster_sha256`, expected original `run_ref`, `sources` (filename → SHA256) and
`bindings`. Each entry has `obligation_id`, `checker_ref`, `property_name`,
`activation_cover`, `basis_ref`. Required entries cannot be omitted. The qualified
mode covers are `c_active_normal` and `c_active_risk`; `c_active_any` cannot stand
in for either. Hashes bind supplied content, not completeness or acceptance.

## Saved Verilator evidence

`opentools.verilator-activation.v1` records the original scope/run, inputs, actual
checker/observer hierarchy and target, resolved scalar pin/clock mappings, source
locations, native covers, drive/sample rows, runtime enables and assertion actions.
It identifies the method as `bounded_simulation`, never unbounded proof.

Tested: Verilator 5.020 on Linux with GCC 13.3; saved data read on Windows/Linux.
One target level under `top`; one independent bound `obligation_observer`; zero
or one bound `activation_checker`; six settled Boolean drive inputs. The property
family is a positive-edge same-cycle `event_req |-> condition_ok`, disabled by
`reset || extra_disable`. Actual XML source predicates and the five user covers
are checked over all 32 Boolean role combinations. This does not parse arbitrary
SVA, establish property adequacy or decode native opaque C++ gates.

The reader follows checker/observer ports through the target's top-level instance,
including scalar constants and supported Boolean reset expressions. Clock inputs
must resolve directly to the observed always-on or functional clock. Each drive
record carries the native runtime `assertOn()` value. Expected clock edges, sample
values, assertion actions and cover counts must agree. Covers are checked
separately from runtime assertion enable; their counters can remain positive
while assertion evaluation is disabled.

The original build/XML command layouts are those in `native_capture.BUILD`/`XML`,
with `--assert` and `--coverage-user`. Required retained files include five inputs
(`top.sv`, `checker.sv`, `composition.vh`, `selection.vh`, `main.cpp`), original
commands/build diagnostics, compiler version, execution record, original ELF
artifact, `model.xml`, `coverage.dat`, runtime stdout/stderr and window end marker.
Missing, truncated or inconsistent artifacts remain unresolved. An empty cover
population is not silently interpreted as zero hits. The binary is hashed, never run.

Capture context supplies run/scope, family-review basis and dependency completeness.
These are declarations with references, not authenticated measurements or automatic
dependency closure. Critical files are rehashed/reparsed on review. Paths are
relative POSIX paths below the evidence root; links and escaping paths are unsupported.
XML external entities and imported instructions are not executed.

## Interpretation

Review checks the roster against the actual target, required clock/edge, selected
event/mode, checker sample, runtime enable and guard. A corrected active checker
can expose a condition failure; that is retained alongside activation. Foreign
or changed run/source evidence is quarantined before attributing a failure.

Unselected observer events/native failures stay visible. They do not automatically
expand the caller's roster; an agreeing shortened roster/map still needs AI review
against original intent. A no-failure observation is not a formal proof. These
records do not certify asynchronous sampling, physical clocks/reset, broader
protocol/power behavior, checker sufficiency or release/proof acceptance.

Mechanism reference: upstream [Verilator coverage guidance](https://verilator.org/guide/latest/simulating.html#coverage-analysis).
The measured 5.020 artifacts define this profile's support; the link does not
qualify newer releases or other native formats.
