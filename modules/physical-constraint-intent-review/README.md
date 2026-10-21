# Physical constraint intent review

Review a proposed placement or constraint intervention against the original
region requirements. Retain the native metric and placement result alongside
access violations, comparison gaps and receiving-owner actions.

Use [SKILL.md](SKILL.md) with your existing AI host. Python 3.10+ and its standard
library are enough for the saved-evidence helper; no provider SDK is required.

## Saved review

```sh
python physical_review.py capture evidence horizontal-access-baseline --output capture.json
python physical_review.py review evidence evidence/reviews/horizontal-access-drop-and-intrude.policy.json --output review.json
```

Run from this module directory. Outputs require new paths. Exit `0` means within
the declared review scope; `1` findings; `2` incomplete; `3` invalid input/I/O.
Findings take precedence while preserving gaps. Capture success is not acceptance.

## Native example

Configure OpenROAD `v2.0-17598-ga008522d8` in a Linux environment, then:

```sh
python examples/run_native.py evidence --openroad /path/to/openroad
export OPENTOOLS_PHYSICAL_NATIVE="$PWD/evidence"
python -m unittest discover -s tests -v
```

Saved-data review and tests also run on Windows. Set `OPENTOOLS_PHYSICAL_NATIVE`
to the retained collection; native-fixture tests otherwise skip. Installation of
this skill does not install native tools.

The two owned layouts compare unchanged, constraint-preserving and intrusive
placements. Removing a required blockage lets an intrusive candidate pass native
placement checks and reduce the selected terminal bounding box. The review still
finds the intent violation. Keeping the blockage exposes the same intrusion in
the native checker. These scalar layouts qualify physical review mechanics,
not real macro, isolation or clock behavior.

## Existing native flow

Source `export_region.tcl` after loading your database, libraries and constraints:

```tcl
opentools_export_region run_ref data_buffer capture/D root {reset_n fun_enable test_mode} region.jsonl region.odb
```

The exporter reads native objects, records selected timing paths, runs
`check_placement` and saves a new database copy. It does not alter placements or
constraints. Use its facts in the AI workflow; the batch reader has a separate
qualified loader boundary described in [FORMAT.md](FORMAT.md).

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
