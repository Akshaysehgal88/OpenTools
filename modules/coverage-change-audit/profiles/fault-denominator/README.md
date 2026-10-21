# Fault-coverage denominator review

Review test-coverage closure after fault definitions, constraints, patterns,
classification rules or exclusions change. Use the [AI workflow](WORKFLOW.md)
with the team's native reports and [review record](review-record.json). Existing
AI subscriptions and tools are sufficient; the helper and DVIT are optional.

Keep the original fault objective, collapsed correspondence, native classes,
exclusions and reported metric separate. Return a population/change table,
source-backed interpretation, missing evidence and revalidation actions to the
test-coverage owner. An approved exclusion can explain an increase without
representing additional fault detection.

The optional Python 3.10+ helper compares retained Verilator 5.020 campaigns for
one owned finite single-site stuck-at model. It preserves the original census
and response-based collapse map. This profile is separate from the parent
functional-bin comparator; fault classes are never converted into UCIS bins.

```sh
python fault_audit.py compare baseline/run baseline/context.json current/run current/context.json current/policy.json
python fault_audit.py capture current/run current/context.json --output captured.json
```

Exit codes: 0 aligned within the supplied objective, 1 changes requiring review,
2 incomplete evidence, 3 invalid input. `--output` creates a new file. Every review
recaptures the original native artifacts; retained commands are never executed.

The examples compare two different combinational logic networks. Each has a
denominator-only increase, unchanged control, added selected patterns, reviewed
exclusion, changed mode, changed metric, collapsed score, aborted campaign and
unknown class. Native integer fractions keep their own definitions.
See [formats and reproduction](FORMAT.md).

Qualification covers declared injection sites, not all netlist pins. Finite
untestability and response equivalence apply only to the exact legal input space.
Commercial ATPG, transition/delay faults, scan protocols, production collapse
rules and signoff need their actual native evidence and separate qualification.
