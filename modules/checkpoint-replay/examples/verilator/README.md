# Native save/restore qualification recipe

This example implements native `--savable` serialization for one inspected
Verilator **5.020** model plus an explicit C++ wrapper. It is an opt-in Linux
build/run exercise. It does not install tools, change a company runner or make
another testbench savable.

From the checkpoint-replay module directory, with an existing native executable,
runtime root, GCC supporting C++17 and GNU Make:

```sh
python3 examples/verilator/run_example.py --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator --directory native-example --negative-controls --overhead-pairs 6
```

The output directory must be new with an existing parent. Build commands, copied
sources/hashes, executable, native checkpoints, raw process journals, normalized
records, compatibility/qualification reports and scoped timings remain there.
The temporary build uses an owned space-free directory because GNU Make is
sensitive to spaces. Runtime/output paths can contain spaces. The installer never
runs this example or installs Verilator/GCC/Make.

## Model and captured state

The model has 16 memory bytes and a pipelined read-before-write output. The wrapper
loads a 16-byte prefix image through actual writes, then drives deterministic LCG
stimulus. At the default capture point after 64 driver steps, a transaction remains
pending. Each step advances simulation time by two ticks after two reset cycles.

| Required state | Mechanism in this inspected recipe |
|---|---|
| DUT memory, pipeline, clock/trigger state | Generated model stream operators |
| Simulation time | Generated 5.020 root serializes its VerilatedContext; inspected generated source is retained |
| Driver step and advanced RNG | Explicit wrapper scalar fields |
| Pending expected transactions | Explicit ordered queue entries |
| Reference memory and checker digest/counts | Explicit wrapper arrays/scalars |
| Prefix image/seed/point | Native header validation plus content-bound records/current-file checks |
| Delayed HDL scheduler, DPI objects, sockets | Absent from this model/driver; no general support inferred |
| Open input-file positions | None: prefix image is fully read and the file closes before simulation |

This wrapper does not use `$urandom`, a Python interpreter or UVM. Serializing a
VerilatedContext seed setting is not a general advanced-RNG restoration mechanism.
Legacy external simulation-time variables would need their own capture. Native
file-descriptor tables and arbitrary process state are not captured by this recipe.

## Qualification and negative controls

The default control saves state at a quiescent low-clock boundary and continues.
The script checks current files and captured/requested compatibility before normal
restore, then compares all selected boundary/channel values and every one of 128
suffix steps. A separate reset-based run supplies an independent reference; it is
not mislabeled as restored execution. The test suite independently calculates RNG,
memory, pending queue, output, time and checker digest for the native journal.

`--negative-controls` exercises:

- An intentionally uncaptured external RNG: normal compatibility rejects it. A
  controlled bypass using this example's own incomplete file demonstrates that the
  native hardware checker can pass while the continuation changes.
- A deliberately lost pending transaction: the checker fails and observations
  diverge after restore.
- A newly compiled binary with changed wrapper revision, changed prefix-image
  bytes and a changed pre-capture seed: compatibility rejects them before normal
  native restore.
- A deliberately truncated owned checkpoint: the current hash check rejects it.
  A separate controlled bypass demonstrates native restore failure; core dumps
  are disabled for these child processes. This is not normal restoration policy.

No arbitrary external checkpoint is executed by the portable helper. Use only
trusted files with the native mechanism. Normal operational storage/concurrency,
leases and retention remain the runner's responsibility; this fresh-directory
exercise is not an atomic checkpoint catalog or cache service.

## Cost boundary

`summary.json` records native prefix/save/restore/suffix timings, whole child
process wall times, binary/checkpoint bytes and local comparison cost. Individual
invocations retain child user/system CPU. `recipe-timing.json` includes the recipe's
build, executions, records/checks, requested controls and temporary cleanup; it
excludes Python startup, tool installation and human review.

`--overhead-pairs N` alternates full per-step observation and boundary-only reset
runs using the same binary and all reference checks. It verifies matching selected
boundary/final state and retains process/suffix deltas and journal sizes in
`sampling-cost.json`. Boundary-only output cannot qualify the full trajectory.
This measures scoped observation work plus scheduling/filesystem noise; it is not
a production instrumentation benchmark or a reduced-evidence equivalence claim.

The tiny prefix may cost less than capture/restore. Compare full repeated-task cost
before adoption, including first capture and qualification amortization. No SoC
speedup, universal state equivalence or useful production milestone is inferred.

## Native tests

```sh
OPENTOOLS_CHECKPOINT_NATIVE=/path/to/verilator_bin VERILATOR_ROOT=/path/to/share/verilator python3 -m unittest discover -s tests -v
```

Without those environment variables, the portable suite runs and native execution
is explicitly skipped. The native qualification uses Linux, Verilator 5.020,
GCC 13.3 and GNU Make 4.3. Other versions, operating systems, timed/UVM/cocotb/DPI
models and process checkpoint mechanisms need their own capability/state review.
Cross-host or ABI transfer is not qualified. Include relevant runtime/ABI identity
in the captured/requested configuration and qualify that transfer before use;
portable Python records do not make native serialized bytes platform-independent.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
