# Cost accounting executable formats

UTF-8 JSON. Duplicate keys, nonfinite numeric values, invalid shapes and unexpected
fields fail rather than silently selecting a convenient value. The manual
`record_type` template is separate. [The generator](examples/create_example.py)
provides complete executable examples.

## Run: `opentools.cost-run.v1`

Required root keys: `format`, `run_ref`, `task`, `window`, `completion`,
`collection`, `phases`, `resources`, `simulation_progress`, `context`. Optional
`provenance` retains source-specific information without changing accounting rules.

`window` has `start_s`, `end_s`, `basis`, `clock_ref`, `scope_ref`, `evidence_ref`.
Boundaries are finite numeric seconds relative to one declared origin, or null.
Basis is `measured`, `estimated` or `unknown`. References are nonempty strings or
null. A measured wall budget requires both sourced measured bounds and known
clock/scope. End before start is invalid. A zero window is retained, without a
percentage or positive-wall rate denominator.

`completion` has `outcome` (`completed`, `failed`, `running`, `unknown`),
`required_evidence_complete` (boolean/null), `evidence_ref`. This concerns the
selected task, not universal hardware correctness. A completed failure-reproduction
task may produce its required failure report; preserve that native outcome in its
original artifact/provenance. Failed/truncated invocations must not be normalized
into completed tasks merely to make cost comparisons succeed.

`collection` has `complete` (boolean/null), `evidence_ref`. It declares the phase
population captured for this selected window. The helper does not establish
capture completeness. A known outer window with incomplete markers is still
useful elapsed evidence; its stage attribution remains partial.

## Phases and budget

Each phase has exactly `id`, `stage`, `accounting`, `start_s`, `end_s`, `basis`,
`evidence_ref`. IDs are unique. Stages are local nonempty names; no universal stage
ontology is imposed. `accounting` is `stage` or `overlay`. Boundaries use the same
seconds/origin/clock as the window. Normalize another clock explicitly with its
evidence before using it here.

Measured, sourced intervals are clipped to the window, retaining a note when
clipping occurs. Unknown/estimated/unsourced stages remain unqualified; their
duration is not guessed. The timeline partitions at measured interval endpoints:

- One active stage: `stage:<name>`; concurrent instances of that stage count once.
- Several stages: `shared:<canonical JSON array of names>`; the interval is counted
  once as shared, not assigned in full to each stage.
- No measured stage: `unallocated`; it is not automatically idle or waste.

Shared labels encode the actual set, so company stage names containing `+` cannot
collapse distinct overlap groups. Each segment retains phase IDs, overlays and
sources. Bucket durations conserve the selected measured wall window.

Overlays such as tracing are unioned separately by stage name. They never fill a
stage gap or add to the wall budget. An overlay duration can describe when dumping
was enabled; it does not establish exclusive I/O time or the speedup from disabling it.

## Separate measurements

Every resource has `id`, `kind`, `value`, `unit`, `definition_ref`, `scope_ref`,
`basis`, `evidence_ref`. IDs are unique. Value is nonnegative finite numeric/null.
Kinds are `cpu_time`, `elapsed_time`, `peak_memory`, `byte_count`, `engineer_effort`.
Definitions distinguish, for example, user CPU from system CPU or logical trace
file size from device bytes written. Inclusive observations, different scopes and
memory peaks are not automatically summed.

Recognized time units: fs, ps, ns, us, ms, s, min, h. Recognized byte units: B, kB,
MB, GB, KiB, MiB, GiB. Unknown unit strings remain unqualified rather than guessed.
Measured values with known definition/scope/source normalize to seconds or bytes;
estimated/unknown measurements remain retained without measured normalization.
CPU may exceed elapsed wall time under parallel work. Engineer effort is separate
from run time. Absent CPU or memory observations do not become zero.

`simulation_progress` has `amount`, `unit`, `definition_ref`, `scope_ref`, `basis`,
`evidence_ref`. Units are cycles or a recognized simulated-time unit; cycles are
nonnegative integers. The definition identifies the counted clock/phase or time
basis. A measured positive-wall rate requires the same scope as the window and
a known definition/source. Zero progress remains zero without proving a hang.
Progress/window scope mismatch or missing definition leaves the rate unknown.

Raw measurements and references remain in the report. Computed values are decimal
strings, generally using 40-digit Decimal working precision; wide counter identity
is retained before rate rounding. These digits are arithmetic precision, not a
claim about timestamp/sampler accuracy.

## Context and comparison contract

`context` contains exactly these five distinct fields, each
`{"value": "reference-or-null", "evidence_ref": "source-or-null"}`:
`configuration_ref`, `workload_ref`, `instrumentation_ref`, `tool_ref`,
`evidence_scope_ref`. Configuration includes material execution settings when
relevant; workload and required evidence scope remain separate.

`opentools.cost-comparison.v1` has `format`, `baseline_run_ref`, `current_run_ref`,
`question`, `roles`. Each of the five context fields needs a rule with `role`
(`fixed`/`intended`), `reason`, `evidence_ref`. Run bindings must match. Missing
references remain unknown even when both are null. Fixed differences are
confounders; intended differences remain explicit. Window scopes must correspond.
Successful task completion with required evidence needs a supplied source on both
sides. These declarations are inspectable assumptions, not authenticated truth.

Statuses:

| Report | Status | Exit |
|---|---|---|
| Analysis | accounted_window | 0 |
| Analysis | partial_accounting | 2 |
| Comparison | comparable_window_observation | 0 |
| Comparison | descriptive_difference | 0 |
| Comparison | confounded | 1 |
| Comparison | incomplete | 2 |

Intended configuration/workload/evidence-scope changes, or different measured
progress amounts/definitions, produce a descriptive difference rather than a
same-work benefit. Instrumentation can be the intended variable while required
evidence scope stays fixed. Confounders take exit/status precedence over missing
basis; both lists are retained. A numeric wall delta remains reported when both
measured windows exist, even if unqualified. Percentage requires a positive
baseline window. Rate ratios require matching measured amount and definition;
unknown progress does not prevent an otherwise bounded elapsed observation.

Partial stage attribution remains in each comparison's embedded audit. Matching
declared context alone does not establish causal improvement, equal verification
quality, resource savings, total workflow savings or financial benefit. A policy
must reflect the actual question; making all differences intended cannot prove a
different original claim. Exact repeated records are flagged as `same_input_record`.

Reports are `opentools.cost-audit.v1` or
`opentools.cost-comparison-report.v1`. Output files are new/distinct and must have
existing parents. Invalid input/I/O is exit 3; argument syntax errors use argparse's
exit 2. Analysis/import exit 0 is not an engineering pass/acceptance decision.

## SiliconCompiler JSON reader

Profile: `SiliconCompiler.0.38.11.schema-0.57.2.cost.v1`. JSON Project files only;
no schema classes, dataroots, commands or network calls are loaded. Root explicit
node records are inventoried; defaults and history are not substituted. Other
known producer/schema versions are unqualified. Missing producer identity leaves
its timing/measurements unqualified rather than assuming compatibility.

The native template is `opentools.sc-cost-context.v1`, with keys `format`,
`manifest_sha256`, `run_ref`, `task`, `clock_ref`, `clock_evidence_ref`, `scope_ref`,
`nodes`, `collection`, `completion`, `context`. Node selections have `step`,
`index`, `stage`, `accounting`; duplicate selections fail. Default stage labels
retain native step/index without guessing simulation/boot semantics.

The exact manifest bytes are bound. Start/end use the producer's UTC timestamp
format and retain raw source records in provenance. A common clock basis is
caller-supplied; UTC labels alone do not establish clock coherence across hosts.
The origin is the earliest selected known timestamp. Total bounds exist only when
all selected starts/ends are present. A missing node/boundary remains unknown.
The selected-node window excludes outer queue, preparation, collection and human
review unless separately measured in a normalized record.

Native status/exit/times establish completed or failed invocation as supported.
Context completion has only `required_evidence_complete` and `evidence_ref`; it
cannot override native outcome. Native success never manufactures complete
verification evidence or simulation progress.

`exetime`, `tasktime`, `totaltime`, `memory` retain their explicit native units and
definitions. The first three are separate elapsed observations; none becomes CPU
time or a new disjoint stage. In the pinned source `tool.py`, exetime is recorded
using `time.time()` subtraction. The native total uses recorded node interval
aggregation; do not add it to task/execute time or assume it is the full external
workflow window. Missing native units are not inferred from names.

Reference: [SiliconCompiler data model](https://docs.siliconcompiler.com/en/latest/user_guide/data_model.html).
