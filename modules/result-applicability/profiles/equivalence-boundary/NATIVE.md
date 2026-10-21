# Saved Yosys profile

Qualification uses **Yosys 0.33 (git sha1 2584903a060)** native
[`miter -equiv`](https://yosyshq.readthedocs.io/projects/yosys/en/docs-previewtest/cmd/miter.html)
and SAT. The retained version's help and actual exports define this profile.
Current documentation is not a claim of support for other releases.

The sources define `gold` and `gate`. `recipe()` in
[yosys_equivalence.py](yosys_equivalence.py) emits the exact supported script:
read `reference.v` and `implementation.v`, apply explicit numeric parameters,
run `proc`, retain `compared.json`, build and flatten the native equivalence miter,
prepare `miter`, retain `miter.json`, and prove `trigger=0` with defined inputs.
An optional `-set in_NAME 0|1` restricts the caller's selected scalar mode.
Arbitrary scripts, hidden data constraints, point deletion and automatic remapping
are unsupported. Imported scripts are never executed.

Retain these original files in one workdir:

```text
reference.v          implementation.v
run.ys               version.txt
compared.json        miter.json
command.json         execution.json
native.log           equivalence.log
witness.json         # required for native FAIL
```

`command.json` is the original argv array `[executable, "-Q", "-T", "-s", "run.ys"]`.
`execution.json` contains `{"exit_code": 0}`. Exit zero establishes completed tool
execution; the SAT log supplies PASS/FAIL. Native table and WaveJSON witness must
agree on all exposed inputs, outputs and comparators.

Interfaces use ordinary identifiers, unsigned 1..32-bit ports, at most sixteen
inputs and sixteen outputs and 128 bits per direction. At most eight explicit
unsigned integer parameter selections per side are supported. The reader checks
actual resolved parameters and source identities rather than relying on filenames.
It validates native point/trigger wiring and rejects undefined drivers, cycles,
state, memories, blackboxes and unknown cells. The accepted primitive set is
explicit in `COMBINATIONAL`; unsupported exports remain unresolved.

There is one native whole-miter proof scope, not a multi-partition EQY flow.
Defined two-state combinational equivalence is complete within the selected input
restrictions. It says nothing about sequential initialization, retiming, temporal
reset behavior, memory abstraction or four-state equivalence. Use a suitable native
flow and semantic export for those claims; the AI workflow can review their scope.
Do not substitute an independent example reference for a native engine verdict.
