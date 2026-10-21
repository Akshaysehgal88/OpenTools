# Native controls

The owned four-word RAM implements 32 data + 7 ECC bits. Its Hamming SECDED
encoder/decoder and the Python column model use separate algorithms. The native
codec probes three data patterns with no fault, all 39 single-bit faults and all
741 double-bit pairs, plus 32 clean data-basis vectors: 2,375 probes.

Run from this module on Linux with Verilator 5.020, C++, make and Python 3.10+:

```sh
python examples/run_native.py /tmp/storage-proof --verilator /path/to/verilator_bin --verilator-root /path/to/verilator/share/verilator
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_VERILATOR` and `OPENTOOLS_VERILATOR_ROOT` to include the native
test in unittest. The runner uses a temporary build directory, retains sources,
commands, diagnostics, executable and raw records in a new output directory,
then compares actual array transactions against a separate byte-vector ledger.

| Control | Observation |
|---|---|
| Boot/DMA before scrub | Premature release; partial-write old read sees controlled UE and aborts. |
| Boot/DMA after scrub | Full data/ECC initialization precedes release, partial update and read. |
| Selected full write first | Target initialized without old read; global completion stays false. |
| Wrong word + forced global flag | Target remains uninitialized despite the flag. |
| Single data-bit fault | RMW corrects the unmodified byte before merging. |
| Double data-bit fault | RMW aborts despite prior initialization. |
| Valid code, no initializer | Successful ECC/data operation still violates readiness history. |

Reset sets each codeword to `3`: two check-bit flips in encoded zero. This is
an explicit two-state fault precondition, not a model of every uninitialized RAM.
The bench captures initial words, 39 memory transactions and nine release events.
It does not qualify X behavior, physical macros, timing, power or retention.
SECDED single/double controls make no guarantee for three or more errors.

## Optional external comparison

[reference_manifest.json](reference_manifest.json) pins the upstream lowRISC
OpenTitan Hamming encoder, decoder and Apache license by commit and SHA-256.
Fetch those files separately under their original names and pass
`--reference-dir /path/to/files` (or `OPENTOOLS_ECC_REFERENCE` for unittest).
The runner verifies every hash and compares the native encodings, decoded data,
syndromes and flags after the documented bit permutation. It never downloads
anything. External source is not bundled or required for ordinary use/tests.

OpenTitan's [SRAM theory of operation](https://opentitan.org/book/hw/ip/sram_ctrl/doc/theory_of_operation.html)
describes sub-word RMW and initialization of data/integrity. That mechanism is
useful context; this owned wrapper and pinned Hamming codec do not claim to be
the OpenTitan SRAM implementation or its current integrity-code configuration.
