# Native transition controls

The owned RTL transfers one resource from two old reader claims to a new exclusive
user. Directory mode requires distinct invalidation acknowledgements and returned
data. The two-worker ring mapping requires both worker completions before a
producer can reclaim/rewrite its slot; data-return correctness is not its property.
Both are explicit owned subsets of the same exclusive-handoff mechanism.

Run from this profile directory on Linux with Verilator 5.020, C++, make and
Python 3.10+:

```sh
python examples/run_native.py /tmp/transition-proof --verilator /path/to/verilator_bin --verilator-root /path/to/verilator/share/verilator
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_VERILATOR` and `OPENTOOLS_VERILATOR_ROOT` for the native unittest.
No Slang library is needed. Outputs are created in a new directory and retain
source, commands, diagnostics, executable, raw messages/permissions and reports.
Nothing downloads or installs tools.

Eight cases produce 84 observations. An independent set-based
[reference ledger](reference_model.py) compares every native action/state field.

| Control | Actual observation |
|---|---|
| Premature directory grant | One old reader remains when new permission becomes usable. |
| Complete directory transfer | Both distinct releases and data precede accepted grant. |
| Late data | Releases are complete, but granted data is zero rather than expected 17. |
| Duplicate acknowledgement | Numerical count reaches zero while the other source is still pending. |
| Stale epoch reply | Reply is ignored; current replies complete the transfer. |
| Premature/correct ring completion | Producer reclaim/rewrite conflicts with a remaining worker only in the bad control. |
| Backpressured grant | Offered token persists; only one accepted frontier is counted. |

The premature cases permit a new-user write of165 while an old holder can still
read17. Correct controls revoke old access before reuse. Late receipts produce a
good final state but cannot remove the earlier conflict. `stable_label` is a debug
observation; it does not authorize permission or discharge obligations.

This is not a complete MSI/CHI/AXI or production ring implementation. No retry,
cancellation, eviction, reset-overlap, network fairness or general liveness proof
is claimed. Qualify each additional profile against its actual source rules.
The harness serializes command events and backpressures the grant output; it does
not establish complete multi-channel ordering or checker coverage for another design.

gem5 illustrates [transient states waiting for acknowledgements and data](https://www.gem5.org/documentation/learning_gem5/part3/cache-declarations/).
OpenTitan documents [response/request source-ID matching](https://opentitan.org/book/hw/ip/tlul/doc/TlulProtocolChecker.html).
These are mechanism references; this recipe does not execute gem5, TileLink or SBY.
