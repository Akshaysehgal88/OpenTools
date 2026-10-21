# Scan closure population review

This activity starts after insertion/reordering or a state-role/exclusion change.
Its output supplements the existing DFT closure review and handoff.

Establish the selected design/configuration and the independent required state
source before reading chain counts. Include functional sequential state outside
the chains. Record clock/power grouping, test intent, correspondence across views
and the owner who can accept non-scan treatment. Keep an incomplete denominator
open; observed scan members cannot define what should have been scanned.

Compare native pre-insertion census, post-insertion census/connectivity and the
actual chain report. Retain native diagnostics and source/library/configuration
identities. Account for every required state as scanned, currently justified
outside scan, mismatched or unresolved. A completed insertion can omit a required
flop; a reduced scan count can also be valid under a supported exclusion.

For each exclusion, inspect its reason, revision, authority and current role,
clock/power premises. Distinguish an old retained-only role from current functional
use. An owner label or matching digest cannot establish that the rationale is
true. Check the original source when matching roster/policy metadata may share
an omission or a weakened requirement. Preserve current native state when the
exclusion population appears unchanged but its premise has changed.

Use the [saved-data helper](GUIDE.md) when its [native profile](FORMAT.md) applies,
or use the team's native reports and another source-backed method. Its structural
checks do not limit the AI review or supply ATPG evidence. Optional scoped context
uses the [consumer interface](../../../../CONTEXT_PORT.md); continue independently
when it is unavailable and reject stale or foreign context as a current basis.

Produce this compact handoff record beside the original artifacts:

| Field | Record |
|---|---|
| Boundary | Domain/stage, design/configuration, selected population and receiving owner |
| Required source | Independent required/non-scan intent and completeness basis |
| Native evidence | Tool/version, original commands/sources, pre/post census, membership and diagnostics |
| Correspondence | State identities, scan cell mapping and clock/power grouping; unresolved mappings |
| Per-state result | Required treatment, native membership, exclusion ID/reason/revision, applicable premises |
| Changes | Missing state, membership/exclusion drift and false or unavailable premises |
| Decision | Supported finding or explicit gap; keep native completion separate from acceptance |
| Next action | Responsible owner, supported insertion/policy correction or narrowly justified evidence request |
| Acceptance/recheck | Owner decision/reference or pending; source, role, clock/power, insertion and policy changes to recheck |

Retain admitted exclusions in the population. Do not silently delete a missing
state, rewrite native reports, weaken required intent or infer fault coverage from
membership. Check fresh native output after an authorized insertion correction;
retrieve matching retained evidence when the problem is merely a stale attachment.
