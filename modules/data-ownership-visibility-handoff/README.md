# Data ownership and visibility handoff

Use this module to review one shared-data transfer from producer writes through
publication, consumer use, completion and reuse. It checks whether the consumer
used the **intended object and version under the required visibility and ownership
contract**.

This fits in hardware/firmware integration, DMA or shared-queue bring-up, and
revalidation after mapping, cacheability, coherency, maintenance or completion
changes. Producer, consumer, platform and DV owners can use it to reconcile
assumptions that are often spread across RTL, driver code and platform documents.

A visible control flag does not establish visible payload. A clean request is
not a clean-completion receipt. Correct returned bytes do not establish valid
ownership. The review keeps these premises separate. It supplements platform
APIs, scoreboards and native traces; it replaces manual reconstruction of the
selected scalar handoff's mapping, visibility and ownership history.

| Activity | Question |
|---|---|
| Default: visibility and ownership | Did the intended consumer path observe the required payload/version after the required maintenance/order, and did completion/reuse respect ownership? |
| [Ordering boundary](profiles/ordering-boundary/README.md) | Does a selected publication-ordering control cover the actual access domains and placement, and what does model/observation evidence establish? |

## First use

Python 3.10+ and the standard library are sufficient. Run from
`modules/data-ownership-visibility-handoff`:

```sh
python examples/create_example.py .local/handoff-stale --case dma-no-clean
python handoff_review.py .local/handoff-stale/inventory.json .local/handoff-stale/journal.json .local/handoff-stale/policy.json --output .local/handoff-stale/review.json
```

Expected exit: **1**, `review_required`. In this owned example the consumer sees
the published flag but reads stale backing data **17/version 0**, rather than
the intended **165/version 1**. The payload path is noncoherent and the producer
has not completed the necessary writeback. Inspect `publications`, `reads`,
`findings` and `gaps` in `review.json`.

Compare a completed-maintenance path:

```sh
python examples/create_example.py .local/handoff-clean --case dma-clean-complete
python handoff_review.py .local/handoff-clean/inventory.json .local/handoff-clean/journal.json .local/handoff-clean/policy.json --output .local/handoff-clean/review.json
```

Expected exit: **0**, `within_observed_contract`. `dma-coherent` is a second
control: it obtains the intended payload through the explicit snoop path even
while backing memory remains stale. Neither case is a general cache-maintenance
recipe. Example directories and output files must be new; the generator also
writes its own `report.json` for comparison.

## Helper and input records

`handoff_review.py INVENTORY JOURNAL POLICY` replays the supplied scalar lifecycle.
It checks the required object/mapping population, payload/control identity,
captured clean request/completion, release ordering, actual consumer value/version,
completion and ownership reuse. `--output` saves JSON to a fresh file; omit it
to print JSON. It does not execute cache operations or parse arbitrary drivers.

[FORMAT.md](FORMAT.md) defines the three records:

| Input | Source and important fields |
|---|---|
| Inventory | Platform-reviewed objects and producer/consumer aliases, physical identity, mapping epoch, coherent path, cacheability, shareability, line geometry and maintenance actor. |
| Journal | Original ordered, accepted events and observed effects in one isolated window: writes, clean request/completion, order, publish, actual read response, completion and reclaim. |
| Policy | Independent required objects/mappings, intended payload/control paths, expected value/version, milestone IDs, ordering/completion contracts and selected event window. |

Do not set the expected value to whatever the consumer returned. Bind journal and
policy to their original inputs using the format's canonical digests. Scope
includes project, configuration, mode and handoff identity.

Addresses are byte addresses; mapped events name an exact scalar start. Values
fit the declared whole-byte width, and versions are explicit unsigned identities.
Unknown values, receipt effects, path semantics or initial ownership remain null
and produce gaps. Use lossless integer handling.

A `clean_complete` must identify the earlier request's **captured** target,
value and version. A later clean cannot repair an earlier stale read.
`release_order` records the version covered by a supplied platform ordering
mechanism; it is separate from maintenance and does not itself drain a cache.
Publication, qualified consumption, completion and reclaim retain their distinct
ownership meanings.

## Integrate with your transfer flow

1. Identify one transfer objective, original expected payload/version and lifecycle
   boundary. Ask producer and consumer owners what publication and completion
   actually authorize.
2. Resolve both aliases to the same intended physical object and mapping epoch.
   Establish payload and control paths independently, including actual cache and
   coherency attributes.
3. Retain native evidence for accepted writes, maintenance completion, platform
   ordering, publication, actual consumer response and ownership transitions.
   A software command alone is not an observed hardware effect.
4. Export the inventory/journal and source the independent policy. Keep required
   objects and mappings even when an imported trace omits them.
5. Review the report with the responsible mapping, cache, producer or consumer
   owner. Inspect earlier findings even if a later event succeeds.
6. Fix the original flow or sourced contract, then recapture and revalidate.
   Preserve the original request, mappings, journals, report and owner decision.

The helper operates on a reviewed scalar inventory and ordered events. It does
not infer DMA/ISA semantics, implement IOMMU translation or prove a production
coherence protocol.

## AI-led adoption and native validation

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), the transfer objective,
actual driver/sequencer source, mapping evidence and native observations:

> Trace this payload separately from its publication flag. Establish object/alias
> identity, cache/coherency path, maintenance completion, ordering and completion
> authority. Check the actual read response and ownership through reuse. Ask for
> missing platform premises before recommending a maintenance or barrier change.

Use [ONBOARDING.md](../../ONBOARDING.md), module
`data-ownership-visibility-handoff` / activity `default`. Your existing AI host
can investigate other native evidence or adapt a validated exporter. Optional
[context sources](../../CONTEXT_PORT.md), including DVIT, can add scoped ownership,
mapping and completion relationships without being required for operation.

The [native controls](examples/NATIVE.md) use Linux, Verilator 5.020 and a C++/Make
toolchain. Eleven cases exercise two four-byte scalar lines, backing/snoop paths,
pending/wrong-target maintenance, early reuse/completion, shared queues, missing
ordering and a wrong consumer mapping. The mapping is source-reviewed, not a
general driver extractor.

## Outcome and limits

| Exit | Meaning |
|---:|---|
| 0 | Within the supplied observed contract. |
| 1 | Known visibility, mapping or lifecycle findings; inspect coexisting gaps. |
| 2 | Incomplete scope, observation, expectation or platform evidence. |
| 3 | Invalid input or I/O. |

Argument errors use exit 2. A known finding survives later successful maintenance
or reuse. Reports establish neither source authority nor receiving acceptance.

The owned model has no eviction, speculation, full snoop protocol, autonomous
writeback or compiler/ISA execution. Linux DMA APIs, IOMMU behavior, shared-line
effects, bidirectional transfers and device-to-CPU paths need their own contracts
and native qualification. A logical order marker is not physical ordering proof.

```sh
python -m unittest discover -s tests -v
```

Native tests require the tool environment described in the native guide. The
ordering profile has a separate test directory and qualification.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
