# Address decode and attribute agreement

Use this module at a hardware/software address-map handoff, or after a decode,
remap, permission or memory-attribute change. It answers: **do the resolved
hardware and software views describe the same effective address space for the
selected initiator, configuration and mode?**

It is intended for SoC integration, interconnect DV and firmware teams. A generated
address table, passing access test and driver header can describe different stages
of a route. This review makes that boundary explicit before comparing values.

## Where it fits and what it adds

| Existing work | Contribution |
|---|---|
| Map generation and integration review | Repeatable comparison of byte windows, target offsets, permissions and attributes |
| Firmware / MMU / IOMMU configuration handoff | Check that the software view means effective mapping, rather than intended driver use |
| Decode verification | Independently required ranges, overlap and intentional-alias review alongside native results |
| Change review / CI | JSON and Markdown findings attached to the existing integration ticket or gate |

The module can replace a manual field-by-field comparison of **resolved** views.
It supplements the generator and native verification flow. It does not generate
a map, derive arbitrary RTL decode, model hierarchical translation or establish
security and cache-coherency correctness.

## Start with your existing AI agent

Give the agent this [workflow](SKILL.md), the original question and both original
views. For example:

> Review our hardware and effective software maps for the selected initiator and
> mode. Establish address units, remap stage and revisions first. Find the
> independently required ranges and alias rationale. Resolve window correspondence
> from sources, ask for missing mappings, then report differences and the native
> checks or owner decisions still needed.

For a project-local installation or reusable setup, use
[shared onboarding](../../ONBOARDING.md) with module
`address-decode-attribute-agreement` and workflow `default`. The AI can use company
native interfaces or a separately validated exporter. The bundled comparator is
optional; [AI_USAGE.md](AI_USAGE.md) describes the source review. No extra model
account or DVIT connection is required.

## First use: inspect a permission mismatch

The saved-data path requires Python 3.10+ and its standard library. No EDA engine
is required. From the clone root, enter the module folder. An installed bundle
has the same `modules/address-decode-attribute-agreement` folder.

```sh
cd modules/address-decode-attribute-agreement
python -c "from pathlib import Path; Path('.local').mkdir(exist_ok=True)"
python examples/create_example.py .local/address-permission --case permission
python address_review.py compare .local/address-permission/hardware.json .local/address-permission/software.json .local/address-permission/policy.json --json-out .local/address-permission/review.json --markdown-out .local/address-permission/review.md
```

Expected exit: **1**. Hardware permits a device write while the effective software
view forbids it. The separately permitted processor alias remains allowed; its
policy does not authorize another initiator or hide an address overlap. Inspect
both values and their evidence references before deciding which view needs repair.

Use fresh paths for a positive control:

```sh
python examples/create_example.py .local/address-valid --case valid
python address_review.py compare .local/address-valid/hardware.json .local/address-valid/software.json .local/address-valid/policy.json --json-out .local/address-valid/review.json --markdown-out .local/address-valid/review.md
```

Expected exit: **0**, agreement within the declared scope. Other cases are
`overlap`, `hole` and `paired`. The paired case explicitly updates the requirement
and both views; agreeing observations alone would not authorize that change.
Generators require a new directory; report files must also be new.

## Helper: `address_review.py`

| Operation / feature | Purpose |
|---|---|
| `compare HARDWARE SOFTWARE POLICY` | Compare explicit one-to-one pairs and retain unmapped or unknown obligations |
| Window / translation comparison | Check base, size, target and linear target-local offset, separately per initiator |
| Permissions / attributes | Compare read/write/execute and cacheable/shareable/security values, including known false values |
| Overlap / required-range review | Identify same-initiator overlap and independently required ranges not observed |
| Alias review | Admit only an evidenced initiator/window pair and its explicitly allowed differences |
| `digest RECORD` | Print the canonical JSON digest used to bind an exact view in the policy |
| `--json-out` / `--markdown-out` | Save structured evidence and the review report without overwriting inputs or prior results |

The helper reads supplied records. It executes no RTL, compiler, project script
or imported command and does not infer correspondence from similar names.

## Prepare real inputs

| Input | Engineering meaning |
|---|---|
| Hardware map | Effective selected decode after the identified configuration/remap stage |
| Software map | Effective software-visible route, permissions and attributes at the same boundary |
| Policy | Independent required ranges, explicit correspondence and current alias rationale |

Maps use `opentools.address-map.v1`. Each window identifies the initiator,
half-open byte interval `[base, base + size)`, target/local offset, permissions,
attributes and source evidence. Translation is limited to
`target_base + address - base`. Numeric fields are JSON integers in bytes.
A driver's decision not to write does not establish that hardware forbids writes.

The `opentools.address-policy.v1` policy binds both canonical view digests:

```sh
python address_review.py digest hardware.json
python address_review.py digest software.json
```

Put those values in the reviewed policy's `hardware_sha256` and `software_sha256`.
Do not refresh bindings merely to silence a disagreement. Record the original
revision, configuration, mode and semantic basis; declare completeness only for
the population actually exported. Nulls remain unknown. [FORMAT.md](FORMAT.md)
defines the records, exact alias rules and report.

## Integrate with an existing flow

1. Select one boundary and initiator/mode. Establish units, pre/post-remap stage
   and target-local offsets with the integration and software owners.
2. Reuse the company's generator, native database API or reviewed export.
   Normalize the selected resolved windows and retain their originals. Hierarchy,
   interleaving and dynamic IOMMU state require their own semantics and validation.
3. Obtain required decode ranges and alias decisions from the interface contract,
   configuration specification or receiving owner, independently of observed maps.
4. Compare matching scoped views. Attach JSON/Markdown to the integration change;
   use the team's existing policy to decide how findings and gaps affect its gate.
5. Revalidate after address/permission changes, renames, changed initiators,
   remap/configuration changes or changed software effective mapping.

A complete export with a hole differs from an incomplete export that did not
return a window. Two agreeing stale views cannot establish current applicability.

## Native evidence and supported scope

The [native recipe](examples/NATIVE.md) builds an owned two-initiator RTL decoder
and C map table. It queries selected bytes/boundaries, operations and security
inputs and checks the observations against an independent expanded-byte reference.
With the pinned runtime already configured on Linux:

```sh
python examples/run_native.py .local/address-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Qualified environment: Verilator **5.020**, GCC **13.3.0** targeting
`x86_64-linux-gnu` and Make 4.3. Nothing is installed automatically. This qualifies
the owned generator/table profile; it is not a generic RTL, C, device-tree or
IOMMU extractor or production security/coherency signoff.

## Results, handoff and checks

| Exit | Meaning / action |
|---|---|
| `0` | Agreement within supplied scope; retain source and policy bindings |
| `1` | Known view, overlap, alias or required-range issue; route it to its owner |
| `2` | Incomplete, stale, foreign or unsupported evidence; resolve the listed gaps |
| `3` | Invalid input or I/O failure; repair the record/path before interpreting a verdict |

Argument syntax errors also use 2. Known findings retain accompanying gaps.
No output approves a decode or access-policy change. Return the affected
initiator/window, original requirement, both observations, proposed correction,
receiving owner and revalidation trigger.

Run `python -m unittest discover -s tests -v` for local checks. The native test
uses `OPENTOOLS_ADDRESS_NATIVE` as described in the recipe.

[DVIT's intent integrity layer](../../DVIT.md) can carry route, alias and consumer
relationships into dependent reviews. Local/company sources remain fully usable
through the optional [context interface](../../CONTEXT_PORT.md).

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
