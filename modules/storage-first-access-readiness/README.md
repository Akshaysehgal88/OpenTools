# Storage first-access readiness

Use this module before releasing a memory region to its first consumer, or after
changing reset/retention, scrub, byte-write or ECC-wrapper behavior. It reviews
**which target words were initialized by an admitted owner before any old-data
read depends on them**.

This fits in boot, memory-wrapper integration and functional release review.
Memory, firmware and DV owners can use it alongside native RAM/ECC verification.
A sub-word bus write can perform an internal read-modify-write. A global
`init_done` flag or clean ECC codeword alone does not establish initialization
history for the target word.

The activity supplements wrapper verification and release policy. It replaces
manual word-readiness and first-access reconciliation; it does not implement
memory initialization or discover hidden accesses.

| Activity | Question |
|---|---|
| Default: first-access readiness | Do target-word initialization, release and internal-read/ECC outcomes satisfy the original consumer contract? |
| [Test/repair handoff](profiles/test-repair-handoff/README.md) | Do test ownership, repair/mapping epoch, initialization and functional release remain consistent through the handoff? |

## First use

Python 3.10+ and the standard library suffice. From
`modules/storage-first-access-readiness`:

```sh
python examples/create_example.py .local/storage-early --case boot-before-scrub
python storage_review.py .local/storage-early/inventory.json .local/storage-early/journal.json .local/storage-early/policy.json --output .local/storage-early/review.json
```

Expected exit: **1**, `violated`. The owned consumer is released before scrub;
a partial write needs old data, observes the controlled uncorrectable codeword
and aborts. That can demonstrate a release-policy violation even when aborting
is correct wrapper behavior.

Compare initialization before release:

```sh
python examples/create_example.py .local/storage-ready --case boot-after-scrub
python storage_review.py .local/storage-ready/inventory.json .local/storage-ready/journal.json .local/storage-ready/policy.json --output .local/storage-ready/review.json
```

Expected exit: **0**, `satisfied` within the supplied contract. Full data/ECC
initialization precedes release, partial update and read.

Other controls cover selected-word full writes, a second first master, wrong-word
initialization with a forced global flag, correction before merge, double-bit
abort and a valid codeword without initialization history. Open JSON for release
words, replayed readiness, actual accesses, findings and gaps. Directories/
reports must be new; the generator also writes `report.json`.

## Helper and records

`storage_review.py INVENTORY JOURNAL POLICY` replays readiness, accepted
initialization/writes, release and effective old-data reads, preserving actual
ECC/error/commit outcomes. `--output` saves JSON to a fresh file; omit it to
print JSON. It executes no native commands.

[FORMAT.md](FORMAT.md) defines:

- **Inventory:** memory/initializer/test roles, aligned byte-address geometry,
  data/ECC/codeword widths, byte order and explicit wrapper traits. Include whether
  partial/full writes read old data, full writes initialize, zero masks are no-ops,
  uncorrectable errors abort and global done covers all words.
- **Journal:** current isolated initialization epoch, original initial word
  readiness/codeword and ordered initialize/read/write/inject/release events
  with actual old-data reads, byte masks, codeword transitions and outcomes.
- **Policy:** independent consumer masters, required release words/events,
  accepted access identities, global-done/correctable/codec requirements and any
  allowed full write before release.

Ready state needs original reset/retention/initialization evidence. Test injection
changes bits without granting readiness. A partial write preserves readiness
history even if its final codeword is valid. A full write grants readiness only
under the actual wrapper contract and admitted owner.

Addresses are aligned word byte addresses; this core does not split unaligned
or multi-word transactions. Counts/widths and unsigned values are explicit, with
null for unknowns. Missing target words/accesses cannot shrink the independent
requirement population.

## Codec boundary

The optional codec/merge cross-check is specifically
`opentools.hamming39_32.interleaved-even.v1`: 32 data plus 7 check bits, four
little-endian bytes, partial-write internal reads, no full-write old read,
full-write initialization, zero-mask no-op and UE abort.

Another 39/32 layout is not automatically the same codec. The owned mapping uses
positions 1–38 with Hamming parity at 1/2/4/8/16/32 and overall parity at physical
bit 38. A broader readiness review does not qualify another ECC implementation.

The [native controls](examples/NATIVE.md) use Linux, Verilator 5.020 and C++/Make.
Separate RTL/Python algorithms and an optional pinned external comparison check
the owned codec; 2375 probes exercise clean/single/double faults and data bases.
Original transaction/release observations are compared with a separate byte-vector
ledger. No dependency is downloaded by the recipe.

The controlled initial codeword is a two-state fault precondition, not every
possible uninitialized physical RAM state. Three-or-more-error behavior,
X propagation, foundry macros, physical timing/power and retention cells remain
outside qualification.

## Integrate into memory release

1. Establish the original release/first-access objective and current epoch.
   Identify initializer, test owner and every first consumer.
2. Inspect actual wrapper geometry, byte lanes and internal RMW/full-write
   behavior. Trace what constitutes complete data-and-ECC initialization.
3. Retain initial word history, actual initialization/release and internal reads/
   response/error/commit evidence. Do not rely solely on a global flag.
4. Write independent required words/accesses and policy. Review readiness,
   old-data prerequisites and codec outcomes separately.
5. Correct the original initialization sequence, release policy, wrapper or
   sourced requirement, then rerun and revalidate.
6. Hand off original intent, native source/evidence, records, report and owner
   decision. Repeat after mapping, epoch, wrapper or consumer changes.

Hidden owners, concurrent updates, additional resets and speculative internal
reads on unaccepted transactions require a broader native observation method.

## AI-first adoption and outcomes

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), original release contract,
RAM wrapper, initialization source and native observations:

> Trace readiness for the actual first target words. Determine whether partial
> writes read old data, who can initialize and when release is allowed. Preserve
> internal reads and actual ECC/commit outcomes; distinguish correct abort from
> an unsafe release policy. Ask for missing word/epoch history.

Use [ONBOARDING.md](../../ONBOARDING.md), module
`storage-first-access-readiness` / activity `default`. Existing AI/native tools
suffice. Optional [context sources](../../CONTEXT_PORT.md), including DVIT, can
connect initialization owners and release dependencies; independent use requires none.

| Exit | Meaning |
|---:|---|
| 0 | Satisfied within the supplied contract. |
| 1 | Known readiness/release/access or codec finding. |
| 2 | Incomplete evidence or original intent. |
| 3 | Invalid input or I/O. |

Argument errors use exit 2. Findings retain coexisting gaps. Current scope/content
bindings do not prove source truth or complete discovery.

```sh
python -m unittest discover -s tests -v
```

The native guide explains opt-in tool/reference variables. Other wrappers need
their own normalization/native qualification; ordinary saved review needs no
simulator or DVIT installation.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
