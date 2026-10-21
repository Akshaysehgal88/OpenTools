# Cross-mode obligation evidence

Audit existing combined-transition obligations against retained scenarios, traces
and checker observations. Use it when a shared resource or dependency creates an
interaction that separate feature tests cannot establish.

Use [WORKFLOW.md](WORKFLOW.md) with your existing AI assistant. Python 3.10+ and
the standard library suffice for saved-data review. DVIT is optional.

```sh
python modules/campaign-progress/profiles/interaction-obligations/interaction_check.py capture scenario run scenario/context.json --output scenario/native.json
python modules/campaign-progress/profiles/interaction-obligations/interaction_check.py review plan.json corpus.json --json-out review.json --markdown-out review.md
```

Start with [plan.template.json](plan.template.json) and
[capture-context.template.json](capture-context.template.json). Collect receipt
paths and the capture command's `receipt_sha256` values in
[corpus.template.json](corpus.template.json). Fill requirements
from independent design evidence, not the passing scenarios. See [FORMAT.md](FORMAT.md).
Capture reads files without executing commands. Outputs require new paths.

Review exits: `0` selected obligations supported; `1` known difference, native
comparison failure or invalid checking; `2` missing evidence; `3` invalid input/I/O.
Findings retain coexisting gaps. Capture exit 0 means import succeeded, including
native FAIL. Missing combined activity is not inferred to be nonapplicable.

The optional native reader supports Verilator 5.020 finite, single-clock Boolean
event/hold/ack journals with explicit mapping. It preserves original checker
results; typed triggers locate existing occurrences. It generates no tests or
exhaustive feature product. Instrumentation, oracle and applicability sources
still require review. Supported windows do not establish verification completeness.

## Examples and tests

The optional Linux recipe uses an existing Verilator 5.020 installation and
installs nothing. Choose a new output directory.

```sh
python modules/campaign-progress/profiles/interaction-obligations/examples/run_native.py example-output --verilator /opt/verilator/usr/bin/verilator_bin --verilator-root /opt/verilator/usr/share/verilator
python -m unittest discover -s modules/campaign-progress/profiles/interaction-obligations/tests -v
```

The [owned contract](examples/CONTRACT.md) selects three shared-state interactions.
Reset/interrupt and sleep/maintenance contexts include passing separate tests,
actual combined failures, a valid discard mode, disabled checkers and short windows.
Two builds serve 26 runs and 30 review packets; joined packets reuse retained runs.
Independent equations check every native sample/action. Set
`OPENTOOLS_INTERACTION_EXAMPLE` to retained output to enable native regression tests.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
