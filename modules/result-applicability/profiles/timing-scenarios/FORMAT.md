# Scenario profile records

`opentools.sta-scenario-plan.v1` identifies scope, design, configuration,
requirements source and owner. `obligations` is the independent roster, not a
list inferred from the selected run inventory. Each entry has:

- `id`, `applicability` (`required`, `not_applicable`, or null).
- `reason`, `basis_ref`, and `exclusion_ref` for a nonapplicable combination.
- `required_fields`: values with their own `evidence_ref`, using the parent
  [result-request field format](../../FORMAT.md).

Required field names are `scope.identity`, `implementation.source_sha256`,
`library.source_sha256`, `physical_library.source_sha256`, `library.pvt`,
`scenario.mode`, `scenario.corner`, `power.state`, `native.cases`,
`clock.definition`, `rc.view`, `profile`. Additional requested fields remain
unresolved when the reader cannot supply them. Missing foundation fields cannot
be dropped to obtain acceptance. Unknown values/references use null.

`library.pvt` contains library name and normalized min/max process, voltage_V and
temperature_C. The reader retains raw native floats and rounds these model values
to six decimal places for representation consistency; this is not an engineering
tolerance. Clock period and PVT values use JSON floating-point values; cases use
integer 0/1 or null. Native types and exact value identities are preserved by the
parent comparator. Mode/power roles are supplied source declarations.

`opentools.sta-scenario-corpus.v1` contains `runs`, a list of distinct actual
archive directory/run references. Repeated analysis with a new actual run ID may
be retained, but it still covers only its matching obligation. An alias cannot
create additional evidence. The reviewer does not generate new combinations.

`opentools.sta-scenario-context.v1` records original run/scope/design/configuration/
scenario identities, source-backed mode/corner/power roles and closed native
setup. The collector writes the original plan/corpora before native execution,
and freezes each run's context, sources, invocation and reference table. The
execution record binds their original bytes plus actual tool and native artifacts.
Review reads data only and does not execute archived Tcl.

The native JSON-lines export retains library default and **selected min/max**
operating-condition values, their object correspondence, cases, clock sources
and register associations, scalar clock/data/output pin census, selected path
endpoints/slack and completion boundary. The original stdout separately retains
the bounded native parasitic-annotation report. Missing/changed artifacts,
producer scripts, original contexts, unsupported records or versions reject
intake. Byte identity does not authenticate authority, consumption or freshness.

The native snapshot uses `opentools.result-snapshot.v1`. Its pass/fail classifies
only the selected maximum-setup representative; it is not a complete native STA
verdict. Required-outcome `any_observed` allows an applicable failed observation
to account for scenario evidence while preserving the timing failure in the
scenario report. Unknown native scope remains incomplete.

`opentools.sta-scenario-review.v1` keeps independent obligations, per-candidate
parent audits, admitted/quarantined native outcomes, covered counts, findings,
gaps, source/owner references and recheck triggers. Nonapplicability requires an
identified combination and an explicit source decision. The helper checks record
structure/correspondence; the AI/engineer must inspect that actual decision source.
The example references are owned fixture premises, not production approvals.
