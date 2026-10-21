# Low-power quiescence obligations

Review a drain acknowledgement, clock stop or power-down against all required
work owners. Use the [AI workflow](SKILL.md) with native transition evidence,
counter definitions and the shutdown contract. Your existing AI host and tools
are sufficient; DVIT is optional.

The optional Python 3.10+ helper checks owner counts and explicit prerequisites
throughout the sampled protected interval. It keeps local idle separate from
system quiescence and does not add counts with different units.

```sh
python examples/create_example.py /tmp/quiescence-example --case power-local-only
python quiescence_review.py review /tmp/quiescence-example/inventory.json /tmp/quiescence-example/journal.json /tmp/quiescence-example/policy.json
```

The example reports an external response still pending after local work has been
handed off. `power-system-drain` is the control. Other cases cover credit return
before clock stop, missing isolation and new admission after acknowledgement.
See [native controls](examples/NATIVE.md).

Use new paths with `--json-out` and `--markdown-out` to retain reports. Exit codes:
0 within the supplied sampled contract, 1 review required, 2 incomplete,
3 invalid input or I/O error. Findings retain accompanying gaps; inputs are never
overwritten. A missing milestone is bounded to the selected observation window.

## Supply the owners and obligations

Keep the required-owner roster independent of the observed export. Include work
in external queues, responses, credits or other owners that can still depend on
the retiring domain. Preserve each count's unit and counting basis. A local idle
flag cannot establish that a remote owner has completed its obligation.

[FORMAT.md](FORMAT.md) defines the inventory, transition journal and caller policy.
The helper checks each configured milestone while its protected state is active;
new work after acknowledgement can fail even when all counts were zero at the
acknowledgement sample. It does not certify coverage or counter normalization.

## Boundaries

This profile reviews one sampled shutdown and explicit owner predicates. It does
not extract arbitrary UPF, infer owner coverage, prove absence of activity between
samples or qualify analog/electrical power behavior. Abort, restore and repeated
transitions need their own applicability and temporal analysis. Native power-aware
tools remain authoritative for their supported claims.

Inspect raw source even after a favorable result. An omitted owner, a remote count
copied from local occupancy, or a flag that only claims admission is closed can
manufacture agreement. Install through the repository's project-local installer.
Optional [context sources](../../CONTEXT_PORT.md) may supply scoped ownership,
drain intent and dependent consumers. Nothing installs or downloads DVIT.

Reference: [OpenTitan power-manager operation](https://opentitan.org/book/hw/top_earlgrey/ip_autogen/pwrmgr/doc/theory_of_operation.html).
Its sequence and abort rules are design-specific, not universal assumptions here.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
