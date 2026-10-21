# Clock mode and dependency review

Use this module when a boot, wake or mode transition waits for clocked work that
may depend on the transition itself. It makes the **clock owner, gate prerequisite
and acknowledgement producer** explicit, then asks whether the requested readiness
facts can be established in the selected mode.

This belongs in clock/reset sequencing design review, firmware integration and
transition verification. A typical trigger is a gate-enable change, a new wake
source, a restore prerequisite or a readiness timeout. Architecture, RTL, firmware
and DV owners can use the report to reconcile their dependency assumptions.

The module has two activities:

| Activity | Place in the flow |
|---|---|
| Default: positive prerequisite analysis | Review whether the selected boot/wake goals are derivable from declared initial facts, producers and clock lineage. |
| [STA lineage](profiles/sta-lineage/README.md) | Review actual timing-clock definitions, generated relationships and selected-mode consumer coverage against independent intent. |

The default activity supplements a sequencer review and native transition tests.
It replaces manually following the selected prerequisite graph. It does not
replace temporal verification, physical clock checks or timing analysis.

## First use

Python 3.10+ and the standard library are sufficient. From
`modules/clock-mode-dependency-review`:

```sh
python examples/create_example.py .local/clock-cycle --case boot-cycle
python clock_review.py analyze .local/clock-cycle/model.json .local/clock-cycle/request.json --json-out .local/clock-cycle/review.json --markdown-out .local/clock-cycle/review.md
```

Expected exit: **1**, `review_required`. The gate-enable rule waits for
`worker_ready`, but the worker can produce that acknowledgement only when its
gated clock is available. The report expands clock prerequisites and identifies
the unresolved cycle and requested goal. This is a finding in the supplied
availability model; check the real design before calling it a runtime deadlock.

Compare a repaired dependency:

```sh
python examples/create_example.py .local/clock-fixed --case boot-fixed
python clock_review.py analyze .local/clock-fixed/model.json .local/clock-fixed/request.json --json-out .local/clock-fixed/review.json --markdown-out .local/clock-fixed/review.md
```

Expected exit: **0**, `derivable_within_declared_model`. Gate enable no longer
waits for the acknowledgement it enables. The `wake-cycle` and `wake-fixed`
cases add a restore prerequisite. `wake-no-restore` is blocked **without** a
cycle because restore readiness has no supplied producer.

Example and report paths must be new; output parents must exist. JSON retains
expanded rules, goal states, derivable facts, cycle candidates, findings and gaps.
Markdown is the readable owner handoff.

## What the helper does

| Operation | Feature |
|---|---|
| `clock_review.py analyze MODEL REQUEST` | Expands each producer's explicit requirements with its clock-lineage availability facts, computes positive closure and reviews requested goals. |
| Candidate-cycle reporting | Identifies strongly connected groups among facts not already derivable; alternative enabling rules or an initial seed can break a cycle. |
| Unknown-state review | Separates a dependence on unknown initial state from a goal unreachable in a complete declared abstraction. |
| `clock_review.py digest MODEL` | Prints the canonical JSON SHA-256 used by the independent request's `model_sha256` binding. |
| `--json-out` / `--markdown-out` | Writes structured and readable reports without overwriting inputs. |

Start with [FORMAT.md](FORMAT.md) and the worked generator's records. The model
contains facts, clocks and producer rules; the request contains the required
consumer goals.

- Facts name their owner, source and initial state. `false` means unavailable
  initially, not permanently impossible; a producer can establish it. `null`
  means unknown.
- Each clock has an availability fact and one explicit parent, or is a root.
  Resolve mux selection for the specific mode before exporting this lineage.
- A rule needs all listed facts **and** the availability facts along its clock
  lineage. Multiple rules producing the same fact are alternative enabling paths.
  An explicitly non-clocked producer uses `clock_ref: null` with a sourced basis.
- Scope identifies project, configuration and mode. Request and model scopes,
  basis and digest must agree. `inputs_complete` refers to this selected
  abstraction, not every dependency in the chip.

These are positive, monotonic prerequisites: once available, a fact remains
available in the abstraction. There is no timing unit or transition latency in
this analysis.

## Integrate with RTL, firmware and clock-control review

1. Choose the original transition objective and its consumers. Read the actual
   sequencer/firmware, reset, gate and restore logic, plus the consumed mode
   configuration.
2. Identify the owner and producer of each readiness fact. Ask which clock the
   producer actually needs; matching signal names do not establish ownership.
3. Export only source-supported positive prerequisites. Include external seeds,
   bypass/wake paths and restore conditions that apply to the selected mode.
4. Bind the independent request to the reviewed model using `digest`, then
   analyze it. Review missing owners, unresolved lineage and unknown initial
   state before interpreting a favorable closure.
5. Inspect reported cycles and blocked goals in the source. A missing external
   prerequisite can block progress without a cycle; an incorrect initial seed
   can make a bad model look derivable.
6. Validate the corrected path in the existing native transition test and carry
   both static and observed evidence to the receiving owner. Revalidate after
   gate ownership, mode selection, reset, restore or wait-condition changes.

The [native controls](examples/NATIVE.md) compile an owned Verilator 5.020 design
on Linux and compare five boot/wake cases with an independent edge schedule.
They validate this source mapping and bounded progress. They are not a generic
RTL/SDC extractor or an integrated clock-gate qualification.

## AI-led adoption

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), the original transition
objective and your native source/configuration:

> Trace the producer and clock owner of every wait in this transition. Establish
> independent initial seeds and applicable restore/bypass paths. Build a
> source-backed positive prerequisite model where appropriate, and explain any
> temporal behavior that needs another method. Validate reported blockers in
> source and native observations before recommending a change.

Use [ONBOARDING.md](../../ONBOARDING.md) for project-local setup, module
`clock-mode-dependency-review`, activity `default` or `sta-lineage`. Your existing
AI host can inspect broader team-native evidence. Optional
[context sources](../../CONTEXT_PORT.md), including DVIT, can contribute scoped
ownership, intent and dependent-wait relationships. Local use requires none.

## Interpret the outcome and scope

| Exit | Meaning |
|---:|---|
| 0 | Requested goals are derivable within the declared positive model. |
| 1 | Known model findings require review, including unreachable requested goals. |
| 2 | Missing basis, unknown state or incomplete structural/context evidence. |
| 3 | Invalid input or I/O. |

Syntax errors use exit 2. Findings retain accompanying gaps.

Use native temporal analysis for deassertion, inhibitors, mutual exclusion,
ordering, deadlines, pulse persistence or fairness. This abstraction checks
neither physical waveform quality nor ICG implementation, CDC/RDC, timing
constraints or clock-tree signoff. The STA activity has its own bounded clock
setup reader and qualification.

Keep the original transition request, source-reviewed model, reports, native
control observations and owner decision together.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
