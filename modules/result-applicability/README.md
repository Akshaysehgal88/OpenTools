# Result applicability

Check whether a saved result supports a requested configuration and claim.
The comparator preserves the original outcome, checks claim-relevant fields and
verifies retained result-file bytes. Requires Python 3.10+ and the standard library.
Use [SKILL.md](SKILL.md) for the AI workflow; see [AI_USAGE.md](AI_USAGE.md).

## Quick start

From the repository root:

```sh
python modules/result-applicability/examples/create_example.py .local/result-example
python modules/result-applicability/applicability_check.py compare .local/result-example/snapshot.json .local/result-example/request.json --json-out .local/result-audit.json --markdown-out .local/result-audit.md
```

Expected exit: **1**. The synthetic result used `ECC_EN=0`; the request requires
`ECC_EN=1`. The original pass stays recorded. Examples and outputs require new paths.

Select fields relevant to the claim: configuration, executable, checker, runtime
inputs and scope. Add `--reuse reviewed-reuse.json` only for an existing approved
rule bound to the run, claim and exact value pair. The utility does not authenticate
approvals. A rule cannot replace missing evidence or bypass result integrity.

## SiliconCompiler import

The read-only profile supports **SiliconCompiler 0.38.11, schema 0.57.2 Project
JSON** without loading SiliconCompiler. Use an original final job/node `.pkg.json`
with the selected node's root execution records.

```sh
python modules/result-applicability/applicability_check.py inspect-sc run.pkg.json --step lint --index 0 --output inventory.json --context-template context.json
python modules/result-applicability/applicability_check.py import-sc run.pkg.json --context context.json --output snapshot.json
python modules/result-applicability/applicability_check.py compare snapshot.json request.json
```

Fill the context from original run evidence between inspection and import. It binds
the manifest bytes and node. Select recorded hashes/configuration with JSON pointers;
do not substitute today's checkout for the inputs consumed by the run.

Native success and exit 0 can establish completed tool execution, not a test pass,
complete dependencies or sufficient checking. Missing records stay unknown. The
reader does not search `history`, fall back to older jobs or support other schema
versions/classes. Import returns 2 for partial execution/result evidence.

An optional Linux example uses SiliconCompiler 0.38.11 and Verilator 5.020:

```sh
python -m pip install -r modules/result-applicability/requirements-native-example.txt
python modules/result-applicability/examples/create_sc_example.py .local/sc-result-example --verilator verilator
```

It records an `ECC_EN=0` lint run, not ECC functional verification.

## Formal premise review

Use the [formal assumptions profile](profiles/formal-assumptions/README.md) before
using a proof in an integration claim. It reviews assumption ownership, producer
guarantees and required activation under matching clock/reset/mode scope. Its
optional saved-SBY reader distinguishes induction, BMC, counterexamples and
bounded cover attempts; it executes no imported configurations.

## Equivalence/ECO review

Use the [equivalence comparison profile](profiles/equivalence-boundary/README.md)
before accepting or reusing a native equivalence result. It reviews the compared
designs, approved point mapping, model boundary and required modes. The optional
saved-Yosys reader preserves native PASS/FAIL and counterexamples; it neither
matches points automatically nor approves an ECO.

## Interface timing budget handoff

Use the [interface budget profile](profiles/interface-budget/README.md) after
block-to-top allocations, reference edges, loads or models change. It compares
both block assumptions with the integrated path and preserves timing debt,
missing premises and budget ownership.

## Status and tests

For STA scenario planning and run-coverage review, use the
[timing scenario profile](profiles/timing-scenarios/README.md). It reconciles an
independent obligation roster with actual model, mode, clock, power and RC evidence,
and composes this comparator per scenario. Required analysis and observed timing
failures remain separate; counts and sampled clean paths do not establish signoff.

For report reuse after a physical ECO, use the
[ECO evidence profile](profiles/eco-evidence/README.md). It reviews native changed
objects, report dependencies, operating phases and supplied reuse conditions,
and locates matching current results already retained.

`0` applicable within scope or supplied reviewed reuse; `1` known mismatch;
`2` unresolved; `3` invalid input/I/O. Mismatches take precedence while retaining
unknowns. Argument errors use exit 2. A failed result can correspond to an
`any_observed` request and remains failed. Applicability does not prove checker
sufficiency or design correctness.

```sh
python -m unittest discover -s modules/result-applicability/tests -v
```

Set `OPENTOOLS_SC_MANIFEST` to the native example's final
`build/top/job0/top.pkg.json` and install the pinned package to enable API cross-checks.
See [FORMAT.md](FORMAT.md); the [manual template](record.template.json) and
[manual example](example.json) are separate review formats.

## Erratum and workaround maintenance

Use the [erratum/workaround profile](profiles/erratum-workaround/README.md) before
applying, removing or carrying forward a supplied workaround. It keeps underlying
conditions, observed efficacy, dependent premises and current approval evidence
separate. The native example qualifies a synthetic notice and owned model only.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
