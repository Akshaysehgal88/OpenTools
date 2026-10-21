# Reset review records

UTF-8 JSON with unsigned integer state samples. Duplicate keys, nonfinite values,
boolean integers and duplicate state/rule identities are invalid. See
[create_example.py](examples/create_example.py) for complete fixtures.

All records have `format`, exact `scope` (`project`, `configuration`, `mode`,
`reset_event_ref`), `basis_ref` and boolean `inputs_complete`. The basis defines
state identity, sampling boundaries and the consumed reset contract. Completeness
is a caller declaration for the selected scope, not a whole-design attestation.

## Inventory: `opentools.reset.inventory.v1`

Nonempty `states` entries: unique `id`, `width` (1–64), `owner_ref` and
`reset_domain_ref` (text or null), scalar `reset_value` (unsigned or null),
`evidence_ref`. Unknown owners/domains are gaps. Retain real reset values rather
than substituting zero for missing evidence.

## Journal: `opentools.reset.journal.v1`

`inventory_sha256` binds the exact inventory. `phases` are unique and ordered:
`before`, `held`, `released`, `post`. Missing phases remain gaps. Every selected
state needs a value in each phase; null is unknown.

Each phase has `phase`, `values` (state-ID to scalar/null), `reset_active`
(reset-domain to boolean/null), `prerequisites` (named boolean/null),
`hardware_quiet` (boolean/null), `evidence_ref`.

`before` and `held` delimit the clearing/preservation check. Quiescence is required
to attribute preservation across that interval. `released` samples the reset
boundary before new work changes state. `post` is an explicitly identified bounded
observation window, not necessarily the first cycle or all subsequent behavior.
Record actual asserted resets and responses; do not derive them from intent.
Extra native counters/provenance may be retained but are not interpreted as proof.

## Policy: `opentools.reset.policy.v1`

`inventory_sha256` and `journal_sha256` bind supplied content. Exact scope and basis
must match. Required lists:

- `state_expectations`: one per selected state, `state_ref`, `effect`
  (`clear/preserve/unconstrained` or null), `required_reset` (boolean/null),
  `evidence_ref`. Clear compares held state with its native reset value; preserve
  compares before/held. Unconstrained needs an explicit reviewed rationale.
- `release_requires`: unique `id`, `evidence_ref`. The released sample must
  establish each prerequisite. False is a finding; unknown is a gap.
- `continuity`: unique producer/context pairs, `producer_pending_ref`,
  `consumer_context_ref`, `allow_replay` (boolean/null), explicit
  `producer_identity_ref`/`consumer_identity_ref` (both IDs or both null),
  `evidence_ref`. Presence flags are one bit. If both survive, supplied equal-width
  identities are compared. Surviving producer work with cleared consumer context
  is a risk unless replay is explicitly permitted. Replay authority does not
  establish readiness; supply its release prerequisites and post expectations.
- `post_expectations`: unique `state_ref`, unsigned `equals`, `evidence_ref`.
  Compare actual post-release effects, such as an orphan flag expected to remain
  zero. Source this intent independently of the observed outcome.

The bounded pending-work profile requires release, continuity and post intent;
empty lists remain unreviewed gaps. AI/native workflows can review other reset
activities outside this helper profile.

`python reset_review.py digest record.json` prints canonical SHA-256 (sorted keys,
compact separators, UTF-8, nonfinite values disabled). Hashes do not establish
correct state roles, source authenticity, replay permission or approval.

## Report

State-by-owner rows preserve all four phases. Findings, gaps and declared replay
permission remain separate. Status is `review_required` with findings, otherwise
`incomplete` with gaps, otherwise `within_sampled_reset_contract`. A continuity
risk is not proof of an actual stale completion; cite the separate native effect
when observed. A valid bounded journal is not exhaustive reset verification.
