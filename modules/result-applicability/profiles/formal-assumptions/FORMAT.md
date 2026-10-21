# Saved evidence format

Review uses independent scope and retained evidence JSON. Native paths are
relative POSIX paths below the directory containing `evidence.json`. Duplicate
JSON keys/non-finite numbers are rejected. Configurations are read, never executed.

## Qualified reader

Tested: SBY revision `85dd50b92a3acf170954a06f20f49e2162ce5273` (tag `yosys-0.33`),
Yosys0.33 git `2584903a060`, Z3 4.8.12 64-bit. Exact resolved task shape:

```text
[options]
mode prove
depth 8

[engines]
smtbmc z3

[script]
read -formal model.sv
prep -top consumer
write_json cells.json

[files]
model.sv
selection.vh
```

Mode may be `prove`, `bmc` or `cover`; depth is a positive state count and top an
explicit identifier. Supports one prepared flat module, one consumer assert/cover
pair and explicitly mapped assumptions. Producer tasks have one assertion, no
cover and no `$assume` cells. Other versions/scripts, hierarchy, multiple engines/
properties/covers, multiclock and arbitrary reports are outside qualification.

Required artifacts: `status`, `logfile.txt`, `config.sby`, `src/model.sv`,
`src/selection.vh`, `src/cells.json`, mode-specific terminal engine logs and actual
VCD/Yosys witnesses for cover hits or safety failures. Census includes native
creator/source attributes. Native status must agree with terminal/engine evidence.
UNKNOWN/ERROR is not a design failure; missing artifacts remain unresolved.

Capture emits parent `opentools.result-snapshot.v1` with mode/depth/top, source
hashes, cell census and result meaning. Scope, original command, SBY/solver revision
and dependency completeness are supplied declarations, not authenticated native
measurements. This reader does not establish dependency closure or equivalence
between HDL and solver model.

## Scope: `opentools.formal-assumption-scope.v1`

- `scope_ref`, `claim_ref`, `claim`, `owner_ref`: independent question.
- `consumer`: `sources` (filename → SHA256), `top`, `scope`, sorted `cells`
  (`id`, `type`, `source`), `basis_ref`, `property_ref`, `activation_ref`,
  `assumptions` (`cell_id`, `condition_ref`, `owner_ref`, `support_ref`). Every
  native assumption must be mapped; empty inventories cannot hide premises.
- `scope`: `clock_ref`, `reset_ref`, `integration_mode_ref`, `model_scope_ref`.
- `guarantees`: support ID → producer source/top/scope/cells/basis plus
  `condition_ref`, `owner_ref`, `port_binding_ref`. Clock/reset/mode must match the
  consumer. Predicate/port equivalence still requires source review.
- `run_refs`: expected `proof`, `cover`, `guarantees` ID → original run reference.
  Different runs are quarantined, not silently substituted.

Unknown substantive fields use `null`, not invented values. Unknown inventories,
sources, scope or owners leave the review open. Missing claim/basis structure is
invalid input. `cells` includes the complete selected assert/assume/cover
population, ordered by native ID. No reuse exception or automatic premise removal.

## Evidence: `opentools.formal-assumption-evidence.v1`

`scope_sha256` is the parent's canonical JSON digest of scope. `proof` and `cover`
embed snapshots or `null`; `guarantees` maps declared support IDs to snapshots.
See a generated native bundle for concrete inputs.

The receipt hashes all critical files. Review rehashes/reparses them, compares
the whole receipt and calls the parent comparator for source/model correspondence.
Changed, missing or foreign records are quarantined. Paths cannot escape the
selected root; linked evidence files/directories are unsupported.

Meanings remain distinct: conditional induction proof, bounded BMC pass, safety
counterexample, activation witness and not-reached-within-depth. Hashes/references
do not authenticate authorship, establish semantic completeness or accept a proof
on behalf of an engineering owner.
