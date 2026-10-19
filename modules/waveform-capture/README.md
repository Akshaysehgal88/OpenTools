# Waveform capture

Plan signal selection and time history for a simulation question. Optional helpers
resolve trace objects/aliases, convert time units and preview a supported wrapper
command. Use [SKILL.md](SKILL.md) with your existing AI agent and simulator;
see [AI_USAGE.md](AI_USAGE.md).

## Quick start

Python 3.10+; standard library for saved-plan assessment/rendering.
From this module directory:

```sh
python examples/create_example.py demo
python waveform_capture.py assess demo/plan.json demo/inventory.json --binary demo/sim.bin
python waveform_capture.py render demo/plan.json demo/inventory.json --binary demo/sim.bin --waveform demo/capture.vcd --output demo/recipe.json
```

The synthetic binary is non-executable demonstration data. Inspect the preview;
`assess` and `render` never execute it. Use a new directory. Renderable means command
readiness, not proof of sufficient history or faithful replay.

## Native evidence

VCD import and optional GTKWave save support require
[pyvcd 0.5.0](requirements-native-example.txt).

```sh
python -m pip install -r requirements-native-example.txt
python waveform_capture.py inspect-vcd existing.vcd --output header.json --context-template context.json
python waveform_capture.py import-vcd existing.vcd context.json --output inventory.json
```

Fill unknown context from producer evidence between inspection and import. Verify
binary instrumentation, actual emitted objects, aliases and time origin/scale.
An HDL name alone does not establish runtime visibility.

The [Linux Verilator 5.020 recipe](examples/verilator/README.md) uses an explicit
VCD wrapper with delayed dumping and supported selectors. It demonstrates expansion
from a late timeout window to earlier acceptance and control history. Other native
wrappers need their own supported capability profile.

## Capture procedure

1. Identify the original run, question, failing observation and time basis.
2. Select a causal window and actual signals, including required clock/reset and
   handshake/control context. Explain each group.
3. Check visibility and obtain history through direct capture, an existing trace,
   a supported buffer or qualified replay before the window.
4. Read the emitted trace. Expand history or signal scope if evidence is insufficient.
5. Retain original evidence and label deliberate input/control changes separately.

Capture-time restriction can reduce dumping work. Filtering an existing waveform
cannot recover unrecorded history or remove the cost already spent dumping it.
Measure setup, build, replay, parsing and inspection as well as waveform size.
See [FORMAT.md](FORMAT.md) for exact time mapping and capability checks.

## Status and tests

`0` renderable; `1` unsupported/incompatible; `2` missing evidence;
`3` invalid input/I/O. Outputs must be new and distinct.

```sh
python -m unittest discover -s tests -v
```

See the [manual record](record.template.json) and [example](example.json).
