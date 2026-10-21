# Timing exception reach

Review a setup false path when selectors, hierarchy, operating mode or path intent change. This activity checks which native endpoint pairs the exception actually masks and whether its current reach still matches the rationale that permitted it.

Use it during SDC review, block integration, mode bring-up and waiver revalidation. An STA engineer owns the native setup; the design or methodology owner supplies the independent timing requirement and exception rationale. The output supplements the STA report and exception review record. It can replace a manual before/after reach comparison within the supported scope; it does not approve an exception or edit SDC.

## Start with your existing AI agent

From a clone, give your file/tool-enabled agent this request:

> Use the timing-exception activity in waiver-revalidation. Identify the actual setup exception, affected modes, original rationale and current endpoint timing requirements. Inspect the native selector/application history and compare before/after reach. Keep observed reach separate from approval, and ask for any missing intent or source evidence.

The agent can follow [WORKFLOW.md](WORKFLOW.md) using your company's native STA flow. For project-local installation and discovery, follow [onboarding](../../../../ONBOARDING.md). No model SDK or additional subscription is required by this helper.

The bundled reader needs Python 3.10+ standard library. Saved-data capture and review work on Windows and Linux. The native example requires Linux and OpenROAD **v2.0-17598-ga008522d8**, already available in its normal runtime environment.

## First use: reproduce the reach review

Run these commands from this profile directory. Choose a new output directory:

```sh
python examples/run_native.py .local/exception-native --openroad /path/to/openroad
python sta_exception.py capture \
  .local/exception-native/shift-window-baseline \
  .local/exception-native/shift-window-baseline/context.json \
  --output .local/exception-native/shift-window-baseline/recaptured.json
python sta_exception.py review \
  .local/exception-native/shift-window-baseline \
  .local/exception-native/shift-window-baseline/contract.json \
  .local/exception-native/shift-window-baseline/recaptured.json \
  --json-out .local/exception-native/shift-window-baseline/new-review.json \
  --markdown-out .local/exception-native/shift-window-baseline/new-review.md
```

The baseline review returns **0**, `BOUNDED_REACH_ACCOUNTED`. Now review the selector expansion:

```sh
python sta_exception.py review \
  .local/exception-native/shift-window-expanded \
  .local/exception-native/shift-window-expanded/contract.json \
  .local/exception-native/shift-window-expanded/evidence.json \
  --json-out .local/exception-native/shift-window-expanded/new-review.json \
  --markdown-out .local/exception-native/shift-window-expanded/new-review.md
```

This returns **1**, `REACH_REVIEW_REQUIRED`: `capture*` also masks a new functional capture pair. The native command can complete successfully while the exception's applicability needs review.

If you already have an intact archive from this exact producer, start at `capture`. It reads saved artifacts; it never executes archived Tcl. All report destinations must be new files. The recipe creates owned demonstration requirements and approval references; they are not an organization's real approval records.

## What the helpers do

| Helper | Responsibility |
|---|---|
| `examples/run_native.py` | Build the owned flat design, write original requirements/context, run the pinned native cases and retain sources, invocations and artifacts. |
| `sta_exception.py capture` | Check the original context, pinned producer, completion boundary and artifact bytes; preserve native selector, application, clock and path observations. |
| `sta_exception.py review` | Re-read the native evidence and compare masked pairs, roles, clock associations and binary mode premises with the independent contract. |
| `sta_exception.py drift` | Compare two reviews through the parent waiver records; use explicit reviewed correspondence when identities change. |

The gap is between an exception's syntactic validity and the continuing validity of its meaning. A stable pair count can hide a retargeted endpoint; a selector rename can preserve meaning; a mode change can invalidate the original premise.

## Prepare the engineering inputs

Use [FORMAT.md](FORMAT.md) for exact schemas and the generated example records as a worked reference.

| Input | What to establish |
|---|---|
| Native run directory and `context.json` | Actual design/configuration/mode, explicit clocks, native cell selectors, case ports and trace enable. Preserve the original source and command. |
| `contract.json` / `expected` | Original run identity, source hashes and command binding. |
| Exception rationale | Exception ID, rationale revision/reference, approval reference, permitted source/destination role pairs and binary native case premises. |
| Endpoint intent | Actual endpoint names, whether timing is required, expected clocks, source/destination roles and a source reference per observed pair. |
| `intent_basis_ref` / `owner_ref` | The requirement source and person/team responsible for the review. |
| Optional identity map | Reviewed one-to-one old/current endpoint correspondence with its evidence reference. |

An absent requirement is unknown, not permission to mask a path. Every observed before-pair remains visible even if independent intent is missing. Do not change the contract merely to agree with a native result: the original digest and requirement source must remain reviewable.

## Revalidate after an ECO or rename

Compare archived baseline and current runs:

```sh
python sta_exception.py drift \
  --baseline-run .local/exception-native/shift-window-baseline \
  --baseline-contract .local/exception-native/shift-window-baseline/contract.json \
  --baseline-evidence .local/exception-native/shift-window-baseline/evidence.json \
  --current-run .local/exception-native/shift-window-renamed \
  --current-contract .local/exception-native/shift-window-renamed/contract.json \
  --current-evidence .local/exception-native/shift-window-renamed/evidence.json \
  --identity-map .local/exception-native/shift-window-renamed/identity-map.json \
  --json-out .local/exception-native/rename-drift-new.json \
  --markdown-out .local/exception-native/rename-drift-new.md
```

Supply the map only after reviewing the actual correspondence. A map cannot erase changed timing meaning, roles or mode premises. The example also includes same-count retargeting, wrong-mode and missing-history controls.

In an organization, insert this review after the native constraint check and before accepting an exception carry-forward. Retain the original SDC/application history, before/after endpoint population, source intent, findings, gaps and owner disposition together. Re-run it when selectors, RTL identities, case analysis, clocks, mode requirements or rationale revisions change.

## Read the result

| Exit | Meaning | Next action |
|---|---|---|
| 0 | Bounded reach accounted or unchanged within declared scope | Review that scope and the source rationale before accepting the handoff. |
| 1 | Review required | Inspect newly masked, retargeted or premise-incompatible pairs and obtain a disposition. |
| 2 | Incomplete or quarantined evidence | Recover missing history, source identity, mode or intent; keep unresolved pairs open. |
| 3 | Invalid input or I/O failure | Repair records or paths and retry without replacing original evidence. |

Read both findings and gaps: a known required pair may be masked even when other evidence is incomplete. `BOUNDED_REACH_ACCOUNTED` is a bounded comparison result, not timing/CDC signoff or proof of exception safety.

## Native support and adoption boundary

The owned loader starts a fresh flat `top` with explicit clocks and binary/null case ports. It applies exactly one plain `set_false_path -setup` between native cell selectors. It does not execute imported SDC or combine through/reset/edge-specific and other exception families.

The collector supports simple flat names, `*`/`?` cell patterns and 1–64 selected instance pairs. It queries maximum-setup representatives per native path group before and after application and retains all returned records. The population is endpoint pairs, not every structural path or rise/fall alternative.

Selected scalar registers must have one native clock pin, data pin and output pin, one active clock association and an independent intent entry. Multiple clock associations, unknown modes, partial intent or missing application history remain unresolved. The journal distinguishes selector queries from actual exception applications and preserves resolved values before native handles can be reused.

For another STA tool, use its native exports and a separately checked completeness/mapping basis through the workflow. The bundled parser accepts its pinned producer only. Hold and multicycle reach, mixed-exception precedence and hierarchical propagation need another qualified method. Matching hashes bind bytes; they do not authenticate an approval or reconstruct missing history.

An agent can reason beyond the bundled reader using your established tools. Preserve the helper result and label any separate analysis with its evidence and support limits. Optional [context sources](../../../../CONTEXT_PORT.md), including DVIT, can add scoped intent, questions and evidence; standalone use stays complete without that connection and never installs DVIT automatically.

## Tests and handoff

```sh
python -m unittest discover -s tests -v
```

For native-corpus tests, set `OPENTOOLS_STA_EXCEPTION_EXAMPLES` to an intact generated archive before running the same command. Without it, input tests run and that class is skipped.

Hand off the report, original native archive, contract/rationale references, any reviewed map and the unresolved-item owner. Keep the native timing result, applicability review and engineering approval distinct.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
