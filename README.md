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

## Tools

| Module | Purpose |
|---|---|
| [Waiver revalidation](modules/waiver-revalidation/README.md) | Compare suppression populations and recorded waiver premises. |
| [Coverage change audit](modules/coverage-change-audit/README.md) | Separate new hits from changed bins, exclusions and thresholds. |
| [Descriptor layout check](modules/descriptor-layout-check/README.md) | Compare hardware and firmware binary layouts. |
| [PPA comparison check](modules/ppa-comparison-check/README.md) | Check the conditions behind reported PPA deltas. |
| [Result applicability](modules/result-applicability/README.md) | Match a result to a requested configuration and claim. |
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

See [installation](INSTALL.md), [usage conventions](USING_THE_GUIDES.md) and
[architecture](ARCHITECTURE.md).
