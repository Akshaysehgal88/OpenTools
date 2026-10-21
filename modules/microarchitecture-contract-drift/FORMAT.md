# Capacity record formats

The helper checks the bounded proposition `maximum required <= minimum available`.
It does not parse arbitrary inequalities or infer protocol semantics. JSON objects
reject unknown fields except the explicitly allowed record `provenance` object.
Duplicate keys, non-finite numbers, booleans as capacities and negative values fail.

## Record

`opentools.capacity-record.v1` requires `record_ref`, `revision_ref`, `scope`,
`inputs_complete` and `facts`. Optional `provenance` retains native collection data.

Scope contains `project_ref`, `interface_ref`, `configuration_ref`, `mode_ref`.
Record revision/scope references may be null; they remain incomplete. Each fact has:

| Field | Meaning |
|---|---|
| id | Unique local identity selected by the contract |
| value | Nonnegative integer or null |
| unit | Explicit comparable unit, such as transactions |
| basis_ref | Shared counting/population/interval definition |
| value_ref | Native or supplied evidence for the numeric value |
| meaning_ref | Evidence that the value has its asserted engineering role |

Except `id`, unknown fact fields are null. Null is never zero. A value reference
and a meaning reference have different roles. A native `ISSUE_LIMIT=4` export does
not establish that the runtime producer cannot issue eight requests.

## Contract

`opentools.capacity-contract.v1` requires exact non-null `scope`, `record_sha256`,
`baseline_sha256`, `population_complete`, `evidence_ref` and a nonempty `checks`
list. Hashes are lowercase SHA-256 over canonical JSON (sorted keys, compact
separators, UTF-8, no NaN); use `contract_review.py digest FILE`.

`record_sha256` binds the current record. Missing/wrong binding or a different
scope blocks its verdict. `baseline_sha256` is null when no baseline is requested.
Completeness is boolean/null and its evidence reference can be null, resulting in
incomplete status. A declaration is not authenticated completeness or approval.

Each check contains `id`, distinct `required_fact` and `available_fact` IDs,
`unit`, `basis_ref`, `evidence_ref`, and a nonempty `premises` list. Each premise
contains unique `id`, boolean/null `holds`, and nullable `evidence_ref`.

State assumptions such as maximum unretired demand, guaranteed usable capacity,
sharing/reservations, admission and credit-return behavior. Supply their actual
source basis. Missing evidence blocks a numeric conclusion. A false premise with
evidence is a review finding; the inequality is not used to override that premise.

Both facts must match the check's unit and basis exactly. No automatic unit,
per-bank/aggregate or time-window conversion occurs. A referenced absent fact
remains unknown. Extra unselected facts establish no additional checked obligation.

## Baseline and report

A supplied baseline must bind its declared digest and the current project,
interface and mode. Configuration/revision changes may be intentional and remain
in the source records. The report lists descriptive value deltas only for matched
fact IDs with equal known units/bases. It does not classify absent facts as removed
or prove semantic identity merely from stable fact IDs.

`opentools.capacity-review.v1` retains exact input digests, requested scope, each
check, known findings, missing premises, descriptive changes and interpretation
limits. Check status is `within_bounds`, `exceeds_capacity`, `premise_false` or
`needs_evidence`. Overall `review_required` takes precedence over `incomplete`;
`within_declared_bounds` requires no known finding or missing required basis.

## Slang mapping

`capture-slang` requires Python 3.11+ for the pinned native package. It reads an explicit parameter-override object and a scope object.
Its mapping has `format="opentools.capacity-mapping.v1"` and a nonempty `facts`
list, for example:

```json
{
  "format": "opentools.capacity-mapping.v1",
  "facts": [
    {"id":"required","symbol":"ISSUE_LIMIT","unit":"transactions","basis_ref":"unretired-window","meaning_ref":"producer-review"},
    {"id":"available","symbol":"AVAILABLE","unit":"transactions","basis_ref":"unretired-window","meaning_ref":"consumer-review"}
  ]
}
```

Only plain top-level parameter identifiers, known integral values and integer
top-module overrides are supported by this profile. Local derived parameters can
be read; they cannot be overridden. Strings, real/unknown/negative values and
nonparameters are rejected. Other native formats can supply normalized records.
Repeat `--source`/`--dependency` for the declared input inventory. Completeness is
the caller's assertion; files are hashed before/after extraction, not a discovered
list of all consumed includes. Native capture is tested on Windows and Linux.

References: [Slang compilation](https://www.sv-lang.com/user-manual.html),
[Verilator binary execution](https://verilator.org/guide/latest/example_binary.html).
