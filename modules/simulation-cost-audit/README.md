# Simulation cost audit

Use this module when deciding where simulation time goes or whether an intervention
improves a task. It accounts for **measured wall intervals, overlap and separately
scoped resources**, then reviews comparisons under an explicit workload/checking
policy.

This fits in regression/campaign cost review before changing builds, checkpoints,
tracing or runner behavior. DV infrastructure and verification owners can use it
alongside scheduler/accounting reports. CPU time, trace-enabled time and elapsed
wall time are different quantities; adding overlapping intervals can invent cost.

The activity supplements native accounting and engineering efficiency review.
It replaces manual timeline union/overlap arithmetic and comparison-context
reconciliation. It does not collect live statistics, launch a profiler or prove
that an intervention causes savings.

## First use

Python 3.10+ and the standard library suffice. From
`modules/simulation-cost-audit`:

```sh
python examples/create_example.py .local/cost-first-use
python cost_audit.py analyze .local/cost-first-use/baseline.json --json-out .local/cost-first-use/analysis.json --markdown-out .local/cost-first-use/analysis.md
python cost_audit.py compare .local/cost-first-use/baseline.json .local/cost-first-use/current.json .local/cost-first-use/policy.json --json-out .local/cost-first-use/comparison.json --markdown-out .local/cost-first-use/comparison.md
```

Expected exits: **0**. The synthetic baseline has 7200 wall seconds. Two overlapping
waveform observations union to 600 seconds; they are overlays, not another
600+200 seconds to add to the wall budget. The separately recorded 18000 CPU
seconds and 0.5 engineer hours retain their own scopes/units.

The current synthetic wall window is 5700 seconds: a descriptive −1500-second
difference under the declared matching context. This illustrates arithmetic, not
a measured optimization or CPU/storage saving. Open Markdown for the budget and
JSON for segments, attribution, raw resource observations and comparison basis.
Directories/reports must be new with existing report parents.

## Helper features and accounting

| Operation | Contribution |
|---|---|
| `cost_audit.py analyze RUN` | Partitions the selected measured wall window into exclusive stages, shared-stage intervals and unallocated time, with separate overlays/resources/progress. |
| `cost_audit.py compare BASELINE CURRENT POLICY` | Retains both audits and descriptive deltas, then checks fixed/intended context, completion and required-evidence basis. |
| `inspect-sc MANIFEST --output INVENTORY --context-template CONTEXT` | Inventories supported original SiliconCompiler accounting records. |
| `import-sc MANIFEST --context CONTEXT --output RUN` | Imports selected nodes using original timestamp/measurement evidence and caller-sourced clock/scope context. |
| `--json-out` / `--markdown-out` | Saves structured/readable audits; Markdown is also printed. |

[FORMAT.md](FORMAT.md) defines `opentools.cost-run.v1` and the comparison policy.

Measured sourced phase intervals use seconds relative to one declared origin.
They are clipped to the selected window and unioned per stage. Overlap between
different stages is counted once as shared time. Unallocated time is **not**
automatically idle, license wait, hang or waste.

Trace/I/O overlays remain separate from the wall partition. They can show when
dumping was enabled; they do not establish exclusive I/O cost or the speedup from
disabling it. Estimated/missing boundaries remain unqualified.

Resources retain kind, value, unit, definition, scope, measured/estimated basis and
source. CPU, elapsed time, memory peaks, bytes and human effort are not automatically
summed. CPU can exceed wall under parallel work. Missing observations do not
become zero.

Simulation progress needs a sourced counter/time definition and matching scope
for a wall-rate calculation. Zero progress does not itself prove a hang. Arithmetic
precision is not timestamp/sampler accuracy.

## Source a comparison correctly

The comparison binds original run IDs and assigns `fixed` or `intended` roles,
reasons and evidence to configuration, workload, instrumentation, tool and required
evidence scope.

Changed fixed conditions confound the question. Intended workload/configuration/
evidence-scope changes produce a descriptive difference, not a same-work benefit.
Instrumentation may be the intended change while required evidence stays fixed.
Progress amount/definition differences also limit rate comparisons.

Both tasks need actual completion and required-evidence basis. A failed or truncated
invocation cannot be relabeled complete to make a comparison pass. Cost accounting
can describe failed runs without implying a design pass.

## Optional SiliconCompiler JSON path

The read-only profile supports **SiliconCompiler 0.38.11, schema 0.57.2 Project
JSON** without loading its package. With original final job/node root records:

```sh
python cost_audit.py inspect-sc run.pkg.json --output inventory.json --context-template context.json
```

Complete `context.json` with selected nodes/stages, original common-clock/origin
and scope evidence, collection and required-result basis. Retain its exact
manifest digest; then:

```sh
python cost_audit.py import-sc run.pkg.json --context context.json --output run.json
python cost_audit.py analyze run.json
```

Window bounds span selected nodes only when all required starts/ends exist.
Outer queue, setup, collection and human review remain outside unless measured
separately. Native UTC labels do not establish coherent clocks across hosts.
Missing bounds are not reconstructed from duration fields; no history fallback
fills them.

Native `exetime`, `tasktime` and `totaltime` are elapsed observations, not CPU
measurements or extra disjoint stages to sum. Source units/definitions remain
explicit. A successful tool exit cannot manufacture simulation progress or complete
verification evidence.

## Integrate into efficiency review

1. State the original task and cost question, including required verification/
   diagnostic evidence.
2. Retain actual native phase/resource observations and their clock/origin/scope.
   Include build, queue, capture, restore and review when the question covers them.
3. Normalize measured intervals and resources without guessing missing markers.
   Validate a native exporter against original accounting records.
4. Analyze before choosing an intervention. Review unallocated/overlapping time
   and evidence gaps with the runner/tool owners.
5. Compare adequate before/after tasks under an independently stated policy.
   Keep descriptive change separate from causal or total-workflow benefit.
6. Hand off raw records, clock/scope rationale, audits and owner decisions.
   Revalidate after workload, checking or measurement-basis changes.

## AI-first adoption, results and tests

Give a file/tool-enabled assistant [SKILL.md](SKILL.md),
[AI_USAGE.md](AI_USAGE.md), original task objective and native accounting:

> Explain the measured wall budget without double-counting overlap. Trace units,
> origins and scopes, distinguish enabled tracing from actual exclusive cost,
> and compare interventions only with the required workload/checking basis.
> Ask for missing measurements rather than inferring waste from silence.

Use [ONBOARDING.md](../../ONBOARDING.md), module `simulation-cost-audit` /
activity `default`. Existing AI/accounting tools suffice. Optional DVIT intent/
dependency context can connect cost interventions to preserved evidence objectives;
independent operation requires none.

| Operation / exit | Meaning |
|---|---|
| Analyze 0 / 2 | Accounted selected window / partial accounting. |
| Compare 0 | Comparable bounded observation or explicitly descriptive difference. |
| Compare 1 / 2 | Confounded / missing basis, retaining both findings and gaps. |
| 3 | Invalid input/import or I/O. |

Argument errors use exit 2. No status establishes causal improvement, equal
verification quality, financial benefit or total workflow savings.

```sh
python -m unittest discover -s tests -v
```

Optional API cross-checks use `OPENTOOLS_SC_MANIFEST` and
[requirements-native-test.txt](requirements-native-test.txt). Other native formats
need separately validated exports. The [manual record](record.template.json)
captures broader interpretation separately from executable formats.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
