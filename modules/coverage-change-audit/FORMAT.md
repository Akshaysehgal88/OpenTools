# Coverage audit formats

Files are UTF-8 JSON. Duplicate keys, non-finite numbers, duplicate identities, negative counts and booleans used as counts fail validation. Unsupported point/bin fields, including per-bin weights and exclusion overlays, are rejected. References are caller-supplied evidence identifiers; the comparator does not fetch them or verify their authority.

## Snapshot: `opentools.coverage-snapshot.v1`

```json
{
  "format": "opentools.coverage-snapshot.v1",
  "metric": "coverpoint-instance-bin-fraction",
  "run_id": "regression-101",
  "scope": "top / opcode_cg / selected instances",
  "configuration_ref": "configuration-content-id",
  "model_ref": "coverage-model-revision",
  "tool_ref": "producer exact-version-and-profile",
  "source_ref": "export-content-id",
  "population_complete": true,
  "points": [{
    "id": "top/cg_i/opcode",
    "definition": "opcode sampled at posedge clk iff valid; resolved-model-key-1",
    "definition_evidence": "model-revision#sampling",
    "at_least": 2,
    "weight": 1,
    "goal": 100,
    "evidence_ref": "export#opcode",
    "bins": [{
      "id": "read",
      "kind": "regular",
      "count": 7,
      "definition": "opcode == 3; resolved-model-key-1",
      "definition_evidence": "model-revision#read",
      "evidence_ref": "export#opcode/read"
    }]
  }]
}
```

Top-level references must be nonempty strings. At least one point is required. `population_complete` describes collection for this selected scope, not design or verification completeness. Only this metric with per-instance aggregation is supported. Counts are nonnegative integers; `at_least` is a positive integer; point weight is a nonnegative integer; goal is an integer from 0 through 100.

Point IDs are unique across the snapshot; bin IDs within each point. IDs are correspondence candidates, not semantic evidence. Point/bin `definition` values may be `null`; known definitions require `definition_evidence`. A point key must encompass sampling, expression and relevant model semantics. A bin key must encompass its resolved obligation and configuration-dependent semantics. Keys are compared exactly: the utility does not parse expressions, prove rewrites equivalent, resolve parameters, or check whether caller-supplied keys are sufficient.

Bin kinds are `regular`, `ignore` and `illegal`. Ignore is a native kind, not an approval of exclusion policy. Illegal hits are separate from coverage progress. The equal-bin fraction does not apply hierarchy weights, normalize to goals, or merge points. Original native reported scores remain in the referenced tool reports.

## XML inventory and context

`inspect-ucis` produces `opentools.coverage-inventory.v1` with exact database SHA-256, reader version, points, native counts/kinds/options and evidence references. It optionally creates this context template:

```json
{
  "format": "opentools.coverage-context.v1",
  "database_sha256": "exact-digest-from-inventory",
  "run_id": "regression-101",
  "scope": "top / selected instances",
  "configuration_ref": "configuration-content-id",
  "model_ref": "coverage-model-revision",
  "tool_ref": "producer exact-version-and-profile",
  "population_complete": false,
  "points": [{
    "id": "copy-exact-point-id-from-inventory",
    "definition": null,
    "definition_evidence": null,
    "bins": [{"id": "read", "definition": null, "definition_evidence": null}]
  }]
}
```

Select at least one inventoried point, listing every bin of each selected point exactly once. Arbitrary bin-subset selection would alter the denominator and is rejected. Context supplies provenance and semantic metadata, and cannot override counts, native kinds, thresholds, weights or goals. The SHA-256 prevents accidental pairing with another XML file; it does not prove that supplied definitions are correct. Missing definitions stay unknown.

Native point IDs retain the full PyUCIS scope path, scope types, covergroup type and instance names. Path segments escape `~` as `~0` and `/` as `~1`. Bin IDs are native names. Reconstructed type points are skipped to avoid counting instance data twice.

## Rename map: `opentools.coverage-map.v1`

```json
{
  "format": "opentools.coverage-map.v1",
  "baseline_run_id": "regression-101",
  "current_run_id": "regression-102",
  "mappings": [{
    "point_id": "top/cg_i/opcode",
    "from": "read_old",
    "to": "read",
    "evidence_ref": "review-42#resolved-bin-rename"
  }]
}
```

Pass with `compare --identity-map`. The point and each mapped bin must exist in their respective snapshots. Correspondence must be one-to-one, including implicit unchanged IDs. Repeated sources, ambiguous targets and different run bindings fail. A map pairs identities only; changed or unknown definitions still block progress claims. Point renames appear as separate populations. No name-similarity matching occurs.

## Report: `opentools.coverage-audit.v1`

Reports retain context/source references, per-point summaries, changes with evidence, issues, limits and progress counts. Zero-denominator fractions are `null`; there is no cross-point percentage. `progress` counts newly hit/lost and newly satisfied/unsatisfied matched regular bins with known unchanged semantics and compatible context. For partial exports, these counts concern observed matched items only. Satisfaction changes can arise from changed thresholds without additional hits.

Status is `incomplete` for collection, context or definition gaps; otherwise `review_required` for changes or illegal hits, and `unchanged_within_scope` when none occur. `review_required` stays true when incomplete status takes precedence. Outcomes do not approve exclusions, establish signoff or prove verification completeness.
