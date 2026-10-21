# Selected configuration records

The comparator consumes two parent `opentools.record-layout.v1` exports and one
`opentools.configuration.contract.v1`. It reuses the parent's shape validation
and source-context identity mechanism. No layout comparison or wire-enum inference
is performed. JSON rejects duplicate keys, boolean integers and nonfinite values.

## Opt-in native facts

The parent hardware capture API accepts `observed_parameters=[...]` and CLI
`--parameter-fact NAME`. Software accepts `constants=[...]` and `--constant NAME`.
Select one to five unique plain identifiers. Defaults remain unchanged otherwise.
Hardware facts are actual known integral port/local parameter values; software
facts are compiler-evaluated integral constants. Values must fit signed64.

Opt-in `provenance` adds `fact_kind=native`, `fact_phase=elaboration/compile`,
`fact_selection`, and either `selected_integral_parameters`/`parameter_fact_refs`
or `selected_constants`/`constant_fact_refs`. Values and references use exact
selected names. Native source/context identity includes the selection. C constants
remain separate from field encoding vocabulary. Textual `actual_port_parameters`
and requested overrides are not fallback observations.

Native qualification remains pyslang12.0.0 and GCC13.3.0 x86_64-linux-gnu LP64.
Capture retains commands/diagnostics and caller-declared dependency inventory;
it does not discover closure. The C layout profile still requires scalar fields.
`fields_complete` concerns struct inventory, not completeness of all configuration
parameters. Reference examples explicitly use `fact_kind=reference-fixture`.

## Contract

`scope` has exact `project`, `configuration_ref`, `family_ref`, `mode`. Nonempty
`basis_ref`, `source_revision_ref`, `requirements_ref` identify independent intent;
boolean `inputs_complete` declares its scope. `views` has exact hardware/software
bindings: canonical `export_sha256`, `source_ref`, `interface_ref`,
`configuration_ref`, `frontend_ref`, `fact_phase`, `fact_kind`. Native method/phase
limits are checked separately from caller labels. Source inventories and capture
selection context must match their recorded source identity.

`parameters` contains one to five distinct roles with `id`, `evidence_ref`,
canonical `unit` string/null, independent signed64/null `required_value` and
hardware/software bindings. Each binding has exact `fact_ref`, `unit` string/null,
`rule_ref` string/null. A source fact cannot silently represent two distinct roles.
Unknown intent/units remain gaps even when captures agree.

`unit_rules` maps IDs to exact `kind`, `source_unit`, `target_unit`, `numerator`,
`denominator`, `evidence_ref`. Kinds: `identity` (same unit,1/1), `exact-scale`
(positive signed64 numerator/denominator), `unknown` (null scale). Source/target
units must match the selected binding and canonical role. Conversion must divide
exactly; no rounding/expression evaluation occurs. Out-of-profile canonical range
remains unqualified. Rule evidence is supplied basis, not automatic owner approval.

Canonical digests use sorted keys, compact UTF-8 JSON and no nonfinite values.
They bind parsed content, not file whitespace or semantic truth. A foreign/stale
view is not interpreted; a known mismatch in another bound view remains visible.

## Report

`views` preserves binding/method/phase/input scope. Each parameter records raw and
canonical values, units, source references and independent requirement. Findings
distinguish required-value disagreement, peer disagreement and nonintegral
conversion. Gaps preserve unavailable facts, missing rules/intent or applicability.

Status/exit: `within_selected_contract`/0, `review_required`/1, `incomplete`/2.
Known findings retain concurrent gaps. Invalid input/I/O exits3. `--output` creates
a new file. Agreement qualifies the selected configuration contract only.
