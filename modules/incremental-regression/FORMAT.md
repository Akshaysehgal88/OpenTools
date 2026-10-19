# Selection and feedback records

UTF-8 JSON, Python 3.10+ standard library. Unknown fields, duplicate keys/IDs and
nonfinite values reject. Optional root `provenance` is included in fingerprints.
Nullable references remain gaps; referenced files are not read and execution
references are never evaluated as commands.

## Four independent inputs

| Input format | Required fields beyond `format` |
|---|---|
| `opentools.test-universe.v1` | `universe_ref`, `revision_ref`, `scope_ref`, `source_ref`, `complete`, `tests` |
| `opentools.regression-change.v1` | `change_ref`, `base_revision_ref`, `revision_ref`, `scope_ref`, `diff_ref`, `complete`, `items` |
| `opentools.test-mapping.v1` | `mapping_ref`, `scope_ref`, `source_ref`, `universe_sha256`, `change_sha256`, `entries` |
| `opentools.regression-policy.v1` | `policy_ref`, `scope_ref`, `source_ref`, `universe_sha256`, `stage`, `mandatory_ids`, `required_ids`, `defer_ids`, `later_stage_ref`, `broaden_categories`, `unknown_impact` |

References are nonempty strings/null; `complete` is boolean/null. Unknown universe
completeness remains unresolved even with every known test selected. Current
universe/change revisions and all four scopes must agree; equality does not
authenticate or prove those declarations.

Universe tests have unique `{id, name, configuration_ref, execution_ref, available,
evidence_ref}`. References/name are string/null; availability boolean/null. IDs
identify intended configuration/build/seed/checker variants, without silently
combining them. Available false and unknown remain distinct.

Changed items have unique `{id, path, category, evidence_ref}`; path/category/evidence
are string/null. Categories are company-defined. Policy names those requiring broad
selection (for example shared/configuration/toolchain/generator); the helper does
not inspect paths or infer transitive dependencies.

Mapping entries have unique `{change_id, test_ids, complete, evidence_ref}`. Test
IDs are unique strings, complete boolean/null and evidence string/null. A sourced
complete empty list is an explicit no-impact claim, not proof. Bindings use SHA-256
of canonical JSON: sorted keys, compact separators, unescaped Unicode, UTF-8, no
nonfinite values. Every field and array order is significant. Use
`regression_select.py digest FILE` after source review. Hashes bind declared records;
they do not prove freshness, content truth or native source closure. Review a
changed record before updating its bindings.

Policy ID/category collections are unique string lists. Mandatory IDs remain in
required obligations; all policy IDs must exist in the independent universe.
`unknown_impact` is `broaden_all` (select all known tests) or `record_gap` (retain
unresolved impact and needs-context). Stale mapping, absent/renamed mapped tests
and scope/policy contradictions require review. No aliases are guessed. Broad
categories select all known tests; direct maps and mandatory tests are unioned.
Selection overrides requested deferral. Other tests remain deferred/unselected
with their availability, required status and later stage.

## Advisory output

`opentools.regression-selection.v1` retains exact input hashes, full population,
reasons, selected/deferred/unselected IDs, unavailable/unknown-availability IDs,
remaining required IDs, impact gaps, conflicts and missing context. Every member
initially has `execution=not_executed`. Status: `advisory_selection` (0),
`review_required` (1), `needs_context` (2). Universe order is not an optimal schedule.

## Actual feedback

`opentools.regression-results.v1` has `campaign_ref`, `kind` (`targeted`/`full`),
`scope_ref`, `source_ref`, `universe_sha256`, `change_sha256`, `selection_sha256`,
`complete`, `attempts` and optional `provenance`. Targeted results bind the exact
canonical selection report. Independent full results may have null selection
binding; both bind universe/change/scope. Establish the full population from native
manifests, not a filtered targeted list relabeled full. Full does not mean passed
or even executed.

Attempts have unique `{attempt_ref, test_id, state, run_ref, evidence_ref, wall_ns}`.
States: `pass`, `fail`, `error`, `skipped`, `not_run`. Run/evidence are string/null;
wall time nonnegative integer ns/null, retained without summing or claiming CPU/
workflow cost. Executed states need run/evidence; skipped/not-run need evidence but
may have null run. Native checker labels are supplied, not inferred from completion.
Multiple attempts of one test remain visible.

A declared complete export missing expected IDs requires review; its matching
sourced observations still inform feedback. Missing/unsourced attempts are not
passes. Foreign bindings remain raw records and do not apply to this scope.
Targeted packets with extra tests must become a separate extended/full campaign
with its true population; extra observations are not silently pruned.

`opentools.regression-feedback.v1` retains original selection, all attempts and
campaign hashes, per-test states, selected passes/pending work, failed/error/mixed
IDs, failures/errors outside selection and remaining required IDs. Any failure/
error persists across retries. A sourced pass without recorded failure/error
satisfies that test's recorded obligation. Omitted tests stay unexecuted until a
bound actual campaign supplies observations. Actual missed failures do not
establish an unobserved miss probability.

Feedback: `recorded_feedback` (0), `review_required`/`failures_observed` (1),
`needs_context` (2). Invalid data/I/O returns 3. Conflicts take precedence; matching
actual observations remain. `release_completeness=not_established` always: selection
or test passes do not establish independent release criteria. Reports require new
paths and never rewrite inputs, mappings, policy or history.
