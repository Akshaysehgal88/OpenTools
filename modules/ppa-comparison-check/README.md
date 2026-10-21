# PPA comparison check

Use this module before interpreting a reported power, performance or area delta.
It checks whether the pair shares a supported **measurement definition, scope
and experiment basis**, and preserves descriptive arithmetic even when the
intended claim is confounded.

This fits in synthesis/implementation experiment review and PPA handoff after an
RTL, constraints, library, corner, tool or flow change. Design, PD and performance
owners can use it alongside native reports. A better slack value under a relaxed
clock is not evidence of RTL improvement under fixed constraints.

The activity supplements native measurement and engineering experiment review.
It replaces manual condition/unit reconciliation. It does not measure PPA itself,
prove causal attribution or validate the scientific sufficiency of a claim.

## First use

Python 3.10+ and the standard library suffice. From
`modules/ppa-comparison-check`:

```sh
python examples/create_example.py .local/ppa-first-use
python ppa_check.py compare .local/ppa-first-use/baseline.json .local/ppa-first-use/current.json .local/ppa-first-use/contract.json --json-out .local/ppa-first-use/review.json --markdown-out .local/ppa-first-use/review.md
```

Expected exit: **1**, `confounded`. In these synthetic records:

- Standard-cell area falls from 1000 to 900 µm², a descriptive **−10%** delta.
  Its contract intentionally includes the combined RTL/constraints change.
- Setup slack rises from −0.4 to 0.2 ns, a **+0.6 ns** delta, but its claim asks
  about RTL under fixed constraints. The period changed from 10 to 12 ns, so that
  claim is confounded.

Neither comparison isolates a causal RTL contribution. Open Markdown for
per-metric decisions and JSON for raw values, roles, confounders, unknowns,
equivalences and arithmetic. Example directories and report files must be new.
The helper never rewrites the source reports.

## Features and input contract

| Operation | Contribution |
|---|---|
| `ppa_check.py compare BASELINE CURRENT CONTRACT` | Compares metric definitions/scope, normalizes supported units, reviews condition roles and produces descriptive deltas plus comparison qualification. |
| `inspect-orfs METADATA --output INVENTORY --context-template CONTEXT` | Inventories supported original ORFS finish metadata and creates a digest-bound context template. |
| `import-orfs METADATA --context CONTEXT --output SNAPSHOT` | Imports selected native measurements and caller-sourced units/conditions, preserving unknown values and native provenance. |
| `--json-out` / `--markdown-out` | Saves structured/readable comparisons; Markdown is also printed. |

[FORMAT.md](FORMAT.md) defines normalized snapshots and the experiment contract.
Each metric retains kind, exact definition/scope, raw value/unit with evidence,
measurement completeness and source-backed run conditions.

For each metric's **own claim**, classify conditions:

| Role | Review meaning |
|---|---|
| `fixed` | Known changes confound the claim unless an explicit reviewed equivalence matches this exact pair. |
| `intended` | Part of the stated treatment; unchanged values warn that the intended change is not observed. |
| `derived` | Expected to change through declared parent conditions; the observed ancestry must account for the change. |
| `irrelevant` | A sourced reason explains why it does not qualify this particular metric/claim. It cannot hide required identity or power basis. |

Required identities include design, RTL, final netlist, stage, tool and flow.
Library, corner and constraints need declared rules. Additional unclassified
changes remain unresolved. Pair-specific equivalence evidence must establish
meaning, not similar names.

Definitions and scope must match before arithmetic. Cell area is not die area.
Supported units normalize area to `um2`, time to `ns` and power to `W`; unknown
or unsupported units remain incomplete. Delta is current minus baseline.
Area/power percentages require a positive baseline; slack percentages are always
null. No frequency gain or cross-metric score is inferred.

## Optional ORFS metadata path

The qualified saved-file profile is **Metrics_2.1.2 finish-stage** metadata.
With your actual metadata available:

```sh
python ppa_check.py inspect-orfs reports/metadata.json --output inventory.json --context-template context.json
```

Complete `context.json` before import: select metrics, source their report-specific
units and scope, declare collection completeness and provide missing run conditions.
Retain the exact metadata digest. Context cannot override native producer facts.

```sh
python ppa_check.py import-orfs reports/metadata.json --context context.json --output snapshot.json
```

Repeat for the other run and compare with an independently written contract.
Import with incomplete measurement declarations returns 2; a successful complete
import qualifies collection only, not the comparison claim.

The profile reads instance, standard-cell and die area plus worst setup slack.
Missing/non-numeric values remain unknown. Platform unit labels are not
automatically assigned to every metric. Reported clock strings do not reconstruct
complete SDC, and a synthesis hash does not identify the final measured netlist.
Optional local artifact hashes identify declared files, not what the old run
consumed or all indirect dependencies.

Reader qualification used this pinned
[historical upstream artifact](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/e8bb32499b8fceb3f194b12f42cc03fce261bd95/flow/designs/nangate45/swerv/metadata-base-ok.json).
That is file-format coverage, not a new OpenROAD benchmark. Other metadata
versions, commercial reports and native power extraction need separately validated
exports. Normalized power records must include activity source/window/scope,
mapping, annotation scope/basis/fraction and unannotated-signal policy.

## Integrate into experiment review

1. State the original decision and claim per metric before choosing a favorable
   report. Identify whether the experiment studies a combined change or an
   isolated contribution.
2. Retain native measurements, actual consumed identities and source evidence for
   run conditions. Source units and measurement population explicitly.
3. Write condition roles/reasons and any exact reviewed equivalences. Preserve
   missing context rather than assuming fixed conditions.
4. Compare. Review descriptive deltas separately from confounders and unknown
   evidence, including activity annotation for any power claim.
5. Correct the source/context or run an adequate control experiment when needed.
   Recompare and route unresolved claims to the relevant owner.
6. Hand off the original question, raw reports, contract, audit and receiving
   decision. Repeat after measurement-definition or experiment-basis changes.

## AI-first adoption and results

Give a file/tool-enabled assistant [SKILL.md](SKILL.md),
[AI_USAGE.md](AI_USAGE.md), original experiment intent and native reports:

> Establish what this PPA comparison is intended to show. Trace actual measured
> definitions, units, final implementation identity and changed conditions.
> Separate descriptive deltas from causal claims, and ask for missing controls,
> activity/annotation or corner evidence before interpreting improvement.

Use [ONBOARDING.md](../../ONBOARDING.md), module `ppa-comparison-check` /
activity `default`. Your current AI/native tools suffice. Optional DVIT
intent/context can connect experiment changes to original product/performance
constraints; the module is independently usable without it.

| Compare exit | Meaning |
|---:|---|
| 0 | Comparable within the declared contract. |
| 1 | Known confounders. |
| 2 | Incomplete basis; retained confounders remain visible. |
| 3 | Invalid input/import or I/O. |

Argument errors use exit 2. Incomplete takes status precedence; `confounders_found`
is independent. No result establishes electrical accuracy, experimental sufficiency,
causation or signoff.

```sh
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_ORFS_METADATA` to the pinned artifact for its integration test.
Manual interpretation uses [record.template.json](record.template.json), a
separate format from executable snapshots.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
