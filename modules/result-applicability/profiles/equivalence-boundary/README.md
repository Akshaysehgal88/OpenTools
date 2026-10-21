# Equivalence comparison boundary

Review whether a saved native equivalence result covers an ECO's intended designs,
compare points and functional modes. Use it before accepting or reusing that result.
The receiving team's approved mapping and ECO intent remain the authority.

Use [WORKFLOW.md](WORKFLOW.md) with your existing AI assistant. Python 3.10+ and
the standard library suffice for saved-data review. No model SDK or DVIT is needed.

## Saved native evidence

From the repository or installed bundle root:

```sh
python modules/result-applicability/profiles/equivalence-boundary/equivalence_review.py capture evidence run evidence/context.json --output evidence/snapshot.json
python modules/result-applicability/profiles/equivalence-boundary/equivalence_review.py review evidence/intent.json evidence/snapshot.json --json-out review.json --markdown-out review.md
```

Fill [capture-context.template.json](capture-context.template.json) from the original
run and [intent.template.json](intent.template.json) from the independent ECO request.
See [FORMAT.md](FORMAT.md) for fields and [NATIVE.md](NATIVE.md) for retained artifacts.
Import reads data; it never executes the recorded script or command.

Review exits: `0` native result supports the declared scope; `1` known difference
or in-scope counterexample; `2` missing evidence; `3` invalid input/I/O. Findings
take precedence while retaining gaps. Capture exit 0 means import succeeded,
including when the native result is FAIL. Existing output files are preserved.

## Native boundary

The saved-data reader is qualified for **Yosys 0.33 (git sha1 2584903a060)**,
whole-miter SAT equivalence of defined, unsigned, stateless combinational designs.
It retains source bytes, resolved parameters, explicit point correspondence,
native restrictions and the original PASS/FAIL counterexample. A complete
combinational proof has no sequential, memory, reset-history or X-state claim.
Other native flows can be reviewed through the AI workflow with their own evidence
and stated limits; their formats are outside this reader.

A mode-0 pass cannot justify a mode-1 requirement. A mode-1 counterexample cannot
decide a mode-0-only claim. Mapping references are supplied, not authenticated.
This review does not approve an ECO, discover matching points or replace an engine.

## Examples and tests

The optional Linux example requires an existing qualified Yosys installation;
`--yosys-prefix` points to its `usr`-style directory containing `bin/yosys`.
It installs nothing. Choose a new output directory.

```sh
python modules/result-applicability/profiles/equivalence-boundary/examples/create_example.py example-output --yosys-prefix /opt/yosys-0.33/usr
python -m unittest discover -s modules/result-applicability/profiles/equivalence-boundary/tests -v
```

Arithmetic and pending/IRQ fixtures exercise the same review stage: equivalent
rewrites, seeded mode-dependent changes, legitimate narrow scope and an outside-scope
witness. Control interfaces include 8- and 32-bit selections. The example runs ten
native tasks and fourteen reviews; finite references qualify small examples, not
replace native verdicts. Set `OPENTOOLS_EQUIVALENCE_EXAMPLE` to its output directory
to enable saved-native tests. Synthetic approvals in fixtures are not real approvals.
