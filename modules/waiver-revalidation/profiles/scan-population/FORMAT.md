# Scan population native profile

## Independent requirements

`population.json` uses `opentools.scan-population.v1`. It records exact scope,
design, configuration and population references, an independent `source_ref`,
Boolean/null `complete`, and distinct state IDs mapped one-to-one to native
instances. Each state supplies Boolean/null `scan_required`, role, mapped clock
net, logical power group and source basis. Null fields remain unknown. A declared
complete roster that omits a native sequential state is still incomplete.

`exclusions.json` uses `opentools.scan-exclusions.v1`, the same four identity fields
and explicit records. Each has a distinct ID/instance, reason, rationale revision,
approval/source references and required role/clock/power-group premises. These
references are declarations requiring source/owner review, not authenticated
authority. An empty records list selects no exclusions.

Required state cannot be exempted by a conflicting exclusion. Non-required intent
alone cannot justify unscanned state: a matching current exclusion and supported
premises must also be present. Stale exclusion scope admits no exemptions. Allowed
unscanned state stays in the output denominator and is counted separately.

`contract.json` uses `opentools.scan-contract.v1`. Its `expected` fields select the
run, scope, design, configuration, population and qualified profile, plus original
native source/command SHA256 values and independent intent identities from the
review request. Requirements/receiving-owner
references may be null and then remain gaps. A different native/source identity
quarantines evidence before failure attribution. Hashes bind content; matching
hashes do not prove source meaning or requirement completeness.

## Original native artifacts

`context.json` uses `opentools.scan-context.v1`: the five identities, module,
functional/scan masters, six cell pin roles and mapping/library/logical-power
bases. The original run directory must contain:

- Inputs: `seed.v`, `cells.lib`, `cells.lef`, `flow.tcl`, `population.json`,
  `exclusions.json`.
- Native artifacts: `pre.txt`, `post.txt`, `pre.v`, `post.v`, `pre.odb`, `post.odb`.
- Execution records: `command.json`, `execution.json`, `stdout.txt`, `stderr.txt`,
  `version.txt`.

The [example collector](examples/run_native.py) creates the supported layout.
It hashes inputs before and after actual insertion. Population/exclusion sources
are independent input records; OpenROAD does not interpret their policy semantics.
The provenance distinguishes four native-tool inputs from the two intent files.
A derived review packet may pair unchanged native artifacts with newer independently
applicable intent, preserving the original packet and its source identities. That
is a new evidence association, not a new native execution or automatic approval
of the newer requirement. Do not replace native inputs without matching fresh output.

Native text exports contain a format/stage header, `SEQ` from `all_registers -cells`,
ODB `CELL`/`PIN`/`PORT` records and a completion marker. The profile accepts a flat
1–256-cell scalar sequential census using the two explicitly mapped masters and
four functional/six scan pins. It rejects other cells, multibit/multi-edge formats,
identity loss, ambiguous serial branches and unsupported netlist syntax. Native
serialized source and ODB pin maps must agree. Functional pin connections survive
insertion. Every scan cell must occur in exactly one native plan/stitched path,
with a common mapped clock/enable and native serial boundaries.

Actual qualification covers the owned four-state single-clock and eight-state
mixed-clock contexts. The size limit is a reader bound, not production qualification
of every design. Logical power grouping is independently declared; it is not a
native supply-network or UPF result.

Capture reads commands/Tcl/databases as data and retains their identities. It
checks completion markers as well as exit status. Review rehashes and recaptures
all original fields before analysis. Duplicate JSON/native identities, path escapes
and symlinks are rejected. Saved artifacts are not authenticated execution proofs.

## Reports and historical drift

`opentools.scan-review.v1` preserves native insertion `COMPLETE`, counts and a
per-state membership/exclusion table. `BOUNDED_POPULATION_ACCOUNTED` means the
selected supplied population is accounted for; it does not establish coverage or
owner acceptance. Known mismatches take precedence over gaps, with both retained.
Missing/stale/foreign sources cannot silently establish a good result.

The optional drift command normalizes actual selected unscanned-state observations
into the parent waiver record format. `SELECTED_UNSCANNED_STATE` identifies an
inventory observation, not a native tool violation. Definition digests describe
the actual exclusion records; explicit role, native-clock and logical-power
premises are passed to unchanged `waiver_core.compare`. The complete original
parent audit remains in `opentools.scan-exclusion-drift.v1`; missing rationale
bases are also retained. No fabricated empty waiver is created when none is
selected. Stable instance identities are required in this qualified drift path.

Historical population/premise comparison cannot replace the independent current
membership review. Neither report proves ATPG fault coverage, observability,
silicon defect detection, electrical power behavior or production signoff.
