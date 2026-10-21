# Timing endpoint review

Use this module before accepting timing completeness or carrying endpoint
exemptions forward. It reconciles **the complete native endpoint population
with current timing intent**, including endpoints for which path queries return
nothing.

This fits in STA setup/completeness review after clock, I/O constraint, mode,
role or constant-premise changes. STA, integration and endpoint owners can use
it alongside native `check_setup` and path reports.
A zero-path output or unclocked source must not disappear from the reviewed
population; `INF` unconstrained slack is not a numeric pass.

The activity supplements native diagnostics and exemption review. It replaces
manual census/intent reconciliation. It does not infer timing intent, approve
exemptions or establish complete timing signoff.

## First use

Saved-data review needs Python 3.10+ and the standard library. From
`modules/timing-endpoint-review`, use a complete retained collection at
`.local/endpoint-native`, or generate one on Linux with existing
**OpenROAD v2.0-17598-ga008522d8** and its runtime:

```sh
python examples/run_native.py .local/endpoint-native --openroad /path/to/openroad
```

Replace the executable path. The recipe installs nothing and needs a new output.
Block-interface and macro-interface contexts vary clock/reset polarity and
interface requirements while exercising the same review stage.

Capture and review the missing functional-output constraint:

```sh
python endpoint_review.py capture .local/endpoint-native/block-interface-missing-output .local/endpoint-native/block-interface-missing-output/context.json --output .local/endpoint-native/block-interface-missing-output/recaptured.json
python endpoint_review.py review .local/endpoint-native/block-interface-missing-output .local/endpoint-native/block-interface-missing-output/contract.json .local/endpoint-native/block-interface-missing-output/recaptured.json --json-out .local/endpoint-native/block-interface-missing-output/new-review.json --markdown-out .local/endpoint-native/block-interface-missing-output/new-review.md
```

Expected review exit: **1**, `ENDPOINT_REVIEW_REQUIRED`. The functional output
lacks its required external timing. Diagnostic and constant endpoints remain in
the denominator with their own current exemption rationale.

Compare the complete intent/control:

```sh
python endpoint_review.py review .local/endpoint-native/block-interface-complete .local/endpoint-native/block-interface-complete/contract.json .local/endpoint-native/block-interface-complete/evidence.json --json-out .local/endpoint-native/block-interface-complete/new-review.json --markdown-out .local/endpoint-native/block-interface-complete/new-review.md
```

Expected exit: **0**, `BOUNDED_ENDPOINT_INTENT_ACCOUNTED`. This need not mean
zero unconstrained endpoints: two explicit exemptions are accounted within the
selected contract. Open Markdown for disposition and JSON for the native census,
independent roster, path classes, admitted exemptions, findings/gaps/quarantine.

Both report flags are required. Outputs must be distinct new paths. Capture exit
0 means valid intake; a successful native diagnostic command alone does not
establish a clean report.

## Helpers and native export

| Helper | Contribution |
|---|---|
| `export_endpoints.tcl` | Retains actual native unconstrained report, output/data endpoint census, clock associations, case/forced/simulated constants and selected PathEnd classes. |
| `endpoint_review.py capture RUN_DIR CONTEXT --output FILE` | Validates original producer/source/setup/command/artifacts and captures retained facts without executing Tcl. |
| `endpoint_review.py review RUN_DIR CONTRACT EVIDENCE --json-out JSON --markdown-out MD` | Revalidates originals, reconciles independent endpoint roles/requirements and checks current exemption premises. |

For a qualified loaded setup, from a fresh native artifact directory:

```tcl
source export_endpoints.tcl
opentools_export_endpoints run_ref {reset_n power_ok run_enable}
```

Replace run/case-port identities. It writes `native.jsonl`, `unconstrained.txt`,
`native.odb` and `consumed.sdc` in the native working directory. The Python
batch reader additionally requires the original context/contract, sources,
invocation, execution and completion identities in [FORMAT.md](FORMAT.md).
A generic export alone does not qualify another loader.

## Supply current intent and exemptions

The independent contract binds original run/scope/design/configuration/mode/power,
source/command identities, requirements/owner, clock/cases and input-delay basis.
Its complete endpoint roster states output/data kind, current role, whether
timing is required, source/target clock, required output delay and any constant
premise.

Exemptions separately name endpoint, permitted current role, mode/power scope,
reason/source/approval basis and optional constant value. A non-timed label is
not an exemption. A changed role or contrary native value remains a finding;
unknown applicability stays open.

Native report membership and path-query results are independent. A reported
unconstrained endpoint can have no PathEnd. The unconstrained-inclusive query
also returns constrained paths, so query flags/counts cannot substitute for
actual native classification.

Output-delay margins retain their I/O meaning; register setup margins cannot
be reinterpreted as output-delay requirements. Input-delay assumptions are bound
consumed setup, not a generic posthoc getter. Time uses the pinned native ns UI;
formatted precision is not an engineering tolerance.

## Integrate into STA completeness review

1. Establish original endpoint roles and timing/exemption intent with receiving
   owners before filtering reports.
2. Retain native unconstrained diagnostics and the full output/register-data
   census, including constants and zero-path objects.
3. Source clock/case/I/O assumptions and explicit current exemption premises.
   Keep simulated constants separate from forced/case assumptions.
4. Capture and review all selected endpoints. Route missing external timing,
   unclocked sources, changed roles and stale premises to their owners.
5. Correct original setup or sourced requirement, rerun native checks and
   revalidate. Do not remove an endpoint from the roster to clear a finding.
6. Hand off original intent, native artifacts, report and receiving decision.
   Repeat after endpoint, role, mode, clock or constraint changes.

## AI-first adoption and outcome

Give a file/tool-enabled assistant [SKILL.md](SKILL.md),
[WORKFLOW.md](WORKFLOW.md), original timing intent and native reports:

> Reconcile every selected native endpoint with current timing intent. Preserve
> zero-path and constant objects, distinguish native path classes, and inspect
> the source/authority of each exemption in the current mode. Ask for missing
> clock/I/O or premise evidence instead of filtering it away.

Use [ONBOARDING.md](../../ONBOARDING.md), module `timing-endpoint-review` /
activity `default`. Existing AI/STA methods suffice. Optional DVIT context can
connect endpoint roles/exemptions to original interface requirements; local use
requires no connection.

| Review exit | Meaning |
|---:|---|
| 0 | Bounded endpoint intent accounted. |
| 1 | Known timing/role/exemption finding; gaps remain. |
| 2 | Incomplete or quarantined evidence. |
| 3 | Invalid/changed native package or I/O. |

Argument errors use exit 2. Source/reference hashes do not authenticate approval.

Qualification covers a fresh flat mapped scalar top, one clock, explicit binary/
unknown cases and I/O inputs, no imported SDC/exceptions/parasitics. Physical tie
integrity, all-mode constancy, reset safety, hierarchy, incremental history,
hold, CDC/RDC and complete timing closure need separately qualified methods.

Set `OPENTOOLS_STA_ENDPOINT_NATIVE` to the retained collection and run:

```sh
python -m unittest discover -s tests -v
```

Saved-data review works on Windows/Linux. Without an archive, input tests run and
native-corpus tests skip.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
