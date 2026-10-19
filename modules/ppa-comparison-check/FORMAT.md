# PPA comparison formats

Inputs are UTF-8 JSON (a BOM is accepted). Duplicate keys, non-finite normalized
numbers, booleans used as measurements and unsupported structural fields are
rejected. Native ORFS error/non-finite values are preserved as unknown observations
by its separate reader. References identify supplied evidence; the comparator does
not authenticate them, execute scripts or retrieve remote artifacts.

## Snapshot: `opentools.ppa-snapshot.v1`

Top-level fields are `format`, nonempty `run_id`, `source_ref`, `context_ref`, a
nonempty `metrics` array and optional `provenance`. Each metric has exactly:

```json
{
  "id": "setup_slack",
  "kind": "setup_slack",
  "definition_ref": "project:reported-worst-setup-slack.v1",
  "scope_ref": "project:whole-top-and-selected-analysis-views",
  "value": -0.4,
  "unit": "ns",
  "unit_evidence": "report-content-id#reported-unit-definition",
  "evidence_ref": "report-content-id#measured-slack",
  "measurement_complete": true,
  "conditions": {
    "stage": {"value": "finish", "evidence_ref": "run-manifest#stage"}
  }
}
```

Metric IDs are unique within a snapshot. Kinds are `instance_area`, `stdcell_area`,
`die_area`, `setup_slack`, `total_power`, `dynamic_power` and `leakage_power`. The
definition reference must establish the actual reported quantity; same units or
similar names do not make cell area and die area interchangeable. Definitions and
scope must match across the selected pair for arithmetic. Scope, value, unit and
unit evidence can be `null` when unavailable. Area/power values cannot be negative;
slack can. `measurement_complete` is a caller declaration about this measurement,
not a signoff, population or verification-completeness claim.

Conditions map names to exactly `{value, evidence_ref}`. Values are JSON scalars
or flat lists of known scalars; `null` or missing evidence means unknown. Identity
values (`design_ref`, `rtl_ref`, `netlist_ref`, `stage`, `tool_ref`, `flow_ref`) must
be nonempty strings or null. Comparisons require those identities known. All
metrics also need declared rules for `library_ref`, `corner_ref` and
`constraints_ref`; a genuinely irrelevant condition may remain unmeasured under an
explicit justified rule. A corner reference must identify the actual selected
analysis view or view set, not an inferred label from a platform filename.

Power additionally requires known `activity_source_ref`, `activity_window`,
`activity_scope_ref`, `activity_mapping_ref`, `annotation_scope_ref`,
`annotation_basis`, `annotated_fraction` (finite number 0..1) and
`unannotated_policy`, each with evidence. Different annotation bases are not equal
because their percentages happen to match. These fields retain the declared
estimate basis; the utility does not measure annotation itself or prove that a
source/report is authoritative.

## Contract: `opentools.ppa-contract.v1`

The root has exactly `format`, `baseline_run_id`, `current_run_id` and `metrics`.
Run IDs must match the selected snapshots. Each metric entry has `id`, `claim`,
`rules` and optional `equivalences`. A rule has `role`, nonempty `reason` and
`evidence_ref`. `role` is one of:

- `fixed`: differing known values are confounders, unless an explicit reviewed
  equivalence matches this observed pair.
- `intended`: the changed condition is part of the experiment. Unchanged values
  receive a warning because the intended treatment is not observed.
- `derived`: has a nonempty `from` list of declared parent conditions. A changed
  derived value needs an observed change in a declared ancestor. Cycles are
  invalid; reviewed-equivalent aliases do not explain a derived change.
- `irrelevant`: the supplied reason explains why this field does not qualify this
  particular metric/claim. It cannot hide missing hard identity or power basis.

Every required condition needs a role. Additional observed changes without a role
are unresolved; unchanged additional known fields are visible but do not themselves
make the comparison incomplete. Derived links and irrelevance are assertions in
the contract, not proven dependencies or scientific conclusions.

An equivalence entry has exactly `field`, `baseline`, `current`, `evidence_ref`.
The field must be fixed, known and different; values must match this exact pair.
There can be only one equivalence per field. Its evidence should establish the
relevant characterization/meaning, not merely name similarity. Stale, repeated or
misbound equivalences fail validation. See the executable
[example generator](examples/create_example.py) for complete contracts and records.

## Units and arithmetic

Supported area units are `nm2`, `um2`, `mm2`, `m2` (canonical `um2`); time units
`fs`, `ps`, `ns`, `us`, `ms`, `s` (canonical `ns`); power `W`, `mW`, `uW`, `nW`
(canonical `W`). Case matters. Other/missing units make arithmetic incomplete.
Both sides require an evidence basis for the unit. Units are never inferred from
field names or platform defaults.

Arithmetic uses decimal representations of parsed JSON numbers, with 40-digit
working precision; native bytes remain identified by their source reference.
Normalized values, deltas and percentages are decimal strings. `delta` is current
minus baseline. Area/power percentages use a strictly positive baseline; otherwise
they are null. Slack percentages are always null. No delta establishes frequency
gain, statistical significance, experimental sufficiency or causation.

## ORFS inventory and context

`inspect-orfs` accepts a metadata file or a directory containing `metadata.json`.
It recognizes flat `run__flow__metrics_version: Metrics_2.1.2` and these native keys:

| Key | Kind |
|---|---|
| `finish__design__instance__area` | `instance_area` |
| `finish__design__instance__area__stdcell` | `stdcell_area` |
| `finish__design__die__area` | `die_area` |
| `finish__timing__setup__ws` | `setup_slack` |

The `opentools.orfs-inventory.v1` output retains the metadata digest, profile,
native run ID, selected raw/numeric values, native conditions and platform unit
labels. `opentools.orfs-context.v1` has exactly `format`, `metadata_sha256`,
`run_id`, `conditions`, `artifacts`, and `metrics`. The generated template is the
starting point. Each selected metric context has exactly `id`, `key`, `scope_ref`,
`unit`, `unit_evidence`, `measurement_complete`. Keys may be selected from the table
even if missing in this file, in which case their measurement remains unknown.

Context cannot override native `design_name`, `platform_name`, `tool_ref`,
`flow_ref`, `reported_clocks` or `stage`. External conditions supply the actual
design/RTL/final-netlist/library/analysis-view/constraints evidence. Optional
`artifacts` maps condition names to local files relative to the context file; names
cannot overlap supplied conditions or native fields. Their bytes are hashed into
condition values, and paths/digests are retained in provenance. Hashing a selected
file does not establish that the run consumed it or every indirect dependency.
For multi-file sources/libraries, an existing manifest should identify actual
content digests if its hash is used as the collection identity; a path list alone
does not identify the bytes of the referenced files.

The reader does not infer metric units from UI unit labels, reconstruct complete
SDC from clock strings, identify a final netlist from synthesis hashes, parse power
activity/annotation reports or accept another metadata version automatically.
Use normalized records for independently extracted supported measurements.

## Audit: `opentools.ppa-audit.v1`

Per-metric results retain measurements, conditions, roles, evidence, reviewed
equivalences, unknowns, warnings, known confounders and any arithmetic. Status is
`incomplete`, `confounded` or `comparable_within_contract` in that precedence.
`confounders_found` remains independent of an incomplete overall status. The report
lists metrics omitted by the contract and input content fingerprints. A repeated
snapshot/source reference is flagged without implying that other pairs are
independent. A positive qualification concerns this declared contract and evidence;
it neither approves the free-form claim nor proves causal attribution or signoff.
