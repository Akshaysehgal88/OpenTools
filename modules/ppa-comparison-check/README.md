# PPA comparison check

Check whether reported power, performance or area deltas share a supported
comparison basis. `ppa_check.py` reads saved records and writes JSON and Markdown.
Requires Python 3.10+ and the standard library. Use [SKILL.md](SKILL.md) to review
the experiment with your existing AI agent; see [AI_USAGE.md](AI_USAGE.md).

## Quick start

From the repository root:

```sh
python modules/ppa-comparison-check/examples/create_example.py .local/ppa-example
python modules/ppa-comparison-check/ppa_check.py compare .local/ppa-example/baseline.json .local/ppa-example/current.json .local/ppa-example/contract.json --json-out .local/ppa-audit.json --markdown-out .local/ppa-audit.md
```

Expected exit: **1**. The synthetic area delta is -10% under an intended combined
RTL/constraints change. Slack increases 0.6 ns, but its contract asks about RTL
under fixed constraints: the clock changed from 10 to 12 ns. That claim is
confounded. Neither delta isolates a causal RTL contribution.

## ORFS metadata import

The read-only native profile supports **Metrics_2.1.2 finish-stage** metadata.

```sh
python modules/ppa-comparison-check/ppa_check.py inspect-orfs reports/metadata.json --output inventory.json --context-template context.json
python modules/ppa-comparison-check/ppa_check.py import-orfs reports/metadata.json --context context.json --output snapshot.json
```

Between commands, fill in selected metrics, report-specific units, completeness
and missing run conditions. Context binds the exact metadata SHA-256 and cannot
override producer facts. Optional local artifact hashes identify declared files;
they do not prove which bytes the original run consumed.

The profile reads instance, standard-cell and die area, and worst setup slack.
Missing/non-numeric values stay unknown. Platform unit labels are not assigned to
every metric. Clock strings are not a complete SDC interpretation, and a synthesis
hash does not identify the final measured netlist.

The reader was tested against a pinned [historical upstream artifact](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/e8bb32499b8fceb3f194b12f42cc03fce261bd95/flow/designs/nangate45/swerv/metadata-base-ok.json).
This is file-format coverage, not a fresh OpenROAD benchmark.

## Comparison contract

Each metric declares its claim and condition roles: `fixed`, `intended`, `derived`
or `irrelevant`. Supply reasons and evidence for those roles. Changed fixed
conditions are confounders unless an explicit pair-specific reviewed equivalence
applies. Unclassified changes and missing required evidence remain unresolved.

Reports retain raw measurements and descriptive deltas even when the claim is
confounded. Different definitions or scopes block arithmetic. Units convert only
through supported rules. No frequency inference or cross-metric score is produced.

Normalized power records require activity source/window/scope, mapping, annotation
basis/fraction and an unannotated-signal policy. **Native power extraction is outside
this ORFS profile.** The utility does not verify electrical accuracy or prove the
contract's scientific sufficiency.

## Status and tests

Compare: `0` comparable within contract, `1` confounded, `2` incomplete, `3` error.
Incomplete takes precedence while retaining confounders. Import success describes
collection only. Argument errors use exit 2. Existing outputs are never replaced.

```sh
python -m unittest discover -s modules/ppa-comparison-check/tests -v
```

Set `OPENTOOLS_ORFS_METADATA` to the pinned artifact for its integration test
(SHA-256 `26fee48996075b7ecfe43805d9da105b209d082991fa4dd24cb2f859bab79e86`).
See [FORMAT.md](FORMAT.md); the [manual template](record.template.json) and
[manual example](example.json) use separate formats.
