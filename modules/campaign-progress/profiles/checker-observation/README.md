# Checker observation validity

Review whether a checker samples the accepted and completed work that a campaign
claims to verify. Use this stage after changes to checker logic, enable, event
mapping, clock/reset or mode, and before interpreting a passing campaign.

Use [WORKFLOW.md](WORKFLOW.md) with your existing AI assistant. Python 3.10+ and
the standard library suffice for retained-data review. DVIT is optional.

```sh
python modules/campaign-progress/profiles/checker-observation/observation_check.py capture evidence run evidence/context.json --output evidence/observations.json
python modules/campaign-progress/profiles/checker-observation/observation_check.py review evidence/intent.json evidence/observations.json --json-out review.json --markdown-out review.md
```

Complete [capture-context.template.json](capture-context.template.json) from the
original run and [intent.template.json](intent.template.json) from the independent
event contract. See [FORMAT.md](FORMAT.md) for native artifacts and boundaries.
Capture reads files without executing commands. Outputs require new paths.

Review exits: `0` observed correspondence within the contract; `1` known observation
difference; `2` missing evidence; `3` invalid input/I/O. Findings take precedence
while retaining gaps. Capture exit 0 means import succeeded, including when the
native checker detected a failure. A correctly detected functional failure can
have valid observation. Neither outcome establishes verification completeness.

The optional reader supports retained **Verilator 5.020** data for one flat,
settled, positive-edge ready/valid request/completion pair. It checks identities,
observed payloads and enable intervals. Original C++ instrumentation and expected
data semantics require source review; arbitrary UVM logs are outside this reader.

## Examples and tests

The optional Linux recipe uses an existing Verilator 5.020 installation and
installs nothing. Choose a new output directory.

```sh
python modules/campaign-progress/profiles/checker-observation/examples/run_native.py example-output --verilator /opt/verilator/usr/bin/verilator_bin --verilator-root /opt/verilator/usr/share/verilator
python -m unittest discover -s modules/campaign-progress/profiles/checker-observation/tests -v
```

Stream and mailbox fixtures use different names, reset polarities and payload
relations for the same workflow. Two builds serve 22 runs: correct, gated, disabled,
wrong-event and wrong-ID checkers, faults, stalls, reset cancellation and short
windows. A separately expressed finite model checks every native sample/action;
it is fixture qualification, not a general functional oracle. Set
`OPENTOOLS_OBSERVATION_EXAMPLE` to retained output to enable native regression tests.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
