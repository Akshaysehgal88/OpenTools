# ECO evidence review

Use this activity after a bounded ECO to decide **which saved reports still
support the receiving claim**. It keeps changed native objects, report-specific
dependencies, required operating phase and existing reuse authority separate.

This fits in physical/integration ECO handoff and report revalidation. PD, STA,
DFX verification and receiving owners can use it alongside their native checks.
The same changed-cell count can have different consequences for a data-path report
and a clock-delivery observation.

The activity supplements ECO verification and the parent result-applicability
review. It replaces manual report-by-report dependency reconciliation. It neither
approves an ECO nor creates a reuse rule.

## First use

Saved-data review needs Python 3.10+ and the standard library. Run from
`modules/result-applicability`. Use a complete retained collection at
`.local/eco-native`, or collect one on Linux with existing
**OpenROAD v2.0-17598-ga008522d8**, **Verilator 5.020**, C++ and Make:

```sh
python profiles/eco-evidence/examples/run_native.py .local/eco-native --openroad /path/to/openroad --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Replace the tool/runtime paths and configure native libraries. The recipe installs
nothing. Test-override/active-low-reset and wake-override/active-high-reset contexts
exercise unchanged, data/control endpoint rewires and phase changes.
Choose a new output directory.

Inspect original evidence and review the old reports after a data rewire:

```sh
python profiles/eco-evidence/eco_review.py capture .local/eco-native test-control-before --output .local/eco-native/recaptured-before.json
python profiles/eco-evidence/eco_review.py review .local/eco-native .local/eco-native/reviews/test-control-data-old.policy.json --output .local/eco-native/data-old-review.json
```

Expected review exit: **1**, `review_required`. The rewire changes selected STA
dependencies while preserving the selected clock cone. Report applicability is
not determined by an unchanged cell count or a single global “ECO safe” flag.

Compare the policy selecting the retained current STA result:

```sh
python profiles/eco-evidence/eco_review.py review .local/eco-native .local/eco-native/reviews/test-control-data-cached.policy.json --output .local/eco-native/data-cached-review.json
```

Expected exit: **0**, `selected_evidence_corresponds`. The example selects current
STA evidence and retains old clock evidence only under an exact supplied
conditional rule and unchanged selected dependencies/phase. Fixture approvals
are illustrative, not real production authority.

A control rewire can break required clock delivery; merely selecting a current
report does not turn the actual failed behavior into a pass. Missing correspondence
and foreign binding controls remain incomplete. Outputs must be new files.

## Helper and records

| Operation | Responsibility |
|---|---|
| `eco_review.py capture ROOT RUN_REF` | Reads original native graph, logical mapping, report artifacts, source/executable/setup identities and outcomes. |
| `eco_review.py review ROOT POLICY` | Reimports both bound runs, compares changed objects and report projections, composes the parent applicability audit and identifies matching current evidence already retained. |
| `--output FILE` | Saves JSON to a new path; omit it to print JSON. |

Commands above include the profile path from the parent module directory.
The reader executes no received Tcl, command or binary. Capture exit 0 means
readable evidence, not ECO/report acceptance.

[FORMAT.md](FORMAT.md) describes complete records and original artifacts.
Each flat run retains consumed Verilog/models, LEF/Liberty, SDC/loader, graph,
database, logical XML, reports, original executable, commands/versions and execution
evidence. `sta.snapshot.json` and `clock.snapshot.json` preserve their own
original outcome and report bytes; they can be reconstructed only from matching
original artifacts.

The independent policy binds before/after run identities, role selection,
source/graph/executable/tool and canonical report fingerprints. It states original
claim/owner, correspondence source, required phases/outcomes, both report selections
and stronger required claims. Required reports cannot be dropped.

Exact reviewed reuse records bind original report, target run, report type,
observed/requested identity pairs and existing rule/approval/basis/reason.
Only changed global netlist/executable identities can be bridged here, conditional
on identical selected dependencies, phase, checker, models, libraries and tool.
A label or hash is not proof of approval authority.

## Integrate into report revalidation

1. State the original ECO intent and receiving claims. Identify which report
   types and operating phases remain required.
2. Retain actual before/after native objects and consumed source/setup. Establish
   stable object/pin correspondence rather than inferring impact from cell count.
3. Trace each report's selected dependency projection and actual native outcome.
   Keep global identity changes separate from report-local applicability.
4. Select old/current evidence explicitly and use only existing reviewed rules.
   Keep missing/changed report bytes unresolved, without rewriting native PASS/FAIL.
5. Review affected reports with their owners. Use a matching retained current result
   where appropriate, or perform the needed native reanalysis.
6. Hand off original intent, before/after artifacts, report selections, rule basis,
   findings/gaps and receiving decision. Repeat after dependency or phase changes.

Missing correspondence is held before attribution. Rebinding a foreign report
cannot establish current evidence.

## AI-first adoption

Give a file/tool-enabled assistant [WORKFLOW.md](WORKFLOW.md), original ECO request,
native changes and selected reports:

> Review report applicability individually after this ECO. Trace actual changed
> connections, each report's dependencies and the required operating phase.
> Preserve native failures, inspect existing reuse authority and look for matching
> current evidence before proposing redundant reanalysis.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module `result-applicability` /
activity `eco-evidence`. [REVIEW.md](REVIEW.md) records the handoff. Existing
AI/company tools suffice. Optional DVIT intent/dependency context can connect the
ECO to affected report assumptions; independent use requires no connection.

## Outcomes and qualification

| Review exit | Meaning |
|---:|---|
| 0 | Selected evidence corresponds within the bounded scope. |
| 1 | Known report/dependency/phase or native-result finding; gaps remain. |
| 2 | Incomplete or quarantined correspondence/identity. |
| 3 | Invalid/changed native package or I/O. |

Argument errors use exit 2. Missing raw reports do not establish hardware failure.

The qualified class is an endpoint rewire with two observations: selected
OpenROAD/OpenSTA constrained-path presence and finite Verilator Boolean
clock-delivery count. Flat scalar connections/aliases, bundled primitive models,
exact loaders and pinned versions define support. Half-cycle samples do not
measure physical pulse width or STA time.

Changed cell population/master, placement/boundary, stateful clock dependencies,
cycles, unknown drivers or unobserved clock transfers require another method.
Complete equivalence, routing, parasitics, timing closure, power behavior and
production signoff remain open.

Set `OPENTOOLS_ECO_NATIVE` to the retained collection and run from the module:

```sh
python -m unittest discover -s profiles/eco-evidence/tests -v
```

Native-corpus tests otherwise skip. Saved-data review runs on Windows/Linux.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
