# Equivalence comparison boundary

Use this activity before accepting or reusing a native equivalence result for an
ECO. It checks whether the **intended designs, approved point correspondence,
model boundary and required functional modes** match what the engine compared.

This fits in equivalence/ECO handoff between design, formal and receiving
integration owners. It supplements the equivalence engine and existing mapping
review. It replaces manual reconciliation of selected native comparison scope
with the independent ECO request; it does not discover matching points or approve
an ECO.

A mode-0 PASS cannot establish a mode-1 requirement. Conversely, a mode-1
counterexample cannot decide equivalence for a mode-0-only question. The review
preserves the original native verdict and interprets its scope separately.

## First use

Saved-data review needs Python 3.10+ and the standard library. Run from
`modules/result-applicability/profiles/equivalence-boundary`. Use a complete
retained collection at `.local/equivalence-native`, or generate it on Linux with
existing **Yosys 0.33, git 2584903a060**:

```sh
python examples/create_example.py .local/equivalence-native --yosys-prefix /path/to/prefix
```

The prefix contains `bin/yosys` and matching runtime libraries. The recipe installs
nothing and needs a new output. Ten native tasks support fourteen reviews across
arithmetic and pending/IRQ contexts, including 8- and 32-bit format selections.

Capture and review an all-mode rewrite:

```sh
python equivalence_review.py capture .local/equivalence-native/arithmetic-rewrite-all-modes run .local/equivalence-native/arithmetic-rewrite-all-modes/capture-context.json --output .local/equivalence-native/arithmetic-rewrite-all-modes/recaptured.json
python equivalence_review.py review .local/equivalence-native/arithmetic-rewrite-all-modes/intent.json .local/equivalence-native/arithmetic-rewrite-all-modes/recaptured.json --json-out .local/equivalence-native/arithmetic-rewrite-all-modes/new-review.json --markdown-out .local/equivalence-native/arithmetic-rewrite-all-modes/new-review.md
```

Expected review exit: **0**,
`native_result_supports_declared_equivalence_scope`. Open Markdown for the
scope disposition and JSON for parent correspondence, native observation,
findings, gaps and input identities.

Compare a mode-restricted green result against an all-mode request:

```sh
python equivalence_review.py review .local/equivalence-native/arithmetic-hidden-functional-change/intent.json .local/equivalence-native/arithmetic-hidden-functional-change/snapshot.json --json-out .local/equivalence-native/arithmetic-hidden-functional-change/new-review.json --markdown-out .local/equivalence-native/arithmetic-hidden-functional-change/new-review.md
```

Expected exit: **1**, `review_required`. Native mode-0 equivalence does not
cover the independently required mode-1 behavior. The
`arithmetic-legitimate-mode0` control accepts the explicitly narrow claim,
while `arithmetic-outside-requested-mode` returns **2** because its native
failure witness is outside the requested mode.

Use new outputs. Keep each receipt beside its complete `run/` directory; review
resolves artifact paths from the snapshot's parent. Capture exit 0 means valid
import, including native FAIL, not equivalence acceptance.

## Helper and required records

| Operation | Contribution |
|---|---|
| `equivalence_review.py capture ROOT WORKDIR CONTEXT --output SNAPSHOT` | Reads original sources, resolved parameters, explicit common-input/output comparison, restrictions, native SAT outcome and counterexample. It executes no imported script. |
| `equivalence_review.py review INTENT SNAPSHOT` | Revalidates original artifacts, compares expected design/mapping/boundary/engine/partition facts and interprets required modes and native witness. |
| `--json-out` / `--markdown-out` | Saves structured/readable handoff reports; JSON is also printed. |

Use [capture-context.template.json](capture-context.template.json) for original
run/manifest/ECO identity, explicit scalar mode input and scope/dependency basis.
Use [intent.template.json](intent.template.json) for the independent ECO request.

Intent must contain original expected:

- Gold/gate source, resolved parameter and netlist identities.
- Reviewed common-input and exposed native output-point correspondence.
- Defined two-state combinational model boundary and whole-miter proof scope.
- Engine profile, compared outputs and excluded-point population.
- Selected mode input, required modes and original mode rationale.
- Mapping review status, existing responsible reviewer and source basis.

The helper checks supplied correspondence, not the authority of approval
references. Proposed/unknown mapping or missing evidence stays open. Do not copy
available native restrictions into the request to make the result fit.

[FORMAT.md](FORMAT.md) defines exact JSON; [NATIVE.md](NATIVE.md) lists the
original sources, scripts, models, logs, command/execution and required native
FAIL witness. Changed/missing/foreign artifacts cannot support current attribution.

## Integrate into equivalence/ECO review

1. Establish the original ECO intent and required functional modes with the
   receiving owner before selecting a passing result.
2. Retain the actual reference/implementation sources, parameter selections,
   approved mapping and native model boundary.
3. Inspect engine setup for input restrictions, excluded points, partitions and
   state/memory/blackbox/reset treatment.
4. Import and review against independent intent. Keep native PASS/FAIL separate
   from scope correspondence; inspect the counterexample's actual input mode.
5. Correct the original comparison setup, implementation or sourced requirement,
   then rerun the native engine and revalidate.
6. Hand off original ECO request, accepted mapping basis, native artifacts, report
   and receiving decision. Repeat after source, point-map, parameter or mode changes.

A failure outside the request does not prove the requested region equivalent;
it leaves the question unresolved. A passing restricted result cannot establish
omitted modes.

## AI-first adoption and outcomes

Give a file/tool-enabled assistant [WORKFLOW.md](WORKFLOW.md), original ECO
request, approved mapping and native evidence:

> Reconcile what the engine compared with what this ECO must preserve. Inspect
> actual source/parameters, compared points, model boundary and mode restrictions.
> Interpret native counterexamples within the requested scope, and ask for missing
> mapping authority or native evidence rather than broadening a result's meaning.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module `result-applicability` /
activity `equivalence-boundary`. Existing AI/native tools suffice. Optional DVIT
intent/dependency context can connect comparison boundaries and mode changes to
affected obligations; independent operation requires no connection.

| Review exit | Meaning |
|---:|---|
| 0 | Native result supports the declared equivalence scope. |
| 1 | Known scope difference or in-scope counterexample; gaps remain. |
| 2 | Missing/unqualified evidence or outside-request witness. |
| 3 | Invalid record/artifact or I/O. |

Argument errors use exit 2. The supplied reader qualifies defined unsigned,
stateless combinational `miter -equiv`/SAT in the pinned Yosys version: ordinary
1–32-bit ports, bounded explicit parameter selection and one whole-miter aggregate.
It validates actual comparator/trigger wiring and rejects unsupported state,
memories, blackboxes, cycles or native cells.

Sequential initialization, retiming, temporal reset, memory abstraction,
four-state equivalence and multi-partition EQY/commercial flows need separately
qualified methods. Finite example references qualify small controls; they never
replace the native engine verdict. Synthetic mapping approvals are fixture data.

Set `OPENTOOLS_EQUIVALENCE_EXAMPLE` to the retained collection and run:

```sh
python -m unittest discover -s tests -v
```

Saved-native tests need no solver. The broader AI workflow can review your
company-native evidence with its own stated support boundary.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
