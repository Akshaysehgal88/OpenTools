# Bring-up observation comparison

Review a captured status observation before comparing it with a pre-silicon
expectation. Keep device/image identity, reset history, diagnostic side effects
and source-read time separate from the returned value. See
[WORKFLOW.md](WORKFLOW.md) for the AI workflow and [FORMAT.md](FORMAT.md) for records.

Use your existing assistant and lab workflow. The optional saved-data helper needs
Python 3.10+ and the standard library. Install `side-effect-access-order` with the
repository installer; it includes the existing diagnostic receipt engine.
DVIT/MCP is optional and separately configured.

```sh
python modules/side-effect-access-order/profiles/bringup-observation/bringup_review.py review saved-runs question.json --json-out observation-review.json --markdown-out observation-review.md
python modules/side-effect-access-order/profiles/bringup-observation/bringup_review.py capture saved-runs selected-run --output captured.json
```

Choose new output paths. Review returns `0` supported within the owned emulation,
`1` inapplicable, contrary or known review findings, `2` inconclusive, or `3` invalid
input/I/O. A read after a clearing reset can remain inconclusive about an earlier
fault. A retained early receipt can support a bounded comparison. A qualified
value outside the original observation window cannot answer that comparison.
Capture success is an intake result, not a hardware-test pass.

The optional Linux example uses **Ubuntu GCC 13.3.0**:

```sh
python modules/side-effect-access-order/profiles/bringup-observation/examples/run_native.py native-observation-example --cxx /usr/bin/g++
OPENTOOLS_BRINGUP_NATIVE=native-observation-example python -m unittest discover -s modules/side-effect-access-order/profiles/bringup-observation/tests -v
```

Set the environment variable using your shell's syntax. Native tests skip without
the corpus. Eighteen command-image runs cover cold-start and wake-entry contexts.
The producer models sampled sticky status, POR/warm reset, read effects and a host
capture buffer. Model identities and timestamps are emulated observations.
It does not qualify real silicon, instruments, firmware ISA execution, physical
reset/power sequencing, clock synchronization or root cause.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
