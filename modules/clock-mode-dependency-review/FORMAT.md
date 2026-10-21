# Clock prerequisite records

UTF-8 JSON, no duplicate keys or nonfinite values. Both records include `format`,
exact `scope` (`project`, `configuration`, `mode`), `basis_ref` and boolean
`inputs_complete`. The basis identifies the reviewed abstraction and applicability.
Use [create_example.py](examples/create_example.py) for complete fixtures.

## Model: `opentools.clock.model.v1`

`semantics` is `positive-monotonic-prerequisites`. This is an availability
abstraction: established facts remain available; rules describe sufficient
enabling paths. It is not a temporal state machine. Use another method if facts
must deassert, two resources cannot coexist, or an ordered pulse must be captured.

- `facts`: 1–256 unique `id` values, `initial` (`true/false/null`), `owner_ref`
  (text or null), `evidence_ref`. False means initially unavailable; a producer
  rule may establish it. Null is unknown. No producer for a false fact means the
  declared model supplies no path to establish it.
- `clocks`: unique `id`, explicit `parent_ref` (null for a root),
  `available_fact`, `owner_ref` (text or null), `evidence_ref`. This profile
  supports one parent per clock; mux selection must already be resolved by mode.
- `rules`: unique `id`, `requires` (unique fact IDs), one `produces` fact ID,
  explicit `clock_ref` (null for a declared non-clocked rule), `evidence_ref`.

A rule requires all listed facts and availability facts along its clock lineage.
Multiple rules producing one fact are alternatives. An empty prerequisite list
with null clock is an explicitly declared unconditional source; cite its basis.
Clock-lineage loops, missing references and unknown owners are gaps. Declared
relationships are not inferred from signal names or hash validity.

## Request: `opentools.clock.request.v1`

`model_sha256` binds the full model. `goals` has unique `fact_ref` entries with
`evidence_ref` identifying the consumer requirement. Scope and basis must match.
Use `python clock_review.py digest model.json` for the canonical SHA-256 (sorted
keys, compact separators, UTF-8, nonfinite values disabled).

## Interpretation

Closure starts from known-true facts. A second closure permits unknown initial
facts to distinguish a dependency on unknown state from an unreachable goal.
Only a complete, bound and structurally resolved abstraction yields
`goal_unreachable_in_declared_model`. Partial evidence remains incomplete.

`candidate_cycles` are strongly connected groups among facts not already
derivable. Alternative seeds can break a cycle. A missing external prerequisite
can block a goal with no cycle. Neither result proves a native deadlock or clock
glitch. Check the actual sequencer, reset, bypass/wake paths and native observations.

The report retains expanded rules, derivable facts, goal states, candidate cycles,
findings and gaps. Status is `review_required` with findings, otherwise
`incomplete` with gaps, otherwise `derivable_within_declared_model`. Hash bindings
and completeness flags establish neither source truth nor engineering approval.
