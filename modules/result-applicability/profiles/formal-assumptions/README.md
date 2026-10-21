# Formal assumption applicability

Review proof setup before using a result for an integration claim. Check the
actual premises, their owners and producer support, clock/reset and operating
mode, then the required activation witness. A green property alone does not
answer these questions.

Use [WORKFLOW.md](WORKFLOW.md) with your existing AI assistant and formal flow;
[REVIEW.md](REVIEW.md) gives the review record. Optional saved-data commands need
Python 3.10+ and no solver, provider SDK or DVIT connection.

## Saved-data commands

```sh
python formal_review.py capture retained-run proof capture-context.json --output proof-snapshot.json
python formal_review.py review scope.json retained-run/evidence.json --json-out review.json --markdown-out review.md
```

Run from this profile directory or use full script paths. `proof` is relative to
`retained-run`. Capture reads files and never executes the SBY configuration.
Use original context or the [template](capture-context.template.json), preserving
unknowns. Review embeds proof/cover/producer snapshots; native paths are relative
to the directory containing `evidence.json`. Read [FORMAT.md](FORMAT.md) for the
qualified reader shape. The AI workflow can use other native evidence with its
own explicit support boundary.

## Native example

With the existing qualified Linux tools described in [NATIVE.md](NATIVE.md):

```sh
python examples/create_example.py new-example --sby /path/to/sby/sbysrc/sby.py --yosys-prefix /path/to/prefix
python formal_review.py review new-example/wake-guaranteed/scope.json new-example/wake-guaranteed/evidence.json
```

The prefix contains `bin/yosys`, `bin/yosys-smtbmc`, `bin/z3` and `share/yosys`.
The recipe runs the owned models, installs nothing and requires a new output path.
It retains 18 tasks, eight review bundles and independent finite-state/witness checks.

| Control | Review result |
|---|---|
| Excluding required wake/backpressure activation | Incomplete: green proof, missing activation/support |
| Unrestricted inputs | Review required: matched property counterexample |
| Held request/data with separately proved producer | Supported within the declared logical model |
| One-state cover attempt | Incomplete: no witness within that depth |
| Short BMC pass | Incomplete: bounded pass only |

Wake and stream qualify one workflow stage; they are not separate tools or a
claim about every request/stream protocol.

## Results and tests

Review exits: `0` supported within the declared model; `1` known review finding;
`2` incomplete; `3` invalid input/I/O. Findings retain accompanying gaps. Capture
exit `0` means a complete parsed observation, including native FAIL; it is not an
applicability verdict. Unknown execution returns `2`.

```sh
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_FORMAL_EXAMPLE` to the native example root to recheck all bundles
and real witnesses on Linux or Windows. Other tests use synthetic parser fixtures
and do not claim solver execution. This profile does not automatically remove
assumptions, accept proofs or certify composition, physical clocks/resets,
liveness, property sufficiency or signoff.
