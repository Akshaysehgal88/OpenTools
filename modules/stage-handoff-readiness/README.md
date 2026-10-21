# Execution-stage handoff readiness

Use this module before accepting a control transfer to a successor execution stage.
It checks **the image, entry, stack and readiness at the transfer boundary**,
then retains the successor's actual first stack access and observed result.

This fits in boot/integration and firmware-stage handoff review. ROM-to-loader
and loader-to-firmware are two applications of the same activity. Firmware,
platform and validation owners can use it alongside their existing boot traces,
image tools and emulation.

A correctly loaded image can still fault immediately because the stack is unready.
Readiness becoming true later does not repair the transfer snapshot.
The activity supplements native execution and initialization review, replacing
manual boundary-state/image/access reconciliation. It does not implement a
bootloader or approve a handoff.

## First use

Python 3.10+ and the standard library suffice. From
`modules/stage-handoff-readiness`:

```sh
python examples/create_example.py .local/stage-early --case rom-early
python handoff_review.py .local/stage-early/inventory.json .local/stage-early/journal.json .local/stage-early/policy.json --output .local/stage-early/review.json
```

Expected exit: **1**, `review_required`. The image fits, but the independent
successor requirement says its stack must be ready at transfer. The first stack
write fails. Inspect obligations, actual transfer state, first stack access,
observed result, findings and gaps in JSON.

Compare readiness before transfer:

```sh
python examples/create_example.py .local/stage-ready --case rom-ready
python handoff_review.py .local/stage-ready/inventory.json .local/stage-ready/journal.json .local/stage-ready/policy.json --output .local/stage-ready/review.json
```

Expected exit: **0**, `within_observed_contract`. The reference successor
completes with result 90. `firmware-valid` exercises another image/stack with
result 165. Other controls cover late readiness, wrong image, wrong initial stack
and an entry outside loaded code.

Examples are reference fixtures unless produced by the native recipe. Directories
and report files must be new; the generator also saves `report.json`.

## Helpers and records

| Helper | Contribution |
|---|---|
| `handoff_review.py INVENTORY JOURNAL POLICY` | Checks image/load identity, entry/stack setup, original boundary prerequisites, actual first stack use and selected successor result. |
| `--output FILE` | Saves JSON to a new path; omit it to print JSON. |
| `image_capture.py IMAGE --output FILE` | Reads actual supported ELF identity/load/entry metadata without executing the image. It supplies image facts, not a readiness verdict. |

[FORMAT.md](FORMAT.md) defines the inventory, journal and policy:

- **Inventory:** evidence method/source revision, image SHA-256, entry and resolved
  load segments with permissions. Addresses/ranges are explicit unsigned 64-bit
  byte addresses and half-open ranges.
- **Journal:** ordered facts, actual loaded image identity, one handoff snapshot
  with successor/entry/SP/prerequisite state, actual accesses and result.
- **Policy:** independent successor requirement, expected image/entry/SP, stack
  region/alignment, nonempty readiness requirements and optional expected result.

The handoff snapshot is the observed boundary. Later facts do not overwrite it;
missing snapshot facts stay gaps even when surrounding evidence is favorable.
Actual first accesses retain actor, purpose, operation, address/size and success.
An attempted write is not automatically completed. Foreign-actor events receive
no successor-result credit.

Source the policy from the successor contract, not the evidence. A matching hash
establishes identity, not secure-boot authenticity or loaded-address applicability.

## Native execution and image metadata

The [native recipe](examples/NATIVE.md) uses Linux, GNU Binutils **2.42**,
Python 3.10+ and **Unicorn 2.1.4**:

```sh
python -m pip install -r requirements-native.txt
python examples/run_native.py .local/stage-native
python image_capture.py .local/stage-native/loader.elf --output .local/stage-native/loader-metadata.json
```

The recipe installs nothing itself. It builds two real x86-64 receiver ELFs,
cross-checks metadata with GNU readelf and executes actual push/pop/result-store
instructions in Unicorn. An owned page-protection model makes an early first
stack write fault. Native logs retain instruction bytes, accesses, next-PC
confirmation, result store and errors.

The metadata reader supports static identity-mapped **ET_EXEC x86-64 ELF64
little-endian** images up to 64 MiB, nonoverlapping PT_LOAD ranges and executable
entry. It does not support dynamic/interpreter, relocated/extended headers or
other architectures/formats. Use those targets' native metadata methods to provide
separately validated normalized facts.

## Integrate into a stage handoff

1. Obtain the original successor contract, loaded-image identity and intended
   entry/SP/stack region with firmware/platform owners.
2. Trace initialization/readiness dependencies at the actual boundary: memory,
   stack, clocks, reset or other state required by that successor.
3. Retain original image metadata, actual load/control transfer and native access/
   result evidence. Keep the handoff snapshot before later initialization.
4. Bind inventory/journal/policy and review. Separate image/setup mismatch,
   false/missing readiness and actual successor-access failure.
5. Correct the original load/sequence/setup or sourced requirement, then rerun and
   revalidate. Later readiness cannot retroactively clear a failed transfer.
6. Hand off original intent, artifacts, report and receiving decision. Repeat
   after image, entry, stack or initialization changes.

One scoped transfer/result is supported. Multi-stage or reentrant histories need
separate scoped reviews or a broader native method.

## AI-first adoption and outcome

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), original successor
requirements, image/build records, initialization source and native observations:

> Establish exactly what must hold when control transfers. Trace actual loaded
> bytes, entry/SP, readiness snapshot and first successor accesses. Separate
> later initialization from boundary readiness, and ask for missing image or
> native access evidence.

Use [ONBOARDING.md](../../ONBOARDING.md), module `stage-handoff-readiness` /
activity `default`. [REVIEW.md](REVIEW.md) records handoff actions. Existing
AI/native methods suffice. Optional [context sources](../../CONTEXT_PORT.md),
including DVIT, can connect successor requirements and artifact dependencies;
independent operation needs none.

| Exit | Meaning |
|---:|---|
| 0 | Within the supplied observed handoff contract. |
| 1 | Known prerequisite/image/setup/access or expected-result finding. |
| 2 | Incomplete evidence, including missing first-stack observation. |
| 3 | Invalid input/image or I/O. |

Argument errors use exit 2. Findings retain gaps. Missing observation does not
prove no access occurred.

The native page-protection readiness surrogate qualifies no ECC, cache/MMU,
physical RAM/clock/reset, multicore or product-ROM sequence. It executes owned
receivers, not U-Boot or a real silicon boot flow. No status grants approval.

```sh
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_HANDOFF_NATIVE=1` in the qualified environment for native tests.
Saved-data review needs no emulator or DVIT connection.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
