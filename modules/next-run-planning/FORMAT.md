# Optional experiment records

The [short Markdown record](RECORD.md) is enough for normal use. JSON is optional
when exact plan/result/history correspondence helps. The helper uses Python 3.10+
standard library only, reads supplied files and writes new reports. It does not
launch jobs, fetch evidence references or evaluate natural-language truth.

JSON keys are unique, fields exact, numbers finite. Null is unknown; use an
explicit JSON value for a known absence. Canonical digests hash UTF-8 JSON with
sorted keys, compact separators and unescaped Unicode (`experiment_core.fingerprint`).
Evidence references are supplied claims, not authentication or automatic fact checks.

## Plan: opentools.experiment-plan.v1

Required fields: `format`, `plan_ref`, `investigation_ref`, `original_run_ref`,
`observation`, `question`, `hypotheses`, `variables`, `required_observations`,
`outcomes`, `next_action`, `stopping_condition`, `reproduction`, `prior_search`,
`unknowns`. Optional `provenance` is uninterpreted JSON retained by the digest.

- `plan_ref`: nonempty immutable identity. Other top-level question/references and
  stop condition are strings/null. `observation` has `statement`, `evidence_ref`.
- `hypotheses`: unique `{id, statement, basis_ref}`. At least two grounded
  explanations are required for an inspect/proposed-run record to be structured.
  Context requests and stopping decisions need not invent alternatives.
- `variables`: unique `{name, role, baseline, proposed, evidence_ref}`. Roles are
  `fixed`, `intended`, `uncontrolled`; values are JSON. Known fixed changes require
  review; unknown fixed values need context. Multiple intended changes are allowed.
  Free names preserve local terminology rather than impose a universal dimension
  list. Uncontrolled factors remain visible; they do not establish equivalence.
- `required_observations`: unique `{id, description, scope, attainability_ref}`.
  Actual transaction/time/identity scope and an attainable source are required;
  a field name or generic trace request alone does not prove attainability.
- `outcomes`: unique `{id, kind, condition, requires, effects, next_step, evidence_ref}`.
  Kind is `observation`, `inconclusive`, `execution_failed`, `replay_diverged`.
  `requires` is a unique list of known observation IDs. Normal outcomes need
  nonempty requirements. Effects are unique `{hypothesis_id, assessment}` entries,
  with known IDs and assessment `supported`, `weakened`, `unresolved`, `not_tested`.
  These are supplied interpretations, never proven automatically. Negative-outcome
  support/weakening is warned about for scope review, not universally prohibited:
  a load failure can inform a loader hypothesis without answering hardware behavior.
- `next_action`: `{kind, summary, rationale, alternatives, evidence_ref}`. Kind is
  `inspect_existing`, `request_context`, `propose_run`, `stop`. Alternatives are
  `{kind, why_not, evidence_ref}`. A new-run proposal needs an inspected prior-evidence
  scope and at least one considered cheaper route. No cost ranking is computed.
- `reproduction`: `{kind, basis_ref, limits}`. Kind is `original_reproduction`,
  `exploratory`, `evidence_only`; limits is a string list. Reproduction is planned,
  not established by a seed/binary label. Actual correspondence is a result fact.
- `prior_search`: `{performed: boolean|null, scope_ref, evidence_ref}`. This records
  a scoped inspection claim, not an exhaustive automated repository search.
- `unknowns`: nonempty-string list. Declared uncertainties can legitimately remain
  for the step to investigate; missing required fields remain separate gaps.

References/condition/decision strings may be null, producing missing context.
Unknown/duplicate IDs, invalid types or references to nonexistent IDs are invalid.
Proposed runs require inconclusive and execution-failure decisions, plus a divergent
replay decision when targeting original reproduction. There is no arbitrary run,
signal, compute, hypothesis or company-stage cap.

## Result: opentools.experiment-result.v1

Required fields: `format`, `result_ref`, `plan_sha256`, `state`, `actual_route`,
`execution`, `outcome_id`, `actual_variables`, `observations`, `correspondence`,
`interpretation`, `remaining_unknowns`, `cost_observations`. Optional `provenance`
is uninterpreted JSON. A revised plan gets a new identity; changing a hypothesis
afterward invalidates the original result binding.

State is `not_executed`, `observed`, `failed`, `inconclusive`, `diverged`.
`actual_route` uses the action kinds. `outcome_id` references the unchanged plan's
map or is null. A different actual route/control is visible for review rather
than silently rewriting the experiment.

`execution` is `{attempted: boolean|null, run_ref, exit_code: integer|null,
evidence_ref}`. Inspecting existing evidence has attempted=false and no new run
identity/exit; the source execution remains in the plan/evidence references.
A normal new-run result needs a completed zero-exit invocation with source evidence.
Known nonzero exit cannot be presented as a normal observed result. Failed and
inconclusive records remain legitimate data. An unexecuted proposal cannot claim
actual observations, outcome or attempted execution.

`actual_variables` has unique `{name, value, evidence_ref}`. Known mismatches
against fixed/intended target values require review, including in failed/divergent
records. Missing normal-result control evidence remains a gap. `observations` has
unique `{id, value, complete: boolean|null, evidence_ref}` with plan IDs. Every
observation required by the chosen outcome must have known, complete, sourced
values. This checks declarations, not their truth or whether a value matches the
outcome's natural-language condition.

`correspondence` has `status`, `evidence_ref`, `limits`; status is
`matched_selected_observables`, `unknown`, `diverged`, `not_applicable`. A normal
original-reproduction conclusion requires a sourced matched scope. Unknown
correspondence stays unestablished; known divergence cannot support that conclusion.
An explicit exploratory branch can legitimately differ and retain its scoped facts.

`interpretation` is string/null; `remaining_unknowns` is a string list. Costs are
`{metric, value, unit, scope_ref, basis, evidence_ref}` observations, with value an
opaque string/null and basis `measured`, `estimated`, `unknown`. Costs are retained,
not summed, converted, fact-checked or used to prove savings. Preserve full workflow
scope and unmeasured engineer review cost when making the independent judgment.

## Reports and history

`audit-plan` optionally reads repeated `--prior` plan files. Exact design identity
includes every plan field except `plan_ref`, `provenance`, `unknowns`; order,
source references, question and all control/decision fields remain significant.
This is deliberately exact comparison, not semantic duplicate detection. The same
plan ID with different content requires review. An exact repeated-design notice
does not forbid useful replication or prove zero information gain.

Plan report statuses: `structured_plan` (0), `review_required` (1), `needs_context`
(2). A structured plan is not proof that hypotheses are plausible, observations
discriminate them or the route is cheapest. An AI/engineer must assess those facts.

Result reports retain the plan review, execution/correspondence, actual variables,
observations, selected map/effects, interpretation, uncertainty and costs. Status
is `recorded_outcome` (0), `review_required`/`execution_failed`/`replay_diverged` (1),
or `needs_context`/`not_executed`/`inconclusive` (2). A zero status is structural
correspondence only; a wrongly selected but well-shaped outcome can still pass.
Invalid data/I/O returns 3. Output paths must be new and separate from inputs;
original plans, results and prior records are never rewritten.
