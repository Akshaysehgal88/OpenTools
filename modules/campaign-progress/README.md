# Campaign progress

For checker integration and observation validity, use the
[checker observation profile](profiles/checker-observation/README.md). It reviews
accepted/completed identities, checker sampling and enable intervals, then reuses
this module's exposure accounting.

For source-backed combined transitions, use the
[interaction obligation profile](profiles/interaction-obligations/README.md).
It audits an explicit roster against existing scenario/checker windows and reuses
named-goal accounting; separate feature passes do not close missing interactions.

Compare saved campaign exports against declared objectives. Separate named
coverage goals, effective event counts, required execution and resource observations.
Use [SKILL.md](SKILL.md) with your existing AI agent and review process. The optional
offline helper requires Python 3.10+ and the standard library; see [AI_USAGE.md](AI_USAGE.md).

## Quick start

From this module directory:

```sh
python examples/create_example.py demo
python campaign_progress.py summarize demo/contract.json demo/before.json demo/after.json --output demo/review.json --markdown demo/review.md
python campaign_progress.py digest demo/contract.json
```

The synthetic campaign adds no coverage goal, while effective checked handshakes
rise from 64 to 128 against a target of 192. The remaining run and unhit goal stay
required. Use a new directory. Record the engineering decision in your existing
review system or [DECISION.md](DECISION.md).

## Integration

Start from an independent [objective contract](record.template.json), full required
population and current policy. Translate native states with original values and
references. Compare cumulative exports over a known interval. Preserve queued,
running, failed, aborted, not-run and missing records separately.

Bind configuration, model and measurement definitions. The coverage profile uses
Boolean named goals with an explicit population; richer native coverage needs a
qualified translation. Changed definitions or denominators block comparability.

Effective exposure uses source-qualified integer event ranges. Overlap counts
once, and cumulative snapshots are compared rather than added. Inspect the native
counter's workload/checker meaning: elapsed simulation, seed count and different
labels do not prove fresh effective events or independent trials. Failed prefixes
are eligible only under explicit objective policy.

Keep resource observations separate, with units/origin/scope. Statistical assurance
objectives require an independently qualified method; this helper does not infer
confidence, resource forecasts or whole-workflow savings. See [FORMAT.md](FORMAT.md).

## Limits and status

The [Linux Verilator recipe](examples/verilator/README.md) demonstrates productive
work during a coverage plateau, ineffective runs, changed configuration/denominator,
a failed prefix and a missing export. Inspect source counters even when the packet
passes structural checks. A successful process exit is not automatically a test pass.

`0` recorded progress, including unmet objectives or measured zero effectiveness;
`1` contradictions/execution findings; `2` missing context; `3` invalid input/I/O.
No result grants stopping or signoff authority. This is an offline review tool,
with no live monitor, scheduler, job stopper or DVSim/UVM importer.

```sh
python -m unittest discover -s tests -v
```

Core tests run on Windows/Linux. Native support is limited to the documented fixture.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
