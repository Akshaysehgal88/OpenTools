# Access records

UTF-8 JSON; integers use byte addresses and unsigned register values. Duplicate
keys, nonfinite numbers, boolean integers and overlapping fields are invalid.
See [create_example.py](examples/create_example.py) for a complete fixture.

All records contain `format`, `scope`, `basis_ref` and boolean `inputs_complete`.
Scope has exactly `project`, `configuration`, `mode`, `address_space_ref`. The
basis identifies reviewed sampling, address/byte-lane and semantic conventions.
Exact scope/basis mismatch prevents comparison. Completeness covers selected
artifacts, accesses and intent, not the entire device.

## Specification: `opentools.access.spec.v1`

`registers`: unique `id`, byte `address`, `width` (8/16/32/64), `access_width`
equal to width, `evidence_ref`, nonempty `fields`. Selected register spans cannot
overlap. Each field supplies `name`, `lsb`, `width`, `sw` (`r/w/rw` or null),
`onread` (`none/clear/unsupported` or null), `onwrite`
(`none/assign/one_clear/unsupported` or null), unsigned field `reset` or null,
and `evidence_ref`. Reset is retained context; the helper does not establish
initialization from its presence. Null and unsupported semantics are gaps.

## Trace: `opentools.access.trace.v1`

`spec_sha256` binds the complete specification. `state_basis` must be
`selected-field-storage`: samples come from field storage, not a second software
read that may itself have side effects. `events` are in strictly increasing `seq`
order. Each event supplies:

- `seq`, `register_ref`, `kind` (`read/write`), `operation_ref`, `evidence_ref`.
- `accepted`, `error`, `hardware_quiet`, `reset_inactive`: booleans or null.
- `before`, `after`: register-width storage samples or null.
- `read_data`: read response sample, otherwise null.
- `write_data`, `byte_enable`, `bit_enable`: write operands, otherwise null.

For this profile byte-enable bit 0 controls register bits 7:0; bit 1 controls 15:8,
and so on. `bit_enable` preserves the native bus write mask. A mismatch is a gap;
the helper does not silently convert an unknown lane mapping. Writes of enabled
ones outside selected fields remain unmodeled. Readback compares readable field
bits only. Reserved bits are not assigned invented values.

Only accepted, error-free accesses with established quiescence and inactive reset
are attributed to field effects. Native errors remain findings. Missing samples
and unresolved premises remain gaps. Complete traces also check sampled storage
continuity between consecutive accesses to a selected register.

## Policy: `opentools.access.policy.v1`

`spec_sha256` and `trace_sha256` bind the exact records. Every selected trace event
needs one rule in `events`: `seq`, `allowed_clear_mask`, `required_clear_mask`,
`observation_only`, `after_seq` (prerequisite accepted event IDs), `evidence_ref`.
Masks and observation flag may be null for unresolved intent. Required clear bits
must be allowed. A required bit already zero creates no false acknowledgement
obligation. An observation-only access must not change selected field storage.
Order is observed event order, without a temporal/causality or unseen-flow proof.

Source intent independently from driver arguments, acknowledgement ownership or
reviewed debug policy. Do not derive allowed masks from the resulting trace.

Canonical SHA-256 uses sorted keys, compact separators, UTF-8 and nonfinite JSON
disabled. `python access_review.py digest record.json` prints it. These hashes
bind supplied content; they establish neither authenticity nor semantic roles.

## Report

`opentools.access.report.v1` retains bindings, findings, gaps and per-access cleared
masks. Status is `review_required` if any finding exists, otherwise `incomplete`
if gaps exist, otherwise `within_observed_contract`. No passing status establishes
global driver safety, ownership approval or completeness of source relationships.
