# Simulation cost audit

Account for wall time, overlapping stages and resource observations from saved
run records. Compare costs under an explicit workload/checking policy. Requires
Python 3.10+ and the standard library. Use [SKILL.md](SKILL.md) for AI-assisted
investigation; see [AI_USAGE.md](AI_USAGE.md).

## Quick start

From the repository root:

```sh
python modules/simulation-cost-audit/examples/create_example.py .local/cost-example
python modules/simulation-cost-audit/cost_audit.py analyze .local/cost-example/baseline.json --json-out .local/cost-audit.json --markdown-out .local/cost-audit.md
python modules/simulation-cost-audit/cost_audit.py compare .local/cost-example/baseline.json .local/cost-example/current.json .local/cost-example/policy.json --json-out .local/cost-comparison.json --markdown-out .local/cost-comparison.md
```

The synthetic baseline has 7,200 wall seconds. Overlapping trace observations
cover 600 seconds of that budget. The separately recorded 18,000 CPU seconds and
0.5 engineer hours are different quantities. The example comparison illustrates
arithmetic, not measured optimization. Outputs must use new paths.

## Accounting rules

Measured intervals partition the selected window into exclusive, shared-stage and
unallocated time. Concurrent intervals in one stage use their union. Trace/I/O
overlays remain separate; they are not added again to the wall budget.

Supply clock/origin, window scope and source references. Different hosts need a
common time basis. Missing markers remain unknown; log silence does not prove
idle time, a hang or license wait. Estimated boundaries are not measured time.

Keep CPU, memory, bytes, simulated progress and human effort in their own units
and scopes. Compare equivalent workloads, checkers and instrumentation. Include
build, queue, capture, replay and review costs when assessing an intervention.

## SiliconCompiler import

The read-only profile supports **SiliconCompiler 0.38.11, schema 0.57.2 Project
JSON**. No SiliconCompiler package is needed to read the saved JSON.

```sh
python modules/simulation-cost-audit/cost_audit.py inspect-sc run.pkg.json --output inventory.json --context-template context.json
python modules/simulation-cost-audit/cost_audit.py import-sc run.pkg.json --context context.json --output run.json
python modules/simulation-cost-audit/cost_audit.py analyze run.json
```

Between inspection and import, select nodes/stages and supply the original clock
and scope basis. Use final job/node manifests with root records. Context binds
exact bytes. The window spans selected nodes only when all bounds are present;
outer queue/setup/review work remains outside it. No history fallback is performed.

Native `exetime`, `tasktime` and `totaltime` are elapsed observations, not CPU
measurements or extra stages to sum. Missing bounds are not inferred from durations.
The reader does not collect live process statistics, launch a profiler or establish
simulation progress from a successful tool exit.

## Status and tests

Analyze: `0` accounted selected wall budget, `2` partial. Compare: `0` qualified or
explicitly descriptive difference, `1` confounded, `2` missing basis. Errors return
`3`; argument errors use `2`. Cost accounting can describe failed runs and never
implies a design pass.

```sh
python -m unittest discover -s modules/simulation-cost-audit/tests -v
```

Optional API cross-checks use `OPENTOOLS_SC_MANIFEST` and
[requirements-native-test.txt](requirements-native-test.txt).
See [FORMAT.md](FORMAT.md); the [manual template](record.template.json) and
[manual example](example.json) use separate formats.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
