# Interaction records

JSON keys are exact and unique. Unknown references use `null` and remain gaps.
Source/owner/review references are declarations, not authenticated authority.

## Independent roster

`opentools.interaction-obligations.v1` has `review_ref`, `claim`, `scope_ref`,
`configuration_ref`, `model_ref`, `owner_ref`, `population_ref`, `population_complete`,
`basis_ref`, `scope_facts`, `runs`, `obligations`. Use [plan.template.json](plan.template.json).

`scope_facts` currently supports `retain: {value: 0|1|null, basis_ref}`. This is the
first Boolean retained-event profile, not a universal mode schema. Every selected
native frame must agree with known facts. Other flows can be reviewed through the
AI workflow using separately validated semantic exports.

Each requested run has `run_ref`, `scope_ref`, `configuration_ref`, `model_ref`,
`scenario_ref`, `clock_ref`, `reset_ref`, `reset_active`, `port_map`, `sources`,
`command_sha256`. Obtain these from original build/execution evidence independently
of the imported receipt. `sources` maps `top.sv`, `ports.hpp`, `main.cpp` to hashes.

Each obligation has:

- `id`, `title`, `definition_ref`, `owner_ref`.
- `relationship`: `resource_ref`, `producer_ref`, `consumer_ref`, `risk_ref`,
  `source_ref`, `revision_ref`, `design_source_sha256`, `configuration_ref`.
  Design/configuration bindings must match selected native evidence; stale
  relationships are quarantined. Correct hashes do not prove the risk interpretation.
- `applicability`: `status` (`applicable`, `not_applicable`, `unknown`), `facts`,
  `basis_ref`, `reviewer_ref`, `reason`. Nonapplicability needs explicit matching
  scope facts and a sourced review; lack of activity cannot supply it.
- `trigger`: conjunction of `{field, offset, equals}` terms. Offset is `0` or `-1`;
  value is Boolean 0/1. Fields are frame values below, excluding tick/clock/enable.
  These terms locate existing combined occurrences, not synthesize assertions/tests.
- `after`: 0..64 sampled edges following each trigger; every selected occurrence
  needs its full span. Initialization reset inside the span leaves it unresolved.
- `checkers`: `{id, observed, basis_ref}`, where `observed` is `post_pending` or
  `post_visible`. Actual actions must bind those native values throughout the span.

An empty/all-nonapplicable roster cannot establish closure. Agreeing records can
still omit a real obligation; the AI must compare with original source intent.

## Corpus and native receipt

`opentools.interaction-evidence-corpus.v1` has `complete`, `evidence_ref`, and
`runs: [{path, sha256}]`. Paths are relative POSIX paths to native receipt JSON
inside the corpus directory. Each receipt's evidence is relative to its own parent.
Use [corpus.template.json](corpus.template.json); capture prints the new receipt's
byte SHA-256 as `receipt_sha256` for each entry.
Preserve original run IDs when copying or joining retained evidence.

`opentools.interaction-capture-context.v1` uses
[capture-context.template.json](capture-context.template.json). It selects the
original run/scenario, clock/reset and eight distinct native port roles. Scope,
instrumentation, oracle and dependency bases remain supplied. Missing bases block
qualified attribution.

The data-only reader supports Verilator 5.020, one flat top and one positive clock.
Mapped ports are scalar; additional ports remain in the inventory and need their
original configuration evidence when relevant. Fixture bug controls are not
required roles. Initialization reset is distinct from the consumer `hold` used for
reset/sleep transitions. Global initialization can invalidate a required window.

Retain `top.sv`, `ports.hpp`, `main.cpp`, `model.xml`, original Linux `Vtop`,
`version.txt`, build/XML command JSON and stdout/stderr, run command JSON and
stdout/stderr, and `execution.json` (`build_exit`, `xml_exit`, `run_exit`,
`binary_sha256`). The recipe in [examples/run_native.py](examples/run_native.py)
defines exact supported build/XML commands. Review rehashes and recaptures all
critical files without executing imported commands.

The native journal contains:

```text
FRAME tick reset hold event ack retain pre_pending pre_visible post_pending post_visible enabled pre_clock post_clock
CHECK tick checker_id expected observed ok
RESULT frames checks failures
```

Frames are contiguous from zero, Boolean, sampled before/after clock 0→1. CHECK
belongs to the preceding frame, has unique tick/ID and a consistent comparison
action. RESULT agrees with the full journal and execution exit 0/1. Instrumentation
and expected-state/delivery meaning require source review; the reader does not
attest arbitrary C++ or prove oracle adequacy. Native connection mechanics follow
the [Verilator model interface](https://verilator.org/guide/latest/connecting.html);
actual 5.020 artifacts define support, not the current manual's release.

## Output

`opentools.interaction-obligation-review.v1` preserves the roster's applicability,
native run outcomes, trigger/checker windows, findings and gaps. Per-row
`observed_failure` includes native mismatches or invalid required checking, such
as disabled checkers; inspect witness details before making a hardware conclusion.
A failure remains visible even if another selected window passes. Original native
PASS/FAIL is never rewritten.

The existing campaign summarizer unions explicit named passing obligations.
Nonapplicable rows remain in the population; required IDs reflect the reviewed
scope. No Cartesian product is generated. Missing timestamps, scope or population
remain explicit; named attainment does not establish whole-campaign completion,
oracle adequacy, unbounded liveness, physical reset behavior or signoff.
