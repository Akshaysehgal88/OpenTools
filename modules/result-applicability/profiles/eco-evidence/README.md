# ECO evidence review

Review which saved reports still apply after a bounded ECO. Keep changed objects,
report dependencies, required operating phases and reuse approvals separate.
Start with the [workflow](WORKFLOW.md); use the [review record](REVIEW.md) for a handoff.
The host AI can use existing team reports and tools throughout this stage.

The optional Python 3.10+ helper compares original before/after evidence through
the parent result-applicability audit. It preserves native outcomes and recommends
matching current results already retained. It approves no ECO or reuse rule.

## Saved evidence

```sh
python profiles/eco-evidence/eco_review.py capture evidence test-control-before --output capture.json
python profiles/eco-evidence/eco_review.py review evidence evidence/reviews/test-control-data-old.policy.json --output review.json
```

Run from the result-applicability module directory. Output paths must be new.
Exit codes: `0` selected evidence corresponds within scope; `1` review required;
`2` incomplete; `3` invalid input/I/O. Findings take precedence and gaps remain listed.
Capture success establishes readable evidence, not acceptance.

## Native example

Linux collection requires OpenROAD `v2.0-17598-ga008522d8`, Verilator `5.020`,
a C++ compiler and make, configured in the adopting environment:

```sh
python profiles/eco-evidence/examples/run_native.py evidence --openroad /path/to/openroad --verilator /path/to/verilator_bin --verilator-root /path/to/verilator/runtime
export OPENTOOLS_ECO_NATIVE="$PWD/evidence"
python -m unittest discover -s profiles/eco-evidence/tests -v
```

Saved-data review also runs on Windows, using Python alone. Set
`OPENTOOLS_ECO_NATIVE` to the evidence directory before running tests; otherwise
native-fixture tests skip. Native tool setup is separate from installing the skill.

The example has two contexts: test override with active-low reset, and wake
override with active-high reset. Both exercise endpoint rewires, unchanged results
and phase changes. The same cell count can hide different report consequences.
A data rewire changes selected STA dependencies while preserving the selected
clock cone; a control rewire breaks required clock delivery. Existing exact-pair
approval is still required to bridge changed global identities.

See [FORMAT.md](FORMAT.md) for the qualified helper boundary. Complete equivalence,
parasitics, routing, power behavior and production signoff require their own evidence.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
