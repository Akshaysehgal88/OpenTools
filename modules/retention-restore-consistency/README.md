# Retention and restore consistency

Review a selected retained structure against the state its consumer needs after
wake. Use the [AI workflow](SKILL.md) with retention selections, restore source,
native state observations and post-wake reads. Your existing AI host and tools
are sufficient; DVIT is optional.

The optional Python 3.10+ helper checks scalar bundle members, exposure
prerequisites and actual read outcomes across one observed loss/restore window.
It separates selection from obligation: lost state may be rebuilt before use,
and a cold restart can have a different contract from warm resume.

```sh
python examples/create_example.py /tmp/restore-example --case cache-metadata-only
python restore_review.py review /tmp/restore-example/inventory.json /tmp/restore-example/journal.json /tmp/restore-example/policy.json
```

The example preserves metadata while losing payload; its read hits but returns
the wrong value. `cache-paired` is the control. Other examples cover payload-only
retention, dirty metadata loss, valid-before-initialization, staged rebuild, an
explicit cold restart and a context payload/owner bundle. See
[native controls](examples/NATIVE.md).

Use new paths with `--json-out` and `--markdown-out` to retain reports. Exit codes:
0 within the supplied observed contract, 1 review required, 2 incomplete,
3 invalid input or I/O error. Findings retain accompanying gaps; inputs are never
overwritten. A correct final snapshot does not erase earlier exposure or read faults.

## Supply the consumer contract

Keep bundle members and expected roles independent of the observed selection
list. Include the payload's identity/ownership, valid state, dirty/status and
initialization dependencies that matter to this consumer. Source the before
snapshot and any reinitialized values; do not substitute reset values for unknown
saved state. [FORMAT.md](FORMAT.md) defines the records.

The helper accepts exact scalar values up to 4096 bits. It does not parse arbitrary
UPF or vendor retention reports. Supply reviewed normalization or use existing
native methods directly with the AI workflow. Preserve original artifacts and
lossless integer values.

## Boundaries

The native example models selective logical state loss in owned RTL. It does not
validate retention cells, ECC encoding, X propagation, analog power or physical
timing. A logical initialization-ready bit is not an ECC implementation. Dirty
metadata loss can violate the bundle even when a read returns correct data; that
does not itself prove an observed writeback failure.

Inspect raw evidence even after a favorable report. Wrong member roles, aliased
read data or omitted early history can manufacture agreement. Cold discard needs
its own authority and dirty-state handling; it is not a universal repair for lost
retention. Install through the repository's project-local installer. Optional
[context sources](../../CONTEXT_PORT.md) may supply scoped bundle, restore-order
and consumer relationships. Nothing installs or downloads DVIT.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
