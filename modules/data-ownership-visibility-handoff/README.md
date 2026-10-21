# Data ownership and visibility handoff

Review one shared-data transfer from producer writes through consumer use,
completion and reuse. Use the [AI workflow](SKILL.md) with effective mappings,
cache/coherency paths, maintenance and ordering contracts, source and native
observations. Your existing AI host and tools are sufficient; DVIT is optional.

The optional Python 3.10+ helper checks explicit scalar payload/control identity,
clean request/completion, release ordering, actual read value/version and ownership
history. A coherent control flag does not establish coherent payload. A clean
request is not a completion receipt; correct bytes do not establish valid ownership.

```sh
python examples/create_example.py /tmp/handoff-review --case dma-no-clean
python handoff_review.py /tmp/handoff-review/inventory.json /tmp/handoff-review/journal.json /tmp/handoff-review/policy.json
```

`dma-clean-complete` and `dma-coherent` are controls. Other cases cover pending
writeback, wrong aliases, early writes/completion, shared queues, missing release
order and a consumer reading another buffer. See [native controls](examples/NATIVE.md)
and [records](FORMAT.md).

Exit codes: 0 within the supplied observed contract, 1 findings, 2 incomplete
evidence, 3 invalid input or I/O error. `--output new.json` creates a report and
refuses to overwrite an existing file. Findings retain accompanying gaps.

## Supply the platform contract

Keep expected payload/version, actors, mappings and lifecycle milestones independent
of observed data. Resolve producer/consumer aliases to the same physical object;
establish the actual payload path separately from control. Include mapping epoch,
cacheability, shareability, maintenance target and completion, publication ordering
and what the completion signal authorizes.

The core accepts a reviewed scalar inventory and ordered events. It does not parse
arbitrary drivers or infer platform DMA/ISA semantics. Its release-order event is
a supplied platform observation, not a flush instruction or universal fence recipe.
Use existing native/company methods beyond this bounded profile.

The owned cache model has two four-byte scalar lines and separate backing/snoop
paths. It is not a production cache, Linux DMA API execution, compiler/ISA ordering
test, IOMMU model or full coherence proof. Bidirectional/device-to-CPU transfers
and shared cache-line effects require their own contracts and native qualification.

Install through the repository's project-local installer. Optional
[context sources](../../CONTEXT_PORT.md) can supply scoped object, owner, mapping
and completion relationships. Nothing downloads or installs DVIT.

For domain-specific ordering claims and model/observation evidence, use the
[ordering-boundary profile](profiles/ordering-boundary/README.md). Its owned native
path actually gates publication; it does not turn this helper's logical ordering
marker into an ISA or platform guarantee. Run the profile tests separately.
