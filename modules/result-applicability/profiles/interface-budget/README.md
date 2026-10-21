# Interface timing budget review

Review the block-to-top timing handoff after interface allocations, reference
edges, models or loads change. Compare the original budget with both block views
and the integrated path. Preserve failing results and identify the owning source
that needs review. See [WORKFLOW.md](WORKFLOW.md) for the AI workflow and
[FORMAT.md](FORMAT.md) for the bounded native reader.

Use your existing assistant and timing flow. The optional Python helper needs
Python 3.10+ and the standard library; saved-data review needs no native engine.
Install the `result-applicability` module through the repository installer.
DVIT/MCP context is optional and separately configured; nothing installs it.

```sh
python modules/result-applicability/profiles/interface-budget/budget_review.py review saved-runs original-contract.json --json-out budget-review.json --markdown-out budget-review.md
python modules/result-applicability/profiles/interface-budget/budget_review.py capture saved-runs selected-run --output captured.json
```

Choose new output paths. Review returns `0` bounded agreement, `1` findings,
`2` unresolved evidence or `3` invalid input/I/O. Findings take precedence while
retaining gaps. Capture success only establishes a readable bound observation.

The optional Linux example uses **OpenROAD v2.0-17598-ga008522d8**:

```sh
python modules/result-applicability/profiles/interface-budget/examples/run_native.py native-budget-example --openroad /path/to/openroad
```

It collects 42 native views in two reference-edge contexts. Permissive block
budgets each pass while the integrated path fails. Coherent slow budgets agree
but retain timing debt; a shorter coherent control passes. Wrong edge, load,
library and unknown-mode controls remain distinct. The owned scalar models and
unannotated interconnect illustrate evidence correspondence, not silicon timing.

```sh
OPENTOOLS_INTERFACE_BUDGET_NATIVE=native-budget-example python -m unittest discover -s modules/result-applicability/profiles/interface-budget/tests -v
```

Set the same environment variable using the syntax of your shell. Native tests
skip when the corpus is absent. The first reader scope is one mapped scalar
interface, one mode/corner and selected max setup paths in explicit ns/pF. It
does not establish hold, all-path closure, functional equivalence, extracted RC,
frequency capability or signoff. It writes no design constraints or jobs.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
