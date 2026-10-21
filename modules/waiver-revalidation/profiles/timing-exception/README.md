# Timing exception reach

Review a setup false path after hierarchy, selector, mode or intent changes.
Preserve its native resolved selectors and the setup endpoint pairs it masks;
compare those observations with the original rationale and current path intent.
Use the [workflow](WORKFLOW.md) with your existing AI agent and native STA tools.

The optional Python helper reads saved evidence and reuses the parent waiver
snapshot, premise and one-to-one correspondence records. It does not edit SDC.
Python 3.10+ standard library; saved-data review works on Windows and Linux.
No model API or DVIT installation is required.

## Native example

The collector is qualified on Linux with OpenROAD
**v2.0-17598-ga008522d8**. Supply your tool's normal runtime environment.
From this directory:

```sh
python examples/run_native.py runs --openroad /path/to/openroad
python sta_exception.py review runs/shift-window-expanded \
  runs/shift-window-expanded/contract.json \
  runs/shift-window-expanded/evidence.json \
  --json-out reach.json --markdown-out reach.md
```

The review exits **1**: `capture*` also masks a new functional capture pair.
The same activity is exercised in shift-only and clock-boundary contexts.
Reviewed renames preserve meaning; same-count retargets and mode changes require
review. Native clock membership supports the clock-pair observation; the declared
independence premise remains a separate source obligation.

For an existing qualified archive:

```sh
python sta_exception.py capture RUN CONTEXT.json --output evidence.json
python sta_exception.py drift \
  --baseline-run BASE --baseline-contract BASE/contract.json \
  --baseline-evidence BASE/evidence.json \
  --current-run CURRENT --current-contract CURRENT/contract.json \
  --current-evidence CURRENT/evidence.json \
  --identity-map correspondence.json --json-out drift.json --markdown-out drift.md
```

Omit `--identity-map` unless an actual reviewed rename is supplied. Original
artifacts stay in place; outputs must be new files. See [FORMAT.md](FORMAT.md).

## Supported scope

The owned loader starts with a fresh flat `top`, explicit clocks and binary/null
case ports. It applies exactly one plain `set_false_path -setup` between native
cell selectors, with no through, reset, edge-specific or other exception family.
No imported SDC executes. This closed scope establishes the precedence boundary.
Simple flat names and `*`/`?` cell patterns; 1–64 selected instance pairs.

Each pair is queried before and after application for a maximum-setup
representative per native path group. All returned records are retained; multiple
clock associations remain incomplete. The population is **endpoint pairs**, not every structural path
or rise/fall alternative. Native register census must show one clock pin, data
pin and output pin per selected scalar register. Require one active clock and an
independent intent entry for every observed pair. Multiple clocks, absent history,
unknown modes or partial intent remain unresolved. Hold reach, multicycle pairs,
mixed-exception precedence and hierarchical propagation require another qualified
method. Matching reach cannot establish exception safety or timing/CDC signoff.

The reusable workflow accepts other native exports with their own support and
completeness basis. The bundled reader accepts only this pinned producer; writing
matching hashes does not authenticate engineering intent or approval.

## Results and tests

Exit 0: bounded reach accounted / unchanged within scope. Exit 1: review needed.
Exit 2: incomplete or quarantined evidence. Exit 3: invalid input or I/O failure.
Read findings and gaps together; a known finding can coexist with incomplete
evidence. Engine completion remains separate from review disposition.

```sh
OPENTOOLS_STA_EXCEPTION_EXAMPLES=/path/to/runs \
  python -m unittest discover -s tests -v
```

Without a native archive, input tests run and the native-corpus class is skipped.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
