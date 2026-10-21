# Result applicability

Use this module before reusing a saved result for a new configuration, handoff or
engineering claim. It asks whether **the recorded execution and result actually
correspond to the requested question**, preserving the original outcome and
checking retained result-file bytes.

This fits in evidence acceptance across DV, formal, STA, PD and validation.
Result producers and receiving owners can use it alongside native reports.
A test name, commit or PASS label does not identify the executable, generated
inputs, firmware, checker and operating scope consumed by the run.

The activity supplements native verification/signoff methods. It replaces manual
claim-to-manifest/result reconciliation. It does not convert a result into a pass,
prove checker sufficiency or accept a release.

## First use

Python 3.10+ and the standard library suffice. From
`modules/result-applicability`:

```sh
python examples/create_example.py .local/result-first-use
python applicability_check.py compare .local/result-first-use/snapshot.json .local/result-first-use/request.json --json-out .local/result-first-use/review.json --markdown-out .local/result-first-use/review.md
```

Expected exit: **1**, `inapplicable`. The synthetic passing result used
`ECC_EN=0`; the independent request requires `ECC_EN=1`. The original PASS
remains recorded. Open Markdown for the field comparison and JSON for the
original execution/result, request, mismatches, unknowns and artifact integrity.

The example includes a retained result file whose current bytes are rehashed.
A missing/changed file makes result integrity unresolved; it does not establish
a hardware failure. Example/report paths must be new with existing report parents.

## Choose the activity for the decision

| Activity | Workflow stage and question |
|---|---|
| Default | Does this saved execution/result support the requested selected fields and outcome? |
| [Formal assumptions](profiles/formal-assumptions/README.md) | Before proof reuse: are premises owned, guaranteed and activated in the required clock/reset/mode scope? |
| [Equivalence boundary](profiles/equivalence-boundary/README.md) | Before equivalence acceptance: did the native comparison cover the intended designs, point mapping, boundary and modes? |
| [ECO evidence](profiles/eco-evidence/README.md) | After physical ECO: which reports still apply given changed native objects, dependencies, phase and reuse conditions? |
| [Timing scenarios](profiles/timing-scenarios/README.md) | During STA run coverage: do independent required scenarios have corresponding native mode/model/clock/power/RC evidence? |
| [Interface budget](profiles/interface-budget/README.md) | During block/top handoff: do changed allocations, reference edges, loads and models preserve the integrated timing budget? |
| [Erratum/workaround](profiles/erratum-workaround/README.md) | Before applying/removing a workaround: do current underlying conditions, efficacy evidence, premises and approval correspond? |

Each specialized guide describes its native support and evidence limits.
A portable record format does not imply universal commercial-tool compatibility.

## Helper features and records

| Operation | Responsibility |
|---|---|
| `applicability_check.py compare SNAPSHOT REQUEST` | Checks execution/result basis, claim-selected facts and retained result-file integrity, preserving original outcomes and unselected fields. |
| `compare --reuse REVIEWED_RULES` | Applies only existing supplied reuse exceptions bound to the exact run, claim and observed/requested value pair. |
| `inspect-sc MANIFEST --step STEP --index INDEX` | Inventories a qualified SiliconCompiler Project JSON node without loading its package or executing commands. |
| `import-sc MANIFEST --context CONTEXT --output SNAPSHOT` | Imports selected native facts plus digest-bound original execution/checker context. |
| `--json-out` / `--markdown-out` | Saves structured/readable comparisons; Markdown is also printed. |

[FORMAT.md](FORMAT.md) defines the executable records separately from the
[manual review template](record.template.json):

- **Snapshot:** original run/manifest, execution state and command/executable/
  dependency basis, actual checker outcome/completeness/run association, result
  file/hash, and selected source-backed facts.
- **Request:** independent claim/scope, required fields and required outcome:
  `pass`, `fail` or `any_observed`.
- **Optional reuse:** an existing reviewed rule's source, responsible approval
  reference, basis and reason for each exact differing field pair.

Keep implementation/configuration, executable, checker, runtime inputs and claim
scope separate where relevant. Selected facts can be structured JSON; null
anywhere, empty text or missing evidence remains unknown. Values compare exactly:
`false`, `0`, `0.0` and `"0"` are distinct. No enum/path/unit normalization
or cross-company ontology is inferred.

Executed checker FAIL differs from tool execution failure. A failed result can
correspond to an `any_observed` question and remains failed. A valid reuse rule
cannot fill missing facts or exempt execution, completeness, outcome or result
integrity. Approval references are supplied declarations, not authenticated authority.

## Optional SiliconCompiler path

The read-only profile supports **SiliconCompiler 0.38.11, schema 0.57.2 Project
JSON**. Use the original final job/node `.pkg.json` with root execution records.

```sh
python applicability_check.py inspect-sc run.pkg.json --step lint --index 0 --output inventory.json --context-template context.json
```

Before import, complete `context.json` from original run evidence. Keep its
manifest-byte/node binding, select recorded configuration/hashes using inspected
JSON pointers, and supply the original argument list, executable/dependency basis
and actual checker outcome/artifact evidence.

```sh
python applicability_check.py import-sc run.pkg.json --context context.json --output snapshot.json
python applicability_check.py compare snapshot.json request.json
```

The reader does not guess shell tokenization, search history/older jobs or replace
missing original inputs with today's checkout. Node success/exit 0 establishes
completed execution only when the native execution basis is present; it does not
establish a test pass. Partial execution/result import exits 2.

For the optional Linux example, with Verilator 5.020 already available:

```sh
python -m pip install -r requirements-native-example.txt
python examples/create_sc_example.py .local/sc-result-example --verilator verilator
```

This records an `ECC_EN=0` **lint run**, not ECC functional verification.
Other schema/classes, commercial manifests and recursive dependency discovery are
outside the reader; independently validated normalized exports can support the
broader workflow.

## Integrate into evidence handoff

1. State the original receiving claim and its required outcome before selecting
   an available passing report.
2. Identify claim-relevant configuration, source/build/checker, runtime inputs and
   scope. Ask the producer for original consumed-byte evidence and dependency basis.
3. Export/import the snapshot and retain the result artifact. Source request
   values independently from the specification/handoff.
4. Compare. Review known differences, unknown facts, execution versus checker
   status and artifact integrity separately.
5. Use only already reviewed applicable reuse rules. Otherwise obtain matching
   native evidence or route unresolved scope/premises to their owners; do not
   weaken the request to fit the result.
6. Hand off original request, manifest/artifacts, comparison, approved exception
   basis and receiving decision. Revalidate after claim-relevant changes.

The helper cannot determine whether the selected fields fully represent a
free-text claim. Source/intent review remains necessary even for an exact match.

## AI-first adoption and results

Give a file/tool-enabled assistant [SKILL.md](SKILL.md),
[AI_USAGE.md](AI_USAGE.md), original receiving intent and saved native evidence:

> Determine what this result can support for the requested configuration/claim.
> Trace actual execution, consumed inputs, checker and observation scope. Ask for
> missing dependencies or original artifacts, preserve FAIL/unknown evidence and
> identify matching retained results or a justified revalidation step.

Use [ONBOARDING.md](../../ONBOARDING.md), module `result-applicability` /
activity `default` or a specialized activity above. Your existing AI/native
tools suffice. Optional DVIT intent/dependency context can reveal claim-relevant
relationships and stale premises beyond a local manifest; operation is independent.

| Compare status / exit | Meaning |
|---|---|
| `directly_applicable_within_scope` / 0 | Selected facts and declared execution/result basis correspond. |
| `applicable_with_reviewed_reuse` / 0 | The bounded checks correspond under exact supplied reviewed exceptions. |
| `inapplicable` / 1 | Known selected-value or required-outcome difference; unknowns remain. |
| `unresolved` / 2 | No stronger mismatch, but required evidence/capture/integrity is missing. |
| Error / 3 | Invalid data/rules or I/O. |

Argument errors use exit 2. No status proves design correctness, sufficient
checking, authenticity or signoff.

```sh
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_SC_MANIFEST` to the example's final
`build/top/job0/top.pkg.json` and install the pinned package for optional API
cross-checks. Run specialized activity tests in their own folders.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
