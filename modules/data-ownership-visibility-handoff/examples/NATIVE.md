# Native cache/handoff controls

The owned RTL has two four-byte scalar cache lines, a producer write-back cache,
backing memory and an independently visible control register. A noncoherent
consumer reads backing memory; the coherent setting actually reads the producer's
cache through a snoop path. A clean captures a line/value/version and completes
later. The logical release-order marker does not drain it.

Run from this module on Linux with Verilator 5.020, C++, make and Python 3.10+:

```sh
python examples/run_native.py /tmp/handoff-proof --verilator /path/to/verilator_bin --verilator-root /path/to/verilator/share/verilator
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_VERILATOR` and `OPENTOOLS_VERILATOR_ROOT` to include the native
test in unittest. The runner creates a new directory and retains source, commands,
diagnostics, executable, raw state/read records, normalized inputs and reports.
It does not download or install tools.

Eleven cases produce 98 observations. All consumer reads see the control flag.
The expected payload is 165 at version 1; stale backing data is 17 at version 0.

| Control | Observed distinction |
|---|---|
| No clean | Control is visible while noncoherent payload remains stale. |
| Completed clean | Backing memory is updated before publication; consumer reads 165. |
| Coherent payload | Consumer reads 165 from the cache while backing remains 17. |
| Clean pending | Early consumer reads 17; later completion cannot erase it. |
| Wrong clean alias | Receipt targets the other buffer; required payload remains stale. |
| Write while consumer owns | Read returns 165, but producer modified the buffer prematurely. |
| Completion before read | Completion/reclaim precede consumption despite correct later bytes. |
| Shared-queue coherent/noncoherent | Same activity in a second agent context; path controls visibility. |
| Coherent without order marker | Correct bytes do not satisfy the declared ordering obligation. |
| Consumer wrong mapping | Visible control accompanies a read of the other buffer, value 34. |

[cache_model.py](cache_model.py) independently maintains immutable private/backing
versioned images and a captured writeback ledger. The runner compares every native
state/action field, mapping target and actual consumer read with that reference.
These are owned scalar path controls, not production cache or protocol qualification.

There is no eviction, speculative execution, full snoop protocol, autonomous
writeback, compiler/ISA reordering, Linux DMA API execution, IOMMU or shared-line
model. The ordering marker is a contract observation; its absence is not an
observed physical reordering failure. Completion/ownership outputs deliberately
allow misuse so the review can detect it.

The Linux [DMA mapping guide](https://docs.kernel.org/core-api/dma-api-howto.html)
distinguishes coherent/streaming mappings and explains that ordering barriers may
still be required with coherent memory. Apply the actual platform's DMA/ISA rules;
this example does not provide a universal cache-maintenance recipe.
