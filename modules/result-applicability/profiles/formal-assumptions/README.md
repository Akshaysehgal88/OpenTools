# Formal assumption applicability

Use this activity before carrying a proof into an integration claim. It reviews
**the actual premises, their owners and producer support**, matching clock/reset/
mode scope, and a witness that the required activation is reached.

This fits in formal setup, assume/guarantee handoff and proof reuse after environment
or mode changes. Formal, design and integration owners can use it alongside their
native engine. A green property under an activation-excluding premise does not
answer the original integration question.

The review supplements native proof/cover evidence and assumption ownership.
It replaces manual reconciliation of the selected premise population, producer
guarantees and activation. It does not automatically remove assumptions, certify
composition or accept a proof.

## First use

Saved-data review needs Python 3.10+ and the standard library. Run from
`modules/result-applicability/profiles/formal-assumptions`. Use a complete
retained collection at `.local/formal-native`, or generate one on Linux with the
pinned tools in [NATIVE.md](NATIVE.md):

```sh
python examples/create_example.py .local/formal-native --sby /path/to/sby/sbysrc/sby.py --yosys-prefix /path/to/prefix
```

Qualification uses SBY revision `85dd50b92a3acf170954a06f20f49e2162ce5273`
(tag `yosys-0.33`), Yosys 0.33 git `2584903a060` and Z3 4.8.12 64-bit.
The prefix includes `bin/yosys`, `bin/yosys-smtbmc`, `bin/z3`, `share/yosys`
and required runtime support. The recipe installs nothing and needs a new output.

Review a source-supported hold premise and separate producer proof:

```sh
python formal_review.py review .local/formal-native/wake-guaranteed/scope.json .local/formal-native/wake-guaranteed/evidence.json --json-out .local/formal-native/wake-guaranteed/new-review.json --markdown-out .local/formal-native/wake-guaranteed/new-review.md
```

Expected exit: **0**, supported within the declared logical model.
The report retains consumer proof, activation witness and producer support
separately, with original native outcomes and source/scope correspondence.

Compare an activation-excluding setup:

```sh
python formal_review.py review .local/formal-native/wake-excluded/scope.json .local/formal-native/wake-excluded/evidence.json --json-out .local/formal-native/wake-excluded/new-review.json --markdown-out .local/formal-native/wake-excluded/new-review.md
```

Expected exit: **2**, incomplete despite a green consumer proof: required
activation/support is not established. `wake-unrestricted` exposes a matched
counterexample (exit 1). `wake-shallow-cover` has no activation witness within
its one-state attempt, and `wake-short-bmc` is a bounded pass, not unbounded safety.

Outputs must be new. Keep each `evidence.json` beside its complete proof, cover
and producer directories; review resolves original paths from the evidence
file's parent. Source scripts and commands are read as data, never executed.

## Helper and record features

| Operation | Responsibility |
|---|---|
| `formal_review.py capture ROOT WORKDIR CONTEXT --output SNAPSHOT` | Imports one original saved SBY task, checking status/log consistency, prepared cell census, sources and required native witnesses. |
| `formal_review.py review SCOPE EVIDENCE` | Reimports critical artifacts, checks source/model/scope/run bindings through the parent comparator, and reviews every mapped assumption, guarantee and activation requirement. |
| `--json-out` / `--markdown-out` | Saves structured/readable handoff reports; JSON is also printed. |

To inspect the proof side alone:

```sh
python formal_review.py capture .local/formal-native/wake-guaranteed proof .local/formal-native/wake-guaranteed/proof-context.json --output .local/formal-native/wake-guaranteed/recaptured-proof.json
```

Capture exit 0 means a completed parsed observation, including native FAIL;
unknown execution returns 2. A snapshot alone is not an assumption-applicability
decision.

[FORMAT.md](FORMAT.md) and
[capture-context.template.json](capture-context.template.json) define the inputs:

- **Scope:** original claim/owner, consumer source/top/formal-cell population,
  property/activation references, clock/reset/integration-mode/model scope and
  one ownership/condition/support mapping for every native assumption.
- **Guarantees:** independent producer source/top/cells, matched clock/reset/mode,
  condition/owner and port-binding basis. The assistant must inspect predicate/
  port correspondence; matching labels alone cannot establish it.
- **Evidence:** exact scope digest and embedded proof/cover/producer snapshots,
  each tied to expected original run identities and critical-file receipts.

Unknown sources, owners, population or scope remain gaps. An empty map cannot
hide actual native assumptions. Supplied references are not authenticated authority.

## Integrate into formal handoff

1. State the original integration/property question and required activation before
   selecting green proof output.
2. Inventory actual native assert/assume/cover cells and consumed source/setup.
   Identify the owner and source meaning of each premise.
3. Obtain relevant producer support in the matching logical clock/reset/mode.
   Inspect connection/predicate correspondence with the integration owner.
4. Retain consumer proof and activation cover evidence, distinguishing induction,
   BMC, counterexamples and not-reached-within-depth.
5. Review and route unsupported premises, missing activation or scope differences
   to their owners. Correct the original setup/source, rerun and revalidate.
6. Hand off scope rationale, original artifacts, report, remaining conditions and
   receiving decision. Repeat after premise, producer, mode or property changes.

A bounded cover FAIL means no witness was reached in that attempt. It is not a
general unreachable-state proof. A short BMC PASS does not establish unbounded
safety. Native UNKNOWN/ERROR does not establish a design failure.

## AI-first adoption and outcomes

Give a file/tool-enabled assistant [WORKFLOW.md](WORKFLOW.md), original property,
formal setup and producer/interface sources:

> Review every actual premise against its owner and producer support. Match
> clock/reset/mode and predicate/port meanings, and establish the required
> activation witness. Preserve conditional proof, bounded pass, counterexample
> and missing activation as distinct evidence.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module `result-applicability` /
activity `formal-assumptions`. Existing AI and formal flows suffice.
[REVIEW.md](REVIEW.md) records handoff actions. Optional DVIT intent/dependency
context can expose unsupported or stale environment premises; independent use
requires no provider SDK or DVIT connection.

| Review exit | Meaning |
|---:|---|
| 0 | Supported within the declared logical model. |
| 1 | Known review finding or matched counterexample; gaps remain. |
| 2 | Incomplete/unqualified/quarantined evidence. |
| 3 | Invalid record/artifact or I/O. |

Argument errors use exit 2. Exact native qualification covers one prepared flat
module, one consumer assert/cover pair and explicit assumptions; producer tasks
have one assert and no assume/cover. Other scripts, properties, hierarchy,
multiclock, engines or native formats need another validated method.

The owned wake and stream examples retain eighteen tasks/eight review bundles.
Independent finite-state/witness checks qualify their logical models, not real
protocols, physical clocks/resets, liveness, property sufficiency or whole-system
composition/signoff.

Set `OPENTOOLS_FORMAL_EXAMPLE` to the retained collection and run:

```sh
python -m unittest discover -s tests -v
```

Saved-native tests run on Windows/Linux without a solver. Other parser fixtures
are synthetic and do not claim native execution.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
