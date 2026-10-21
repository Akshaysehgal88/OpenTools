# Crossing premise journal

The population input is an existing `opentools.waiver-snapshot.v1` from
[the module format](../../FORMAT.md). Supply reviewed native normalization or an
explicitly synthetic population; this profile does not create structural findings.

The selected finding adds a `crossing` mapping with nonempty `source`,
`destination`, `source_clock`, `destination_clock`, `source_reset`,
`destination_reset`, `evidence_ref`, and unsigned `width` (1–64). These are explicit
roles, not identities inferred from prose. Other population/capture content is
preserved.

## `opentools.crossing-premise-journal.v1`

- `population_sha256`: existing waiver-core canonical digest of the exact input
  population, including the selected finding and run identity.
- `run_id`, `scope`, `configuration_ref`, `identity_basis`: exact population values.
- `waiver_id`, `finding_id`: exact selected finding identity.
- `crossing`: exactly the finding's reviewed crossing mapping.
- `inputs_complete`: explicit boolean for the selected event coverage.
- `sampling_basis`: `settled-events-closed-window-v1`.
- `events`: nonempty ordered settled observations.

Each event has unsigned increasing `seq`, nondecreasing unsigned `time_tick`,
`evidence_ref`, `source_value` (width-bounded unsigned integer/null), and the
boolean/null fields `window`, `source_reset`, `destination_active`, `source_ready`,
`destination_sample`. Extra native observations may be retained separately.

The data-stability interval includes entry/exit transitions: a value change when
either adjacent known window state is active is a contrary observation. Record
closure before a later permitted update. Unknown boundaries do not establish that
a change happened inside the interval. Supply inactive prefix/suffix, a complete
closed window and an actual destination observation. Capture **all relevant source
updates**, not only destination samples. Missing coverage, samples or values are
gaps; a declared complete journal is not an automatic continuous-waveform proof.

Readiness means source reset inactive and source ready whenever the selected
destination is active. Native source evidence must establish what `ready` means.
This is a supplied exception premise, not a universal CDC/RDC protocol rule.

## Captured snapshot

The original snapshot and structural population are copied. New flat configuration
keys are `crossing:<waiver_id>:<finding_id>:stable_in_window` and
`crossing:<waiver_id>:<finding_id>:source_ready_before_destination`. Values are
boolean or null. Existing keys cannot be overwritten. The configuration basis
retains its original basis and appends `+crossing-journal-v1`.

`crossing_premise_capture` retains input hashes, role mapping, witnesses and gaps.
Known contrary observations remain false even with incomplete coverage. Without
a contrary observation, gaps leave values unknown. Gaps mark population/selected
waiver completeness false, so the normal comparator cannot report unchanged.
This conservative result does not claim the structural source population changed.

Use the existing waiver policy with the generated exact keys and the source-backed
expected values. Compare against a compatible baseline populated through this
same profile. Preserve original native reports and review known findings even when
the final comparator status is incomplete. Hashes bind supplied content; they do
not establish correct roles, coverage, approval or native CDC/RDC signoff.
