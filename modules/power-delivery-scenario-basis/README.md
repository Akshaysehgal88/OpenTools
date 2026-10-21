# Power-delivery scenario basis

Review whether a saved static IR result covers the requested supply, sources,
corner and loading scenario. Preserve the original voltages and native status
alongside mismatches, missing basis and required analyses still open.

Use [SKILL.md](SKILL.md) with your existing AI host. The saved reader requires
Python 3.10+ and its standard library. No inference provider or DVIT SDK is required.

## Saved review

```sh
python supply_review.py capture evidence series-base --output capture.json
python supply_review.py review evidence evidence/reviews/series-old-loads.policy.json --output review.json
```

Run from this module directory. Outputs require new paths. Exit `0` means static
scenario correspondence; `1` a known mismatch or native physical-grid failure;
`2` incomplete; `3` invalid input/I/O. Findings take precedence while preserving
gaps. Correspondence does not approve IR limits or the load model.

A policy selects original evidence and an independent scenario request. It may
also identify a retained candidate result. A new target IR run is not required to
review a prospective request. Requests and complete policy examples are created
by the native example below.

## Native example

Configure OpenROAD `v2.0-17598-ga008522d8` in a Linux environment, then:

```sh
python examples/run_native.py evidence --openroad /path/to/openroad
export OPENTOOLS_SUPPLY_NATIVE="$PWD/evidence"
python -m unittest discover -s tests -v
```

Saved-data review and tests also run on Windows. Set `OPENTOOLS_SUPPLY_NATIVE` to
the retained collection; native-fixture tests otherwise skip. Skill installation
does not install native tools. The two owned networks exercise load/source/corner
changes and physical disconnection while retaining logical supply names.

For an existing loaded flow, source `export_supply.tcl` and call:

```tcl
opentools_export_supply run_ref VDD owned_supply/LOAD supply.jsonl supply.odb
```

This reads physical supply objects and the selected library operating point into
new artifacts. Native static reports and their consumed source/load basis are
separate evidence. See [FORMAT.md](FORMAT.md) for the batch reader's qualification
and the [OpenROAD IR documentation](https://openroad.readthedocs.io/en/latest/main/src/psm/README.html)
for native commands; supported options follow the installed pinned tool.
