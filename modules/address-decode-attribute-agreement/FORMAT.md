# Effective address-map formats

The profile compares byte-addressed windows with linear target translation:
`target_base + address - base`. It does not infer hierarchy, bit interleaving,
dynamic remapping or IOMMU state. Numeric fields are JSON integers, not hex strings.

## Map record

`opentools.address-map.v1` requires `view_ref`, nullable `revision_ref`, `scope`,
`address_unit="bytes"`, nullable `basis_ref`, boolean/null `inputs_complete` and
`windows`. Optional `provenance` retains native/generator context.

Scope contains `project_ref`, `configuration_ref`, `mode_ref`; unknown record
scope values may be null. The semantic basis must identify the same kind of
effective map in both records. Required software access is not interchangeable
with effective hardware permission.

Each window has:

| Field | Meaning |
|---|---|
| id | Unique local ID selected by explicit correspondence |
| initiator_ref | Address-space owner; different initiators are separate spaces |
| base, size | Half-open byte interval `[base, base+size)` |
| target_ref, target_base | Target identity and target-local first-byte offset |
| permissions | Exact read/write/execute booleans or nulls |
| attributes | Exact cacheable/shareable/secure_only booleans or nulls |
| evidence_ref | Original native or supplied source reference |

Unknown values except `id` may be null. Known bases/target offsets are nonnegative
integers; known size is positive. Booleans cannot stand in for numeric addresses.
False permissions/attributes are known values. Duplicate IDs/JSON keys and
non-finite values fail. Unrecognized object fields fail except `provenance` content.

## Policy and binding

`opentools.address-policy.v1` contains exact non-null `scope`,
`hardware_sha256`, `software_sha256`, `basis_ref`, `population_complete`,
`evidence_ref`, `pairs`, `aliases`, `required_decode`.

Map hashes bind canonical JSON (sorted keys, compact separators, UTF-8, no NaN).
Use `address_review.py digest FILE`. Missing/wrong hashes or different scope/basis
block the requested verdict. Hashes do not authenticate semantics or completeness.

Each explicit one-to-one pair contains `hardware`, `software`, `evidence_ref`.
At least one pair is required. Absent/unmapped selected windows remain gaps;
no correspondence is guessed from names. Completeness is declared, not proved.

Each alias rule contains `initiator_ref`, exactly two hardware window IDs in
`windows`, `allow_differences` and `evidence_ref`. Allowed differences name exact
paths such as `permissions.write` or `attributes.cacheable`. The first profile
supports distinct addresses mapping the same full target span. Partial target
overlap needs another interpretation. Rules are exact to the initiator/pair;
they do not waive overlapping address-space decode or grant another route access.

Each required-decode entry contains `initiator_ref`, `base`, `size`, `evidence_ref`.
The range's requirement must come independently from the observed map. Union the
observed address intervals before finding gaps. Missing decode in a declared
complete population is a review finding; a partial/unknown population yields
unobserved obligations. The helper does not invent required ranges from every
hole between two windows.

## Report

`opentools.address-review.v1` retains input/policy hashes, requested scope,
findings, gaps, aliases, required ranges and limits. Reported field differences
preserve both values and references. An overlap is a review observation about the
declared map; it does not prove a native multiple-driver/security defect.

Overall `review_required` takes precedence over `incomplete`. With neither findings
nor gaps, status is `agrees_within_declared_scope`. This establishes only the selected declared
map comparison. Native priority and alias/coherency safety require their actual
source semantics and separate validation.

Reference: [OpenTitan generated integration collateral](https://opentitan.org/book/util/topgen/index.html).
