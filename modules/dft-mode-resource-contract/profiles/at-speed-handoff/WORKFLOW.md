# At-speed test handoff review

Start when the OCC sequence, pattern recipe, mode cases or STA setup changes.
Establish the launch/capture scheme, selected domain/path, incoming/generated
clocks, control setup requirements and receiving owner from independent intent.
Identify actual pattern/ATPG and STA scenarios separately; an owned recipe or a
matching label cannot replace a native ATPG artifact.

Resolve the native clock roots, targets, waveforms, mode cases and exception
endpoint populations. Inspect the consumed constraints. A false path valid in
shift can mask a required capture path while the pulse sequence and simulation
still pass. Native path disappearance is a consequence only when a comparable
unmasked path witness exists; zero paths in both analyses proves no such masking.

Compare actual OCC edges, source-edge selection and reset/scan-enable stability
with the recipe. Check controls before the pulse, including required history.
Do not accept an edge value as proof that setup was met. Preserve differences
between native checker expectations and the independent receiving requirement.
Inspect source when agreeing recipe/metadata could weaken the original guard or
hide a later pulse. Keep incomplete windows and unknown cases unresolved.

Use the team's tools or the optional [saved-data helper](GUIDE.md) where its
[profile](FORMAT.md) applies. The helper is an instrument, not the boundary of
analysis. Check original source/command/configuration identities before joining
STA and behavior. Reuse a matching retained artifact when it answers the task;
do not rewrite its scenario label to make a stale attachment fit.

Record a compact handoff beside the original evidence:

| Field | Record |
|---|---|
| Claim and scope | Scheme, selected domain/path, revision/configuration and receiving activity |
| Independent intent | Recipe source, pulse/source-edge schedule, control guards and accepted timing assumptions |
| Scenario identities | Actual pattern/ATPG, OCC and STA sources; owned/manual/unknown status kept explicit |
| Native timing | Source/generated clock mapping, cases, consumed exception populations and path visibility |
| Observed behavior | Pulse timestamps, sampled widths, reset/enable values and pre-pulse history |
| Findings/gaps | Disagreement, masking consequence or unsupported premise with exact artifact locations |
| Next action | Owner, supported recipe/control/scenario correction and discriminating evidence request |
| Handoff/recheck | Receiving acceptance reference or pending; recipe, clock, mode, source and exception changes to recheck |

Keep shift-only exclusions scoped to their intended mode. Propose a control or
scenario correction from supported intent, then inspect fresh native evidence
where needed. Do not lower the requested guard or substitute membership/logical
simulation for delay-fault coverage, characterized timing or physical pulse quality.

Optional questions/context follow the [consumer interface](../../../../CONTEXT_PORT.md).
No DVIT connection is required. Missing, stale or foreign context cannot supply
current scenario applicability or authorize an engineering acceptance.
