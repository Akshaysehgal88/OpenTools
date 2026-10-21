# Coverage change audit

Separate new functional coverage hits from changes to bins, exclusions, thresholds,
weights and goals. The read-only comparator produces JSON and Markdown using the
Python standard library. Use [SKILL.md](SKILL.md) for AI-assisted interpretation
and [AI_USAGE.md](AI_USAGE.md) for review inputs and outputs.

For DFT test-coverage closure, use the
[fault-denominator profile](profiles/fault-denominator/README.md). It retains
original/collapsed fault populations, native classes and exclusion decisions
with their own measurement definitions.

## Quick start

From the repository root:

```sh
python modules/coverage-change-audit/examples/create_example.py .local/coverage-example
python modules/coverage-change-audit/coverage_audit.py compare .local/coverage-example/baseline.json .local/coverage-example/current.json --json-out .local/coverage-report.json --markdown-out .local/coverage-report.md
```

Expected exit: **1**. Changing 20 unhit bins to ignore bins raises the synthetic
fraction from 180/200 to 180/180, with zero newly hit bins. The report retains the
original population and identifies the kind changes. Output paths must be new.

## UCIS XML import

Optional reader: PyUCIS `0.2.0.22787133465`, tested with Python 3.14.
Install it in your own environment:

```sh
python -m pip install -r modules/coverage-change-audit/requirements-ucis.txt
python modules/coverage-change-audit/coverage_audit.py inspect-ucis run.xml --output inventory.json --context-template context.json
```

Fill in run/configuration/producer identities and semantic definitions from the
original coverage model. Retain every bin of each selected coverpoint instance.
Set `population_complete` only for a complete selected population. Context is bound
to the XML SHA-256 and cannot override native counts, kinds or options.

```sh
python modules/coverage-change-audit/coverage_audit.py import-ucis run.xml --context context.json --output snapshot.json
```

Repeat for the other run, then compare. To generate and reimport synthetic XML,
run `examples/create_example.py NEW_DIRECTORY --ucis` from this module directory.
Commercial simulator exports require separate qualification.

## Report interpretation

- Fractions count regular bins meeting the point's `at_least` threshold, divided
  by regular bins. Ignore and illegal bins remain separate; zero denominator is null.
- New hits and newly satisfied bins are different: lowering a threshold can satisfy
  a bin without additional activity. Weight/goal changes are reported separately.
- Changed or unknown definitions limit progress claims. Names and source lines alone
  do not establish equal semantics. Reviewed renames use an explicit identity map.
- Partial populations mean items were not observed, not proven removed. Changed
  scope/configuration/producer blocks cross-context hit-progress claims.

The XML profile supports per-instance coverpoints with explicit options and bin
kinds, and one range/count per bin. Crosses, code coverage, sequences, multi-range
bins, default kinds, per-bin weights and external exclusion overlays are unsupported.
The pinned reader loses range semantics; supply them through digest-bound context
or leave definitions unknown. Native aggregate scores retain their own semantics.

## Status and tests

Compare: `0` unchanged within scope, `1` review required, `2` incomplete, `3` error.
Import: `0` declared complete population, `2` partial, `3` error. Argument errors
use exit 2. Population completeness alone does not establish semantic completeness.

```sh
python -m unittest discover -s modules/coverage-change-audit/tests -v
```

XML tests skip when the optional dependency is absent. See [FORMAT.md](FORMAT.md)
for validated inputs; [record.template.json](record.template.json) and
[example.json](example.json) are manual review records.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
