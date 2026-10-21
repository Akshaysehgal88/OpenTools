# Incremental regression

Use this module to choose an explainable **first verification stage** after a
change, while retaining the complete applicable test population and later
obligations. It also reviews actual targeted/full feedback so a smaller first
stage does not silently become a claim of complete verification.

This fits between change/dependency review and your existing regression runner,
then again when results return. DV infrastructure, feature and integration owners
can use it to shorten feedback latency without losing mandatory tests, deferred
work or observed failures.

It supplements the test manifest, dependency analysis, policy and scheduler.
It replaces ad hoc selected-test lists and manual targeted/full reconciliation.
The helper does not infer dependencies from paths, dispatch jobs or learn a graph.

## First use

Python 3.10+ and the standard library suffice. From
`modules/incremental-regression`:

```sh
python examples/create_example.py .local/regression-first-use
python regression_select.py plan --universe .local/regression-first-use/universe.json --changes .local/regression-first-use/changes.json --mapping .local/regression-first-use/mapping.json --policy .local/regression-first-use/policy.json --output .local/regression-first-use/selection.json
python regression_select.py review --universe .local/regression-first-use/universe.json --changes .local/regression-first-use/changes.json --mapping .local/regression-first-use/mapping.json --policy .local/regression-first-use/policy.json --results .local/regression-first-use/targeted-results.json --output .local/regression-first-use/targeted-review.json
python regression_select.py review --universe .local/regression-first-use/universe.json --changes .local/regression-first-use/changes.json --mapping .local/regression-first-use/mapping.json --policy .local/regression-first-use/policy.json --results .local/regression-first-use/targeted-results.json --full-results .local/regression-first-use/full-results.json --output .local/regression-first-use/full-review.json
```

The plan and targeted review exit **0**. The synthetic first stage selects
`soc_smoke`, `dma_directed` and mandatory `fabric_integration`. `soc_stress`
remains required and deferred to the declared later stage.

The final command exits **1**: full results expose a stress failure outside the
selection. No jobs were executed by this example. Open the JSON files to inspect
selection reasons, full population, remaining obligations and actual failure
attribution. Every example/report path must be new with an existing report parent.

The example's block names are fixture data; the activity applies to any
source-backed change/test map and workflow stage.

## Helper features

| Operation | Responsibility |
|---|---|
| `regression_select.py plan` | Unions direct mapped and mandatory tests, applies broadening/unknown-impact policy, and retains selected/deferred/unselected members with reasons and availability. |
| `regression_select.py review` | Reconstructs the bound selection and reconciles actual targeted results, optionally with an independently enumerated full campaign. Preserves every attempt and missed failure. |
| `regression_select.py digest FILE` | Prints canonical JSON SHA-256 for the map, policy and result bindings. |
| `--output FILE` | Saves JSON to a fresh path; JSON is also printed. |

Manifest order determines output order. It is not an optimized schedule. Build
sharing, execution order, retry policy and job dispatch stay with the existing
runner.

## Prepare four independent inputs

[FORMAT.md](FORMAT.md) specifies the exact records.

| Input | Required engineering source |
|---|---|
| Universe | Complete applicable manifest at the current revision/scope, including configuration/build/seed/checker variants and known availability. Obtain it independently of the proposed selection. |
| Changes | Actual base/current revision, retained diff and reviewed changed items with company-defined categories. |
| Mapping | Source-backed change-to-test relationships, per-entry completeness and exact universe/change bindings. An explicit empty map is a no-impact assertion requiring evidence. |
| Policy | Current mandatory/required tests, requested deferrals/later stage, broad-change categories and unknown-impact treatment. |

Typical broad categories include shared logic, configuration, toolchain and
generator changes, but policy belongs to your flow. `unknown_impact: broaden_all`
selects every known test; `record_gap` retains unresolved impact instead.
Unknown universe completeness remains a gap even if every known test is selected.

Use `digest` after reviewing a record. Correct hashes bind records; they do not
prove dependency completeness. A changed universe/map/policy needs a new review,
not only updated digests. Renamed tests require explicit correction; no aliases
are guessed.

## Connect to your existing runner

1. Establish the original verification objective and accepted full population.
   Read the actual change, affected requirements, checker configuration and
   dependency evidence with feature/integration owners.
2. Export the four records and run `plan`. Review mandatory tests, broadening,
   unknown impact, unavailable tests and remaining required work.
3. Pass the selected IDs to your existing runner using its own invocation and
   build-sharing mechanisms. Keep deferred requirements visible with their later
   stage.
4. Retain every actual attempt as `pass`, `fail`, `error`, `skipped` or `not_run`,
   with original run/checker evidence. Process exit 0 alone is not a generic
   verification pass.
5. Bind targeted feedback to the exact selection. Run an independently enumerated
   full campaign according to your policy and compare its actual results.
6. Investigate failures outside selection with the dependency/map owner. Correct
   the original mapping or broadening policy, then revalidate on later changes.
   Preserve history; a passing retry does not erase an earlier fail/error.

A full campaign is not a targeted list relabeled “full.” Full also does not imply
passed or even executed. Additional tests in a targeted packet need a correctly
scoped extended/full campaign, not silent pruning.

## AI-first adoption

Give a file/tool-enabled assistant [SKILL.md](SKILL.md),
[AI_USAGE.md](AI_USAGE.md), original change intent, full manifest and runner setup:

> Identify a useful first regression stage for this change. Review actual
> dependencies and mandatory policy, preserve unknown impact and later
> obligations, and adapt the selection to our runner. Compare targeted results
> with independent full feedback; use missed failures to review the map rather
> than treating selected passes as release evidence.

Use [ONBOARDING.md](../../ONBOARDING.md), module `incremental-regression` /
activity `default`. The assistant can investigate native source and evidence
beyond this helper; no DVSim/UVM importer is bundled. Optional DVIT
intent/dependency context can expose relationships absent from local maps and
help scope revalidation. Independent local use requires no connection.

## Interpret results and validate adoption

| Exit | Meaning |
|---:|---|
| 0 | Advisory selection or recorded feedback, with remaining obligations retained. |
| 1 | Policy/binding contradiction, actual failure/error or other finding requiring review. |
| 2 | Missing context or incomplete evidence. |
| 3 | Invalid input or I/O. |

Argument errors use exit 2. Reports retain original attempts and campaign bindings.
`release_completeness` remains `not_established`. Unexecuted obligations stay
unexecuted until sourced actual results arrive.

The [native Verilator example](examples/verilator/README.md) compares targeted
and full **separate executions**, including a fully bound but misleading map that
misses actual failures. It is qualified on Linux with Verilator 5.020, GCC 13.3
and Make 4.3. Production selection quality, commercial runners and different
native exporters need validation in the adopting flow; this fixture establishes
no miss probability or universal speedup.

```sh
python -m unittest discover -s tests -v
```

Keep the change request, population, map/policy rationale, selection, actual
attempts/full comparison and owner decisions together. The
[change record](record.template.json) supports the broader review.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
