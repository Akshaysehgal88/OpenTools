# Coverage change audit

Use this module when a coverage percentage improves and the closure review needs
to know **what changed**: exercised behavior, the population, a bin definition,
an exclusion, a threshold, a weight or a goal. It compares per-instance functional
coverpoint snapshots while preserving the original obligations and their meaning.

This activity fits between coverage export/merge and the coverage-closure review,
and after model or exclusion changes. Coverage owners, DV engineers and reviewers
can use it alongside the simulator's coverage tool. It supplements native scores
and exclusion approval; it replaces manual population and scoring-option diffs.
It does not generate a coverage model or decide whether an exclusion is justified.

For DFT fault-coverage closure, use the separate
[fault-denominator activity](profiles/fault-denominator/README.md). Original and
collapsed faults, native classes and ATPG-style measurement definitions have
different semantics from functional bins.

## First use

Python 3.10+ and the standard library suffice for normalized JSON comparison.
Run from `modules/coverage-change-audit`:

```sh
python examples/create_example.py .local/coverage-first-use
python coverage_audit.py compare .local/coverage-first-use/baseline.json .local/coverage-first-use/current.json --json-out .local/coverage-first-use/review.json --markdown-out .local/coverage-first-use/review.md
```

Expected exit: **1**, `review_required`. The example changes twenty unhit bins
from regular to ignore. The displayed fraction rises from **180/200 to 180/180**,
with **zero newly hit bins**. Open `review.md` for the population/kind changes;
`review.json` retains original rows, context, definitions, issues and progress
counts. The percentage increase alone is not new exercised behavior.

For an unchanged control:

```sh
python coverage_audit.py compare .local/coverage-first-use/baseline.json .local/coverage-first-use/baseline.json --json-out .local/coverage-first-use/unchanged.json
```

Expected exit: **0**, `unchanged_within_scope`. Example directories and report
files must be new. Reports never overwrite the source exports.

## Features and helper responsibilities

| Entry point | What it does |
|---|---|
| `coverage_audit.py compare BASELINE CURRENT` | Compares point/bin populations, kinds, counts, semantic definitions, thresholds, weights, goals and context. Reports new hits separately from newly satisfied bins. |
| `compare --identity-map MAP` | Applies explicit reviewed one-to-one bin renames. It pairs identities, without asserting semantic equivalence. |
| `inspect-ucis XML --output INVENTORY --context-template CONTEXT` | Inventories supported native XML counts/kinds/options and creates a digest-bound semantic context template. |
| `import-ucis XML --context CONTEXT --output SNAPSHOT` | Imports every bin of each selected point, adding sourced semantic metadata without overriding native measurements. |
| `ucis_import.py` | The optional library used by the two XML subcommands; it is not a separate CLI or a new coverage database engine. |

`compare` prints Markdown by default; `--format json` changes stdout.
`--json-out` and `--markdown-out` save both handoff forms.

## Inputs: preserve meaning as well as identities

[FORMAT.md](FORMAT.md) defines `opentools.coverage-snapshot.v1`. Each snapshot
records run, scope, configuration, model, producer/version and source identities,
plus whether the selected population is complete.

Each point retains its ID, definition and definition source, `at_least`,
`weight`, `goal` and complete bin list. Each bin has an ID, kind, nonnegative
count, definition and source. Definitions must capture resolved semantics:
sampling event/condition, expression, ranges and configuration dependence as
applicable. Names and source lines alone do not establish equivalent behavior.
Unknown definitions remain `null`.

The reported fraction is regular bins meeting `at_least` divided by regular
bins. Ignore and illegal bins remain separate. A zero denominator is `null`;
there is no cross-point weighted percentage. Native hierarchy/goal-normalized
scores keep their original definitions in the native report.

A lower threshold can satisfy a bin with no new hit. A rename map cannot make
changed definitions comparable. Partial exports show what was observed, not proof
that missing bins were removed. Cross-context changes can block hit-progress
attribution even when each snapshot is individually valid.

## Optional UCIS XML path

The qualified reader uses **PyUCIS 0.2.0.22787133465**, tested with Python 3.14.
Install the pinned optional dependency into your own environment, not a shared
EDA Python environment:

```sh
python -m pip install -r requirements-ucis.txt
python coverage_audit.py inspect-ucis run.xml --output inventory.json --context-template context.json
```

Complete `context.json` from the original run/configuration and coverage model.
Keep the exact XML digest and native point/bin IDs. Retain every bin of each
selected coverpoint instance, supply semantic definitions with source evidence,
and declare population completeness only when supported. Context cannot change
native counts, kinds, options or thresholds.

```sh
python coverage_audit.py import-ucis run.xml --context context.json --output snapshot.json
```

Repeat for the other export, then compare the snapshots. For a runnable synthetic
XML round trip with source-defined context:

```sh
python examples/create_example.py .local/coverage-xml --ucis
python coverage_audit.py inspect-ucis .local/coverage-xml/current.xml --output .local/coverage-xml/inventory.json --context-template .local/coverage-xml/unfilled-context.json
python coverage_audit.py import-ucis .local/coverage-xml/current.xml --context .local/coverage-xml/current.context.json --output .local/coverage-xml/reimported.json
```

The inventory template is deliberately unfilled; the example's separate
`current.context.json` contains its independently specified synthetic definitions.

Support is per-instance coverpoints with explicit options/kinds and one range/count
per bin. Crosses, code coverage, sequences, multi-range bins, default kinds,
per-bin weights and external exclusion overlays are outside this profile. The
pinned reader loses range semantics, so context must supply them or leave them
unknown. Commercial simulator XML exports require separate qualification.

## Integrate into coverage closure

1. Choose the original closure scope and objective with the coverage owner.
   Retain the baseline before changing the model or exclusions.
2. Export native populations and source identities for both runs. Establish that
   the configuration, measurement definitions and selected scope are comparable.
3. Map semantic definitions from the resolved coverage model. Use a reviewed
   identity map for actual bin renames; do not match by name similarity.
4. Run the comparator. Separate newly exercised bins from threshold effects,
   changed kinds, population changes, illegal hits and unreviewed definitions.
5. Review changes with model and exclusion owners using original requirement
   rationale. The tool's recognition of an ignore bin does not approve it.
6. Correct the model/export or run additional verification as appropriate, then
   re-export and revalidate. Hand off the original objective, both exports,
   semantic context, report and owner decisions together.

## AI-first setup and interpretation

Give a file/tool-enabled assistant [SKILL.md](SKILL.md),
[AI_USAGE.md](AI_USAGE.md), the original coverage objective and native exports:

> Explain the reported coverage change against the original required behavior.
> Find the consumed model and exclusion rationale, preserve the complete selected
> population, and distinguish additional hits from changed definitions or scoring.
> Ask for missing sampling/configuration evidence. Propose owner actions and
> revalidation; do not infer closure from a higher percentage.

Use [ONBOARDING.md](../../ONBOARDING.md), module `coverage-change-audit` /
activity `default`, for project-local installation. Your existing AI host can
review wider native evidence and adapt a validated exporter. Optional DVIT
intent/dependency context can connect changed bins and exclusions back to product
requirements; the module works independently with local sources.

| Exit | Interpretation |
|---:|---|
| Compare 0 | Unchanged within the supplied scope. |
| Compare 1 | Changes or illegal hits require review. |
| Compare 2 | Collection, context or semantic gaps; inspect retained findings too. |
| Import 0 / 2 | Declared complete / partial selected population. This alone says nothing about semantic completeness. |
| 3 | Invalid input, unsupported native shape, dependency or I/O error. |

Argument errors use exit 2. `incomplete` takes status precedence while retaining
`review_required` and known changes. No status approves exclusions or establishes
verification completeness/signoff.

```sh
python -m unittest discover -s tests -v
```

XML tests skip if the optional reader is absent. The
[manual review record](record.template.json) captures interpretation and follow-up
beyond the deterministic comparison.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
