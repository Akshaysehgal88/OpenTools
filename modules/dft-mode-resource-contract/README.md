# DFT mode resource contract

Review the clock, reset, power, isolation and access conditions required before
shift/capture or test-access acceptance. Use this stage after mode-control or
constraint changes and when accepting a new test configuration.

The AI workflow reconciles the team's mode table, native reports and observations,
then records missing resources, responsible owners and recheck conditions. It
works with your existing agent and engineering tools. Start with [SKILL.md](SKILL.md)
and retain the [review record](REVIEW.md) beside the original artifacts.

For OCC recipe or STA scenario changes, use the
[at-speed handoff profile](profiles/at-speed-handoff/GUIDE.md). It compares native
clock/exception evidence with observed pulses and independent control guards,
while retaining separate pattern/ATPG and timing qualification limits.

## Saved-data helper

Python 3.10+; standard library only. The qualified reader accepts one reset-capable
scan chain/domain from OpenROAD `v2.0-17598-ga008522d8` and a finite shift/capture/unload
trace from Verilator 5.020. It checks native connectivity, explicit root case values,
logger bindings and original artifact identities before comparing requirements.
The collection includes the original executable; the reader never executes it.

```sh
python dft_resources.py capture artifacts run context.json --output evidence.json
python dft_resources.py review artifacts contract.json evidence.json \
  --json-out review.json --markdown-out review.md
```

Fill the [context](templates/context.json) from the source mapping and the
[contract](templates/contract.json) from independently established requirements.
Keep source identities from the run request. See [formats and native limits](FORMAT.md).
Outputs must be new files. Review exits: `0` bounded resources supported,
`1` resource mismatch, `2` incomplete or quarantined evidence, `3` invalid input.
Capture exits `0` for a complete saved run even when its native behavior failed.

## Qualification

The owned example uses two different partition interfaces and four/eight-bit scan
chains. OpenROAD performs replacement and stitching; Verilator runs the stitched
netlist. Controls cover reset clamping and supported masking, manufacturing denial,
functional debug, supply/isolation proxies, clock selection, capture enable and
constraint disagreement/unknowns. An independent finite model checks every step.

With the pinned tools already available on Linux:

```sh
python examples/run_native.py out --openroad /path/to/openroad \
  --verilator /path/to/verilator_bin --verilator-root /path/to/verilator-runtime
OPENTOOLS_DFT_RESOURCE_EXAMPLE="$PWD/out" python -m unittest discover -s tests -v
```

Configure runtime libraries for your tool distribution. Generation does not
download tools. Saved-data review and tests also run on Windows. Without the
example environment variable, native-corpus tests are skipped.

These examples use an ideal owned cell library and Boolean supply/isolation/access
proxies. They qualify the review mechanism, without ATPG coverage, characterized
timing, electrical power, security authorization or production signoff. Native
propagated reset values remain unresolved in this profile; explicit case values
and finite observed levels do not replace that evidence.

Install this module alone with the [project-local installer](../../INSTALL.md).
Optional DVIT or other scoped context uses the [context interface](../../CONTEXT_PORT.md).
No model API or DVIT connection is required.
