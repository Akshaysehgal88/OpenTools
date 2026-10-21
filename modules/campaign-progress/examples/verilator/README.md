# Native campaign evidence example

This example shows how to connect campaign-progress accounting to **actual
simulator observations**, rather than treating elapsed cycles or a percentage as
proof of useful progress. Use it when evaluating the module's input contract,
building an exporter, or deciding what an existing regression dashboard should
report.

It compiles an owned SystemVerilog handshake model and executes nine native
attempts. The C++ driver exports DUT accepted counters, actual checker verdicts,
named payload goals and stimulus cycles. The Python recipe retains invocation
costs, builds cumulative campaign snapshots and reviews them offline. It uses no
scheduler or AI service; your assistant can inspect the source and explain which
measurements correspond to your campaign objectives.

## Requirements and first run

Use Linux, Python 3.10+, an existing Verilator **5.020**, GCC supporting C++17 and
GNU Make. The qualified environment used GCC 13.3 and Make 4.3. From
`modules/campaign-progress`:

```sh
python examples/verilator/run_example.py .local/campaign-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Replace the executable/runtime paths. With a complete installed `verilator`
launcher, `--verilator-root` can be omitted. Choose a new output directory.
No dependency is downloaded or installed. The recipe uses an owned space-free
`/tmp` build directory because of Make's path handling, then cleans up only that
scratch directory. Sources and evidence remain in the output.

To inspect a retained collection on a machine without a simulator:

```sh
python campaign_progress.py summarize .local/campaign-native/plateau/contract.json .local/campaign-native/plateau/before.json .local/campaign-native/plateau/after.json --output .local/campaign-native/plateau/new-review.json --markdown .local/campaign-native/plateau/new-review.md
```

This exits **0** because the accounting is consistent. It does not mean the
campaign has finished. Choose new report names on another invocation.

## What to examine

The declared objective requires three native checker passes, four named payload
goals and 192 checked handshakes. Start with these output folders:

| Case | Engineering interpretation |
|---|---|
| `plateau` | The first two attempts hit the same three goals, while checked exposure rises from 64 to 128. Useful exposure and new named-goal attainment are different dimensions; the third required run and unhit goal remain explicit. |
| `recorded-targets` | A directed third attempt attains the declared targets. This reports recorded attainment, without granting release or stopping authority. |
| `ineffective` | Three attempts advance 64 stimulus cycles and 195 ticks each, but accept zero transactions because the active path is disabled. They provide no exposure for this explicit accepted-work objective. |
| `missing-data` | An intentionally incomplete export retains the missing-run gap instead of treating the absent record as zero work. |

Each folder contains `contract.json`, `before.json`, `after.json`, `report.json`
and `report.md`. Review the contract before the result: its requested population,
goal definitions, exposure basis and eligibility policy determine what counts.

Other controls retain changed configuration, a changed coverage definition and
a deliberate checker failure. A three-bin definition displays 100% where the
original four-bin population displays 75%; no new comparable goal was hit.
Configuration changes must not be pooled silently. Failed execution can contain
valid observations, but the passed-only accounting policy excludes that run from
qualified attainment.

The collection also retains native argv/stdout/stderr, process exits, original
sources and binary, normalized exports and `native-observations.json`.
`recipe-cost.json` records the whole recipe scope, including build, exports,
runs, reports and scratch cleanup. Native invocation records distinguish child
process wall measurements from event counts. Neither file timestamps nor
simulation ticks establish a real-time campaign rate.

## Adapt the pattern to your runner

1. Write the independent campaign objective and full requested-run roster before
   collecting results. Name each goal and define the exposure event.
2. Retain actual native process/checker outcomes and the measurement source.
   Do not infer accepted work from driver iterations.
3. Export the existing runner's records into the [module format](../../FORMAT.md),
   preserving original IDs, scope, configuration and definition identities.
4. Review before/after snapshots using [campaign_progress.py](../../campaign_progress.py).
   Keep cumulative identities so a rerun or overlapping export is not counted twice.
5. Send unmapped goals, inactive execution and missing records to their owners.
   Revalidate after fixing stimulus, instrumentation or the accounting policy.

For AI-led use, give the assistant this example, the
[module README](../../README.md) and the original campaign objectives. Ask it to
trace one counter and one named goal back to their native producer before
adapting the exporter. This exercise supplements existing dashboards and runner
accounting; it neither dispatches reruns nor decides when to stop.

Coverage here is a source-defined Boolean goal set, not UCIS/UVM functional
coverage. Deterministic stimulus and a local checker do not establish independent
statistical trials or reliability confidence. The Linux harness is qualified for
the versions above; other simulators, operating systems and production campaigns
need their own native qualification. Offline record review needs only Python.
DVIT is optional and is not involved in the example.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
