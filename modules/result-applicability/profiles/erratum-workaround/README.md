# Erratum and workaround review

Review a supplied notice before applying, removing or carrying forward a
workaround. Keep underlying applicability, observed behavior, mitigation,
dependent premises and current approval evidence separate.
Use [WORKFLOW.md](WORKFLOW.md) with your existing assistant and maintenance process.
The optional helper needs Python 3.10+ and the standard library.

```sh
python modules/result-applicability/profiles/erratum-workaround/erratum_review.py review saved-runs notice.json request.json --json-out maintenance-review.json --markdown-out maintenance-review.md
python modules/result-applicability/profiles/erratum-workaround/erratum_review.py capture saved-runs selected-run --output captured.json
```

Install `result-applicability` with the repository installer. Saved-data review
requires no compiler, model SDK or DVIT connection. Choose new output paths.
Review returns `0` for an accounted review packet, `1` for known findings or
inapplicable evidence, `2` for missing/unknown evidence, or `3` for invalid input/I/O.
Exit zero does not authorize a software change, workaround removal or release.

The optional Linux example uses **Ubuntu GCC 13.3.0**:

```sh
python modules/result-applicability/profiles/erratum-workaround/examples/run_native.py native-erratum-example --cxx /usr/bin/g++
OPENTOOLS_ERRATUM_NATIVE=native-erratum-example python -m unittest discover -s modules/result-applicability/profiles/erratum-workaround/tests -v
```

Set the variable using your shell's syntax. Native tests skip without the corpus.
Twenty-four owned model runs cover two guard-interval contexts. Twelve additional
reviews reuse those results for missing, stale, pending and withdrawn approval,
removal intent and stronger-claim controls. A fixed stepping can still use the
vulnerable baseline producer path; passing with the workaround does not erase
that condition. A primary fix can also invalidate a dependent clock premise.

The notice and event-delivery model are synthetic. This profile does not discover
real errata or qualify silicon, firmware ISA execution, power behavior or safety.
See [FORMAT.md](FORMAT.md) for native and predicate boundaries.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
