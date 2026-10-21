# Event route records

UTF-8 JSON with booleans or explicit null for observations. Duplicate keys,
integer booleans, duplicate obligations and out-of-order samples are invalid.
Use [create_example.py](examples/create_example.py) for complete fixtures.

All records contain `format`, exact `scope` (`project`, `configuration`, `mode`,
`event_ref`), `basis_ref` and boolean `inputs_complete`. The basis identifies
stage roles, sampling and the selected source/route contract. Completeness is
declared for this selected event/window, not the whole design.

## Topology: `opentools.event.topology.v1`

`source`: `id`, `owner_ref`, `persistence` (`held-until-clear/pulse/unknown`),
`evidence_ref`. Unknown persistence remains a gap.

`routes` has distinct `interrupt` and `wake` mappings, each with `id`,
`consumer_ref`, `profile_ref`, `evidence_ref`. Roles remain distinct even when a
design shares physical logic. The helper does not derive clock/gateway semantics
from these strings; inspect native source and actual mode routing.

## Journal: `opentools.event.journal.v1`

`topology_sha256` binds the full topology. `window_ref` identifies the bounded
observation interval; `window_closed` and `event_isolated` are booleans/null.
An open/unknown window or unestablished isolation prevents a passing result.

`samples` have increasing unsigned `seq`, nondecreasing unsigned `time_tick`,
`evidence_ref`, and exact boolean/null mappings:

- `stages`: `asserted`, `interrupt_retained`, `interrupt_delivered`, `serviced`,
  `source_cleared`, `wake_retained`, `wake_requested`.
- `controls`: `functional_clock`, `aon_clock`, `power_available`,
  `interrupt_enable`, `route_selected`, `wake_enable`, `sleep_window`.
- Separate state fields: `source_status`, `interrupt_pending_state`,
  `wake_pending_state`.

Stage fields are **occurrence markers**, not levels that remain true across
samples. For example, wake retention occurs once when its latch captures; its
pending state can stay high afterwards. Native counters may produce occurrence
deltas when their reset/width/coverage basis is established. Extra raw native
counters may be retained; the core does not certify their normalization.

Clock controls identify the actual applicable sampling edge/availability evidence,
not a software clock-enable command. Preserve masks/routes and power state from
the same observation. In the owned example, actual edge-counter deltas establish
the two clock markers.

The first sample must establish a clean prefix: no selected stage or pending/source
state already active. More than one assertion requires a broader attribution
method and remains incomplete here. Missing source/status observations cannot be
filled from a different event or reset assumption.

## Policy: `opentools.event.policy.v1`

`topology_sha256`, `journal_sha256` and exact `window_ref` bind the inspected inputs.

- `required_stages`: unique `stage`, `evidence_ref`; nonempty. These are the
  caller's obligations within the selected window, not inferred from outcomes.
- `orders`: unique `before`/`after` stage pairs with `evidence_ref`. Same or earlier
  settled observations satisfy an order; this does not prove subcycle timing.
- `stage_prerequisites`: unique `stage`, nonempty unique `controls`,
  `evidence_ref`. Required controls must be true when that stage occurs.

Empty order/availability lists remain unreviewed gaps. Use native/company methods
for event routes outside this bounded profile. Do not impose a wake obligation
where the actual sleep-entry policy aborts or falls through instead.

## Interpretation

A complete, closed, isolated window with no required occurrence supports
`required_stage_not_observed_in_window`. Partial/unknown coverage remains a gap.
An observed ordering failure retains its finding even when unrelated gaps coexist.
Stage facts, unknowns and original references remain in the report.

Status is `review_required` with findings, otherwise `incomplete` with gaps,
otherwise `within_observed_event_contract`. A favorable report does not certify
stage roles, native controller correctness, service authority or physical delivery.

`python event_review.py digest record.json` prints canonical SHA-256 (sorted keys,
compact separators, UTF-8, nonfinite values disabled). Hashes bind supplied content;
they do not establish meaning, source authenticity or approval.
