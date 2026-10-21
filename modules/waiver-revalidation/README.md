# Waiver revalidation

Compare observed suppression populations and recorded applicability premises after
an RTL, configuration or rule change. Produces JSON and Markdown review reports.
Requires Python 3.10+; the comparator uses the standard library.

Use [SKILL.md](SKILL.md) with your existing AI agent to inspect the rationale and
source evidence. [AI_USAGE.md](AI_USAGE.md) covers cited review packets.

## Quick start

From the repository root:

```sh
python modules/waiver-revalidation/waiver_revalidate.py compare \
  modules/waiver-revalidation/examples/baseline.json \
  modules/waiver-revalidation/examples/current.json \
  --policy modules/waiver-revalidation/examples/policy.json
```

Expected exit: **1**. The synthetic case expands the suppression population and
changes a recorded premise. Add `--json-out audit.json --markdown-out audit.md`
to save reports. Existing outputs are never overwritten.

## Native capture

Requires Verilator **5.020** in the execution environment.

```sh
python modules/waiver-revalidation/waiver_revalidate.py capture \
  --source modules/waiver-revalidation/examples/native/top.sv \
  --waiver-file modules/waiver-revalidation/examples/native/waiver.vlt \
  --waiver-id unused-signal --top top --scope example/top --run-id baseline \
  --configuration modules/waiver-revalidation/examples/native/configuration.json \
  --complete-inputs --output baseline.json
```

Add `--verilator /path/to/verilator` if needed. Capture runs lint with and without
the selected waiver file and retains both logs in `baseline.evidence/`. Verilator
performs the matching. One waiver ID represents the whole selected file.

Repeat `--source`, `--dependency` and `--include-dir` to declare the input set.
`--complete-inputs` is a caller declaration; files are hashed before and after
capture. Configuration values are command-line macros applied to both invocations,
not effective elaborated parameters or source-local macro values.

Supported waiver files contain `verilator_config`, plain `lint_off` directives
and `//` comments. Selectors: `-rule`, `-file`, `-match`, `-contents`, `-lines`.
The fixed lint profile is `--lint-only -Wall -Wno-fatal`. Other inline suppressions
remain active; control-flow waiver files, other versions and commercial adapters
are unsupported.

## Review and integration

For STA exception closure, the optional
[timing exception profile](profiles/timing-exception/README.md) compares resolved
native setup-exception reach with current path intent and the original mode,
clock and role premises. It distinguishes reviewed renames from newly masked
required paths and reuses the existing waiver records. Matching reach alone
does not approve a timing exception.

For scan insertion/closure, the optional
[scan population profile](profiles/scan-population/GUIDE.md) reconciles an
independent required state roster, actual native chain membership and current
exclusion rationale. It reads a qualified OpenROAD inventory and reuses the
existing comparator for selected exclusion drift. Membership is separate from
ATPG/fault coverage.

For selected CDC/RDC findings, the optional
[crossing-premise profile](profiles/crossing-premises/GUIDE.md) adds observed
data-stability and reset-readiness premises from a bound event journal. It reuses
this comparator and preserves structural reports. Its native example uses an
explicitly synthetic crossing population and actual functional RTL observations;
it does not perform CDC/RDC analysis.

Compare actual native populations. Use `--identity-map` for reviewed one-to-one
renames; moved source locations can change finding IDs. Partial exports do not
prove removal, and zero matches do not establish that an exception is obsolete.
Tool, scope or rule-basis changes can leave correspondence unresolved.

Keep the native reports and route changed premises or populations to the waiver
owner. The utility neither approves nor revokes waivers. See [FORMAT.md](FORMAT.md)
for snapshots and maps. The [manual template](record.template.json) and
[manual example](example.json) are separate review formats.

## Status and tests

| Exit | Meaning |
|---|---|
| 0 | Unchanged within the inspected complete scope |
| 1 | Review required |
| 2 | Incomplete evidence or unresolved comparability |
| 3 | Invalid input, unsupported tool or execution/I/O error |

Argument errors use exit 2. Read the report status as well as the exit code.

```sh
python -m unittest discover -s modules/waiver-revalidation/tests -v
```

Set `OPENTOOLS_VERILATOR` to Verilator 5.020 to enable native tests.
Reference: [Verilator control files](https://verilator.org/guide/latest/control.html).

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
