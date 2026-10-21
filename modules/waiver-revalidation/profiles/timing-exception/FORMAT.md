# Setup-exception profile records

`opentools.sta-exception-context.v1` identifies run, scope, design, configuration
and mode. Its setup contains explicit clocks, case ports, native cell patterns
and trace enable. `config.tcl` must match the original context. The supplied
collector writes source, invocation, tool, original-document and artifact hashes
before/after execution. Review reads data only; archived Tcl is never executed.

`opentools.sta-exception-native.v1` is JSON lines, each a string array:

| Record | Native observation |
|---|---|
| HEADER / END | Profile/run and completed export boundary |
| SELECTOR | Native resolved from/to instance names |
| CASE / CLOCK / MEMBERSHIP / REGISTER_PIN | Before/after case values, clocks and register clock-pin census/associations |
| DATA_PIN / OUTPUT_PIN | Native sequential data/output census; gates the selected scalar-register support boundary |
| PAIR / PATH | Per-phase instance pair count and all returned maximum-setup representative endpoints/slack |
| TRACE | Trace lifecycle, selector-constructor and application counts |
| APPLICATION / EDGE / RESOLVED | Applied exception family arguments and native resolved pin/clock/instance selectors |

The journal wraps the pinned native constructors after frontend resolution and
forwards their arguments/return values unchanged. Query selector constructors are
not applications. The application copies the resolved selectors immediately;
later queries may reuse released native handles. Handles are not public IDs.
An absent journal cannot be reconstructed from matching final path populations.

`opentools.sta-exception-evidence.v1` retains those records, source/file hashes,
execution and command. `capture` checks the pinned producers, native version,
completion marker, actual artifacts and original setup. Review recaptures and
checks the whole evidence record. Missing files, changed bytes, unsupported
records or mismatched saved evidence are invalid input. This is byte binding,
not cryptographic authentication of a tool run or source authority.

`opentools.sta-exception-contract.v1` contains:

- `expected`: original identity, source hashes and command hash.
- `exception`: ID, rationale revision/reference, approval reference, permitted
  source/destination role pairs and explicit binary native case premises.
- `intent`: actual endpoint names, source/destination roles, whether timing is
  required, expected source/destination clocks and a source reference per pair.
- `intent_basis_ref`, `owner_ref`: original requirement and review responsibility.

Examples write `requirements.json`, the contract and independent native truth
table before execution. Their owned references are fixture premises, not real
approval records. Unknown intent values use null. Foreign identities/hashes are
quarantined; missing expected hashes, sources, mode or native history are gaps.
An edited contract differs from the captured original digest and remains open
until checked against its actual source. Do not rewrite intent to match output.

The report preserves every native before-pair, its post-exception presence,
actual clock association, supplied intent, findings and gaps. A required pair
being masked is an applicability finding, not a native engine violation. A native
pair missing independent intent remains in the population and marks it incomplete.

Drift embeds [parent waiver records](../../FORMAT.md), using
`NATIVE_SETUP_ENDPOINT_PAIR_MASKED` and the profile-specific population basis.
IDs are `startpoint->endpoint`. One-to-one maps use the parent's
`opentools.waiver-identity-map.v1` format and cite reviewed correspondence.
Role/timing meaning changes survive an explicit map. The policy observes native
case values; the separate review checks current role, timing and clock premises.
The result never grants exception approval or establishes hold/CDC/STA signoff.
