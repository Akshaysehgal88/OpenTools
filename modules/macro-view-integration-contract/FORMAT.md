# Native view profile

Saved-data review uses Python 3.10+ standard library. Native qualification uses
OpenROAD `v2.0-17598-ga008522d8` and Verilator 5.020 on Linux:

```sh
python examples/run_native.py /tmp/macro-views --openroad /path/to/openroad --verilator /path/to/verilator_bin --verilator-root /path/to/verilator/runtime
OPENTOOLS_MACRO_NATIVE=/tmp/macro-views python -m unittest discover -s tests
```

Two logical elaborations serve twenty native view imports. Original sources,
commands, XML, native JSON lines, database and logs remain alongside the derived
example policies/reports. `examples/reference_model.py` independently checks
expected native object tables, placed geometry, nets, PVT and timing endpoints.
The storage shell is one bit, not a RAM or repair algorithm. The clock-control
shell is a gate network, not a PLL or waveform-safety qualification.

## Export and capture

`export_views.tcl` reads a selected instance and exact fully qualified library
cell from the current OpenROAD session. It exports database units, instance/master
geometry, master terminal direction/use, pin/obstruction rectangles, instance
terminal nets/types, library/default operating point, library ports and timing
endpoint collections. JSON-line records are string arrays with a final `END`.
Internal Liberty ports are retained. The exporter also writes an ODB snapshot.
New output paths are required.

Native timing-role details and Liberty PG-pin associations are not exposed by
this adapter. Arc endpoints do not establish edge polarity or timing validity.
The operating voltage is a library characterization condition, not an electrical
measurement. A byte-identical ODB can accompany a different Liberty point.

The Python capture profile expects `macro.lef`, `macro.lib`, `netlist.v`,
`wrapper.sv`, `macro_model.sv`, `export_views.tcl`, `select.tcl`, `native.jsonl`,
`native.odb`, `logical.xml`, native/logical command JSON and stdout/stderr text,
version text files and `execution.json`. The native exporter source is checked
against this module. The batch command loads the selected files, links one flat
instance, connects one power/ground pair, places it and calls the exporter.
Other session loaders remain explicitly unqualified for automatic attribution;
their exported data can still support source-backed AI review.

The logical reader follows one direct selected instance through actual Verilator
definitions, port directions, packed basic/ref widths and direct variable
connections. Non-scalar, expression or unsupported-width correspondence remains
open. It does not infer bus bit maps, aliases or hierarchy renames. The qualified
batch uses simple instance/library/supply identifiers and one supply domain.

Source hashes bind supplied artifacts; they do not authenticate execution,
freshness, loaded-source provenance or acceptance. The reader never executes saved
commands or parses LEF/Liberty text as a substitute for native object semantics.
ODB hashing streams the file. Selected JSON export is limited to 32 MiB and
logical XML to 128 MiB; the AI workflow can use team-native methods beyond that profile.

## Independent context and policy

`context.json` uses `opentools.macro-context.v1` with `run_ref`, `scope_ref`,
`configuration_ref`, `macro_ref`, `revision_ref`, `corner_ref`, selected physical
and logical instances, logical unit, library cell and view/revision/corner/pin/
supply/placement/access/wrapper/owner basis references. Missing basis stays null.
These are supplied declarations, not native revision authentication.

`policy.json` uses `opentools.macro-policy.v1`:

- `identity` and `selection`: independently accepted context and selected-object
  bindings. `source_sha256`, `database_sha256`, `native_export_sha256`,
  `logical_xml_sha256`, native/logical command hashes bind the selected artifacts.
- `master`, `library_cell`, `geometry`: expected master/library and width, height,
  database units per micron. `operating_point` gives process, voltage and
  temperature. Tolerances are respectively `1e-6`, `1e-6 V`, `1e-4 C` for native
  float representation; these are not allowed operating ranges.
- `pin_map`: original physical/logical/timing correspondence, expected direction,
  signal type, scalar width, net, role and source reference. PG entries have null
  logical/timing pins and a supply owner. Unmapped populations remain open.
- `allowed_orientations`, `required_arcs` and `access_windows`: independently
  required placement, endpoint and access conditions. Access boxes use master-local
  native DBU coordinates and explicit layers; positive-area overlap is checked.
- `required_claims`: explicit booleans for timing polarity, Liberty PG associations,
  memory behavior, clock-waveform safety and DRC/LVS. Requested true claims remain
  unqualified by this helper. Omitted requirements are not assumed false.
- `source_ref`, `owner_ref`, `inputs_complete`: original intake and receiving basis.

## Review output

The report keeps native import/elaboration results, original scope, pin/net
correspondence, selected window observations, findings, gaps, owner and recheck
triggers. Foreign/stale scope or artifact bindings quarantine attribution. Known
violations remain visible beside missing evidence. Aligned is bounded agreement
with the supplied contract, not approval or production macro signoff.
