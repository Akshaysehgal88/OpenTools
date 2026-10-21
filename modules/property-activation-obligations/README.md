# Property activation obligations

Check whether the intended property instance evaluates the required events.
The helper compares an independent obligation roster with actual binding, clock,
guard, runtime-enable and mode-specific activation evidence. A global cover hit
or a run with no assertion failure is insufficient.

Use [SKILL.md](SKILL.md) with your existing AI host and native flow;
[REVIEW.md](REVIEW.md) gives the handoff record. Saved-data review needs Python
3.10+ and the standard library. No provider SDK or DVIT connection is required.

## Commands

From this directory, or using full script paths:

```sh
python activation_check.py capture retained-run run capture-context.json --output evidence.json
python activation_check.py review obligations.json bindings.json retained-run/evidence.json --json-out review.json --markdown-out review.md
```

Native paths are relative to the directory containing `evidence.json`; store a
captured snapshot beside its retained `run/` directory. Capture reads data and
never executes imported scripts, commands or binaries. See [FORMAT.md](FORMAT.md)
and the [context template](capture-context.template.json). Outputs require new paths.

Review exits: `0` within the selected observed activation contract; `1` finding;
`2` incomplete; `3` invalid input/I/O. Capture exit `0` means successful parsing,
including native assertion failures; it is not a passing-design verdict.

## Native example

With existing Linux Verilator 5.020, its runtime and a C++ build toolchain:

```sh
python examples/run_native.py new-example --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
python activation_check.py review new-example/power-clean/obligations.json new-example/power-clean/bindings.json new-example/power-clean/evidence.json
```

The recipe installs nothing. Eight builds produce twelve bounded runs across
drain-before-power-off and cancellation-before-flush contexts. They retain actual
SVA binds, elaborated XML, sample/drive logs, runtime assertion-enable values,
native user-cover counters and assertion actions, checked against an independent
clock/Boolean reference.

Controls include a disabled risk interval despite normal-mode hits, a gated wrong
clock, decoy or absent bind, reset masking, runtime assertions off with positive
cover counts, corrected active bindings exposing a fault and clean active runs.
The example checker/observer is qualification code, not an assertion generator.

```sh
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_ACTIVATION_EXAMPLE` to a retained native example root to enable real
artifact tests on Windows or Linux. Other tests use isolated synthetic core
records. The native profile covers stable-before-edge scalar same-cycle checking;
it does not establish arbitrary SVA adequacy, asynchronous reset behavior,
physical clock safety, unbounded proof or signoff. The AI workflow can use broader
company-native methods while preserving those methods' evidence limits.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
