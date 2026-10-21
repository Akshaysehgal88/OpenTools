# OpenTools

OpenTools helps semiconductor engineers review whether engineering evidence still
supports the original requirement, configuration and intended product behavior.
Use it for a specific workflow stage: a waiver change, a hardware/software handoff,
a timing exception, a test-mode setup, or a simulation-efficiency decision.

Created by **Akshay Sehgal**, owner of [DVIT](https://github.com/Akshaysehgal88/DVIT_PROD).

**Source-available:** [DVIT Utilities License v1.0](LICENSE) ·
[Attribution](NOTICE) · [Branding terms](BRANDING.txt).

## What you get

The current catalog contains **32 modules, 52 workflow activities and 67 optional
helpers**. Each module packages an AI workflow, engineering guidance, supported
record formats, examples and checks.

- A **module** groups a recurring part of an engineering flow.
- An **activity** is a bounded review within that module, with its own question,
  required evidence, interpretation and receiving owner.
- A **helper** provides a specific operation: comparison, capture, inventory,
  native export or a qualified example runner. Some helpers are supporting
  libraries or Tcl instrumentation, rather than standalone applications.

The existing AI agent does the source interpretation, native mapping and workflow
adaptation. Helpers make supported checks repeatable; they do not define the
limits of the agent's reasoning. OpenTools does not run inference or configure
a model account.

## Start here: give the repo to your agent

Clone the repository or make it available to a file/tool-enabled assistant:

```sh
git clone https://github.com/Akshaysehgal88/OpenTools.git
cd OpenTools
python opentools.py doctor
python opentools.py catalog
```

Then give the agent a concrete question and access to the relevant project. For
example:

> Read OpenTools' SKILL.md and ONBOARDING.md. Help me review whether our latest
> coverage increase supports the original closure objective for this configuration.
> Identify the relevant activity, inspect our existing coverage exports and
> exclusion decisions, and set up the smallest useful project-local integration.
> Use our existing tools and AI environment. Ask for missing intent or native
> mappings, validate the selected extraction method, and return findings with
> their original evidence and the next owner action.

The [root workflow](SKILL.md) routes the agent to the activity. An agent with
authorized file and shell access can install selected modules, inspect artifacts,
prepare a local profile and run applicable checks. A chat-only model needs your
runner to perform the file/tool steps; an API key alone is not that runner.

**You supply the engineering question and existing project context.** The agent
should establish the original intent, selected revision/configuration, native
objects, evidence method and receiving workflow. It should use company APIs,
reports and runners already available before introducing another exporter.

## Try a complete saved-data example

This example needs Python 3.10+ and the standard library. From the repository
root, with fresh output paths:

```sh
python modules/coverage-change-audit/examples/create_example.py .local/coverage-first-use
python modules/coverage-change-audit/coverage_audit.py compare .local/coverage-first-use/baseline.json .local/coverage-first-use/current.json --json-out .local/coverage-first-use/review.json --markdown-out .local/coverage-first-use/review.md
```

The comparison returns **exit 1**, an intentional review result. Twenty unhit
bins became ignore bins: the fraction rises from 180/200 to 180/180 without a new
hit. Open the Markdown report and inspect the retained original population,
kind changes and evidence. This is the gap a percentage-only comparison misses.

The [coverage guide](modules/coverage-change-audit/README.md) explains how to
replace the synthetic records with selected native exports and independently
reviewed definitions. The example runs no simulator and is not a production
coverage result. Each activity guide provides its own first-use path and expected
outcome.

## Choose a workflow stage

| Your current task | Useful starting point |
|---|---|
| Design or integration change | Interfaces, address maps, clocks/resets, low-power prerequisites, retained state, memory and execution handoffs |
| DV closure or checker integration | Waiver/exclusion validity, changed coverage populations, required checker observations and interaction evidence |
| Formal proof or ECO review | Assumption support, activation, abstraction correspondence and equivalence scope |
| DFT integration | Test-mode resources, scan population/exclusions, at-speed handoff, memory test/repair and fault-denominator review |
| PD / power-integrity handoff | Macro views, ECO report applicability, placement constraints, PPA comparison and static IR scenario basis |
| STA closure | Clock setup/lineage, exception reach, required scenarios, unconstrained endpoints and block-to-top timing budgets |
| Firmware / bring-up | First access, loaded-image handoff, reset/read side effects, observation timing and workaround applicability |
| Long simulation campaigns | Build reuse, checkpoint replay, focused waveform plans, staged regression, campaign accounting and next-run decisions |

OpenTools supplements native EDA engines, existing automation, review records and
signoff ownership. Individual helpers can replace a repetitive comparison or
evidence-accounting step. The activity guide identifies which step and which
native analyses remain necessary; no common result is a design-wide signoff.

## Install only what you need

You can use modules directly from the clone. To copy selected workflows and their
documentation into an existing engineering project:

```sh
python opentools.py install --host codex --project /work/chip --module coverage-change-audit --dry-run
python opentools.py install --host codex --project /work/chip --module coverage-change-audit
python opentools.py verify --host codex --project /work/chip
```

Replace `/work/chip` with an existing project directory; quote paths on Windows.
Repeat `--module` to select more modules, or omit it for the full catalog.

| Host option | Project-local package |
|---|---|
| `codex` | `<project>/.agents/skills/opentools/` |
| `claude` | `<project>/.claude/skills/opentools/` |
| `generic` | `<project>/.opentools/skills/opentools/` |

Open the installed package's `SKILL.md` in your host, or reload/start a session
using that host's normal discovery mechanism. A generic export must be opened or
registered in the existing agent. The installer copies a self-contained package,
including the license and attribution documents. It changes no global agent
instructions, model settings, EDA installation or project runner.

See [INSTALL.md](INSTALL.md) for updates, modified-file preservation and uninstall.
This repository README describes the whole catalog; selected installed packages
route through their root skill and the included module READMEs.

## Connect the activity to a real project

Start with one answerable question and one retained native run or artifact set.

1. **Select the activity.** Use `python opentools.py onboard list` or the module
   guide. Match the engineering stage, not only a familiar signal or tool name.
2. **Establish intent and scope.** Find the original requirement, acceptance
   condition, revision, configuration and applicable mode. Preserve exclusions
   and unknown requirements separately from favorable results.
3. **Resolve evidence.** Map actual design/tool entities, units and native result
   meaning. Reuse an existing export or collect the smallest missing evidence.
   Validate any new query/adapter against native/reference output and controls.
4. **Review.** Run a supported helper or use a separately validated native method.
   Keep machine findings, AI interpretation and unresolved questions identifiable.
5. **Integrate the handoff.** Attach the report to the existing ticket, review,
   regression or acceptance stage. The receiving team decides disposition.
6. **Retain and revalidate.** Save the source-backed setup and revisit affected
   obligations when requirements, mappings, scripts, modes or sources change.

For a reusable local setup, the agent can start here:

```sh
python opentools.py onboard list --module coverage-change-audit
python opentools.py onboard start --project /work/chip --module coverage-change-audit --workflow default --project-ref chip-A --question "Does this increase support the original closure objective?"
```

`start` returns **exit 2** because it creates an unreviewed draft. It inventories
selected artifacts and writes an ignored local work area, the original request,
intent draft and agent handoff; it runs no model or native command. The agent then
fills the record from real sources, validates mappings and uses `seal` / `review`
as described in [ONBOARDING.md](ONBOARDING.md) and [INTENT.md](INTENT.md).
An already answerable review does not require onboarding first.

## Native-tool adoption and prerequisites

The common launcher/installer uses Python 3.10+ and the standard library. Specific
capture helpers and native examples can need additional Python packages, a native
toolchain or a particular OS/version. Every activity guide separates that path
from saved-data review.

Many qualified examples use open EDA tools. Their versions and bounded native
profiles are stated in the relevant guide. A normalized record format is not a
claim that every Synopsys, Cadence or Siemens database can be read directly.
With another tool, the agent should use an available native API/report, establish
the original semantics and validate the mapping before relying on it.

No EDA tool, model or DVIT component is installed automatically. The launch and
install paths are exercised on Windows and Linux; macOS has not been qualified.

## Module catalog

Use the module README to find its activities, helpers, inputs, commands and
integration procedure. Discover the current machine-readable catalog with
`python opentools.py catalog --json`; activity contracts come from
`python opentools.py onboard list`.

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

## Intent integrity and optional DVIT

The useful question is whether evidence answers the original engineering
obligation as the design and configuration evolve. OpenTools captures the intent
needed for one activity and preserves its connection to actual observations.

[DVIT's intent integrity layer](DVIT.md) extends that context across requirements,
rationale, revisions and dependent reviews. Its white papers report recovered
evidence gaps, actionable handoffs and scoped generation savings. The planned
public production repository is
[DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).

Local/company sources remain fully useful. A DVIT connection is optional and uses
a separately configured adapter with published interfaces; see
[CONTEXT_PORT.md](CONTEXT_PORT.md). Reading a guide does not enable a provider.

## License and credit

Original repository: [Akshaysehgal88/OpenTools](https://github.com/Akshaysehgal88/OpenTools).

The custom [DVIT Utilities Source-Available License](LICENSE) permits use and
modification for personal or business work, including qualifying commercial
products. Free forks retain the original credit and links. Selling or commercially
repackaging the utilities, or offering paid access to their functionality, requires
Akshay Sehgal's separate written permission under that license.

Keep [NOTICE](NOTICE) and follow [BRANDING.txt](BRANDING.txt) with distributed
copies. This is source-available software; its resale restrictions mean it is not
OSI-approved open-source software.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
