# Notice, evidence and review records

`opentools.erratum-notice.v1` contains a versioned supplied notice/source/owner,
one applicability predicate, scoped guard intervals, ordering/clock mitigation
premises and one dependent-exception premise. The [owned fixture](examples/fixture.py)
defines the full structure. The example notice `OWNED-E001` is synthetic.

Predicates support `all`, `any`, typed `equal` and finite `in` membership only.
Maximum depth is 5, with 48 nodes, 8 terms per group and 16 scalar membership
values. Each relationship/leaf has its own basis reference. Unknown fields or
missing rule sources remain unknown. False in `all` or true in `any` can decide
the selected condition while retaining unresolved sibling facts. No code or
arbitrary expression executes.

`opentools.erratum-request.v1` records the independent review question, owner,
scope, current review cut, `apply/retain/remove` intent, selected notice profile
and canonical JSON notice digest. It binds native identity, consumed source hashes,
original context/invocation and required source/model/image/guard fields.
An optional supplied approval binds status, source/decision, notice digest, scope,
mode, image, intent and review cut. Matching fields do not authenticate authority.

Each run preserves `device.cpp`, `device.cfg`, `firmware.txt`, `device` binary,
context, invocation, original captured notice/request, execution record, compiler
version and native stdout/stderr. Execution binds original file bytes; notice and
request content digests use sorted compact JSON separately. New notices/queries
may reuse retained facts; original captured sources and changed-source flags
remain in the report. Do not edit captured originals to create a new question.

The qualified Linux producer is an owned C++17 event-delivery model compiled
with **Ubuntu GCC 13.3.0**. It interprets one bounded command image, not a firmware
ISA. `BASE_FENCE` precedes the workaround phase; `WA_FENCE` does not mark baseline
ordering fixed. Trace records preserve command effects and actual active-clock
ticks. The selected checker tests accepted delivery of payload 42; completion and
its PASS/FAIL are separate.

Reported fuse `X` remains null. Private model configuration used by the independent
test oracle is not substituted for a missing consumer readout. Complete original
artifacts, current qualified producer, source/context/invocation bindings and the
completion marker are required. Intake executes no archived binary or source.

The unchanged parent comparator checks source correspondence with `any_observed`,
preserving a failed selected result. Separate comparisons check mitigation and
interaction premises. Approval correspondence, applicability, current mechanism
observations and outcome remain distinct. Guard checks use observed active ticks,
not just the requested guard argument or a workaround-enabled label.

`REVIEW_PACKET_ACCOUNTED` means the stated bounded review inputs correspond.
`REVIEW_REQUIRED` preserves known efficacy, timing, interaction, intent or approval
findings. `INAPPLICABLE_EVIDENCE` quarantines contrary source/scope correspondence.
`INCOMPLETE` retains missing or unknown premises. Findings take precedence while
retaining gaps. None of these statuses authorizes removal or release.

Limits: one supplied notice, one selected owned event path and dependent premise,
one operating configuration per observation, finite predicate and model bounds.
No real erratum discovery, silicon/ISA/power qualification, all-mode verification,
approval authentication or automatic action. Use the existing company process for
broader claims and keep its evidence qualification separate.
