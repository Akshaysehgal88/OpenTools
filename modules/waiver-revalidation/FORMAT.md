# Waiver export formats

All files are UTF-8 JSON. Duplicate keys, duplicate identities, non-finite numbers, missing required fields, and incorrectly typed completeness fields are rejected. Additional metadata fields are permitted. These are validated record formats implemented by `waiver_core.py`, not general SARIF or proprietary tool readers.

## Snapshot: `opentools.waiver-snapshot.v1`

Use [baseline.json](examples/baseline.json) as a complete minimal example.

| Field | Required meaning |
|---|---|
| `format` | Exact format identifier above |
| `run_id` | Nonempty recorded execution identity |
| `scope` | Stable project/engineering population scope |
| `configuration_ref` | Reference or digest identifying the observed configuration |
| `configuration` | Object of known configuration values; null values mean unavailable for premise evaluation |
| `configuration_basis` | Optional nonempty observation-basis identifier; omitted means exporter-defined. Native captures use `command-line-macro-inputs`, not effective elaborated values. |
| `tool.name`, `tool.version`, `tool.ruleset` | Nonempty source-tool and analysis-policy identities |
| `identity_basis` | Nonempty identifier describing how finding IDs are established |
| `population_complete` | Explicit boolean; false prevents an unchanged outcome |
| `waivers` | Nonempty array of explicitly selected waiver records |

Each waiver requires unique `id`, lowercase 64-character `definition_sha256`, boolean `complete`, and a `findings` array. Each finding requires unique `id` within that waiver, `object`, `rule`, `message`, and `evidence_ref`, all nonempty strings. An empty complete current population is reported for review; it is not automatic evidence of a valid or obsolete waiver.

The definition digest describes the actual waiver definition/file, not a generated label. Native captures include original invocation arguments, return codes, logs, input digests, and capture issues under `capture`. A declared complete manual export is a claim by its exporter; the comparator cannot establish that omitted native material never existed.

Only comparable scope, tool policy/version, and identity bases support an unchanged result. Configuration revisions and source revisions can change without automatically invalidating a waiver; the observed population and explicit premises determine the reported changes.

## Policy: `opentools.waiver-policy.v1`

Use [policy.json](examples/policy.json). `waivers` contains unique `id` values present in the current snapshot. Each entry has a `premises` array. A premise has a unique flat configuration `key`, scalar non-null `equals`, and a nonempty `evidence_ref` identifying its recorded basis.

Equality is type-sensitive: JSON `false` is not integer `0`. Missing/null observations are unknown. No expression evaluation, automatic unit conversion, nested-key guessing, or inference from rationale text is performed. Premise evidence establishes what was recorded; it does not grant engineering authority.

## Correspondence: `opentools.waiver-identity-map.v1`

```json
{
  "format": "opentools.waiver-identity-map.v1",
  "mappings": [
    {"waiver_id": "debug-receiver", "from": "old-finding-id", "to": "new-finding-id", "evidence_ref": "review:explicit-correspondence"}
  ]
}
```

Both endpoints must exist in the specified waiver. Mappings must remain one-to-one when unchanged identities are included. A correspondence can account for a moved/renamed source object, but a changed rule/message still requires review. The original mapping and evidence reference remain in the report.

## Audit: `opentools.waiver-audit.v1`

The output preserves baseline/current run IDs, normalized input fingerprints, global comparability issues, per-waiver additions and absent/unmapped findings, explicit mappings, premise evaluations, and review issues. Status is `unchanged_within_scope`, `review_required`, or `incomplete`. The separate `review_required` boolean remains true when review findings coexist with incomplete evidence.

No output approves/rejects a waiver or establishes a design defect. Original evidence references are retained so a reviewer can inspect the native observations.
