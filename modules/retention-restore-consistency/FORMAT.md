# Restore bundle records

UTF-8 JSON. State values are unsigned integers or explicit null. Use lossless
integer tooling for wide values. Boolean integers, duplicate keys/identities,
nonfinite values and out-of-order samples are invalid. See
[create_example.py](examples/create_example.py) for fixtures.

All records contain `format`, exact `scope` (`project`, `configuration`, `mode`,
`transition_ref`), `basis_ref` and boolean `inputs_complete`. The basis identifies
state roles and the selected sampling/loss/restore method. Completeness is a
declaration for that selected window, not an attestation of the whole design.

## Inventory: `opentools.restore.inventory.v1`

`selection_basis_ref` identifies the native or reviewed selection method.
Nonempty `states` entries have unique `id`, `width` (1–4096), `role_ref`,
`owner_ref`, `power_domain_ref`, `reset_domain_ref`, `selection`
(`retained/lost/unknown`) and `evidence_ref`. Role/owner/domain fields may be null
when unresolved. Unknown definitions or selections remain gaps.

Selection describes what the source/model says survives the selected event. It
does not dictate whether a consumer must preserve, rebuild or invalidate it.
The owned example's selection basis is explicitly logical, not a physical cell export.

## Journal: `opentools.restore.journal.v1`

`inventory_sha256` binds the full inventory. `before_seq` selects the pre-loss
snapshot. `window_ref`, boolean/null `window_closed` and `transition_isolated`
identify one restore window without unrelated state updates. Open or unisolated
coverage cannot pass. Multiple loss cycles require a broader method.

`samples` have increasing unsigned `seq`, nondecreasing unsigned `time_tick`,
`evidence_ref`, `values` (state-ID to width-bounded unsigned integer/null), and exact
boolean/null `controls`: `transition_active`, `power_available`,
`consumer_enabled`, `restore_ready`. The before sample must establish power
available and transition inactive. An actual selected loss and subsequent wake
must be observed; two matching snapshots alone do not test retention.

Each sample includes `reads`, an explicit list that can be empty. Events contain
`read_ref`, `bundle_ref`, `requested`, `response_valid`, `hit`, `error`, `data`,
`evidence_ref`. Flags are booleans/null; data is an unsigned scalar/null. Use one
request and response per selected read identity. Separate request/response samples
are supported when they retain that identity. Unattributed or unobserved responses
remain gaps rather than invented reads or an unbounded liveness verdict.

Record the full relevant post-loss exposure history, including early accesses
before a later ready indication. Preserve actual response data and fault flags;
a before snapshot or software buffer is not a native read response. Extra raw
counters may be retained but their normalization is not certified by the core.

## Policy: `opentools.restore.policy.v1`

`inventory_sha256`, `journal_sha256`, exact `window_ref` bind inspected inputs.
`bundles` has unique `id`, `consumer_ref`, one-bit `eligible_ref`, boolean
`require_ready`, `evidence_ref`, and:

- `members`: independent unique `state_ref`, expected `role_ref`,
  `expected` (`preserve_before/constant/unknown`), `evidence_ref`. Constant
  expectations also supply width-bounded `value`. Preserve reads the exact before
  snapshot; unknown expectations remain gaps. Required members absent from the
  observed inventory cannot silently redefine the bundle.
- `prerequisites`: unique `state_ref`, unsigned `equals`, `evidence_ref`.
  These must hold whenever the powered consumer is enabled and eligible.
- `read`: boolean `required`, boolean/null `expected_hit` and `expected_error`,
  `data_state_ref` (expected member or explicit null), `evidence_ref`, and nonempty
  `prerequisites` with unique `control`, boolean `equals`, `evidence_ref`.
  A declared expected hit needs an expected data member.

Members are checked after wake when ready is declared or when the enabled consumer
is eligible. Temporary loss while validity stays unpublished may therefore be
repaired before exposure. No ready/exposure observation leaves member verification
incomplete. Selected inventory states must be covered by a member, eligibility or
prerequisite obligation. Missing both a member and its requirement still needs
source-based discovery; a matching pair of censuses is not proof of coverage.

Read outcomes are compared only after request attribution. Data is compared with
the member's expected restored value, not whichever value the live field happens
to contain. A required but unobserved read leaves consumer verification incomplete.

## Report and limits

The report preserves expected members/selections, ready/exposure sequences, actual
reads, first mismatch witnesses and gaps. Known mismatches retain review findings
when unrelated evidence is incomplete. Status is `review_required` with findings,
otherwise `incomplete` with gaps, otherwise `within_observed_restore_contract`.

`python restore_review.py digest record.json` prints canonical SHA-256 (sorted
keys, compact separators, UTF-8, nonfinite values disabled). Hashes bind supplied
content; they do not establish state roles, selection truth, completeness or approval.
