# DFT mode resource contract

Use this module when accepting a test-mode configuration or after changing mode
controls, reset masking, clock selection, access policy, supply/isolation assumptions
or constraints. It reviews whether the resources needed for **shift, capture and
unload** are present under the original mode contract.

This belongs between scan insertion/mode setup and test-access acceptance.
DFT, DFX verification, reset/clock, low-power and integration owners can use it
to reconcile a mode table with native connectivity and observed behavior.

A stitched chain or a passing functional run does not establish manufacturing
access, released reset or useful scan activity. This review supplements scan
insertion, mode diagnostics and native simulations. It replaces manual
reconciliation of the selected chain's resource prerequisites; it does not replace
ATPG, power-aware verification or timing/security signoff.

| Activity | Scope |
|---|---|
| Default: mode resources | Native chain connectivity and finite shift/capture/unload resource conditions. |
| [At-speed handoff](profiles/at-speed-handoff/README.md) | Independent OCC recipe versus observed pulses, control guards, STA clocks/cases and exception applicability. |

## First use with retained native evidence

Python 3.10+ and the standard library suffice for saved-data review. Run from
`modules/dft-mode-resource-contract`. Use a complete retained example at
`.local/dft-native`, or collect one on Linux with existing
**OpenROAD v2.0-17598-ga008522d8**, **Verilator 5.020**, a C++/Make toolchain and
the runtime libraries required by your tool distribution:

```sh
python examples/run_native.py .local/dft-native --openroad /path/to/openroad --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Replace the native tool paths. Generation installs nothing. The two owned
partition interfaces use four/eight-bit scan chains; OpenROAD replaces/stitches
the cells and Verilator runs the stitched netlist. Choose a new output directory.

Capture and review the supported reset-mask case:

```sh
python dft_resources.py capture .local/dft-native register-bank-supported-mask/run .local/dft-native/register-bank-supported-mask/context.json --output .local/dft-native/register-bank-supported-mask/recaptured.json
python dft_resources.py review .local/dft-native .local/dft-native/register-bank-supported-mask/contract.json .local/dft-native/register-bank-supported-mask/recaptured.json --json-out .local/dft-native/register-bank-supported-mask/new-review.json --markdown-out .local/dft-native/register-bank-supported-mask/new-review.md
```

Expected review exit: **0**, `BOUNDED_RESOURCES_SUPPORTED`. Inspect the Markdown
for the phase disposition and JSON for native status, observed steps, resource
evidence, findings and gaps.

Compare the functional-debug case:

```sh
python dft_resources.py review .local/dft-native .local/dft-native/register-bank-debug-is-not-manufacturing/contract.json .local/dft-native/register-bank-debug-is-not-manufacturing/evidence.json --json-out .local/dft-native/register-bank-debug-is-not-manufacturing/new-review.json --markdown-out .local/dft-native/register-bank-debug-is-not-manufacturing/new-review.md
```

Expected exit: **1**, `RESOURCE_MISMATCH`, even though that native behavior run
passes. Functional debug availability does not satisfy the independently required
manufacturing-mode/access contract.

Capture's exit 0 means valid intake, including a native FAIL. Both review outputs
are required and must be distinct new files with existing parent directories.
Keep the complete collection: the report rechecks artifacts relative to its
explicit root, not just the captured JSON.

## Helper and records

| Operation | Feature |
|---|---|
| `dft_resources.py capture ROOT WORKDIR CONTEXT --output RECEIPT` | Reads original native connectivity, source/role mappings, mode cases, observations and outcomes. Verifies artifact identity without executing commands. |
| `dft_resources.py review ROOT CONTRACT RECEIPT --json-out JSON --markdown-out MD` | Revalidates the originals and captured fields, compares independent requirements by phase, and preserves native verdict, mismatches and missing evidence. |

Fill [templates/context.json](templates/context.json) from the original source
mapping and [templates/contract.json](templates/contract.json) from independent
mode requirements. [FORMAT.md](FORMAT.md) lists the exact artifact package.

The context selects design/configuration/scope/mode/domain/run, chain and wrapper
instance, twelve input and six observed-output roles, source/measurement bases
and dependency completeness. The contract binds expected original identities,
source hashes, consumed mode SDC and run command; it states clock period and
separate phase requirements, minimum samples, selected clock and resource levels.

Keep explicit root case values, same-net connectivity and propagated leaf-reset
observations separate. This reader retains an unresolved native leaf value.
`require_propagated_reset: true` therefore remains unsupported; a finite observed
released pin or root case does not supply the stronger native propagation proof.

The qualified protocol requires released reset, manufacturing mode/access, power
available, isolation inactive and scan enable **1/0/1** for shift/capture/unload.
At least a full chain is shifted and unloaded, with useful changing state and
varying serial unload data. Another protocol needs a separately qualified reader
or the broader AI/manual review.

## Integrate into test-mode acceptance

1. Identify the original mode table, selected domain/chain and receiving acceptance
   criteria. Involve the reset, access, power and DFT owners where their premises
   differ.
2. Retain the native replaced/stitched netlist, database/preview, library/setup,
   mode SDC and tool completion evidence. Do not infer successful Tcl execution
   solely from process exit 0.
3. Map actual chain connectivity and wrapper observation roles. Preserve original
   source identities from the run request and inspect logger/model semantics.
4. Capture the finite phase trace and review it against independently written
   resource requirements. Keep manufacturing access distinct from functional debug.
5. Route known mismatches and missing reset/power/dependency evidence to their
   owners. Correct the original configuration/constraints or sourced requirement,
   then recollect and revalidate.
6. Hand off the mode contract, original artifacts, reports, limitations and
   receiving decision. Repeat after relevant control, mode, chain or setup changes.

## AI-led adoption

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), the original mode table,
native setup, connectivity and observations:

> Establish what this selected test phase needs before accepting activity. Trace
> reset masking, manufacturing access, selected clock, scan enable, power and
> isolation from source through native evidence. Separate observed finite behavior
> from unresolved propagation or stronger acceptance requirements.

Use [ONBOARDING.md](../../ONBOARDING.md), module `dft-mode-resource-contract` /
activity `default`. The [REVIEW.md](REVIEW.md) record captures owner actions.
Your existing AI and engineering tools suffice. Optional
[context sources](../../CONTEXT_PORT.md), including DVIT, can add scoped
mode/dependency intent without being required or automatically installed.

## Results and qualification

| Review exit | Meaning |
|---:|---|
| 0 | Bounded resources supported for the selected chain/phases. |
| 1 | Known resource mismatch. |
| 2 | Incomplete or `QUARANTINED` evidence; resolve identity/applicability before attribution. |
| 3 | Invalid input/artifact or I/O. |

Argument errors use exit 2. Quarantine takes precedence over attributing a result;
otherwise known mismatches retain coexisting gaps.

The saved reader supports one reset-capable, common-root chain/domain of 1–32
cells with the documented six-functional-pin mapping and qualified tool versions.
The owned ideal library and Boolean supply/isolation/access proxies establish no
electrical power behavior, characterized timing, ATPG coverage, authorization or
production signoff. Other tools/cells/protocols need native qualification.

Set `OPENTOOLS_DFT_RESOURCE_EXAMPLE` to the retained collection to include tests:

```sh
python -m unittest discover -s tests -v
```

Native-corpus tests otherwise skip. Saved-data review and tests also run on Windows.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
