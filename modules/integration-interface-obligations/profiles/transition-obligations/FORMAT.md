# Transition records

UTF-8 JSON. Flags are booleans/null; values and IDs are unsigned integers/null.
Duplicate keys/identities, boolean integers, nonfinite values and out-of-order
events are invalid. [create_example.py](examples/create_example.py) produces fixtures.

All records contain `format`, exact `scope` (`project`, `configuration`, `mode`,
`protocol_ref`, `transaction_ref`, `epoch_ref`), `basis_ref`, boolean `inputs_complete`.
The protocol and basis identify consumed source rules and the reviewed mapping.
This profile does not infer semantics from an industry protocol name.

## Model: `opentools.transition.model.v1`

`semantics` is `accepted-exclusive-handoff`. Nonempty `resource_ref`,
`grantor_ref`, `requestor_ref`, `request_class_ref`, `grant_class_ref`,
`completion_class_ref`, `protocol_contract_ref`, unsigned 64-bit `transaction_id`
and `epoch` define one ownership frontier. Acceptance of that token permits exclusive
consumer use; other protocol frontiers require separate qualification.

`participants`: 1–64 unique `id`, `role_ref`, `evidence_ref`.
`initial_holders`: unique old-holder participant IDs, excluding the requestor.
`obligations`: 1–64 unique `id`, `kind` (`release/data`), `source_ref`,
`message_class_ref`, `evidence_ref`. A source/class/kind tuple identifies one
obligation. Release sources must cover the independent old-holder roster.

## Journal: `opentools.transition.journal.v1`

`model_sha256`, `window_ref`, boolean/null `epoch_isolated`, `window_closed`,
`events_complete`, and `initial_holders` (participant-ID to boolean/null actual
permission) bind one observed epoch/window. Completeness and source roles need review.

`events` have unique `event_ref`, increasing unsigned `seq`, nondecreasing
unsigned `time_tick`, `source_ref`, `message_class_ref`, `resource_ref`,
`message_id`, `message_epoch`, `state_label`, `evidence_ref`, and:

- `kind`: `initial/idle/request/data/release/grant/new_read/new_write/old_read/finish`.
- Explicit boolean/null `accepted`, `offered`, `requestor_permission`,
  `data_valid`, `active`, `read_valid`, `write_committed`.
- `holders` and `reported_pending`: maps from every selected old holder to
  boolean/null observed permission and outstanding-release bit.
- Explicit `reported_pending_count`, `data_value`, `read_value`. Counts/IDs/epochs
  fit unsigned 64 bits; scalar values fit 4096 bits; use null for unknowns.

Current transaction/resource/epoch and source/class must match before receipt
credit. A release acknowledgement also needs observed released permission. A
data receipt needs observed availability; unknown bytes stay a gap without turning
a known receipt into an absent one. Duplicate source credit never clears another
obligation. Foreign messages are retained as ignored, not renamed to current work.

Only accepted grants cross the permission frontier. Stable labels and offered
tokens are informational. Actual permission overlap is checked independently;
permission revocation before a later acknowledgement is allowed but does not
discharge it. Pending counters/masks are compared with the distinct-source ledger.
Counts describe release obligations, not combined data/message traffic.

The owned producer emits one selected message/effect per step. Broader native
normalization must preserve simultaneous events and separate asynchronous grant
acceptance rather than hiding it behind another operation class.

## Policy: `opentools.transition.policy.v1`

`model_sha256`, `journal_sha256`, exact `window_ref` bind inputs. Independently
supply the model's contract fields and typed transaction ID/epoch, plus:

- `required_participants`: unique `id`, `role_ref`, `evidence_ref`.
- `required_initial_holders`: unique old-holder IDs.
- `required_obligations`: unique typed obligations in the same shape as the model.
- Boolean `check_returned_data`, explicit unsigned/null `expected_data`.
- `required_events`: unique `event_ref`, `kind`
  (`request/grant/new_read/new_write/finish`), `evidence_ref`. These milestones
  must be observed accepted. Keep their identities independent of observed exports.
- `start_seq`, `end_seq`: up to 4097 consecutive observations. Missing samples or
  observations outside the window are gaps.

Known pending prerequisites at an accepted grant/finish are findings. Uncertain
receipt identity, acceptance, rights or incomplete coverage leaves uncertain
obligations and a gap; it cannot prove premature completion. Actual incompatible
permissions or other known findings retain accompanying gaps. A favorable final
ledger does not erase earlier acceptance or consumer violations.

## Report

The report retains grants with remaining/unknown obligations, actual reads,
ignored foreign messages, duplicate receipts and the event ledger. Status is
`review_required` with findings, otherwise `incomplete` with gaps, otherwise
`within_observed_contract`. Stale/foreign scope or binding supplies no ledger.

Canonical SHA-256 uses sorted keys, compact separators, UTF-8 and no nonfinite values
(`transition_core.digest`). Hashes bind supplied content, not source roles,
complete discovery, native applicability or owner approval. The profile cannot
certify arbitrary protocol translators or establish unbounded completion/liveness.
