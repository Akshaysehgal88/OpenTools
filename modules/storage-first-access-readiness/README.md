# Storage first-access readiness

Review initialization coverage, release and the first accesses to a memory region.
Use the [AI workflow](SKILL.md) with the actual RAM wrapper, boot or handoff policy
and native observations. Your existing AI host and tools are sufficient; DVIT is
optional.

For the memory-test stage, use the
[test/repair handoff profile](profiles/test-repair-handoff/README.md). It follows
test ownership, physical repair views, mapping epochs and functional release
through one recurring handoff lifecycle.

The optional Python 3.10+ helper replays word readiness and checks old-data read
prerequisites. A sub-word bus write can perform an internal read-modify-write.
A global `init_done` flag or clean ECC codeword does not establish that the target
word was initialized by an admitted owner.

```sh
python examples/create_example.py /tmp/storage-review --case boot-before-scrub
python storage_review.py /tmp/storage-review/inventory.json /tmp/storage-review/journal.json /tmp/storage-review/policy.json
```

`boot-after-scrub` is the control. Examples also cover selected-word full writes,
DMA first access, a false global completion flag, single-bit correction before
byte merge, double-bit abort and a valid codeword without initialization history.
See [native controls](examples/NATIVE.md) and [input records](FORMAT.md).

Exit codes: 0 within the supplied contract, 1 findings, 2 incomplete evidence,
3 invalid input or I/O error. `--output new-report.json` creates a report and
refuses to overwrite an existing file. Findings retain accompanying gaps.

## Supply the wrapper contract

Identify data/ECC/codeword geometry, byte lanes, reset or retention epoch, the
initializer and the first masters. Keep required target words and access intent
independent of observed coverage. Capture internal reads and actual ECC/error/
commit outcomes. Distinguish full-codeword initialization, ordinary writes and
test-only fault injection.

The checker accepts a reviewed word inventory and an ordered, complete transaction
journal for one isolated epoch. It cross-checks codec and merge semantics only for
the owned little-endian Hamming SECDED (39,32) example. Another wrapper needs its
own normalization and native qualification; matching bit counts are insufficient.
The AI workflow can use existing company tools beyond this helper's profile.

The two-state native example starts with a controlled invalid codeword. It does
not model physical uninitialized RAM, X propagation, foundry macros, timing,
retention cells or arbitrary ECC. A correctly aborted RMW can still reveal a
release-policy violation rather than a wrapper implementation defect.

Install through the repository's project-local installer. Optional
[context sources](../../CONTEXT_PORT.md) may supply scoped initialization owners,
release dependencies and memory relationships. Nothing downloads or installs DVIT.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
