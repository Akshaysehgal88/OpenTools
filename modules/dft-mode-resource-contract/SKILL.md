---
name: dft-mode-resource-contract
description: Review DFT mode resources and at-speed recipe/STA alignment before test handoff, using independent clock/reset/enable/power/access requirements and existing native engineering evidence.
---

# DFT mode resource review

For first use in a project or changed tool/entity mappings, follow the
[shared onboarding](../../ONBOARDING.md). Reuse applicable local setup; an
existing evidence review does not require restarting onboarding.


For an OCC recipe, launch/capture mode or STA constraint handoff, follow the
[at-speed workflow](profiles/at-speed-handoff/WORKFLOW.md). It compares native
clock/exception populations and observed pulse/control timing with independent
intent. Keep native ATPG, characterized timing and physical pulse-quality claims
separate; continue with the team's tools beyond the bounded saved-data profile.

Establish the selected test mode, phase sequence, domain boundaries, lifecycle
policy and receiving owner. This workflow covers mode setup and resource
acceptance. Chain-population closure and at-speed timing need their own evidence.

Read the team's required mode table before interpreting results. Identify the
clock source/gating path, reset polarity and masking path, scan-enable schedule,
powered/isolation state, access prerequisite and timing scenario for each phase.
Include dependencies outside the selected hierarchy. Preserve distinct functional
debug and manufacturing authorization policies.

Compare those requirements with original native connectivity/constraints and
actual observed control/serial behavior. Check source/configuration identities,
port meanings, model assumptions and whether stimulus exercises the intended
load, capture and unload. A connected chain or a passing denial test does not
establish available test resources. An unresolved constraint remains unresolved.
Inspect source when agreeing tables and reports might share an omitted dependency.

Use the team's tools or the optional [saved-data reader](README.md) when its
[native profile](FORMAT.md) applies. Keep native failures intact and quarantine
stale or foreign evidence before attributing it to this mode. The reader does
not establish that requirements or owner references are correct. Its finite
example is not the acceptance boundary for the wider review.

Produce the [review record](REVIEW.md): phase/resource findings, source evidence,
open dependencies, owner and recheck trigger. Propose the smallest correction
supported by the intended design/policy, then obtain a fresh native run under
the corrected setup. Do not treat access bypass or a weaker requirement as a fix.
Leave physical power, clock implementation, timing, authorization and coverage
claims open until their required evidence is present.

Optional external context follows the [context interface](../../CONTEXT_PORT.md).
Use supplied artifacts without requiring DVIT or installing another service.
