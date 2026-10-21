# Ordering records

UTF-8 JSON. Flags are booleans/null; sentinel values are unsigned 0/1 or explicit
null. Duplicate keys/identities, boolean integers and nonfinite values are invalid.
[create_example.py](examples/create_example.py) produces complete records.

All records contain `format`, exact `scope` (`project`, `configuration`,
`boundary_ref`, `mode`), `basis_ref`, boolean `inputs_complete`. The basis names
consumed source/attribute/observation meaning, not an attestation of truth.

## Contract: `opentools.ordering.contract.v1`

Nonempty `model_ref`, `model_revision_ref`, `model_kind`, `producer_ref`,
`observer_ref`, `producer_contract_ref`, `observer_contract_ref`,
`attribute_basis_ref`, `visibility_basis_ref`, `instruction_scope_ref` identify
the selected contract. This helper qualifies only model
`opentools.owned-buffered-publication.v1`, kind `owned-implementation`.
`sentinel_bits` is integer 1. `observer_ordered` is boolean/null; the owned
observer polls publication then conditionally reads payload without speculation.

`attributes` has exact `payload` and `publication` objects with `path_ref`,
`cacheability_ref`, `shareability_ref`, `mapping_revision_ref`, `evidence_ref`.
Unknown attribute refs may be null and remain gaps. The native recipe's model
revision binds both owned RTL and the independent enumerator source hashes.

`program` is an ordered list of unique `id`, `kind`, `actor_ref`, `evidence_ref`:

- `store`: `object_ref`, `domain` (`I/O/R/W` or null), unsigned `value`.
- `ordering_control`: unique known-domain lists/null `predecessors`, `successors`.

The qualified family issues payload value1 through W, an optional control and
publication value1 through W or O; both start at0. Controls before payload or
after publication do not retroactively order them. Extra operations/other families
remain unqualified. These domain labels describe the owned path, not executed
ISA instructions or a hardware mapping decoder.

## Evidence: `opentools.ordering.evidence.v1`

`contract_sha256` binds all selected context. `model_result` is an object or null:

- `kind`: `owned-three-event-enumeration.v1`; `model_ref`, `model_revision_ref`,
  `program_sha256`, boolean/null `complete`, `evidence_ref`.
- `outcomes`: unique objects with explicit `flag` and `payload`.
- `witnesses`: unique `order` permutations of `payload-commit`,
  `publication-commit`, `observe`, plus `flag`, `payload`, `evidence_ref`.

Payload is null when flag0 means the observer did not read it; flag1 with null
payload means an unknown response. Outcomes must have supporting legal witnesses.
A matching control requires payload commit before publication commit. The checker
validates this tiny owned ordering graph and the reported outcomes; it is not an
ISA memory-model implementation. A complete label needs every legal order. A
partial legal stale witness can establish permission, but missing orders cannot
establish exclusion.

`observations` is a list, possibly empty, with unique `run_ref`, `kind`,
`model_revision_ref`, `program_sha256`, `evidence_ref`, `flag`, `payload`, and
boolean/null `payload_read_valid`, `all_steps_enabled`. Supported kinds are
`owned-rtl-simulation` and `owned-reference-fixture`, preserved distinctly.
Hardware/other methods need separate qualification. A blocked propagation attempt
can leave `all_steps_enabled=false`; that is a partial linearization, not an
ordering violation or proof of liveness. A captured stale read is retained even
when memory becomes correct later.

`program_sha256` is the canonical digest of `program`, `attributes`,
`producer_ref`, `observer_ref`, `producer_contract_ref`, `observer_contract_ref`.
Each result/observation retains that exact program/path basis. RAM evidence cannot
silently acquire I/O applicability through matching values alone.

## Claim: `opentools.ordering.claim.v1`

`contract_sha256`, `evidence_sha256`, the selected `model_ref`, `model_revision_ref`,
`producer_ref`, `observer_ref`, `producer_contract_ref`, `observer_contract_ref`
bind the requested claim independently. `property` is
`publication_implies_payload` or `atomicity`; `strength` is
`selected_model/isa/hardware`. Only the publication property at selected-model
strength is qualified. ISA, hardware-wide and atomicity claims remain gaps.

`payload_event_ref`, `publication_event_ref`, explicit string/null
`control_event_ref`, exact `required_domains` (`payload`, `publication`), and
`required_attributes` independently specify the intended boundary. Each required
attribute object has nonempty `path_ref`, `cacheability_ref`, `shareability_ref`,
`mapping_revision_ref`. Do not derive the intended path from the supplied outcome.

## Report

The report separates `control_covers_boundary`, `model_permits_stale`
(true/false/null), `model_witness`, actual `observations`, `observed_stale_runs`,
findings and gaps. Coverage metadata alone does not certify a result; the explicit
model output must be supplied. `model_permits_stale=false` requires complete,
matching enumeration. A favorable selected observation cannot override a legal
stale model witness. Known findings retain unrelated gaps.

Status is `review_required` with findings, otherwise `incomplete` with gaps,
otherwise `within_selected_owned_model`. Foreign/stale contract/scope bindings
supply no outcome interpretation. Canonical SHA-256 uses sorted keys, compact
separators, UTF-8 and no nonfinite values (`ordering_core.digest`). Hashes establish
content identity, not source meaning, physical applicability or owner acceptance.
