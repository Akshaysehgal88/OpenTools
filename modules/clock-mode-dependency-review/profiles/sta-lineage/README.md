# STA clock lineage and mode coverage

Review native clock definitions and register clock coverage against the original
selected-mode contract. Use the [workflow](WORKFLOW.md) with your existing AI host
and native tools. The optional saved-data helper needs Python 3.10+ only.

```sh
python profiles/sta-lineage/sta_review.py capture evidence boot-divider-complete --output capture.json
python profiles/sta-lineage/sta_review.py review evidence evidence/reviews/boot-divider-missing-generated.policy.json --output review.json
```

Run from the clock-mode-dependency-review module directory. Outputs require new
paths. Exit `0` means clock-contract correspondence within scope; `1` review
required; `2` incomplete; `3` invalid input/I/O. Findings retain accompanying gaps.
This is a clock-setup disposition, not physical clock or timing signoff.

## Native example

Configure OpenROAD `v2.0-17598-ga008522d8` in a Linux environment, then:

```sh
python profiles/sta-lineage/examples/run_native.py evidence --openroad /path/to/openroad
export OPENTOOLS_STA_LINEAGE_NATIVE="$PWD/evidence"
python -m unittest discover -s profiles/sta-lineage/tests -v
```

Saved-data review and tests also run on Windows. Set
`OPENTOOLS_STA_LINEAGE_NATIVE` to the retained collection; native-fixture tests
otherwise skip. Installing the skill does not install native tools.

The two owned timing trees exercise boot divide-by-two and wake divide-by-four
paths. Missing the final generated-clock definition leaves required consumer clock
pins uncovered while upstream clocks remain defined. Other controls change mux
case, divide ratio, gate state and ideal/propagated state. Automatic master inference
and untraced lineage remain explicit evidence gaps in this profile.

## Existing native flow

Load `trace_clocks.tcl` and start tracing before clock definitions. End tracing
before collecting final objects:

```tcl
opentools_clock_trace_start
# Run your native clock definitions here.
opentools_clock_trace_end
source export_clocks.tcl
opentools_export_clocks run_ref {reset_n boot_sel clock_enable} capture/D clocks.jsonl clocks.odb
```

The trace retains resolved native constructor arguments. The exporter also works
without a trace to inspect final collections, but cannot recover absent creation
history. See [FORMAT.md](FORMAT.md) for ABI, lifecycle and batch-reader limits.
