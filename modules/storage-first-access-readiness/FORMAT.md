# Storage records

UTF-8 JSON. Flags are booleans or explicit null; data/codewords are unsigned
integers or explicit null. Duplicate identities/keys, boolean integers, nonfinite
values and out-of-order events are invalid. Use lossless integer tooling.
[create_example.py](examples/create_example.py) generates complete records.

All records contain `format`, exact `scope` (`project`, `configuration`, `mode`,
`init_epoch_ref`), `basis_ref` and boolean `inputs_complete`. The basis identifies
the consumed wrapper and reviewed mapping. A reset/retention epoch must be
current and isolated; reusing a prior epoch's ready state requires native evidence.

## Inventory: `opentools.storage.inventory.v1`

`memory_ref`, `initializer_ref`, `test_port_ref`, `geometry_evidence_ref`,
`traits_evidence_ref` and `ecc_profile_ref` are nonempty references. Initializer,
test port and consumer roles are separate. Injection never grants initialization.

`geometry` has `base_address`, `size_bytes`, `word_bytes`, `word_count`,
`data_bits`, `ecc_bits`, `codeword_bits`, `byte_order` (`little/big/unknown`).
Data width is eight times word bytes; codeword width includes ECC; region size
is word count times word bytes. Base addresses are aligned byte addresses. Each
positive count/width is at most 4096; the address range fits unsigned 64 bits.
The core does not split unaligned or multi-word bus transactions.

Exact boolean/null `traits`: `partial_write_reads_old`, `full_write_reads_old`,
`full_write_initializes`, `zero_mask_noop`, `abort_on_uncorrectable`,
`global_done_covers_all`. Unknown semantics remain gaps. A true all-word global
flag with a known uninitialized word is a finding; selected-word release can
otherwise proceed while unrelated words remain uninitialized.

## Journal: `opentools.storage.journal.v1`

`inventory_sha256`, `window_ref` and explicit boolean/null `isolated_epoch`,
`window_closed`, `accesses_complete` bind one initialization/first-access window.
Completeness is a reviewed declaration, not automatic whole-design discovery.

`initial` lists unique word byte `address`, `ready`, `codeword`, `evidence_ref`.
Missing words/values remain gaps. Ready state needs reset/retention/initialization
evidence; ECC validity alone is insufficient.

`events` have unique `event_ref`, increasing unsigned `seq`, nondecreasing
unsigned `time_tick`, `master_ref`, `evidence_ref`, `kind`:

- `release`: `released` and `global_done` flags.
- `initialize/read/write/inject`: aligned word `address`, `write_data`,
  `byte_enable`, `inject_mask`, `before_codeword`, `after_codeword`, `old_data`,
  `read_data`; and exact required flags `accepted`, `internal_read`,
  `correctable`, `uncorrectable`, `committed`, `error`, `before_ready`,
  `after_ready`, `global_done`, `released`. Integers/flags may be null when unknown.

`initialize` means an admitted full data-and-ECC write, not a completion flag or
partial scrub claim. Byte-enable bit 0 selects the lowest byte in the owned
little-endian profile. Partial writes preserve readiness history, even when
their resulting codeword is clean. Full writes grant readiness only under the
explicit wrapper contract and an admitted consumer. Initializer writes require
the inventory's owner. Test injections change bits without granting readiness.

The helper checks history continuity, release and effective old-data reads. It
does not qualify speculative internal activity on unaccepted transactions;
observed reads on those transactions require native review. Other hidden owners,
concurrent updates or reset cycles require a broader observation method.

## Policy: `opentools.storage.policy.v1`

`inventory_sha256`, `journal_sha256`, exact `window_ref` bind supplied evidence.
Boolean `require_codec_check`, `require_global_done`, `allow_correctable` record
review intent. `masters` independently lists unique `id`, `release_event_ref`,
nonempty unique `release_addresses`, `allow_full_write_before_release`,
`evidence_ref`, and nonempty `required_accesses`. Each required access has unique
`event_ref`, `kind` (`read/write`), word `address`, `evidence_ref`. A required event
must match identity and be accepted; missing observations cannot shrink intent.

Codec/merge cross-checks require `opentools.hamming39_32.interleaved-even.v1`,
32 data + 7 check bits, four little-endian bytes, internal partial-write reads,
no full-write read, full-write initialization, zero-mask no-op and UE abort.
The owned code uses positions 1–38, parity at 1/2/4/8/16/32, overall parity at
physical bit 38, and even parity. The systematic reference uses a permutation,
not a different code family. Another 39/32 codec is not interchangeable.

## Report

The report retains bindings, findings, gaps, release words, actual access
outcomes and replayed readiness. Status is `violated` with findings, otherwise
`incomplete` with gaps, otherwise `satisfied` within the supplied contract.
Cross-scope/stale bindings cannot contribute readiness. Known violations retain
unrelated gaps. Hashes use sorted keys, compact separators, UTF-8 and no nonfinite
values (`storage_core.digest`); they establish content identity, not truth or
complete discovery. Optional codec checks do not turn other ECC into qualified
support, even if the readiness-only review succeeds.
