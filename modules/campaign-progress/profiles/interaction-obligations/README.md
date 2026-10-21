# Cross-mode obligation evidence

Use this activity during functional scenario closure when two individually tested
features share state or a dependency. An event arriving during consumer hold,
pending work entering sleep, or acknowledgement coinciding with a new arrival
can exercise a different obligation from either feature alone. This review asks
whether the **required interaction actually occurred and was checked**.

The users are feature owners, integration DV engineers and campaign reviewers.
Run it after defining the interaction from the design contract, after collecting
scenario evidence, and again after changing the state ownership, mode policy or
checker. It supplements your test plan, assertions, scoreboards and coverage
database. It replaces manual reconciliation of the selected interaction roster
with retained native events; it does not generate an exhaustive feature product
or replace the functional oracle.

## Adopt with an AI assistant

Give your file/tool-enabled assistant [WORKFLOW.md](WORKFLOW.md) and this request:

> Review the original shared-state contract and identify the selected producer,
> consumer and resource relationships. Establish which combined transitions are
> required, which are explicitly inapplicable in this configuration and why. Map
> the actual scenario and checker evidence to those obligations. Preserve absent
> combinations, incomplete windows, native failures and disabled checking; do not
> infer closure from separate feature passes.

Use the repository [ONBOARDING.md](../../../../ONBOARDING.md) for project-local
installation. Select `campaign-progress` / `interaction-obligations`. Python
3.10+ and the standard library suffice for saved-data review. The assistant can
work with other company evidence and a validated exporter; the bundled reader
has the narrower native boundary below. DVIT is optional.

## Try the owned example

Run these commands from
`modules/campaign-progress/profiles/interaction-obligations`. If you already have
the complete retained example, place it at `.local/interactions-native` and skip
native generation. Otherwise use Linux with an existing Verilator 5.020, GCC
C++17 and Make:

```sh
python examples/run_native.py .local/interactions-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Replace the executable and runtime paths. The recipe installs nothing. Its two
builds serve 26 runs and 30 review packets; joined packets reuse existing runs.
The independently stated [example contract](examples/CONTRACT.md) selects
arrival-under-hold, pending-enters-hold and acknowledgement-with-new-arrival.

Start with the run containing only separate feature activity:

```sh
python interaction_check.py review .local/interactions-native/interrupt-separate-good/plan.json .local/interactions-native/interrupt-separate-good/corpus.json --json-out .local/interactions-native/interrupt-separate-good/new-review.json --markdown-out .local/interactions-native/interrupt-separate-good/new-review.md
```

Expected exit: **2**, `incomplete`. The native run passes, but separate event,
hold and acknowledgement activity does not establish the selected combined
obligations. Open the Markdown report to see the absent triggers.

Then review a portfolio that actually exercises them:

```sh
python interaction_check.py review .local/interactions-native/interrupt-portfolio-good/plan.json .local/interactions-native/interrupt-portfolio-good/corpus.json --json-out .local/interactions-native/interrupt-portfolio-good/new-review.json --markdown-out .local/interactions-native/interrupt-portfolio-good/new-review.md
python interaction_check.py review .local/interactions-native/interrupt-portfolio-bug/plan.json .local/interactions-native/interrupt-portfolio-bug/corpus.json --json-out .local/interactions-native/interrupt-portfolio-bug/new-review.json --markdown-out .local/interactions-native/interrupt-portfolio-bug/new-review.md
```

The good portfolio exits **0**, `selected_obligations_supported`. The defective
portfolio exits **1**, retaining the native comparison failures and their
interaction witnesses. These are finite observations of the named obligations,
not a proof of all possible interleavings.

Every output path must be new. Choose different report names for another run.
Preserve the complete archive, original IDs and relative directory structure;
copying only a receipt cannot support artifact revalidation.

## Helpers, inputs and features

| Operation | Purpose |
|---|---|
| `interaction_check.py capture ROOT WORKDIR CONTEXT --output RECEIPT` | Imports one original run without executing its recorded commands; retains native frames, checker actions, source identity and verdict. Prints `receipt_sha256` for corpus assembly. |
| `interaction_check.py review PLAN CORPUS` | Validates the selected population, source/configuration relationships, applicability, actual trigger occurrences, complete observation windows and required checking. |
| `--json-out` / `--markdown-out` | Saves the structured evidence review and a readable owner handoff. The review is also printed as JSON. |

Prepare the records in this order:

1. [plan.template.json](plan.template.json): source the claim, owner, complete
   requested population, original run identities and obligations independently
   of the receipts. Each obligation names the resource, producer, consumer, risk,
   revision and design/configuration binding.
2. [capture-context.template.json](capture-context.template.json): identify the
   original run/scenario, instrumentation/oracle sources, clock/reset and eight
   native port roles. Retain the complete native artifact set in [FORMAT.md](FORMAT.md).
3. [corpus.template.json](corpus.template.json): list captured receipt paths and
   their exact byte SHA-256 values, using the capture command's output. Declare
   whether the requested collection is complete.

A normal per-run capture looks like this after you have retained `scenario/run`
and completed its independent context:

```sh
python interaction_check.py capture scenario run scenario/capture-context.json --output scenario/native.json
```

Receipt artifact paths resolve from that receipt's parent. Corpus receipt paths
are relative POSIX paths inside the corpus directory. Keep the corpus and its
referenced receipts/artifacts together when joining runs.

Triggers are explicit conjunctions of Boolean frame values at the current or
previous sampled edge. They locate occurrences already in the evidence. A
required observation spans 0–64 following edges, with actual checker actions on
the required post-state or delivery value. Initialization reset inside a window
leaves it unresolved. Consumer hold is a separate signal from initialization
reset.

Applicability is `applicable`, `not_applicable` or `unknown`. A reviewed
nonapplicability needs matching configuration facts and a sourced reason. For
example, a discard configuration can legitimately change a retention obligation;
it does not make acknowledgement/new-arrival behavior disappear. Missing
activity is never a basis for declaring an obligation inapplicable.

## Place it in your workflow

1. Review the architecture/state-transition source with the feature owner. Choose
   the workflow boundary and selected interaction population before querying
   available passing scenarios.
2. Define triggers, required windows and checking from that source. Check that
   the observer can distinguish a new arrival, old pending state, acknowledgement
   and delivery in the relevant mode.
3. Retain the existing simulator's sources, XML, executable, commands, journals
   and outcomes. Bind run/source/configuration identities to the original plan.
4. Capture each run and assemble the corpus. Preserve independent requested runs
   even when they did not execute or their evidence is missing.
5. Review and send each finding or gap to its feature/checker owner. A passing
   occurrence in another run does not erase an observed failure.
6. Fix the implementation, checker, scenario or sourced applicability decision,
   then rerun and revalidate. Carry named qualified obligations into campaign
   accounting with the original native verdicts.

The bundled data-only reader supports **Verilator 5.020**, one flat top, one
positive-edge clock and finite Boolean event/hold/ack/retain frames with explicit
mapping. Instrumentation and expected-state equations still need source review.
Arbitrary UVM logs, different sampling models and other EDA tools need an adapter
validated against their original evidence; renaming fields is insufficient.

## Read the outcome

| Review exit | Meaning |
|---:|---|
| 0 | `selected_obligations_supported` in the declared scope and retained windows. |
| 1 | Known difference, native mismatch or invalid required checking; inspect witnesses before attributing a hardware defect. |
| 2 | Required occurrence, source, scope, population or complete observation window is missing. |
| 3 | Invalid record/artifact or I/O. Repair the package before interpreting it. |

Argument errors use exit 2. Capture exit 0 means successful import, including
native FAIL. Findings retain coexisting gaps. An empty or entirely inapplicable
roster cannot establish closure. Named attainment establishes neither exhaustive
interaction coverage nor oracle adequacy, unbounded liveness, physical reset
behavior or signoff.

The reset/interrupt and sleep/maintenance fixtures vary native names and reset
polarity. Independent equations qualify their recorded samples and actions. For
the retained collection, set `OPENTOOLS_INTERACTION_EXAMPLE` to its root and run:

```sh
python -m unittest discover -s tests -v
```

Keep the plan, source rationale, native collection, reports and revalidation
decision together. Optional DVIT intent/dependency context can expose missing
relationships or stale rationale beyond what an isolated run contains; the same
workflow remains usable with locally maintained design sources.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
