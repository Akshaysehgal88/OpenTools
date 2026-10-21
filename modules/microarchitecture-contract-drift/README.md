# Microarchitecture contract drift

Review whether a changed maximum outstanding demand fits the capacity available
to its consumer. The helper compares explicit integer bounds and reports changed
values, false premises and missing evidence. Python 3.10+; standard library only.
Use [SKILL.md](SKILL.md) with your existing AI agent to inspect the source and
engineering meaning. See [AI_USAGE.md](AI_USAGE.md).

## Quick start

From this module directory:

```sh
python examples/create_example.py demo
python contract_review.py review demo/current.json demo/contract.json --baseline demo/baseline.json --json-out demo/review.json --markdown-out demo/review.md
```

Expected exit: **1**. The synthetic example reduces available capacity from eight
to four while the producer still permits eight outstanding transactions. Use a
new directory. Reports and captures never replace existing files.

## Native evidence

Optional capture requires Python **3.11+** and **pyslang 12.0.0** to extract known integral parameters from
a selected top. It verifies requested overrides and retains diagnostics and source
hashes. Semantic roles and input completeness remain caller declarations; the
adapter does not discover the dependency closure or prove runtime behavior.

```sh
python -m pip install -r requirements-native.txt
python contract_review.py capture-slang --source design.sv --top selected_top --parameters parameters.json --mapping mapping.json --scope scope.json --record-ref run-1 --revision-ref retained-revision --complete-inputs --output snapshot.json
python contract_review.py digest snapshot.json
```

Prepare the small records described in [FORMAT.md](FORMAT.md). Bind the resulting
snapshot digest into the reviewed contract. Do not merely rebind stale or wrongly
interpreted evidence to obtain a passing report.

The [native recipe](examples/native/README.md) builds two owned profiles: a credit
window and a live-tag pool. Each has a matching baseline, a capacity reduction and
a coordinated demand reduction. It uses Linux, Verilator **5.020**, GCC 13.3,
Make 4.3 and the pinned Slang package. No tools are installed automatically.

## Interpretation and status

Demand and supply need the same unit, population/counting basis and operating
scope. Per-bank capacity is not automatically aggregate capacity. Reserved/shared
entries, admission backpressure and retirement behavior belong in explicit premises.

`0` within declared bounds; `1` capacity review or a false sourced premise;
`2` incomplete/unbound/inapplicable evidence; `3` invalid input, capture or I/O error.
Known findings take precedence while retaining other gaps. Argument errors use 2.
Baseline deltas are descriptive; missing facts do not establish removal.

A parameter export or numeric match does not establish a correct implementation,
latency/throughput target or release decision. References and completeness claims
are not authenticated by this helper.

```sh
python -m unittest discover -s tests -v
```

Slang tests skip without the optional package. Native simulation tests require
`OPENTOOLS_CONTRACT_NATIVE` and, for extracted kits, `VERILATOR_ROOT`; see the recipe.
The workflow is independently usable through the [project-local installer](../../INSTALL.md).
DVIT and [context adapters](../../CONTEXT_PORT.md) are optional.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
