# Offline campaign contract and snapshots

Python 3.10+ standard library; UTF-8 JSON. Root fields are exact; duplicate keys/
identities and nonfinite values reject. Optional root `provenance` participates in
SHA-256 canonical JSON digests (sorted keys, compact separators, unescaped Unicode,
UTF-8). Digests bind records, not native truth or current policy authority.

## Independent contract

`opentools.campaign-contract.v1` requires `campaign_ref`, `scope_ref`,
`configuration_ref`, `model_ref`, `population_ref`, `population_complete`,
`required_run_refs`, `evidence_ref`, `objectives`, `policy`. References are string/null;
completeness is boolean/null; run IDs are unique nonempty strings. Enumerate the
full applicable required execution population independently of observed exports.
Unknown/empty population remains a gap. A retry needs its own execution identity.

Policy has `{ref, evidence_ref, allowed_recommendations, limits}`. Recommendations
are drawn from `continue`, `inspect_effectiveness`, `redirect`, `seek_policy`.
Limits are unique strings. These are review choices, never execution permissions.

Objectives have unique `{id, kind, description, basis_ref, policy_ref,
eligible_states, target}`. Description/basis/policy are string/null; eligible states
are a unique list of normalized states below. Targets depend on kind:

| Kind | Target and meaning |
|---|---|
| execution | `{run_refs: [...]}` subset of independent required population; eligible states must be exactly `["passed"]` |
| coverage | `{population_ids: [...], required_ids: [...]}` unique named Boolean attainment goals with required subset; definition/threshold/aggregation must be qualified externally in `basis_ref` |
| exposure | `{value: nonnegative integer, unit: string/null}` qualified unique event count, with explicit event-space identity |
| manual | source-backed target description string/null; arithmetic and attainment require a separately qualified engineering method |

Named coverage is not a general UCIS/weighted/cross-bin aggregator. Equal names or
counts do not prove equal definitions. Exposure is an integer event-count slice,
not elapsed time, seed count or independent statistical trials. Event-count policy
must state whether real repeated stimulus counts. A zero target has its literal
declared meaning; it creates no assurance. Manual objectives remain visible gaps.

## Cumulative native export

`opentools.campaign-snapshot.v1` requires `campaign_ref`, `snapshot_ref`, `scope_ref`,
`captured_at` (timezone-aware ISO 8601/null), `mode="cumulative"`, `complete`,
`evidence_ref`, `runs`. Snapshots need distinct identities and increasing known
timestamps for interval comparisons. Their campaign/scope must bind the contract.

Runs have unique `{run_ref, configuration_ref, model_ref, native_state, state,
evidence_ref, measurements, resources}`. Native state and evidence are retained
string/null. Normalized state is `passed`, `failed`, `aborted`, `queued`, `running`,
`not_run`, `unknown`. Pass must come from native checker meaning, not just exit 0.
Foreign/unknown configuration/model remains raw and is not pooled. Missing run
records are not inferred to be not-run. A declared complete export omitting required
IDs requires review; matching observations still remain useful.

Measurements have unique `{objective_id, basis_ref, evidence_ref, qualified,
complete, data}`. Qualification/completeness are boolean/null. Aggregation needs
matching objective basis, source and explicit qualification/completeness, and a
state eligible under that objective policy. Queued/not-run measurements cannot
claim executed data. Failed prefixes remain raw and may count only under explicit
eligibility. Missing qualified data stays unknown, rather than becoming zero.

Coverage data: `{population_ids, hit_ids}` unique string lists. Full population must
match the contract's set; hits must be in it. Changed populations/definitions are
noncomparable, even if a percentage rises. Applicable qualified hit sets are unioned.

Exposure data: `{unit, ranges}`. Ranges have `{space_ref, start, stop, evidence_ref}`,
with nonnegative integer half-open bounds `start <= stop`. Source and logical
event-space identity must be known. Ranges are unioned per event space; overlap
counts once, distinct spaces are summed. A declared different space does not prove
fresh events or independence. Empty qualified ranges mean observed zero events.
Counter resets/replays need explicit identity mapping; do not invent new names to
double count the same work. Cumulative totals are compared, never added across
snapshots. Missing/unqualified measurements prevent claiming a comparable delta.

Resource entries are `{metric, value, unit, definition_ref, basis, evidence_ref}`.
Metric is nonempty; value is an opaque string/null; basis is measured/estimated/
unknown. They are retained with origin/units, not totaled, converted or substituted
for exposure. Missing origin/unit on a measured/estimated claim remains visible.

## Review output

`opentools.campaign-progress-review.v1` retains the contract/digests, both snapshots'
raw runs/resources/measurements, normalized states, bound run IDs, full required
population, objective known values, targets, attainment, gaps/exclusions and
same-definition changes. Known partial values remain available even with incomplete
exports; they do not establish a complete total. Target attainment can follow a
qualified lower bound; overall recorded-target attainment additionally requires
complete consistent inputs and all required recorded passes.

Terminal execution data changed under one identity requires review; disappeared
cumulative records remain gaps. Coverage loss or decreasing qualified exposure
requires review. There is no latest-pass overwrite. Missing timestamps prevent a
comparable interval. Manual/statistical objectives require independent analysis.

Status/exit: `recorded_progress` (0), `review_required`/`execution_findings` (1),
`needs_context` (2); invalid data/I/O (3). Recorded progress may include unmet
objectives or completely ineffective execution with well-established zero events.
It means evidence was summarized, not that the campaign is useful or complete.
`release_completeness=not_established` always. The AI/engineer chooses a separate
source-backed recommendation under policy. Nothing is monitored, dispatched or stopped.

JSON and Markdown reports need new distinct paths separate from inputs. Original
contracts, exports and reports are never overwritten. The helper cannot fact-check
qualifications, infer statistical confidence, authenticate policy or certify signoff.
