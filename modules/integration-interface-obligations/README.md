# Integration interface obligations

Review whether connected endpoints agree on receipt, completion, cancellation and
event persistence. Use [SKILL.md](SKILL.md) with your existing AI agent and native
artifacts. [RECORD.md](RECORD.md) retains a compact obligation table.

The optional Python 3.11+ helper uses **pyslang 12.0.0** to capture selected native
port bindings. Matching nets, directions and widths establish only those facts.
The workflow remains usable with existing tool exports when this reader is absent.

## Selected-port example

From this module directory, with the optional dependency installed:

```sh
python -m pip install -r requirements-native.txt
python examples/create_inputs.py demo
python port_capture.py --source examples/handshake.sv --top behavior_top --parameters demo/parameters.json --selection demo/selection.json --scope demo/scope.json --complete-inputs --output demo/connections.json
```

Expected exit: **0**, for four selected direct links. Use new output paths.
Inspection does not run the design. Source hashes, override values and diagnostics
remain with the output. Completeness is caller-declared, not discovered closure.

## Review the actual behavior

Record what the producer offers and what the consumer needs for each event. Keep
receipt, irreversible commit, completion and acknowledged discard distinct. Inspect
the actual bridge/consumer logic and any clock/reset assumptions.

The [native recipe](examples/NATIVE.md) runs pulse and level request profiles through
the same connected hierarchy. It includes valid delayed completion, receipt used as
completion, a cancellation after commit and a valid early discard. Structural
capture remains favorable even when native behavior violates the stated contract.

```sh
python examples/run_native.py native-demo --verilator /path/to/verilator
```

Native simulation is qualified on Linux with Verilator **5.020**, GCC 13.3 and
Make 4.3. Add `--verilator-root` for an extracted kit. No tools are installed by
the workflow. Other native artifacts can be reviewed independently.

## Status and limits

The [transition-obligation profile](profiles/transition-obligations/README.md)
reviews identity/epoch-tagged acknowledgements, transient ownership and accepted
grant/consumer evidence. Its optional Python 3.10+ helper uses the standard library
and does not require the port reader. Run its tests separately from this module's
selected-port tests.

Capture exits: `0` selected direct links connected within profile; `1` known net,
direction or width finding; `2` incomplete/unsupported direct interpretation;
`3` invalid selection, native capture or I/O error. Argument errors use 2.

The profile supports ordinary instance input/output ports on direct net/variable
references. Slices, inversion, concatenation, interfaces and arbitrary bridges need
another native interpretation. Missing objects fail capture; they are not silently
removed from the requested population. This is not a protocol or CDC/RDC engine.

```sh
python -m unittest discover -s tests -v
```

Optional native simulation tests use `OPENTOOLS_INTERFACE_NATIVE`; see the recipe.
See [AI usage](AI_USAGE.md), [formats](FORMAT.md) and the
[project-local installer](../../INSTALL.md). DVIT/context sources are optional.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
