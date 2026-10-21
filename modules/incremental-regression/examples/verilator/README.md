# Native selection comparison

Use this example to evaluate the incremental-regression adoption loop:
source-backed selection, actual targeted execution, independent full execution and
review of what the first stage missed. It helps runner/dependency owners test an
exporter and understand the [module's limits](../../README.md) before changing
regression policy.

The Linux recipe compiles four small owned SystemVerilog variants. Six native
checker populations serve seven scoped scenarios. Targeted and full campaigns
are separate native executions; the full population is independently enumerated,
not copied from the selected list.

## Build and run

Use Python 3.10+, an existing **Verilator 5.020**, GCC C++17 and GNU Make.
The qualified environment used GCC 13.3 and Make 4.3. From
`modules/incremental-regression`:

```sh
python examples/verilator/run_example.py .local/regression-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Replace the native executable/runtime paths. A complete installed `verilator`
launcher can omit `--verilator-root`. No dependency is downloaded or installed.
The output must be new. The recipe uses an owned space-free `/tmp` build
directory, retains native evidence in the output and cleans up only that scratch
directory.

Expected recipe exit: **0** when all owned scenario expectations are met.
Expected failed native tests remain in the collection and feedback. Recipe
success does not mean those campaigns passed.

## Examine the scenarios

| Folder | What to learn |
|---|---|
| `baseline` | Mandatory smoke/integration remain in a first stage, with the rest of the full population explicit. |
| `local` | A smaller selected stage exercises mapped local impact while retaining deferred requirements and actual defects. |
| `shared` / `configuration` | Policy broadens shared or configuration impact to all six known test populations. |
| `unknown` | Unknown impact broadens according to policy rather than silently selecting nothing. |
| `renamed` | An old mapped ID requires review; matching names are not guessed. |
| `misleading-map` | A fully bound map falsely calls a shared edit local/complete. Full execution exposes failures in `soc_stress` and `fabric_long` outside selection. |

Configuration 1 exposes a deliberate fixture defect; local/shared/glue variants
introduce explicit defects. The C++ checker requires actual functional comparisons.
The example's block/test names are application data, not restrictions on the
general selection activity.

Each scenario retains `universe.json`, `changes.json`, `mapping.json`,
`policy.json`, `selection.json`, targeted/full result exports and `feedback.json`.
The collection retains exact sources, binaries and per-invocation argv/stdout/
stderr, exit/checker counts and process wall observations.
`native-observations.json` summarizes scenarios and source identities;
`recipe-cost.json` records the whole recipe scope.

## Re-review a saved collection

No simulator is needed for this step. From the module directory:

```sh
python regression_select.py review --universe .local/regression-native/misleading-map/universe.json --changes .local/regression-native/misleading-map/changes.json --mapping .local/regression-native/misleading-map/mapping.json --policy .local/regression-native/misleading-map/policy.json --results .local/regression-native/misleading-map/targeted-results.json --full-results .local/regression-native/misleading-map/full-results.json --output .local/regression-native/misleading-map/new-feedback.json
```

Expected exit: **1**. Inspect failures outside selection, retained attempts and
remaining required IDs. Use a new report name on another invocation. The helper
reads normalized records; original invocation evidence supplies their native
basis and should remain available for source/checker review.

## Adapt the pattern

1. Ask your AI assistant to inspect [SKILL.md](../../SKILL.md), the original change,
   complete applicable manifest and this exporter.
2. Establish real configuration/build/seed/checker identities and independent
   mandatory/broadening policy in your runner.
3. Retain actual targeted and full attempts with source/checker verdicts. Bind
   them to the original population/change/selection records.
4. Review misses with the dependency owner and correct the map or policy. Validate
   on later changes before relying on a smaller first stage.

The owned manual maps and deliberate defects establish neither production
dependency completeness nor miss probability. Native Windows/macOS, commercial
simulators, UVM and DVSim adaptation are unqualified. Your existing native methods
can supply separately validated exports. The portable selector requires only
Python; DVIT is optional and unused by this example.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
