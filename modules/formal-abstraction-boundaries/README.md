# Formal abstraction boundaries

Review a changed abstraction before using its proof result. The optional helper
compares complete finite combinational boundary relations, retains native property
outcomes and identifies excluded concrete behavior or extra abstract behavior.
Use [SKILL.md](SKILL.md) with your existing AI host; [REVIEW.md](REVIEW.md) gives
the handoff record. No provider SDK or DVIT connection is required.

## Saved-data review

Requires Python 3.10+ and the standard library.

```sh
python boundary_check.py capture retained-run abstract capture-context.json --output snapshot.json
python boundary_check.py review contract.json retained-run/evidence.json --json-out review.json --markdown-out review.md
```

Capture reads the original files and never runs `run.ys`. Review paths are
relative to the directory containing `evidence.json`. Read [FORMAT.md](FORMAT.md)
for the exact reader boundary and [context template](capture-context.template.json).
Outputs require new paths. Exit `0`: supported within the finite boundary;
`1`: review finding; `2`: incomplete; `3`: invalid input/I/O. Capture exit `0`
means parsed evidence, including a native property FAIL, not proof acceptance.

## Native example

With an existing Linux Yosys0.33 prefix matching [FORMAT.md](FORMAT.md):

```sh
python examples/create_example.py new-example --yosys-prefix /path/to/prefix
python boundary_check.py review new-example/operands-exact/contract.json new-example/operands-exact/evidence.json
```

The prefix contains `bin/yosys` and required runtime libraries. The recipe installs
nothing and executes only owned example scripts. Sixteen native runs retain
before/after cut models, complete SAT tuples, property outcomes and witnesses.
An independent exhaustive arithmetic/tag reference checks all 202 captured tuples.

| Control | Observation |
|---|---|
| Independent cut outputs | Conservative expansion; abstract failure can be absent from the concrete relation |
| Correlation with concrete correspondence | Equal selected relation and passing property |
| Unsupported correlation hiding a concrete fault | Green abstract property excludes concrete behavior |
| Restricting allowed input values | Smaller relation; green result cannot cover omitted modes |

## Tests and limits

```sh
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_ABSTRACTION_EXAMPLE` to the native example root for real artifact
and witness checks on Linux or Windows. Core unit tests isolate relation logic
with synthetic records; they do not claim native execution.

The AI workflow can review broader company-native abstractions. This helper
qualifies a stateless finite class, not arbitrary abstraction soundness, sequential
or memory refinement, liveness or signoff. It does not automatically refine cuts,
remove premises or accept proofs.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
