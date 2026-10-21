# Native execution controls

Qualified recipe: Linux, GNU Binutils 2.42, Python 3.10+ and Unicorn 2.1.4. The
helper itself needs only Python standard library. Install test dependencies in
your chosen environment explicitly; the runner downloads/installs nothing.

```sh
python -m pip install -r requirements-native.txt
python examples/run_native.py /tmp/stage-handoff-proof
OPENTOOLS_HANDOFF_NATIVE=1 python -m unittest discover -s tests -v
```

GNU as/ld build two real x86-64 receiver ELFs from [receiver.S](receiver.S).
GNU readelf independently checks exported entry/load metadata. Unicorn executes
actual push, pop and result-store instructions with the selected initial PC/SP.
An owned readiness model applies page protection to two distinct stack regions;
an early transfer faults on its first stack store. The code image fits and is
loaded in both the early and correctly ordered cases.

| Control | Observed consequence |
|---|---|
| ROM-to-loader, stack unready | First push gets a write-protection fault. |
| Readiness before transfer | Push/pop/store complete; result90. |
| Readiness after failed transfer | Earlier fault remains; no retroactive success. |
| Loader-to-firmware, alternate valid image/stack | Actual other image completes with result165. |
| Alternate stage, stack unready | First push faults in its required region. |
| Wrong image | Execution completes with90 instead of required165; identity mismatches. |
| Wrong initial stack | Ready intended region does not protect access to another unready region. |
| Entry outside loaded code | Actual unmapped instruction-fetch fault. |

The independent [reference](reference_model.py) checks first address SP-8,
access width, push/pop value, result address/value, completion and fault class.
Native logs retain instruction bytes, applied state, access attempts, next-PC
confirmation and actual errors. A write attempt alone is not credited as complete.
New output directories retain source, build commands/diagnostics, ELFs, readelf
output, raw accesses, normalized records, reports and tool versions.

Stage names describe an owned handoff experiment, not executed product ROM or
U-Boot firmware. Page protection is an explicit readiness surrogate; it is not
an ECC implementation, cache/MMU model, physical RAM-ready/clock/reset signoff,
secure-boot authentication or multicore protocol qualification. The runner stops
at the receiver's HLT after confirming the previous result store. No silicon boot
sequence is inferred.

[Unicorn's programming documentation](https://www.unicorn-engine.org/docs/tutorial.html)
and [2.1.4 release](https://github.com/unicorn-engine/unicorn/releases/tag/2.1.4)
describe the execution substrate. Existing [U-Boot boot flows](https://docs.u-boot.org/en/stable/develop/bootstd/overview.html)
and [OpenTitan ROM release dependencies](https://opentitan.org/book/hw/ip/rom_ctrl/doc/theory_of_operation.html)
are review references; neither project is executed or qualified here.
