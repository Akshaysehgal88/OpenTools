# Formal abstraction boundaries

Use this module after changing an abstraction or cutpoint and **before accepting
the resulting property evidence**. It reviews which concrete behaviors remain in
the abstract boundary, which extra behaviors were introduced, and whether a
native failure witness belongs to the concrete relation.

This fits in formal model setup, abstraction refinement and block-to-integration
proof handoff. Formal and design owners can use it alongside their existing
proof engine and abstraction review. It replaces manual relation/witness
reconciliation for the selected finite class; it does not implement a general
formal engine or automatically accept/refine an abstraction.

A green abstract proof can hide excluded concrete behavior. An abstract failure
can also be spurious because the cut admits extra behavior. The original property
and concrete correspondence determine which interpretation applies.

## First review

Saved-data review needs Python 3.10+ and the standard library. Run from
`modules/formal-abstraction-boundaries`. Use a complete retained example at
`.local/abstraction-native`, or generate one on Linux with an existing
**Yosys 0.33, git 2584903a060** prefix:

```sh
python examples/create_example.py .local/abstraction-native --yosys-prefix /path/to/prefix
```

The prefix contains `bin/yosys` and its required runtime libraries. The recipe
installs nothing and executes owned example scripts. Sixteen native runs retain
concrete/abstract models, complete SAT tuples, property outcomes and witnesses.

Review the exact correspondence control:

```sh
python boundary_check.py review .local/abstraction-native/operands-exact/contract.json .local/abstraction-native/operands-exact/evidence.json --json-out .local/abstraction-native/operands-exact/new-review.json --markdown-out .local/abstraction-native/operands-exact/new-review.md
```

Expected exit: **0**, `supported_within_finite_boundary`. The selected concrete
and abstract relations are equal and the independently required property holds.
Open Markdown for the relation/witness interpretation and JSON for original
identities, native outcomes, tuple differences, findings and gaps.

Compare a green abstraction with unsupported correlation:

```sh
python boundary_check.py review .local/abstraction-native/operands-unsupported-green/contract.json .local/abstraction-native/operands-unsupported-green/evidence.json --json-out .local/abstraction-native/operands-unsupported-green/new-review.json --markdown-out .local/abstraction-native/operands-unsupported-green/new-review.md
```

Expected exit: **1**, `review_required`. The abstract property passes, but the
abstract relation excludes a concrete faulty behavior. The native proof color
does not supply correspondence. Other controls include conservative independent
cuts and a restricted allowed-input population.

Outputs must be new. Keep `evidence.json` beside its complete concrete/abstract
directories: review resolves original artifact paths from the evidence file's
parent. Saved-data review works without Yosys and executes no archived script.

## Helper features

| Operation | Contribution |
|---|---|
| `boundary_check.py capture ROOT WORKDIR CONTEXT --output SNAPSHOT` | Imports the original saved Yosys models/logs, actual cut/formal-cell population, complete tuple relation, native property outcome and failure witness. |
| `boundary_check.py review CONTRACT EVIDENCE` | Revalidates originals, compares concrete/abstract relations, checks the independent predicate and interprets the selected native witness against concrete feasibility. |
| `--json-out` / `--markdown-out` | Writes structured and readable reviews; JSON is also printed. |

For example, recapture only the abstract side of the exact control:

```sh
python boundary_check.py capture .local/abstraction-native/operands-exact abstract .local/abstraction-native/operands-exact/abstract-context.json --output .local/abstraction-native/operands-exact/recaptured-abstract.json
```

Capture exits 0 for parsed evidence, including native property FAIL. This produces
one snapshot, not the combined evidence/contract needed for a boundary decision.

## Supply the original claim and boundary

[FORMAT.md](FORMAT.md) and
[capture-context.template.json](capture-context.template.json) define the records.

The independent contract states the review claim, owner, scope, boundary/mode,
ordered unsigned domain, complete allowed rows for the selected property, original
concrete/abstract run/source identities and an obligation for every abstract
assumption. An empty assumption roster is valid only when no assumptions exist.

The combined evidence binds the contract digest and both captured snapshots.
Required sources, commands, dependency completeness and tuple exhaustion must
remain explicit. A complete label without the original enumeration is insufficient.
Unknown substantive sources/requirements remain null, not desired conclusions.

The algorithm computes:

| Relation | Interpretation to review |
|---|---|
| Equal | Selected concrete/abstract tuple populations match. Property evidence still needs its original scope and predicate. |
| Conservative expansion | No concrete tuple is lost, but extra abstract behavior can produce a nonconcrete failure witness. |
| Restrictive subset | Concrete behavior is omitted; a green result cannot cover the missing population. |
| Incomparable | Some concrete behavior is omitted and extra abstract behavior is introduced. |

The core relation algorithm accepts at most twelve total unsigned domain bits.
This is not qualification of arbitrary twelve-bit native designs. Bit order,
width, mode and original predicate are exact; no inferred interface mapping or
unit conversion occurs.

## Integrate into formal review

1. State the original integration/property obligation and selected boundary before
   looking at proof colors. Identify the concrete reference and intended modes.
2. Retain before/after model sources, actual cut construction, assumptions,
   property query, complete relation enumeration and native witnesses.
3. Review every assumption's owner and concrete correspondence basis. Source hashes
   bind a file; they do not establish that a premise is justified.
4. Capture using the qualified native reader or another separately validated
   method. Compare the complete selected boundary and classify native failure
   witnesses against concrete feasibility.
5. Route unsupported restrictions, missing modes or spurious-failure explanations
   to model/design owners. Refine the abstraction in the existing formal tool,
   then regenerate native evidence and revalidate.
6. Hand off original intent, assumption rationale, model artifacts, reports and
   receiving decision. Repeat after abstraction, property, source or mode changes.

Use [REVIEW.md](REVIEW.md) for the owner handoff and follow-up.

## AI-first adoption

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), the original property,
concrete model and abstraction/cut setup:

> Explain what concrete behavior this abstraction must preserve. Inspect the
> actual cuts and assumptions, compare native outcomes with independent boundary
> correspondence, and distinguish a spurious abstract failure from excluded
> concrete behavior. Ask for missing modes, source or completeness evidence.

Use [ONBOARDING.md](../../ONBOARDING.md), module
`formal-abstraction-boundaries` / activity `default`. Your existing AI can review
broader company-native abstractions beyond the supplied helper. Optional DVIT
intent/dependency evidence can connect premises and boundary changes to affected
proof obligations; independent operation requires no connection.

## Results, tests and native boundary

| Review exit | Meaning |
|---:|---|
| 0 | Supported within the selected finite boundary and original predicate. |
| 1 | Known correspondence/property/witness finding; gaps remain visible. |
| 2 | Incomplete or quarantined source, scope or relation evidence. |
| 3 | Invalid record/artifact or I/O. |

Argument errors use exit 2. Reports preserve native property PASS/FAIL independently
of the boundary disposition.

The bundled reader qualifies one stateless flat `top` with two-bit `source`,
`left` and `right`, one assertion and a two-output cut in the exact Yosys profile.
It checks complete exhausted SAT tuples, before/after object identity and original
query/witness consistency. The owned arithmetic/tag reference checks all 202
captured tuples independently.

```sh
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_ABSTRACTION_EXAMPLE` to the retained collection for native artifact
and witness tests on Windows/Linux. Core unit tests use labeled synthetic records.
Sequential/memory refinement, liveness, arbitrary abstraction soundness, other
native formats and signoff require their existing qualified methods.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
