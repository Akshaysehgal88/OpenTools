# Incremental regression

Select a first verification stage while retaining the full test population,
mandatory tests and deferred obligations. Use [SKILL.md](SKILL.md) with your
existing AI agent, dependency evidence and runner. The optional Python 3.10+
helper uses the standard library. See [AI_USAGE.md](AI_USAGE.md).

## Quick start

From this module directory:

```sh
python examples/create_example.py demo
python regression_select.py plan --universe demo/universe.json --changes demo/changes.json --mapping demo/mapping.json --policy demo/policy.json --output demo/selection.json
python regression_select.py review --universe demo/universe.json --changes demo/changes.json --mapping demo/mapping.json --policy demo/policy.json --results demo/targeted-results.json --output demo/targeted-review.json
python regression_select.py review --universe demo/universe.json --changes demo/changes.json --mapping demo/mapping.json --policy demo/policy.json --results demo/targeted-results.json --full-results demo/full-results.json --output demo/full-review.json
```

The synthetic selection contains smoke, DMA-directed and mandatory integration.
Stress remains required and deferred. Later full results expose an omitted stress
failure; the final command returns **1**. No jobs are dispatched. Use new paths.

## Integration

Export the full applicable population independently of the proposed selection,
including configuration/build/seed/checker variants. Review the actual change and
dependencies. Bind the map and current policy to those records with canonical
hashes from `python regression_select.py digest FILE`.

The helper unions mandatory and mapped tests, broadens policy-defined categories
and unknown impact, and retains selected/deferred/unselected members separately.
Unknown impact can instead remain a recorded context gap. Manifest order determines
list order; the existing runner handles scheduling and build sharing.

Retain all actual attempts, including errors, unexecuted tests and failed retries.
A passing retry cannot erase an earlier failure. Compare targeted results against
later full campaigns to detect misses. Native exit 0 is not automatically a checker
pass. No DVSim/UVM importer is included. See [FORMAT.md](FORMAT.md) and the
[change template](record.template.json).

## Limits and status

A correctly bound map can still miss dependencies. The [Linux Verilator recipe](examples/verilator/README.md)
includes an incomplete map that misses actual failures. Inspect source/checkers;
hashes do not establish semantic completeness. A selected pass says nothing about
unexecuted obligations or release completeness.

`0` advisory selection or recorded feedback; `1` contradiction/failure/error;
`2` missing context/incomplete evidence; `3` invalid input/I/O. Reports preserve
original records. The helper neither learns a dependency graph nor controls execution.

```sh
python -m unittest discover -s tests -v
```

Core tests run on Windows/Linux. Native qualification is limited to the documented
Verilator fixture; production selection quality needs validation in the adopting flow.
