# Property activation obligations

Use this module before relying on a property's passing run, and after changing
bindings, clocks, disable guards, runtime enables or operating modes. It checks
whether the **intended property instance evaluates the independently required
events**.

This fits in assertion integration, property enablement review and formal/DV
evidence handoff. Property, design and DV owners can use it alongside native
assertion/cover reports. A property can hit in normal mode while remaining disabled
in the risk interval it was intended to protect.

The activity supplements native SVA diagnostics and property review. It replaces
manual reconciliation of selected event obligations with actual binding/sample/
enable evidence. It does not generate assertions or establish their adequacy.

## First use

Saved-data review needs Python 3.10+ and the standard library. From
`modules/property-activation-obligations`, use a complete retained collection at
`.local/activation-native`, or collect one on Linux with existing
**Verilator 5.020**, its runtime and a C++ build toolchain:

```sh
python examples/run_native.py .local/activation-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Replace the executable/runtime paths. The recipe installs nothing. Eight builds
serve twelve bounded runs in drain-before-power-off and cancellation-before-flush
contexts, retaining actual SVA binds, XML, runtime enables, cover counters and
assertion actions.

Reimport and review the clean active control:

```sh
python activation_check.py capture .local/activation-native/power-clean run .local/activation-native/power-clean/capture-context.json --output .local/activation-native/power-clean/recaptured.json
python activation_check.py review .local/activation-native/power-clean/obligations.json .local/activation-native/power-clean/bindings.json .local/activation-native/power-clean/recaptured.json --json-out .local/activation-native/power-clean/new-review.json --markdown-out .local/activation-native/power-clean/new-review.md
```

Expected review exit: **0**, `within_observed_activation_contract`. Inspect the
Markdown for per-obligation tick, target, mode, activation and observed condition.

Compare the disabled risk interval:

```sh
python activation_check.py review .local/activation-native/power-disabled-fault/obligations.json .local/activation-native/power-disabled-fault/bindings.json .local/activation-native/power-disabled-fault/evidence.json --json-out .local/activation-native/power-disabled-fault/new-review.json --markdown-out .local/activation-native/power-disabled-fault/new-review.md
```

Expected exit: **1**, `review_required`. The normal event at tick 5 is checked,
but the required risk event at tick 9 is disabled and its condition is false.
A favorable native no-failure outcome cannot supply the missing activation.
The corrected `power-active-fault` checker exposes the condition failure;
activation and functional condition evidence remain separate in the report.

Outputs must be new. Store each captured snapshot beside its retained `run/`
directory: review resolves original paths from the evidence file's parent.
Capture exit 0 means valid parsing, including native assertion failure.

## Helper and evidence features

| Operation | Responsibility |
|---|---|
| `activation_check.py capture ROOT WORKDIR CONTEXT --output RECEIPT` | Reads original native hierarchy/ports, predicates, drive/sample rows, runtime assertion enables, user covers and actions. It never executes imported commands or binaries. |
| `activation_check.py review OBLIGATIONS BINDINGS RECEIPT` | Rechecks source/run identity, actual target/clock/edge, required mode/event, guard and runtime enable against the independent roster. |
| `--json-out` / `--markdown-out` | Saves structured/readable handoff reports; JSON is also printed. |

[FORMAT.md](FORMAT.md) and
[capture-context.template.json](capture-context.template.json) define the records.

The obligation roster independently states scope, claim/owner/basis, completeness,
property reference and one to eight required target/clock/edge/mode/tick events.
Unknown requirements remain null. Do not select only observed passing events.

The binding map names the expected original run/source hashes and each required
checker/property/activation cover. Mode-specific `c_active_normal` and
`c_active_risk` are distinct; `c_active_any` cannot stand in for either.
Required binding entries cannot be omitted.

Native evidence retains actual observer/checker hierarchy and target, resolved
clock/reset/pin mapping, source locations, cover counters, drive/sample rows,
runtime `assertOn()` state and assertion actions. Positive cover counts do not
automatically establish runtime assertion enable.

## Integrate into property review

1. Source the original property purpose and required risk events with the design/
   property owner. Keep the obligation population independent of the native covers.
2. Inspect the consumed bind/composition, target instance, clock, reset/extra-disable
   expression and runtime assertion settings.
3. Retain native build/XML/coverage, original executable/commands, sample/drive
   journal, assertion actions and completed window. Map observations explicitly.
4. Capture and review. Separate wrong/absent bind, wrong clock, disabled guard,
   runtime assertions off and actual condition failures.
5. Correct the original binding, guard, instrumentation or sourced requirement.
   Rerun and revalidate, preserving newly exposed functional failures.
6. Hand off original intent, roster/map, native evidence, reports and owner
   decisions. Repeat after relevant source, mode, clock or enable changes.

A shortened but agreeing roster/map still needs review against original intent.
Unselected events/native failures stay visible without automatically enlarging
the required population. Hashes establish byte correspondence, not source
authority, completeness or approval.

## AI-first adoption

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), the original property
requirement, bind sources and native artifacts:

> Establish where this property must evaluate, particularly in the risk mode.
> Trace the actual target, clock, guard and runtime assertion enable. Compare
> required events with actual samples/actions and keep condition failures separate.
> Ask for missing source, mode or observation-window evidence.

Use [ONBOARDING.md](../../ONBOARDING.md), module
`property-activation-obligations` / activity `default`. Existing AI/native methods
remain usable beyond the helper. Optional DVIT intent/dependency context can
connect property enablement to product/transition obligations; local use requires none.
[REVIEW.md](REVIEW.md) captures the receiving-owner handoff.

## Outcome and native qualification

| Review exit | Meaning |
|---:|---|
| 0 | Within the selected observed activation contract. |
| 1 | Known activation/binding or required-condition finding; gaps remain. |
| 2 | Incomplete or quarantined evidence. |
| 3 | Invalid record/artifact or I/O. |

Argument errors use exit 2. The method remains `bounded_simulation`, never
unbounded proof.

The native reader qualifies one target level under `top`, an independent observer,
zero/one checker and stable-before-edge Boolean same-cycle checking:
`event_req |-> condition_ok` disabled by `reset || extra_disable`. XML predicates
and five covers are checked over the finite role combinations; clocks resolve
to observed always-on/functional inputs. GCC 13.3 was used for native qualification.

Arbitrary SVA, asynchronous reset/sampling, physical clocks, broader protocol/
power behavior, oracle sufficiency and signoff need separately qualified methods.
Other tool versions/formats do not become supported by renaming fields.

Set `OPENTOOLS_ACTIVATION_EXAMPLE` to the retained collection and run:

```sh
python -m unittest discover -s tests -v
```

Native artifact tests work on Windows/Linux. Other core tests use labeled
synthetic records; native tests otherwise skip.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
