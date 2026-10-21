# ECO evidence profile

`eco_review.py review ROOT POLICY` consumes flat run directories and a
`opentools.eco-policy.v1` JSON record. The example generator shows complete records.
No imported Tcl, shell command or binary is executed by the reviewer.

Each run retains the consumed Verilog, primitive models, LEF/Liberty, SDC/loader,
native graph, saved database, logical XML, report artifacts, original executable,
commands, versions and execution record. `context.json` maps selected roles and
declares design/configuration/phase, relationship bases and owner. Hashes identify
bytes; declarations do not authenticate provenance, freshness or approval.

`sta.snapshot.json` and `clock.snapshot.json` use the parent result-snapshot format.
They preserve producer, original outcome and report bytes. If absent, the reader
can reconstruct them from matching original native artifacts. Missing/changed raw
reports leave applicability unresolved; they never rewrite an original pass as a
hardware failure. Source/model/executable or native graph changes reject capture.

The policy binds both runs' identities, role selections, source/graph/executable/
tool hashes and canonical snapshot fingerprints. It declares independent required
phases and outcomes, both report selections, correspondence source, claim/owner
and explicit required-claim flags. Required reports cannot be dropped. Unknown
correspondence is held before attribution. Broad claims remain open even when
the selected reports match.

`reviewed_reuse` binds the original report and exact target run, report type,
observed/requested identity pairs, rule, approving owner, basis and reason.
Only changed global netlist/executable identities can be bridged, conditional on
unchanged selected dependencies, phase, checker, models, libraries and tool profile.
These records are supplied approvals, not a signature or proof of authority.

## Qualified helper scope

One endpoint-rewire ECO class; two downstream observations:

- OpenROAD/OpenSTA selected constrained-path presence, with actual root clock,
  case values, endpoints and native register clock population retained.
- Verilator finite Boolean clock-delivery count in one declared input phase.
  Logical half-cycle samples do not measure physical pulse width or STA time.

The batch adapter admits flat scalar direct connections/aliases and the bundled
AND/OR/INV/BUF/DFF models/library, exact loaders and pinned versions. It compares
logical/native instance, pin, direction and connection correspondence. Changed
instance population/master, placement, boundary or unknown identities require
another qualified method. Stateful clock dependencies, cycles, unobserved receiver
clock transfers and unknown drivers cannot qualify reuse through this profile.

The structural projection is a bounded dependency record. It is not sequential
equivalence, parasitic validity, route legality, timing closure, power-state
correctness, scan ordering or complete ECO signoff. Keep those required claims
open and route them to their native checks. The general AI workflow accepts the
team's broader evidence without claiming that the batch adapter qualifies it.
