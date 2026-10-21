# Timing endpoint review

Reconcile native unconstrained endpoints with current timing intent and explicit
non-timed exemptions. Keep output ports, register data pins and constant objects
visible even when timing-path queries return nothing. Produces JSON and Markdown.

Use [SKILL.md](SKILL.md) with your existing AI agent and STA flow. The optional
reader requires Python 3.10+ standard library; saved-data review works on Windows
and Linux. [WORKFLOW.md](WORKFLOW.md) describes the review and owner handoff.

## Quick start

From the repository root, with Linux OpenROAD
**v2.0-17598-ga008522d8** in its normal runtime environment:

```sh
python modules/timing-endpoint-review/examples/run_native.py endpoint-runs \
  --openroad /path/to/openroad
python modules/timing-endpoint-review/endpoint_review.py review \
  endpoint-runs/block-interface-missing-output \
  endpoint-runs/block-interface-missing-output/contract.json \
  endpoint-runs/block-interface-missing-output/evidence.json \
  --json-out endpoints.json --markdown-out endpoints.md
```

Expected exit **1**: the functional output lacks its required external timing.
The intentionally non-timed diagnostic and constant endpoints remain visible and
need their own current rationale. The macro-interface context exercises clock
loss, a different reset polarity, and a separate interface timing contract.

Read a qualified archive without running native tools:

```sh
python modules/timing-endpoint-review/endpoint_review.py capture RUN CONTEXT.json \
  --output evidence.json
```

Outputs must be new files. See [FORMAT.md](FORMAT.md) for original artifact and
intent records. A full clone or project-local install includes the workflow,
helper, exporter and examples; no inference SDK or DVIT dependency is installed.

## Supported native scope

One fresh flat mapped `top`, one clock and a scalar output/register-data endpoint
census, with explicit mode/reset/power cases and I/O-delay inputs. The closed
loader imports no existing SDC, timing exceptions or parasitics. The reader checks
the pinned producer and original sources, setup, command and native artifacts.

It retains the native `check_setup` unconstrained population and the actual
PathEnd classifications independently. A report member may have zero paths.
Unconstrained `INF` slack is retained as a native string, not a numerical pass.
Output-delay margins are read from output-delay path ends; register setup margins
are not reinterpreted as I/O delays. Input-delay assumptions are bound consumed
setup declarations, not a generic posthoc native getter.

Native simulated constants are separate from case/forced values. The observation
is scoped to the selected model and conditions; it does not establish physical
tie integrity, reset safety, all-mode constancy or functional correctness.
Other endpoint types, hierarchy, mixed exceptions, incremental-flow history,
hold, CDC/RDC and complete STA/signoff require separately qualified methods.

## Results and tests

Exit 0: bounded endpoint intent accounted. Exit 1: review required. Exit 2:
incomplete/quarantined evidence. Exit 3: invalid input/I/O. Findings may coexist
with gaps; a successful native check command does not establish a clean report.

```sh
OPENTOOLS_STA_ENDPOINT_NATIVE=/path/to/endpoint-runs \
  python -m unittest discover -s modules/timing-endpoint-review/tests -v
```

Without a native archive, input tests run and the native-corpus class is skipped.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
