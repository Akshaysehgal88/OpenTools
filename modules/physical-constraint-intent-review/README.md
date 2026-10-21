# Physical constraint intent review

Use this module when reviewing a proposed placement or constraint intervention.
It asks whether an apparent geometric improvement still respects the **original
region/access requirement and comparison basis**.

This fits in PD experiment review, placement overrides and constraint-change
handoff. PD, integration and receiving-region owners can use it alongside native
placement checks and timing reports. Removing a blockage can make an intrusive
candidate pass native placement checks while violating the original reason the
region was protected.

The activity supplements implementation diagnostics and owner review. It replaces
manual baseline/candidate reconciliation for one selected intervention. It does
not perform placement optimization, routing, extraction or physical signoff.

## First use

Saved-data review needs Python 3.10+ and the standard library. From
`modules/physical-constraint-intent-review`, use a complete retained collection
at `.local/physical-native`, or generate one on Linux with an existing
**OpenROAD v2.0-17598-ga008522d8**:

```sh
python examples/run_native.py .local/physical-native --openroad /path/to/openroad
```

Replace the executable path and configure its runtime libraries. The recipe
installs nothing. Two owned flat scalar layouts each exercise baseline, unchanged,
constraint-preserving and two intrusive placements. Choose a new output directory.

Inspect the baseline and review the intrusive proposal:

```sh
python physical_review.py capture .local/physical-native horizontal-access-baseline --output .local/physical-native/recaptured-baseline.json
python physical_review.py review .local/physical-native .local/physical-native/reviews/horizontal-access-drop-and-intrude.policy.json --output .local/physical-native/intrusion-review.json
```

Expected review exit: **1**, `findings`. Removing the required blockage lets
the candidate pass native placement checks and reduces the selected terminal
bounding-box half perimeter by 7000 DBU, but the instance intrudes into the original
clear region and protection is missing. The report preserves both facts.

Compare a constraint-preserving move:

```sh
python physical_review.py review .local/physical-native .local/physical-native/reviews/horizontal-access-preserving-control.policy.json --output .local/physical-native/preserving-review.json
```

Expected exit: **0**, `within_declared_review_scope`. The selected metric
improves by 4000 DBU while the original region remains protected and clear.
This establishes bounded geometry correspondence, not routed or timing benefit.
Use new report paths. Capture exit 0 means valid intake, not proposal acceptance.

## Helpers and native hook

| Helper | Responsibility |
|---|---|
| `export_region.tcl` | Reads native placements, blockages, selected terminals/paths, clock/cases and placement-check outcome; saves an export and database copy. |
| `physical_review.py capture ROOT RUN_REF` | Validates and reads the original batch artifact package without executing saved scripts. |
| `physical_review.py review ROOT POLICY` | Reimports both bound runs, checks comparison conditions and the original region requirement, then retains metric, native checks, findings and gaps. |
| `--output FILE` | Writes JSON to a new path; omit it to print JSON. |

In an existing loaded native session:

```tcl
source export_region.tcl
opentools_export_region run_ref data_buffer capture/D root {reset_n fun_enable test_mode} region.jsonl region.odb
```

Replace the run, net, endpoint, clock and case ports. The exporter runs
`check_placement` and writes new artifacts; it does not change placements or
constraints. Its export can support AI review in another loader, but the automatic
batch reader additionally requires the exact package and lifecycle in
[FORMAT.md](FORMAT.md).

## Source the original requirement

The context binds run/design/configuration/phase, selected net/endpoint, consumed
setup and relationship sources. Execution records retain original tool/command,
source/artifact hashes, completion and native exit.

The policy binds both original runs and independently states:

- Original selected net/terminal population and permitted moved instance.
- Clear region in native DBU, required hard-blockage protection and instance
  clearance, with rationale and receiving owner.
- Required claim strength and original source/correspondence basis.

The reader checks source/library/tool, floorplan, clock/phase, connectivity,
selected endpoints and placements outside the intervention. Changed conditions
leave a geometric difference unqualified. Region protection and instance intrusion
are checked separately from the native placement result. Under this selected
rule, touching an edge is allowed; positive-area intrusion is a finding.

The metric is the **selected native net-terminal bounding-box half perimeter**.
It requires known instance-terminal positions and no boundary terminals. It is
not routed wirelength, congestion or a physical optimization score.
Coordinates use native DBU; selected path slack uses the pinned ns UI. The
owned batch loader has no interconnect RC model.

## Integrate into a PD experiment review

1. Retain the original region/access rationale and intended intervention before
   measuring the candidate. Ask the receiving owner what must stay protected.
2. Capture baseline and candidate from consumed native setup, preserving tool,
   source, clock/case, connectivity and comparison identities.
3. State which placement change is permitted; keep other changed conditions
   visible rather than attributing every metric difference to the move.
4. Review region protection/intrusion, metric correspondence and native placement
   outcome separately. A favorable native check cannot approve removed intent.
5. Correct the original placement, constraint or sourced requirement, rerun the
   relevant native checks and revalidate.
6. Hand off original rationale, complete artifacts, policy, findings/gaps and owner
   decision. Repeat after relevant region, mapping, placement or setup changes.

Hashes establish byte correspondence, not freshness, source authority or owner
acceptance. Required routing, timing, throughput, macro-access, power/isolation
and full signoff claims remain open.

## AI-first adoption and outcome

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), the original constraint
rationale, candidate intervention and native exports:

> Explain what this region protects and whether the proposed move preserves it.
> Check baseline/candidate comparability, actual native geometry and placement
> diagnostics. Separate a local geometric metric from routing/timing/access
> acceptance, and ask for missing receiving-owner evidence.

Use [ONBOARDING.md](../../ONBOARDING.md), module
`physical-constraint-intent-review` / activity `default`. Existing AI/native
tools suffice. Optional DVIT intent/dependency context can connect an override
to its original rationale and affected consumers; local use requires none.

| Review exit | Meaning |
|---:|---|
| 0 | Within the declared bounded review scope. |
| 1 | Known constraint/geometry/comparison finding; coexisting gaps remain. |
| 2 | Incomplete scope or required claim evidence. |
| 3 | Invalid/changed native package or I/O. |

Argument errors use exit 2. Changed source/native artifacts reject intake rather
than becoming a hardware failure.

Batch qualification covers one translated instance/region, flat scalar loader,
hard blockage, binary cases and the pinned tool. The exporter can also inspect a
reopened database. Other loaders, hierarchical maps, transformed cells, boundary
geometry and commercial tools need separate qualification. The owned layouts do
not establish real macro, isolation or clock behavior.

Set `OPENTOOLS_PHYSICAL_NATIVE` to the retained collection and run:

```sh
python -m unittest discover -s tests -v
```

Native-fixture tests otherwise skip. Saved-data review also runs on Windows.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
