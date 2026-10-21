# Waiver revalidation

Use this module after RTL, configuration, rule or rationale changes to review
whether an existing suppression still has the **same population and applicable
premises**.

This fits in lint/CDC/RDC exclusion review, scan closure and timing-exception
maintenance. Finding, waiver and receiving owners can use it alongside their
native analysis tool. An unchanged waiver file can suppress a larger population;
a zero-match report does not establish that an exception is obsolete.

The activity supplements native analysis and waiver ownership. It replaces
manual observed-population/premise comparison, not approval or revocation.
Original native reports and rationale remain the engineering authority.

| Activity | Workflow portion |
|---|---|
| Default | Suppression population, definition, correspondence and explicit configuration-premise drift. |
| [Crossing premises](profiles/crossing-premises/README.md) | Selected CDC/RDC waiver data-stability and reset-readiness evidence. |
| [Scan population](profiles/scan-population/README.md) | Required state versus native scan membership/current exclusions. |
| [Timing exception](profiles/timing-exception/README.md) | Resolved native setup-exception reach versus current path intent and mode/clock premises. |

## First use

Python 3.10+ and the standard library suffice for comparison. From
`modules/waiver-revalidation`:

```sh
python waiver_revalidate.py compare examples/baseline.json examples/current.json --policy examples/policy.json --json-out .local/waiver-review.json --markdown-out .local/waiver-review.md
```

Expected exit: **1**, `review_required`. The synthetic `debug-receiver` waiver
now suppresses two receivers instead of one, while recorded `DEBUG_EN` changes
from 0 to 1 and violates the original `DEBUG_EN=0` premise.

For an unchanged control:

```sh
python waiver_revalidate.py compare examples/baseline.json examples/baseline.json --policy examples/policy.json --json-out .local/waiver-unchanged.json
```

Expected exit: **0**, `unchanged_within_scope`. Open Markdown for per-waiver
changes and JSON for original IDs, definition digests, mappings, premise
evaluations, global comparison issues and gaps. Report files must be new;
comparison output parents are created as needed.

## The three helpers

| Helper | Contribution |
|---|---|
| `waiver_revalidate.py compare BASELINE CURRENT` | Reviews selected native populations, waiver definitions, explicit premises and optional reviewed one-to-one finding renames. |
| `verilator_capture.py` | Native capture library invoked by `waiver_revalidate.py capture`. Runs the qualified lint profile with/without the selected waiver file, retaining both original logs and input identity. |
| `waiver_assist.py prepare` / `check` | Prepares one complete evidence-bound case for your AI host, then checks the resulting advisory review's binding, citations and declared issue coverage. It does not call a model API. |

`compare --identity-map MAP` uses existing reviewed correspondence; names are
not matched heuristically. `--format json` changes stdout; `--json-out` and
`--markdown-out` save reports.

## Prepare evidence for your AI assistant

From the module directory:

```sh
python waiver_assist.py prepare examples/baseline.json examples/current.json --waiver-id debug-receiver --policy examples/policy.json --notes examples/notes.json --question "Does the recorded rationale still apply, and what evidence would resolve the review?" --output .local/waiver-case.json
```

This operation exits **0** even though the embedded engineering audit requires
review. It retains the selected waiver's complete findings, global comparison
issues, input fingerprints and exact fact IDs. The default UTF-8 packet budget
is 512 KiB; oversize fails rather than truncating. `--max-bytes` explicitly
changes the budget.

Give the file/tool-enabled assistant [SKILL.md](SKILL.md),
[AI_USAGE.md](AI_USAGE.md), the prepared case and original source/native reports.
Ask it to write `.local/waiver-ai-review.json` using the review schema in
`AI_USAGE.md`, with its actual judgment, exact `case_id` and cited fact IDs.
Then check/save that review:

```sh
python waiver_assist.py check .local/waiver-case.json .local/waiver-ai-review.json --json-out .local/waiver-ai-binding.json --markdown-out .local/waiver-ai-review.md
```

`check` validates packet integrity, matching case/status, advisory authority,
existing citations and coverage of each computed issue. It cannot prove that
a cited fact entails the prose or establish review sufficiency. Check original
sources; regenerate the case after inputs or the question change.
Both operations return 0 for successful structure/binding checks or 3 for errors,
independently of the embedded engineering status.

The assistant can inspect broader source/native evidence beyond the comparator.
The helper organizes facts; it does not restrict reasoning to its own findings.

## Optional native lint capture

Use an existing **Verilator 5.020** in a configured native environment:

```sh
python waiver_revalidate.py capture --source examples/native/top.sv --waiver-file examples/native/waiver.vlt --waiver-id unused-signal --top top --scope example/top --run-id baseline --configuration examples/native/configuration.json --complete-inputs --output .local/native-baseline.json
```

Add `--verilator /path/to/verilator` when it is not on PATH. For an extracted
kit, configure its normal `VERILATOR_ROOT` environment. Capture actually runs lint
with and without the selected file using `--lint-only -Wall -Wno-fatal`.
It retains original invocations, exits/logs and declared file hashes in the
sibling `native-baseline.evidence` directory. Verilator performs matching;
one waiver ID represents the entire selected file.

Repeat `--source`, `--dependency` and `--include-dir` for the inspected inventory.
`--complete-inputs` declares that inventory complete; before/after hashing does
not discover closure. Configuration values are macros applied to both invocations,
not effective elaborated parameters or source-local macro observations.

Supported control files contain `verilator_config`, plain `lint_off` directives
and `//` comments, with the documented rule/file/match/contents/line selectors.
Other inline suppressions remain active. Control-flow waiver files, other versions
and commercial native adapters need separate qualification.

## Records and integration

[FORMAT.md](FORMAT.md) defines snapshots, premise policy and correspondence map.

1. Retain baseline and current **actual native populations**, original waiver
   definitions, configuration observation basis and tool/version/rule policy.
2. Source the original rationale and flat typed premises independently.
   Null/missing observations remain unknown; `false` and integer `0` differ.
3. Establish current correspondence. Use reviewed one-to-one maps for real
   moves/renames; changed rule/message still requires review.
4. Compare and inspect known additions, absent/unmapped findings, definition drift,
   premise changes and comparability gaps.
5. Ask the existing waiver owner for the appropriate source/native recheck.
   Correct original setup/rationale as justified, then recollect/revalidate.
6. Hand off original rationale, native exports, audit/AI interpretation, missing
   evidence and receiving decisions. Repeat after relevant source/configuration/
   rule or premise changes.

Partial exports do not prove removal. Changed scope/tool/identity basis can make
comparison unresolved. A matching digest proves neither rationale truth nor
approval authority. No output changes a waiver.

## Adoption, outcomes and tests

Use [ONBOARDING.md](../../ONBOARDING.md), module `waiver-revalidation` /
activity `default`, for project-local use with your existing AI host. Optional
[context sources](../../CONTEXT_PORT.md), including DVIT, can connect waivers to
scoped intent, ownership and dependent assumptions; they are not required or
automatically installed.

| Compare exit | Meaning |
|---:|---|
| 0 | Unchanged within the inspected complete scope. |
| 1 | Review required. |
| 2 | Incomplete evidence or unresolved comparison; `review_required` still retains known findings. |
| 3 | Invalid input, unsupported native tool or execution/I/O error. |

Argument errors use exit 2. Native capture returns 0/2 for complete/partial
population collection, not engineering acceptance.

```sh
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_VERILATOR` to the pinned native executable for opt-in native tests.
Run specialized profile tests separately. The
[manual record](record.template.json) supports interpretation beyond executable
snapshot formats.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
