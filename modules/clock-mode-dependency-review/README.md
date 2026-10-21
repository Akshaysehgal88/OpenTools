# Clock mode and dependency review

Review the clock and acknowledgement prerequisites of a selected boot, wake or
mode transition. Use the [AI workflow](SKILL.md) with existing RTL, clock exports,
sequencer/firmware source and native observations. It works with your current AI
host and engineering tools; DVIT is optional.

The optional Python 3.10+ helper expands declared root/gated clock lineage into
positive prerequisites, checks goal derivability and lists unresolved dependency
cycles. No external packages are needed.

```sh
python examples/create_example.py /tmp/clock-example --case boot-cycle
python clock_review.py analyze /tmp/clock-example/model.json /tmp/clock-example/request.json
```

The example's gate waits for an acknowledgement produced only on the gated clock.
`boot-fixed` and `wake-fixed` provide valid controls. `wake-no-restore` lacks a
restore prerequisite and has no cycle. See [native controls](examples/NATIVE.md).

Use new paths with `--json-out` and `--markdown-out` to retain reports. Exit codes:
0 goals derivable in the declared model, 1 review required, 2 incomplete, 3 invalid
input or I/O error. Findings retain accompanying gaps; inputs are never overwritten.

## Supply the model

Start from the consumed native configuration and the actual owner of each clock,
gate, reset and readiness event. Model only prerequisites whose applicability
you can support. [FORMAT.md](FORMAT.md) describes the positive availability
abstraction. `inputs_complete` declares completeness for that selected abstraction;
it does not attest to the full design. The example is an owned source mapping,
not a general RTL or SDC extractor.

A favorable model can have a wrong initial seed or clock-owner mapping. Inspect
native source and observations even when all supplied goals are derivable. A
blocked goal describes the supplied model; it does not prove runtime deadlock.

## Boundaries

For timing clock definitions and selected-mode endpoint coverage, use the
[STA clock lineage profile](profiles/sta-lineage/README.md). It reviews actual
clock collections, resolved generated relationships, cases and required consumers.

The availability helper models facts becoming available, conjunctive prerequisites and
alternative enabling rules. It does not model deassertion, inhibitors, mutual
exclusion, deadlines, pulse persistence, fairness or state-dependent ordering.
Use native temporal analysis for those claims. That abstraction does not check
clock waveform quality, ICG implementation, CDC/RDC, timing constraints or
clock-tree signoff. The STA profile has its own bounded clock-setup qualification.

Install this module using the repository's project-local installer. Optional
[context sources](../../CONTEXT_PORT.md) may provide scoped clock ownership,
mode applicability and dependent waits. Nothing installs or downloads DVIT.

For a real clock-control example, see
[OpenTitan clock-manager operation](https://opentitan.org/book/hw/top_earlgrey/ip_autogen/clkmgr/doc/theory_of_operation.html).
Its implementation and clock-group rules are design-specific; they are not
assumptions imposed by this tool.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
