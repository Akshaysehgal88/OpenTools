# Quiescence records

UTF-8 JSON. Counts are unsigned integers below 2^64 or explicit null; booleans are
not counts. Duplicate keys/identities, nonfinite values and out-of-order samples
are invalid. See [create_example.py](examples/create_example.py) for fixtures.

All records contain `format`, exact `scope` (`project`, `configuration`, `mode`,
`transition_ref`), `basis_ref` and boolean `inputs_complete`. The basis identifies
owner/count/control roles and sampling. Completeness covers the selected transition
and owner census; it is a caller declaration, not a whole-design attestation.

## Inventory: `opentools.quiescence.inventory.v1`

Nonempty `owners`: unique `id`, `owner_ref`, `unit`, `counting_basis_ref`,
`evidence_ref`. Owner/unit/basis may be null when unresolved. Name the resource
being counted: accepted-but-not-handed-off requests and handed-off-but-not-returned
responses describe different ownership intervals. Do not infer either from a
similarly named idle signal.

## Journal: `opentools.quiescence.journal.v1`

`inventory_sha256` binds the inventory. `window_ref` identifies the bounded
interval. `window_closed` and `transition_isolated` are booleans/null. A passing
result requires a closed isolated shutdown, with an initial sample before request,
acknowledgement, clock stop or power removal.

`samples`: increasing unsigned `seq`, nondecreasing unsigned `time_tick`,
`evidence_ref`, `counts` (owner-ID to unsigned value/null), and exact boolean/null
`controls`: `transition_requested`, `ingress_closed`, `drain_ack`,
`isolation_active`, `clock_available`, `power_available`, `local_idle`.

These are observed states, not equivalent software requests. Clock/power/isolation
meaning must be established by the native method. Extra raw counters can be retained
but their normalization is not certified by the core. Capture relevant owner/control
changes throughout the protected interval, not only the acknowledgement and final
snapshot. Samples do not prove behavior between observations.

## Policy: `opentools.quiescence.policy.v1`

`inventory_sha256`, `journal_sha256`, exact `window_ref` bind the inspected records.

- `required_owners`: nonempty independent roster, each with unique `id`, `unit`,
  `counting_basis_ref`, `evidence_ref`. Unit and basis must match the corresponding
  observed owner. Missing/unknown owners or mismatches remain gaps.
- `checks`: unique `milestone` (`drain_ack/clock_stop/power_remove`), nonempty
  `owners` (IDs from that roster), `evidence_ref`, and nonempty `predicates`.
  Each predicate has unique `control`, boolean `equals`, `evidence_ref`.

All listed checks are required within the selected window. Each checks its owners
for zero while the milestone's protected state is active: acknowledgement true,
clock availability false, or power availability false. This continues after the
first sample; late admission or delayed activity remains visible. Equal counts in
different units are never added or substituted.

Every selected observed owner needs a roster obligation, and every roster owner
must appear in a check. This does not discover an omitted owner absent from both
views. Source review must establish coverage. A local acknowledgement may have a
different scope from system drain; record the actual required owner set rather
than silently broadening or weakening its meaning.

Unknown active state/count/prerequisite remains a gap. A known nonzero count or
false prerequisite retains its finding even with other gaps. A milestone absent
from complete closed coverage requires review; partial/open coverage cannot prove
absence. Reopening an active protected state marks transition reentry unreviewed;
abort/restore protocols need a broader method.

## Report and bindings

The report preserves typed owner summaries, protected milestone samples, first
violation witnesses and gaps. Status is `review_required` with findings,
otherwise `incomplete` with gaps, otherwise `within_sampled_quiescence_contract`.
Repeated identical owner/control violations are represented by their first witness.

`python quiescence_review.py digest record.json` prints canonical SHA-256 (sorted
keys, compact separators, UTF-8, nonfinite values disabled). Hashes bind supplied
content; they establish neither counter meaning, owner completeness nor approval.
