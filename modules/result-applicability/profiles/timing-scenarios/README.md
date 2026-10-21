# Timing scenario coverage

Compare selected native timing runs with independently required operating
scenarios. Check the actual model, mode, clock, power-state and RC basis before
counting a run toward an obligation. Preserve timing failures separately from
whether the required scenario was analyzed.

Use [WORKFLOW.md](WORKFLOW.md) with your existing AI agent and company tools.
The optional Python reader reuses the parent result-applicability records;
it requires Python 3.10+ standard library. Saved-data review works on Windows and
Linux. No model API, DVIT connection or replacement scheduler is required.

## Example

Native collection is qualified on Linux with OpenROAD
**v2.0-17598-ga008522d8**, in its normal runtime environment. From this directory:

```sh
python examples/run_native.py runs --openroad /path/to/openroad
python scenario_review.py review runs \
  runs/requirements/wake-sequence.plan.json \
  runs/requirements/wake-sequence.omitted.corpus.json \
  --json-out scenarios.json --markdown-out scenarios.md
```

Expected exit **1**: three passing runs cover only two of three independently
required obligations. A repeated functional run does not cover the missing
low-voltage wake scenario. The manufacturing-capture example exercises the same
review stage with a different mode/clock recipe and nonapplicable combination.

Read one qualified saved run without launching native tools:

```sh
python scenario_review.py capture runs RUN_REFERENCE --output capture.json
```

Review and capture require new output paths. [FORMAT.md](FORMAT.md) describes the
explicit plan, selected inventory and original artifact bindings.

## Native boundary

One fresh flat `top`, one library and one clock per process, one scalar register
pair, explicit operating conditions and case ports. The reader checks actual
selected min/max PVT objects, library/source bytes, clock definition/coverage,
register pin census, native cases and the selected maximum-setup representative.
The closed loader imports no SDC, timing exceptions or parasitic files.

The example libraries contain illustrative owned scalar timing tables. Their
voltage and temperature values are native **model conditions**, not measured
supply/temperature or characterized silicon behavior. Interconnect is unannotated;
the native annotation report is retained. Power-state/mode roles and scenario
exclusions are supplied source declarations, not physical power measurements.

This profile does not qualify hold timing, all structural paths, extracted RC,
OCV/derates, mixed exceptions or signoff. Use the team's validated native methods
for other scope. Clean selected paths and scenario counts cannot prove sufficiency.
The workflow remains usable beyond this reader's support boundary.

## Results and tests

Exit 0: declared obligations accounted within scope. Exit 1: missing/inapplicable
scenario or observed selected-path timing failure. Exit 2: unresolved evidence.
Exit 3: invalid input/I/O. Findings can coexist with gaps or quarantined runs;
read all three lists. Native outcomes remain visible even when applicability fails.

```sh
OPENTOOLS_STA_SCENARIO_NATIVE=/path/to/runs \
  python -m unittest discover -s tests -v
```

Without an archive, input tests run and the native-corpus class is skipped.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
