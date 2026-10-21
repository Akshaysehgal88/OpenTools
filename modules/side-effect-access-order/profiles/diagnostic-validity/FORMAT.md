# Diagnostic records

UTF-8 JSON with explicit booleans/null, unsigned values, unique keys/event IDs and
strictly increasing sequence numbers. No boolean integers or nonfinite values.
[Examples](examples/create_example.py) produce reference fixtures; native records
retain their distinct evidence kind.

All inputs have `format`, exact `scope` (`project`, `configuration`, `recovery_ref`,
`mode`), `basis_ref`, boolean `inputs_complete`. Journal and policy contain
`spec_sha256`; policy binds `journal_sha256`. Spec/policy `source_revision_ref`
must match. Digests use sorted keys, compact UTF-8 JSON and no nonfinite values.
Foreign bindings supply no observation interpretation. Hashes identify supplied
content, not source meaning or owner acceptance.

## Spec: `opentools.diagnostic.spec.v1`

`status` has `id`, width1..4096, `latch_kind` (`sticky-cause/unknown`), `onread`
(`clear/none/unknown`), `reset_effect` (`clear/retain/unknown`), `evidence_ref`.
`record` has `id`, `reset_effect` and `evidence_ref`. This profile assumes ordinary
quiescent sampled cause latching and full-bank clear effects. Other semantics
need native/company methods; an unsupported name cannot qualify them.

## Journal: `opentools.diagnostic.journal.v1`

`source_kind`, `method_ref`, `coverage_scope_ref` identify the supplied evidence.
Boolean/null `history_complete` covers access/erasure/capture history;
`source_latching_complete` covers the selected bounded source prefix for negative
claims. These are caller declarations, not independent completeness certificates.
`initial_status`, `initial_epoch` are unsigned/null; `initial_available` is
boolean/null. `initial_record` contains `value`, `valid`, `epoch` (unsigned/null,
boolean/null, unsigned/null). An initially valid record has no invented provenance.

Events have `id`, `seq`, `kind`, `evidence_ref`:

- `availability`: boolean/null `value` for the selected access path.
- `read`: `actor_ref`, `source` (`status/record`), `data`, `epoch` (unsigned/null),
  boolean/null `accepted`, `error`, `available`, `hardware_quiet`. Record reads
  also have boolean/null `record_valid`.
- `save`: `actor_ref`, boolean/null `accepted`, `source_read_ref` string/null and
  `record` (`value`, `valid`, `epoch`). The receipt must match a usable prior read.
- `recovery`: boolean/null `observed`; optional unsigned/null `epoch_after`.
- `record_external`: `record` without an invented earlier capture receipt.

Epochs identify status evidence separated by known clears. An accepted clear-on-read
response belongs to the preceding epoch; the bank then enters a new clean epoch.
Recovery advances status epoch only when its declared effect clears the bank.
Saved captures keep their source read's epoch while retention remains applicable.
Hardware epoch tags may be null when complete ordered history derives the basis;
known conflicting tags are rejected. Counter overflow or unknown erasure effects
remain unqualified. The model does not infer real incident tags from counters alone.

The native normalizer keeps injection commands as separate oracle evidence rather
than admitting them as consumer reads. A wider AI review can cite that source
separately; this helper answers the selected artifact's applicability question.

## Policy: `opentools.diagnostic.policy.v1`

Independent `requirements_ref`, one-bit `fault_mask` within status width,
`target_epoch`, `required_through_seq`, `consumer_ref`, nonempty unique
`allowed_capture_actors`, `selected_read_ref`, `claim` (`present/absent/undetermined`).
Do not choose the cause/window from favorable observed values. A negative answer
covers only the selected clean epoch's observed prefix through its source read.
It requires adequate capture/latching coverage and the required sequence boundary;
it does not establish absence before/after that scope or across other fault paths.

## Report

`selected_observation` preserves raw value and source-read provenance.
`selected_cause_bit_set` describes qualified returned bits, including a stale valid
record; it does not alone establish current-epoch occurrence. `evidence_answer` is
`present`, `absent_in_observed_prefix` or `unknown`. Negative support retains
`negative_through_seq`. Erasures, findings and gaps remain separate.

Unknown evidence cannot support a present/absent claim. An explicit undetermined
claim preserves uncertainty without inventing a contradictory fault conclusion.
Status: `within_observed_evidence` (exit0), `review_required` (exit1), otherwise
`incomplete` (exit2). Invalid input/I/O exits3. Known findings retain accompanying
gaps. `--output` creates a new file.
