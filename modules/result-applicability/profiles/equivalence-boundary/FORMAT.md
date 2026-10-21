# Record formats

All records are JSON. Unknown references/requirements use `null`; they are gaps,
not permission to copy observed values into the request. Duplicate JSON keys,
extra schema fields and ambiguous modes are invalid.

## Capture context

`opentools.equivalence-capture-context.v1` contains `run_ref`, `manifest_ref`,
`eco_ref`, `mode_input`, `scope_basis_ref`, `dependencies_complete` and
`dependency_basis_ref`. `mode_input` names an actual scalar common miter input
(for example `in_functional_mode`), chosen explicitly by the caller.
Scope/dependency references are declarations, not native measurements.
The [template](capture-context.template.json) requires completion before import.

The resulting parent `opentools.result-snapshot.v1` preserves execution and native
result separately. Fact entries have `value` and `evidence_ref`. Native fields:

| Field | Recorded fact |
| --- | --- |
| `designs` | gold/gate source hashes, resolved parameters and netlist digests |
| `mapping` | explicit common-input pairs and exposed native output comparators |
| `model_boundary` | defined two-state combinational class; state/memory/blackbox/reset boundary |
| `engine_profile` | exact version/profile and complete combinational proof kind |
| `partition` | single whole-miter aggregate, all compared outputs and no excluded points |
| `mode_constraint` | selected input and native allowed values |

Provenance retains context, workdir, critical-file hashes and native witness.
Every review rehashes and recaptures these files. Hashes establish correspondence,
not authenticity of arbitrary artifacts or approval references.

## Independent intent

`opentools.equivalence-intent.v1` contains:

- `claim_id`, `claim`, `scope_ref`, `eco_ref`, `eco_intent_ref`, `owner_ref`, `run_ref`.
- `required_fields`: exactly `designs`, `mapping`, `model_boundary`, `engine_profile`
  and `partition`, each with independently sourced `value` and `evidence_ref`.
- `mode_input`, sorted unique `required_modes` (0, 1 or both), `mode_basis_ref`.
- `mapping_review`: `status` (`approved`, `proposed`, `unknown`), `reviewer_ref`,
  `basis_ref`. Existing authority must supply approval; the helper cannot verify it.

Use [intent.template.json](intent.template.json). The helper checks internal
correspondence; the assistant must check intent against original source evidence.
Agreeing records can still omit a real requirement.

## Report

`opentools.equivalence-review.v1` retains the parent comparison, native observation,
findings, gaps and input fingerprints. Status is
`native_result_supports_declared_equivalence_scope`, `review_required` or `incomplete`.
An excluded required mode is a finding even for a native PASS. A native FAIL whose
witness is outside requested modes leaves their equivalence unresolved.
