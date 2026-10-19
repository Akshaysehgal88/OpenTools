# Checkpoint and replay records

Python 3.10+ and JSON only. Keys are unique and fields exact; numbers are finite.
Null means unknown, including inside values/configuration. Use an explicit value
such as `{"state":"not_used"}` for a known absent seed. Evidence references are
supplied assertions, not authenticated proof or automatic verification of prose.

All digests are lowercase 64-character SHA-256. Record/profile bindings hash UTF-8
canonical JSON: sorted keys, compact separators, Unicode unescaped, finite numbers.
`replay_core.fingerprint` implements this convention. File digests hash raw bytes.
Changing a record requires new run bindings; a new binding alone does not establish
that its assertions are true.

## Profile: opentools.checkpoint-profile.v1

Required fields: `format`, `id`, `mechanism`, `state`, `observables`, `boundary_ref`,
`evidence_ref`. Mechanisms are `serialized_model`, `native_simulator`,
`process_checkpoint`, `manual_initialization`; their names do not imply capability.

- `state`: nonempty array of unique `{id, requirement, evidence_ref}`. Requirement
  is `capture` or `not_used`. IDs are local to the inspected flow; the helper has
  no universal complete state taxonomy. Inspect actual consumers before declaring
  absence. Every obligation needs nonempty evidence for compatibility.
- `observables`: nonempty unique string list. These are exact selected channel
  names required at the capture boundary, each horizon step and final boundary.
  Channel values are JSON with definitions in the source/boundary contract.
- `boundary_ref` and `evidence_ref`: strings/null describing capture phase, native
  restrictions and inspection basis. Missing basis blocks compatibility.

## Checkpoint: opentools.checkpoint.v1

Required fields: `format`, `checkpoint_ref`, `profile_sha256`, `mechanism`, `context`,
`reference_continuation`, `state_inventory`, `state_inventory_complete`, `capture`,
`artifacts`, `boundary_observation`. Optional `provenance` is uninterpreted JSON
retained through input fingerprints.

`context` contains exactly:

| Field | Meaning |
|---|---|
| `binary_sha256` | Original exact executable bytes, or null |
| `configuration` | Relevant configuration object/null, including instrumentation |
| `prefix_inputs` | Ordered unique `{id, sha256, evidence_ref}` file-content identities consumed before capture |
| `prefix_seed` | Actual pre-capture seed/state identity as JSON; null is unknown |
| `capture_point` | `{step, unit, definition_ref}`: nonnegative integer/string definitions or null |

Context comparison preserves exact configuration, seed, input order/identity and
capture point. Prefix evidence-reference locations do not alter context identity.
No unit conversion, binary compatibility inference, filename alias or phase
classification shortcut occurs. Original consumed-byte evidence is caller-supplied;
hashing a current file cannot reconstruct what an old prefix consumed.

`reference_continuation` is an object/null describing stimulus/settings expected
by the faithful control. The request may choose a new observation extent but may
not silently change this continuation contract.

`state_inventory` has unique `{id, status, method, capture_ref, restore_ref}` entries.
Status is `captured`, `not_used`, `missing` or `unknown`; method/references are
strings/null. The population must exactly match profile obligations. Required
state explicitly missing or wrongly declared not used is incompatible. Unknown/
unlisted state or missing capture/restore basis blocks compatibility. A fully
asserted but incomplete/incorrect profile can still mislead the checker; inspect
the real testbench. `state_inventory_complete` is
`{complete: true|false|null, evidence_ref: string|null}`.

`capture` is `{complete: boolean|null, exit_code: integer|null, evidence_ref}`.
False completion or known nonzero capture exit is incompatible; unknown completion
cannot qualify. This is an invocation result, not a design verification verdict.

`artifacts` is a nonempty required set of `{path, sha256, evidence_ref}` files for
compatibility. Paths are unique relative POSIX paths: no empty/dot/parent component,
colon or backslash. Files are verified under an explicit `--artifact-root`.
Missing files, symlink components, resolved escapes and hash mismatch are
unavailable. Unknown original hashes/evidence or no supplied root remain unknown.
No authenticity, lock/lease, concurrent publication or future file-stability proof
is provided. Normal native operations belong to the existing runner/cache policy.

`boundary_observation` is `{step, values, evidence_ref}`. Step binds the capture
point. Values must contain exactly every selected profile channel without nulls.
This establishes the saved selected-observation reference, not all hidden state.

## Request: opentools.replay-request.v1

Required fields: `format`, `request_ref`, `checkpoint_ref`, `profile_sha256`, `intent`,
`context`, `continuation`, `horizon`, `binary`, `prefix_files`, `evidence_ref`.
Optional `provenance` is uninterpreted JSON. Intent is `faithful` or `exploratory`.
Exploratory requests never qualify as faithful replay, even when selected values
match. They preserve separate provenance rather than establish a new allowed
post-capture variable automatically.

`context` has the checkpoint shape; `continuation` is an object/null. A faithful
request must match captured context and reference continuation. `horizon` has
`start_step`, `end_step`, `unit`, `definition_ref`, `evidence_ref`. Steps are
nonnegative integers/null; a known extent must be positive. Start/unit/definition
must match the captured point. End may select the intended later horizon.

`binary` is `{path, sha256, evidence_ref}` for the actual requested executable.
`prefix_files` has unique `{id, path, sha256, evidence_ref}` entries covering every
requested prefix-input ID. File declarations must match requested context digests
and current bytes under the same explicit root. This catches unreported live
edits as well as correctly reported incompatible identities. Other non-file prefix
settings belong in configuration/seed. Evidence/reference strings may be null;
missing required evidence blocks compatibility.

## Run: opentools.replay-run.v1

Required fields: `format`, `run_ref`, `role`, `request_sha256`, `checkpoint_sha256`,
`profile_sha256`, `horizon`, `completion`, `start`, `samples`, `end`, `observations_ref`.
Optional `provenance` is uninterpreted JSON. The checkpoint digest binds the entire
checkpoint record, not just one native file. Role is `control`, `restored` or
`exploratory`; faithful qualification needs distinct control/restored run identities.

`completion` has the capture-completion shape. Complete successful invocations,
source evidence and exact record/profile/request/horizon bindings are required for
a match. `horizon` has the request shape; evidence location may differ. Foreign
bindings/horizons/roles cannot become divergence or faithful-match proof.

`start` and `end` have the boundary-observation shape. `samples` is an ordered array
of `{step, values}` for **every** step from start+1 through end, exactly once. Each
value object contains exactly all selected profile channels. End values must
agree with the last sample. `observations_ref` supplies the original journal basis.

Absent/null channels and missing, repeated or reordered step populations are gaps.
Known values at uniquely observed common steps can show a difference while other
steps remain incomplete; missing rows alone do not imply behavioral divergence.
Ordering within channel values, e.g. transaction queues, remains significant.
Terminal/boundary contradictions make the pair unqualified. All relevant source
evidence and honesty of the declared channel definitions remain caller concerns.

## Reports and exit codes

`check` returns `opentools.checkpoint-check.v1` with input digests, incompatibilities,
unknowns, live file observations and limits. Known incompatibility takes priority
(exit 1), then unavailable/corrupt files (1), then unknown compatibility (2).
Only no incompatibilities/unknowns plus verified files returns
`compatible_within_declared_scope` (0). That is a preflight observation, not native
execution or operational authorization.

`qualify` returns `opentools.replay-qualification.v1`, retaining compatibility,
record digests, run identities, horizon/channels, differences and all unknowns.
Incompatible/unavailable checkpoint status takes priority (1). An unbound or
contradictory pair is `not_qualified` (2). Otherwise known selected-observation
differences produce `diverged` (1), retaining incompleteness/failure gaps. Remaining
gaps produce `not_qualified` (2). Only a compatible complete bound matching pair
returns `matched_selected_observables` (0). A match applies only to its selected
capture boundary, channels, inputs and horizon. It is not universal equivalence.

Invalid data/I/O returns 3. Reports use new, distinct output files separate from
inputs, checkpoint files, requested binary and prefix files. Writes are sequential,
not transactional native checkpoint publication. The portable helper performs no
native subprocess calls, restoration, checkpoint selection or catalog mutation.
