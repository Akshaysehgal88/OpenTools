# Checkpoint replay

Check saved-state compatibility and compare a restored continuation with a control
run. The portable helper reads records and selected-observable journals; the
[Verilator recipe](examples/verilator/README.md) performs native save/restore.
Use [SKILL.md](SKILL.md) with your existing AI agent; see [AI_USAGE.md](AI_USAGE.md).

## Quick start

Python 3.10+; standard library only. From this module directory:

```sh
python examples/create_example.py demo
python checkpoint_replay.py check demo/checkpoint.json demo/request.json demo/profile.json --artifact-root demo
python checkpoint_replay.py qualify demo/checkpoint.json demo/request.json demo/profile.json demo/control.json demo/restored.json --artifact-root demo --json-out demo/qualification.json
```

Expected exit: **0** for the supplied synthetic records. Their checkpoint is plain
demonstration data. The helper performs no native execution. Use a new directory.

`check` compares binary/configuration, prefix seed/image/point, continuation
conditions and required state. It verifies current checkpoint, executable and
prefix-file bytes. `qualify` also checks distinct bound control/restored runs,
capture-boundary values and every selected step/channel in the requested horizon.

## Qualify a native mechanism

1. Inspect the installed simulator's save/restore support and exact binary basis.
2. Inventory DUT/memory, time, RNGs, queues, scoreboard/reference state, DPI objects,
   file positions and external interactions. Record how each is restored.
3. Capture a control run, restore with the same declared inputs and compare the
   selected observations over a stated horizon.
4. Test incompatible binaries, prefix inputs and deliberately omitted state.
5. Retain journals and costs, including capture, restore and qualification.

The Linux recipe uses **Verilator 5.020**, a synchronous 16-byte memory and an
explicit C++ driver. It compares 128 suffix steps and includes missing-RNG,
lost-queue, changed-input/binary and truncated-restore controls. A reference checker
can pass even when uncaptured RNG changes the continuation.

## Limits

Matching selected observations is bounded by the declared inputs, channels and
horizon. It does not prove full process-state equivalence. Completeness declarations
need source review; the helper cannot discover all unsaved state or infer support
for UVM, cocotb, DPI, timed schedulers or external services.

A changed stimulus/control is an exploratory branch unless correspondence to the
original is established. A restored suffix is not an independently initialized
test. Checkpoint catalogs, leases, runner dispatch and automatic restoration are
outside the portable helper. See [FORMAT.md](FORMAT.md).

## Status and tests

`0` compatible (`check`) or matched selected observations (`qualify`); `1`
incompatible, corrupt/unavailable artifact or observed divergence; `2` unknown;
`3` invalid input/I/O. Reports retain known differences and gaps.

```sh
python -m unittest discover -s tests -v
```

Portable tests run on Windows/Linux. Native support is limited to the documented
Linux harness. See the [manual record](record.template.json) and [example](example.json).
Reference: [Verilator 5.020 save/restore](https://github.com/verilator/verilator/blob/v5.020/docs/guide/simulating.rst#saverestore).

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
