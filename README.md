# OpenTools

Semiconductor engineering tools for evidence review and simulation efficiency.
Each module includes an AI workflow, an optional command-line helper, input
formats, examples and tests. Use them with your existing simulator, build system
and AI subscription.

## Start here

```sh
python opentools.py catalog
```

Choose a module below, then follow its README. Load [SKILL.md](SKILL.md) in your
AI agent or use the [project-local installer](INSTALL.md) for Codex, Claude Code
or another Agent Skills host. The installer copies files; it does not install
models, native tools or DVIT.

For first use in an engineering project, follow [shared onboarding](ONBOARDING.md).
Your AI can discover local artifacts, establish intent and native entity mappings,
then retain a reusable project-local setup.

## Tools

| Module | Purpose |
|---|---|
| [Waiver revalidation](modules/waiver-revalidation/README.md) | Review suppression/scan-exclusion populations and current waiver premises. |
| [Coverage change audit](modules/coverage-change-audit/README.md) | Separate new hits from changed bins, exclusions and thresholds. |
| [Descriptor layout check](modules/descriptor-layout-check/README.md) | Review hardware/software layout and selected configuration consistency. |
| [Microarchitecture contract drift](modules/microarchitecture-contract-drift/README.md) | Review changed outstanding-demand and capacity obligations. |
| [Integration interface obligations](modules/integration-interface-obligations/README.md) | Review endpoint meaning and transient ownership/completion obligations. |
| [Address decode and attribute agreement](modules/address-decode-attribute-agreement/README.md) | Compare initiator-scoped routes, permissions, attributes and aliases. |
| [Side-effect and access-order review](modules/side-effect-access-order/README.md) | Review register side effects and diagnostic evidence across recovery. |
| [Clock mode and dependency review](modules/clock-mode-dependency-review/README.md) | Review clock-owner prerequisites and mode-transition waits. |
| [Timing endpoint review](modules/timing-endpoint-review/README.md) | Reconcile unconstrained endpoints with timing intent and current exemptions. |
| [Reset sequencing and state continuity](modules/reset-state-continuity/README.md) | Review clearing, retention, restart prerequisites and surviving pending work. |
| [Event delivery and acknowledgement review](modules/event-delivery-acknowledgement/README.md) | Trace interrupt, service, source-clear and wake observations separately. |
| [Low-power quiescence obligations](modules/low-power-quiescence-obligations/README.md) | Review owner drain and prerequisites throughout shutdown. |
| [Retention and restore consistency](modules/retention-restore-consistency/README.md) | Review restored bundles, first exposure and actual post-wake reads. |
| [Storage first-access readiness](modules/storage-first-access-readiness/README.md) | Review initialization coverage, release and internal reads before first access. |
| [Memory forward-progress dependencies](modules/memory-forward-progress-dependencies/README.md) | Review resource wait cycles, release paths and conditional blocking witnesses. |
| [Data ownership and visibility handoff](modules/data-ownership-visibility-handoff/README.md) | Review visibility, scoped ordering evidence, ownership and reuse. |
| [Execution-stage handoff readiness](modules/stage-handoff-readiness/README.md) | Review loaded image, entry/stack setup and readiness before control transfer. |
| [PPA comparison check](modules/ppa-comparison-check/README.md) | Check the conditions behind reported PPA deltas. |
| [Result applicability](modules/result-applicability/README.md) | Match a result to a claim; review formal premises and activation. |
| [Formal abstraction boundaries](modules/formal-abstraction-boundaries/README.md) | Review concrete/abstract correspondence and cutpoint counterexamples. |
| [Property activation obligations](modules/property-activation-obligations/README.md) | Review binds, clocks and activation at required mode/event slots. |
| [DFT mode resource contract](modules/dft-mode-resource-contract/README.md) | Review mode resources and at-speed recipe/clock/exception handoff. |
| [Macro view integration contract](modules/macro-view-integration-contract/README.md) | Review native macro pins, supplies, selected corner, placement and access before intake. |
| [Physical constraint intent review](modules/physical-constraint-intent-review/README.md) | Review a placement or constraint intervention against original region intent and native evidence. |
| [Power-delivery scenario basis](modules/power-delivery-scenario-basis/README.md) | Review native static IR evidence against supply, source, corner, load and operating-scenario requirements. |
| [Simulation cost audit](modules/simulation-cost-audit/README.md) | Account for elapsed time, overlap and resource observations. |
| [Build reuse](modules/build-reuse/README.md) | Review whether a compiled artifact fits another run. |
| [Checkpoint replay](modules/checkpoint-replay/README.md) | Check saved-state compatibility and replay observations. |
| [Waveform capture](modules/waveform-capture/README.md) | Plan signal selection and capture windows. |
| [Next-run planning](modules/next-run-planning/README.md) | Record the question, controls and expected outcomes of a run. |
| [Incremental regression](modules/incremental-regression/README.md) | Select an initial test stage and retain later obligations. |
| [Campaign progress](modules/campaign-progress/README.md) | Compare campaign evidence against declared objectives. |

## Integration

Start with saved exports from one existing run. Keep original artifacts and store
review records beside them. Each module documents its supported native versions,
exit codes and limits. Manual templates and executable inputs have separate formats.

The AI can use the bundled helpers or your existing engineering tools. No model
API or DVIT connection is required. Optional adapters can supply scoped context
through the [context interface](CONTEXT_PORT.md).

[DVIT's intent integrity layer](DVIT.md) connects requirements, rationale and
engineering evidence across revisions and dependent reviews. Its white papers
demonstrate recovered evidence gaps and useful engineering handoffs. Use it when
you want to carry an activity's intent into the wider design and verification
context; published connection details will be added when available.

See [installation](INSTALL.md), [usage conventions](USING_THE_GUIDES.md) and
[architecture](ARCHITECTURE.md).
