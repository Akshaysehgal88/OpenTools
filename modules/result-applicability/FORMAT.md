# Executable result correspondence formats

UTF-8 JSON; duplicate keys, nonfinite numbers and unexpected top-level fields are
rejected. The manual `record_type` template is separate from these formats. See
[examples/create_example.py](examples/create_example.py) for complete input records.

## Snapshot: `opentools.result-snapshot.v1`

Required fields:

- `format`, `run_ref`, `manifest_ref`: format and nonempty original identities.
- `execution`: `state` (`completed`, `failed`, `not_run`, `unknown`),
  `evidence_ref`, `command` (argument list or null), `executable_ref`,
  `dependency_capture_complete` (boolean or null), `dependency_evidence_ref`.
- `result`: `outcome` (`pass`, `fail`, `not_run`, `unknown`), `native_status`,
  `complete` (boolean or null), `producer_run_ref`, `evidence_ref`, `artifact`.
- `fields`: named claim-selectable facts, each `{ "value": ..., "evidence_ref": ... }`.
- Optional `provenance`: retained adapter details; it does not change the verdict.

An artifact is `{ "path": "result.txt", "sha256": "<64 lowercase hex digits>" }`
or null. Its path is resolved relative to the snapshot file, unless absolute. The
CLI reads and hashes its current bytes each time. Missing/changed artifacts leave
the result unresolved; they do not establish a design failure. Keeping the file
unchanged does not prove its assertions are truthful or its checker sufficient.

Execution can be completed even when an executed checker reports a failure.
`state=failed` means completed execution of the selected check has not been
established, such as a tool crash. Do not turn a nonzero process exit into an
assertion failure or pass without the native runner/checker's semantics.

Facts may contain JSON scalars, lists or objects. Null anywhere within a selected
fact, an empty string or missing evidence makes the fact unknown. Arrays retain
order; object key order is ignored. Comparison uses canonical JSON identity:
`false`, `0`, `0.0` and `"0"` are distinct. No enum, path, unit or parameter
normalization is implicit. An explicitly empty list/object can be a known empty
value when its meaning and source are established. Field names are local labels;
there is no cross-company requirements ontology.

Keep at least implementation/configuration, executable, checker, runtime inputs
and claim scope separate when relevant. A test name or repository commit alone
does not identify generated/untracked inputs, firmware, checker revisions or the
binary actually used. `dependency_capture_complete=true` is a declaration about
the recorded boundary with an evidence reference, not a completeness proof.

## Request: `opentools.result-request.v1`

Required keys: `format`, `claim_id`, `claim`, `scope_ref`, `required_fields` and
`required_outcome`. The claim, scope and ID are nonempty strings. Select at least
one field with the same fact shape as the snapshot, now describing the requested
value and its request/specification source. `required_outcome` is `pass`, `fail`
or `any_observed` (an executed pass or fail is acceptable evidence for the question).

The helper cannot infer whether your field selection fully represents the prose
claim. An exact match supports correspondence only within the declared boundary.
Choosing one convenient field or changing the request to match the evidence
cannot establish the original engineering claim.

## Reviewed reuse: `opentools.result-reuse.v1`

Optional file with `format`, `claim_id`, `run_ref` and `exceptions` list. Each
exception has exactly:

```json
{
  "field": "runtime.trace_level",
  "observed": "off",
  "requested": "on",
  "rule_ref": "company-policy:trace-observation-only",
  "approved_by": "review-record:responsible-owner",
  "basis_ref": "review-record:trace-noninterference-for-this-check",
  "reason": "The supplied approved rule permits this difference for this claim."
}
```

This is an illustrative policy record, not an approval to reuse any real result.
Every exception must name a selected field with known, differing values matching
the exact recorded pair. Run/claim binding, duplicate fields, stale values,
missing approval references and no-op exceptions are checked. Rules cannot fill
unknowns or exempt execution, completeness, outcome or result-file checks.
Approval names and references remain caller-supplied evidence, not authenticated
authority or machine-proven equivalence. Keep the original approved artifact.

## Result report and exits

`opentools.result-audit.v1` retains the full original native result and execution,
claim/scope, selected field table, exceptions, mismatches, unknowns, unselected
fields, artifact-integrity observation and canonical input fingerprints.

| Status | Exit | Meaning |
|---|---|---|
| directly_applicable_within_scope | 0 | All selected facts match and the declared execution/result basis is present. |
| applicable_with_reviewed_reuse | 0 | The same bounded checks pass with explicit supplied exceptions. |
| inapplicable | 1 | A known selected value or required outcome differs; any unknowns remain listed. |
| unresolved | 2 | No known mismatch, but required evidence, capture or integrity is missing. |

Invalid JSON/schema/rules or I/O errors return 3. CLI syntax uses argparse's code
2. Output files must be distinct, new, and have existing parent directories. No
report overwrites an input. A successful comparison is not a pass converter,
verification sufficiency check or signoff action.

## SiliconCompiler profile and context

`SiliconCompiler.0.38.11.schema-0.57.2.Project.v1` reads JSON only. It verifies the
Project class marker, schema version and selected-node producer version when
present. No schema classes, plugins, dataroots, commands or network fetches run.
It selects exactly the stated step/index in the root `record` tree; it does not
merge earlier jobs, history, defaults or another node to fill execution facts.
Global options read explicit `node/*/*/value` or their native global default.

Native fields are `sc.design`, `sc.jobname`, `sc.flow`, `sc.step`, `sc.index`,
`sc.status`, `sc.toolexitcode`, `sc.toolpath`, `sc.toolargs`, `sc.toolversion`,
`sc.scversion`, `sc.starttime`, `sc.endtime`. Native tool arguments remain their
original string. `execution.command` requires the original argument-list basis;
the reader does not guess shell tokenization. A recorded tool path/version alone
does not establish the consumed executable's byte identity.

`inspect-sc` creates an inventory and optional `opentools.sc-result-context.v1`
template. Required context keys: `format`, `manifest_sha256`, `step`, `index`,
`run_ref`, `selectors`, `fields`, `execution`, `result`. `selectors` maps local fact
names to absolute JSON pointers into this exact manifest. Example:

```json
{
  "configuration.ECC_EN": "/library/top/fileset/rtl/param/ECC_EN/node/*/*/value",
  "inputs.rtl_hashes": "/library/top/fileset/rtl/file/systemverilog/node/*/*/filehash"
}
```

Select pointers by inspecting your real manifest. In the qualified example,
`ECC_EN` is the recorded string `"0"` and hashes are a list. These establish
recorded inputs, not an arbitrary proof of effective design behavior. Missing
pointers yield null. Invalid pointer escapes/array indices fail. `fields` adds
explicit sourced declarations; neither collection can override native facts or
each other. The output records which added facts are native selections versus
context declarations. A copied context cannot bind different manifest bytes.

Context `execution` has only `command`, `executable_ref`,
`dependency_capture_complete` and `dependency_evidence_ref`. Native selected-node
success, integer zero exit code, known producer, and nonempty start/end establish
`completed`; native `error` establishes `failed`; other cases remain `unknown`.
These records are evidence, not authenticated execution attestations.

Context `result` has the full result shape described above. The caller must
supply any actual checker outcome, completeness and run association from its
original evidence. The reader never derives `pass` from node success, zero errors
or an existing output file. Artifact paths are relative to the context; its
recorded SHA-256 must match before import and is rebased relative to the output
snapshot. Comparison checks it again.

Import returns 2 when the declared execution/result basis remains partial; 0 when
present. This is not a request comparison and does not imply claim applicability.
Inspection returns 0 for a valid supported file, including unexecuted snapshots.
Missing metadata remains visible instead of being inferred from today's files.
No execution recorder, recursive dependency discovery, signature verification,
commercial manifest adapter or arbitrary version compatibility is provided.

References: [SiliconCompiler data model](https://docs.siliconcompiler.com/en/latest/user_guide/data_model.html),
[checklists](https://docs.siliconcompiler.com/en/latest/user_guide/checklist.html).
