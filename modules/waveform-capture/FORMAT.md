# Capture records and qualified wrapper

Python 3.10+ is sufficient for saved-plan assessment and JSON recipe rendering.
Optional native VCD inventory/GTKWave save support uses **pyvcd==0.5.0**. JSON keys
are unique, fields exact and numbers finite. Null means unknown. Profile/input
bindings are SHA-256 of UTF-8 canonical JSON: sorted keys, compact separators,
Unicode unescaped and finite numbers (`capture_core.fingerprint`). File/header
digests hash raw bytes. References are supplied evidence claims, not authentication.

## Inventory: opentools.trace-inventory.v1

Required fields: `format`, `profile`, `namespace`, `binary_sha256`, `tick`, `max_tick`,
`trace_compiled`, `complete`, `objects`, `aliases`, `source`.

- Qualified profile: `verilator-5.020-vcd-wrapper.v1`; namespace is
  `vcd_declarations`. This is a supplied declaration export, not full RTL hierarchy.
  A filtered export cannot prove another signal does not exist in the design.
- `binary_sha256` is its producer's exact executable identity or null. The explicit
  current `--binary` must match before a recipe is renderable.
- `tick` is a physical quantity. `max_tick` is the producer's positive integer
  bound up to uint64, or null. Unsupported bounds are rejected, never clipped.
  The supplied demonstration wrapper advertises 1,000,000 ticks; this is its own
  explicit bound, not a universal simulation window/signal cap.
- `trace_compiled` and `complete` are boolean/null. Completeness refers to the
  captured declaration namespace, not all design objects or all possible traces.
- `objects`: unique `{path, id_code, width, kind, selectable, selector, viewer_name}`.
  Paths are nonempty strings; code/kind/selector/viewer name are strings/null;
  width is positive integer/null; selectable is boolean/null. Known aliases sharing
  one VCD code must agree about width. The qualified leaf selector supports basic
  dot-separated identifiers and packed buses. Selector equals the declared path;
  escaped names and individual unpacked-array elements are unsupported. Imported
  unsupported objects remain visible in the inventory with selectable=false.
  Packed viewer names retain the actual `[msb:lsb]`; they are not native selectors.
- `aliases`: unique `{name, target, evidence_ref}` semantic mappings to existing
  paths. Names cannot collide with native paths/other aliases. Missing mapping
  evidence blocks readiness. VCD same-code aliases remain separately listed.
- `source`: `{header_sha256, context_sha256, evidence_ref}`. Digests may be null;
  missing producer/header basis blocks readiness.

## Native import

`inspect-vcd` reads the native header prefix through its complete
`$enddefinitions $end` line and hashes only that prefix, including line endings.
It does not hash the waveform body or claim to verify recorded history. The
qualified reader uses PyVCD tokens, verifies the VerilatedVcd version marker,
timescale, scope structure, unique paths/ranges and alias widths, and retains array
objects without inventing leaf selectors.

`opentools.trace-context.v1` has `format`, `profile`, `producer_version`,
`binary_sha256`, `header_sha256`, `max_tick`, `trace_compiled`, `evidence_ref`,
`aliases`. Producer declaration must be `5.020` or observed runtime string
`5.020 2024-01-01`; the full supplied value stays in the canonical context binding.
Other versions fail closed. Import binds the exact header prefix and canonical
context digest. It does not execute the producer or authenticate its declaration.
Use actual capabilities/source and original binary provenance. The generated
context template leaves unknown producer facts null; fill them from evidence.

## Plan: opentools.capture-plan.v1

Required fields: `format`, `plan_ref`, `question`, `original_run_ref`,
`inventory_sha256`, `operation`, `waveform_format`, `window`, `failure`, `clock`,
`objects`, `history`, `correspondence`, `intent`, `run`, `expansion`. Optional
`provenance` is uninterpreted JSON retained by the input fingerprint.

| Field | Meaning |
|---|---|
| `plan_ref` | Nonempty plan identity |
| `question`, `original_run_ref` | Engineering question and original execution reference, string/null |
| `inventory_sha256` | Canonical digest binding the exact supplied inventory, or null |
| `operation` | `capture_time` or `postprocess`; this renderer accepts capture_time only |
| `waveform_format` | Qualified renderer supports `vcd`; other format requests are rejected |
| `window` | `{start, end, evidence_ref}`, inclusive dump bounds after eval |
| `failure` | `{time, evidence_ref}`, separate observed failure marker |
| `objects` | Unique `{name, role, rationale, evidence_ref}` selections; name resolves through native paths or semantic aliases |
| `intent` | `reproduce` or `exploratory` |
| `expansion` | Sourced `{trigger, action, evidence_ref}` entries describing how inadequate history/scope will expand |

Quantities are `{value, unit}`: finite decimal strings/null and physical unit
`s`, `ms`, `us`, `ns`, `ps`, `fs`, `cycles` or null. Exact rational conversion
preserves low bits of large counters. Requested controls must be nonnegative
integral native ticks; unrepresentable times are rejected without rounding. Window
extent must be positive and run stop must reach its end. A failure outside the
window is a visible warning, not an automatic causal-adequacy verdict.

`clock` is null or `{kind, clock_ref, period, origin, evidence_ref}`. Kind is
`affine_edge_index` or `unknown`. Period/origin are physical quantities. Cycles
require an evidenced positive constant-period relation and actual edge origin:
time = origin + cycles * period. A gated/variable-period clock requires different
evidence or a separately qualified method, not guessed constant conversion.

`history` has `method`, `available_from` (quantity/null), `evidence_ref`. Methods
are `new_run`, `replay_from_reset`, `existing_trace`, `error_trigger`, `rolling_buffer`.
This wrapper renderer supports scheduled new/reset runs only. Available history
must cover the selected start. Existing-file filtering, triggers and rolling
buffers are not silently invented; an error trigger cannot recover unrecorded past.

`correspondence` has `status` (`matched_selected_observables`, `unknown`,
`diverged`, `not_applicable`) and `evidence_ref`. Unknown replay may be planned,
explicitly labeled unqualified. A supplied matched status retains its scope and
does not authenticate that comparison. Known divergence blocks reproduction;
exploratory intent preserves a branch label instead of claiming reproduction.

`run` has `stop` (quantity), `argv` (literal string array) and `evidence_ref`.
Workload arguments pass unchanged after `--`; the renderer does not validate their
engineering meaning or invent flags. Use the original/native invocation/source.
The supplied example strictly rejects unknown workload and trace options.

## Readiness and preview

`opentools.capture-assessment.v1` retains input/binary digests, exact tick controls,
resolved objects/trace aliases, expected declarations, native additional objects,
replay label, rejections, unknowns, warnings and limits. `dumpvars(1,leaf)` prefix/
depth semantics can include one level beneath an identically named aggregate;
additional declarations are reported, not hidden. Depth zero is never emitted.

Known unsupported selections/capabilities/bounds/history or binary mismatch return
`rejected` (exit 1). Remaining required gaps return `incomplete` (2). Otherwise
`renderable` (0) means trace-command readiness only. It does not establish sufficient
scope, causal history, reproduction, semantic correctness of supplied assertions
or efficiency. Invalid data/I/O returns 3.

`opentools.capture-recipe.v1` contains that assessment, literal `argv`, shell=false,
new waveform path, inclusive-bound semantics and viewer selection/marker instructions.
It emits the supported wrapper contract:

```text
BINARY --capture-vcd FILE --start-tick N --end-tick N --stop-tick N --select LEAF [--select LEAF ...] -- WORKLOAD_ARGS
```

No native command executes during assess/render. File outputs are new/distinct
and separate from inputs/binary/waveform; preview does not create a waveform.
Optional GTKWave save files are written through PyVCD's existing formatter;
no viewer is installed/launched and GUI loading is not qualified. Their selections
affect viewing, while native selector/window arguments affect dumping.
