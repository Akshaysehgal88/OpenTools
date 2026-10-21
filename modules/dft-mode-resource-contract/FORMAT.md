# Saved DFT resource profile

## Inputs

`context.json` uses `opentools.dft-resource-context.v1`. Its six identity references
select one design, configuration, scope, mode, domain and run. `chain` names one
1–32-cell, six-functional-pin, common-root chain, the cell pin map, input/output
boundaries and reset release polarity. Ports/instances use ordinary native names
and indexed vector bits. Native connectivity must span every selected cell and
match the serialized netlist and DFT preview order.

`role_map` names twelve wrapper inputs and six observed outputs. Verilator XML
must confirm their unsigned widths/directions and direct binding of the selected
stitched instance's clock, reset, enable, serial input, data and state ports.
The original logger macros must use the same roles. `wrapper_instance` selects
that instance. This does not prove arbitrary wrapper or checker semantics; source
review is required.

Mapping, instrumentation, model, supply, policy, timing and dependency references
identify the supporting records. Null references and `dependencies_complete`
unknown/false prevent a supported result. References are supplied declarations;
the reader does not authenticate them or grant access authorization.

`contract.json` uses `opentools.dft-resource-contract.v1`. `expected` contains the
six identities, chain/role mapping, eight original source SHA256 values, mode SDC
SHA256 and serialized run-command SHA256 from the independent run request. Null
hashes stay gaps. Different identities quarantine the evidence. Requirements
also contain an owner/source basis, a positive native clock period and separate
shift/capture/unload rows with minimum samples, selected clock input, resource
levels and source references.

This profile requires released reset, manufacturing mode/access, power available,
isolation inactive and scan enable `1/0/1`. At least a full chain is shifted and
unloaded, even if the declared minimum is smaller. Useful changing shift/capture
state and varying serial unload data are required. A different mode protocol
belongs in the manual review or a separately qualified reader.

`require_propagated_reset` preserves a stronger acceptance requirement: true
requires complete native leaf-reset values. The owned export returns an unresolved
value at one leaf, so it cannot meet that requirement. False permits only the
explicit-root-case, native same-net alias and finite observed-pin claim.

## Original artifact directory

The capture command reads a relative `workdir` within the artifact root. Retain:

- Sources: `seed.v`, `scanned.v`, `cells.lib`, `cells.lef`, `cells_model.sv`,
  `top.sv`, `ports.hpp`, `main.cpp`.
- Native setup/output: `dft.tcl`, `export.tcl`, `mode.sdc`, `replaced.v`,
  `scanned.odb`, `scanned.def`, `resources.txt`, `model.xml`.
- For each of `dft`, `mode`, `build`, `xml`, `run`: `.command.json`,
  `.stdout.txt`, `.stderr.txt`; plus tool-version text files, `execution.json`
  and the original Linux `Vtop` ELF.

The [example collector](examples/run_native.py) writes the qualified layout and
commands. The reader checks completion markers in addition to exit codes because
this OpenROAD version can exit zero after a Tcl error. Paths must remain inside
the artifact root; symlinks and duplicate JSON keys are rejected. The commands,
Tcl and executable are read as data. Rehashing detects subsequent edits; saved
artifacts are not an authenticated execution attestation.

`resources.txt` is an explicit ODB/OpenSTA export: `MODULE`, `CELL`, `PIN`, `PORT`,
`CLOCK`, `CASE phase port 0|1|X` and `LEAF_SIM phase pin 0|1|X` between format and
completion markers. Explicit cases, same-net connectivity and propagated leaf
values remain separate fields. No `X` is converted to a released reset.

The finite trace contains `CONFIG`, contiguous `STEP` records and `NATIVE_RESULT`.
Each step records selected clocks, effective reset/enable/clock, serial-before,
raw/visible state, native expected values and cumulative failures. The reader
recounts comparisons; the independent [example model](examples/reference_model.py)
additionally checks the owned fixture semantics. Neither mechanism establishes
arbitrary testbench correctness.

## Output

Capture produces `opentools.dft-resource-evidence.v1`, retaining original hashes,
native status/counts, inventory, observed steps and source mapping. Review
revalidates all original artifacts and normalized fields before producing
`opentools.dft-resource-review.v1` and a short Markdown report.

`QUARANTINED` takes precedence over attribution. Otherwise known resource
mismatches take precedence over gaps, while both remain visible. A supported
result is bounded to this chain and finite cycle. It cannot close ATPG coverage,
power-aware simulation, analog supply behavior, clock-tree integrity, timing or
security-policy signoff.
