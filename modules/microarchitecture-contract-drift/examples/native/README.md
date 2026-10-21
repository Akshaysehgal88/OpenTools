# Native capacity profiles

Use this example to connect a capacity contract to **actual elaboration and
observed allocation**, before adapting the module to a design review. It shows
why a parameter export, process exit and engineering result need separate
interpretation.

The Linux recipe uses pyslang 12.0.0 to obtain resolved values, then builds and
runs the owned SystemVerilog fixture with **Verilator 5.020**. The qualified
toolchain uses GCC 13.3 and Make 4.3. It does not modify a company runner or
discover production capacity semantics.

## First run

From `modules/microarchitecture-contract-drift`, with the native tools already
installed and configured:

```sh
python -m pip install -r requirements-native.txt
python -c "from pathlib import Path; Path('.local').mkdir(exist_ok=True)"
python examples/native/run_example.py .local/capacity-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Replace the executable/runtime paths. A complete installed `verilator` launcher
can omit `--verilator-root`. Choose a new output directory with an existing
parent. The recipe downloads no dependencies itself. It uses an owned space-free
`/tmp` alias for build/runtime and retains sources, executables, commands, logs,
Slang evidence, observations and reviews in the output.

Expected recipe exit: **0** when all fixture expectations are met. Deliberate
capacity violations remain visible in their native observations and reviews.

## Read the cases

Credit-window and live-tag profiles exercise the same activity using different
resource mechanisms:

| Folder suffix, for `queue` and `tag` | Demand / supply | Expected observation |
|---|---:|---|
| `baseline` | 8 / 8 | All eight can be accommodated; within declared bounds. |
| `reduced` | 8 / 4 | Four allocation violations; capacity review required. |
| `paired` | 4 / 4 | Coordinated demand reduction supplies a valid changed control. |

The reference independently computes served allocations and violations.
The profiles have no retirement during the selected window. They do not model
general backpressure, credit return, shared banks, latency or an industrial protocol.

Each case retains:

- `snapshot.json` and `slang.evidence/`: resolved required/available values,
  parameter overrides, native diagnostics and source/meaning references.
- `contract.json`, `review.json` and `review.md`: independent bound, premises and
  current/baseline disposition.
- Build command/diagnostics, native executable, run output and `observation.json`:
  actual issued/accepted/violation counts, reference comparison and binary identity.

`summary.json` collects the six cases. Process exit 0 alone is not the engineering
verdict; inspect observed violation counts and the contract review.

## Re-review without a simulator

From the module directory, keep the complete retained collection and run:

```sh
python contract_review.py review .local/capacity-native/queue-baseline/snapshot.json .local/capacity-native/queue-baseline/contract.json --json-out .local/capacity-native/queue-baseline/new-review.json
python contract_review.py review .local/capacity-native/queue-reduced/snapshot.json .local/capacity-native/queue-reduced/contract.json --baseline .local/capacity-native/queue-baseline/snapshot.json --json-out .local/capacity-native/queue-reduced/new-review.json --markdown-out .local/capacity-native/queue-reduced/new-review.md
```

Expected exits: **0** for baseline and **1** for reduced capacity. Use fresh report
names for another invocation. This invokes only the portable record reviewer;
it neither re-executes the archived binary nor proves the source interpretation.

## Adapt and validate

1. Give your AI assistant [SKILL.md](../../SKILL.md), the
   [module guide](../../README.md), original interface requirement and real source.
2. Identify the actual maximum live population and minimum usable entries/tags/
   credits. Inspect reservations, sharing, admission and return paths before
   mapping parameters to those roles.
3. Capture resolved facts or use separately validated native exports, then source
   explicit units, counting basis and premises.
4. Run matching and deliberately incompatible controls in the adopting flow.
   Revalidate after source/configuration or capacity-meaning changes.

Enable native integration tests with `OPENTOOLS_CONTRACT_NATIVE` set to the
native executable and `VERILATOR_ROOT` for an extracted kit. Optional
`OPENTOOLS_CONTRACT_OUTPUT` retains six case directories at a new chosen path:

```sh
python -m unittest discover -s tests -v
```

Other tools, protocols and capacity mechanisms require their own source mapping
and qualification. The portable helper needs no simulator. DVIT is optional and
unused in this recipe.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
