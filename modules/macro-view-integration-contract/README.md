# Macro view integration contract

Review a macro/view set before intake or instance replacement. Use the
[AI workflow](SKILL.md) with existing project tools and the
[review record](review-record.json). The helper and DVIT are optional.

Compare accepted revision/corner, logical and physical pins, supply ownership,
footprint, orientation, test/repair interfaces and selected access requirements.
Return findings, missing evidence, corrective actions and recheck triggers to the
integration owner. A compiling wrapper or matching physical database does not
establish that the selected timing/supply assumptions still apply.

The read-only [OpenROAD exporter](export_views.tcl) records one selected instance
from a loaded database and library:

```tcl
source export_views.tcl
opentools_export_macro u_macro library_name/cell_name view.jsonl view.odb
```

It creates new files and refuses to overwrite existing paths. The JSON lines
contain actual native pin geometry/connectivity, master symmetry, library
operating point and timing endpoints. Use these records directly in the AI review.

The optional Python 3.10+ reviewer supports the qualified batch profile:

```sh
python view_review.py review trial trial/context.json trial/policy.json
python view_review.py capture trial trial/context.json --output captured.json
```

Exit codes: 0 aligned within the supplied contract, 1 findings, 2 incomplete,
3 invalid input. `--output` creates a new file. Saved-data review needs no native
tool installation and never executes retained Tcl or command records.
See [formats and reproduction](FORMAT.md).

The owned storage-shell and clock-control examples qualify one view-intake
activity. They cover wrong supply, changed characterization voltage, pin direction,
orientation, obstruction window, timing endpoints, footprint and instance wiring.
They do not qualify memory behavior, clock safety, characterized timing, routability
or DRC/LVS. Licensed views stay in the adopting environment.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
