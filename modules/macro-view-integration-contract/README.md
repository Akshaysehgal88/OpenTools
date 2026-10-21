# Macro view integration contract

Use this module before accepting a macro view set or replacing an instance.
It reviews whether the **logical, physical and timing views still describe the
accepted integration contract**: revision/corner, pins, supply ownership,
footprint/orientation, selected timing endpoints and access conditions.

This fits in macro intake, IP integration and PD handoff. Integration, library,
DFT/repair-interface and physical-design owners can use it alongside native view
loading, wrapper compilation and placement checks. A compiling wrapper or
byte-identical physical database does not establish that the chosen Liberty
operating point or supply assumption remains correct.

The workflow supplements native import diagnostics and IP acceptance review.
It replaces manual cross-view comparison for a selected instance. It does not
replace macro characterization, behavioral verification, routability or DRC/LVS.

## First use

Saved-data review requires Python 3.10+ and the standard library. Run from
`modules/macro-view-integration-contract`. Use a complete retained collection at
`.local/macro-native`, or generate one on Linux with existing
**OpenROAD v2.0-17598-ga008522d8** and **Verilator 5.020**:

```sh
python examples/run_native.py .local/macro-native --openroad /path/to/openroad --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Replace native tool/runtime paths and configure your distribution's libraries.
The recipe installs nothing. Two logical elaborations serve twenty owned native
view imports. The output directory must be new.

Capture and review the unchanged storage-shell view:

```sh
python view_review.py capture .local/macro-native/storage-good .local/macro-native/storage-good/context.json --output .local/macro-native/storage-good/recaptured.json
python view_review.py review .local/macro-native/storage-good .local/macro-native/storage-good/context.json .local/macro-native/storage-good/policy.json --output .local/macro-native/storage-good/new-review.json
```

Expected review exit: **0**, `aligned`. Inspect the report for selected native
scope, pin/net correspondence, operating conditions, windows, findings and gaps.
Review always recaptures original artifacts; the separate capture command is
useful for inspecting native facts, not a required cached intermediate.

Compare the changed characterization voltage:

```sh
python view_review.py review .local/macro-native/storage-voltage-change .local/macro-native/storage-voltage-change/context.json .local/macro-native/storage-voltage-change/policy.json --output .local/macro-native/storage-voltage-change/new-review.json
```

Expected exit: **1**, `findings`. The original accepted operating point is
retained even when physical geometry agrees. Other controls cover wrong supply,
direction, orientation, blocked access window, changed endpoints/footprint,
wrapper wiring and a valid mirrored placement. Outputs must be new files.

The storage shell is one bit, not a memory/repair algorithm. The second shell is
a clock-control gate network, not a PLL qualification. They exercise one reusable
view-intake activity in different interface contexts.

## Helpers and native export

| Helper | Responsibility |
|---|---|
| `export_views.tcl` | In a loaded OpenROAD design/library, exports one selected physical instance and fully qualified library cell as native JSON-line string arrays, plus an ODB snapshot. |
| `view_review.py capture NATIVE_DIRECTORY CONTEXT` | Checks and reads the original native/logical package without executing its commands; retains object and source identities. |
| `view_review.py review NATIVE_DIRECTORY CONTEXT POLICY` | Recaptures originals and compares with independent accepted selection, source/view bindings, pin/supply, PVT and placement/access requirements. |
| `--output FILE` | Saves JSON to a new path; omit it to print JSON. |

For an existing loaded session:

```tcl
source export_views.tcl
opentools_export_macro u_macro library_name/cell_name view.jsonl view.odb
```

Replace the selected instance and exact library/cell name. The exporter refuses
existing output paths. It records actual database geometry, master symmetry,
physical pin direction/use/rectangles, obstructions, instance terminal nets/types,
library/default operating point, library ports and timing endpoint collections.

Use this native export directly in the AI review if your loader is outside the
qualified batch profile. The Python reader additionally expects the exact
source/context/command/XML/execution package in [FORMAT.md](FORMAT.md), not just
`view.jsonl`. It checks the exporter source and supplied artifact identities.

## Establish the accepted contract

The context identifies run/scope/configuration, macro/revision/corner, selected
physical/logical instances, logical unit/library cell and source bases for views,
pin correspondence, supply, placement, access, wrapper and owner.

The independent policy must retain:

- Accepted selection and original source/database/export/XML/command identities.
- Expected master/library, footprint, database units per micron and characterization
  process/voltage/temperature.
- Explicit physical/logical/timing pin correspondence, direction, scalar width,
  signal type, net, role and supply owner. Unmapped populations stay open.
- Allowed orientations, required timing endpoint pairs and selected access windows.
  Access boxes use master-local native DBU coordinates and explicit layers;
  obstruction checks use positive-area overlap.
- Stronger requested claims, including timing polarity, Liberty PG association,
  memory behavior, clock waveform safety or DRC/LVS.

Operating voltage is a characterization condition, not an electrical measurement.
The comparison's tiny PVT float tolerances handle native representation, not
allowed operating ranges. Timing arc endpoints do not establish edge polarity
or timing validity. Stronger requested claims remain gaps rather than silently
being omitted.

## Integrate into macro intake

1. Source the original accepted revision/corner and receiving requirements before
   choosing available passing views.
2. Load the actual consumed logical/physical/timing files in your existing tools.
   Retain native selection, commands, diagnostics and original source identities.
3. Export the selected instance and resolve pin/supply/wrapper correspondence
   explicitly. Check test/repair/control roles with the relevant owner.
4. Review the accepted policy against native objects. Inspect footprint/orientation,
   PVT, connectivity and access findings separately from successful import.
5. Correct the original view selection, wrapper, supply/placement setup or sourced
   contract; reload and revalidate.
6. Hand off original view identities, reports, unresolved claims and receiving
   decisions. Repeat after revision, corner, mapping, footprint or supply changes.

Licensed views stay in the adopting environment. The tool does not fetch or
redistribute a company's macro library.

## AI-led adoption, results and support

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), original intake criteria,
view manifests, wrapper source and native exports:

> Reconcile this macro's accepted revision/corner with the actual loaded views.
> Trace logical/physical/timing pins, supply ownership, placement and selected
> access requirements. Keep successful import separate from missing behavior,
> characterization or physical signoff evidence.

Use [ONBOARDING.md](../../ONBOARDING.md), module `macro-view-integration-contract` /
activity `default`. The [review record](review-record.json) captures corrective
actions and recheck triggers. Optional DVIT intent/context can connect view changes
to dependent interface/placement obligations; existing AI/local sources suffice.

| Review exit | Meaning |
|---:|---|
| 0 | Aligned within the supplied intake contract. |
| 1 | Known findings; inspect concurrent gaps and owner actions. |
| 2 | Incomplete or quarantined identity/applicability evidence. |
| 3 | Invalid package, unsupported native form or I/O. |

Capture exit 0 means valid intake. Argument errors use exit 2. Hashes bind declared
bytes, not execution authenticity, freshness or acceptance.

Batch qualification uses the pinned tools, flat selected instance, simple names,
scalar direct logical connections and one supply domain. Other loaders, bus maps,
aliases, hierarchy renames or commercial tools need separately validated native
evidence. The AI workflow remains broader than the reader. JSON export/XML limits
and exact supported files are in [FORMAT.md](FORMAT.md).

Set `OPENTOOLS_MACRO_NATIVE` to the retained collection and run:

```sh
python -m unittest discover -s tests -v
```

The independent reference checks native object tables, geometry, nets, PVT and
endpoints. No result grants production macro signoff.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
