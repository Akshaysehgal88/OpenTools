# Scan population and exclusion audit

Use after scan insertion, reordering or an exclusion change. Reconcile the required
functional state population with actual native chain membership and current
non-scan rationale. Start with the [AI workflow](WORKFLOW.md); use your existing
reports and agent. DVIT is optional through the parent's context interface.

## Saved-data helper

Python 3.10+, standard library only. The qualified profile reads OpenROAD
`v2.0-17598-ga008522d8` sequential census, ODB pin exports, serialized netlists and
DFT plans. It supports flat scalar reset-capable cells, rising-edge chains and
separate mapped clock roots. Required roles, logical power groups and exclusion
authority come from independent source records.

```sh
python scan_population.py capture artifacts run context.json --output evidence.json
python scan_population.py review artifacts contract.json evidence.json \
  --json-out review.json --markdown-out review.md
python scan_population.py drift artifacts baseline-evidence.json evidence.json \
  --output exclusion-drift.json
```

Keep original native run/source/command identities and independently applicable
current intent identities. Fill the
[context](templates/context.json), [contract](templates/contract.json),
[population](templates/population.json) and [exclusions](templates/exclusions.json)
from the selected sources. Nulls remain gaps. [FORMAT.md](FORMAT.md) defines the
required native layout and separates membership review from historical drift.
Outputs must be distinct new files. No received command, Tcl or database is executed.
For a new intent review, retain the original packet and create a derived packet
with the same native artifacts and the matching current intent source. Record
that association; it is not a new insertion run.

Review exits: `0` bounded population accounted, `1` membership/premise review,
`2` incomplete/quarantined evidence, `3` invalid input. Capture exits `0` for a
completed native insertion even when required state was omitted from scan. Drift
uses the parent comparator's `0/1/2` unchanged/review/incomplete outcomes and keeps
missing rationale visible. Neither command approves an exclusion.

## Qualification

The owned native flow tests four-state single-clock and eight-state mixed-clock
partitions. Controls include complete membership, a required unscanned flop,
allowed exclusion, changed role/clock premises, missing rationale, stale exclusion
scope, incorrect clock intent and an incomplete roster. Native insertion preserves
functional state while selected `set_dont_touch` controls prevent scan replacement.
An independent serialized-netlist/serial-graph reference checks the observations.

With the pinned OpenROAD runtime already configured on Linux:

```sh
python examples/run_native.py out --openroad /path/to/openroad
OPENTOOLS_SCAN_POPULATION_EXAMPLE="$PWD/out" python -m unittest discover -s tests -v
```

Saved-data review also runs on Windows. Native-corpus tests skip when the environment
variable is absent. The generator downloads nothing. The fixtures use an owned
ideal library and logical group intent, without PDK or physical power qualification.
Membership cannot establish fault coverage, ATPG observability or defect detection.

Install the parent `waiver-revalidation` module with the
[project-local installer](../../../../INSTALL.md). It includes this profile and
the unchanged original waiver comparator.
