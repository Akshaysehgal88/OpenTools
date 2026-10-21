# Bring-up observation comparison

Use this activity before comparing a retained diagnostic read with a pre-silicon
expectation. It checks **device/image/reset conditions, capture provenance and
source-read time**, separately from the returned value.

This fits in bring-up/validation evidence review and pre-silicon-to-lab handoff.
Firmware, validation, lab and model owners can use it alongside their existing
instruments and logging. A post-reset zero can be inconclusive about an earlier
fault; a correct retained value outside the required window cannot answer that
comparison.

The workflow supplements native/lab analysis and the
[diagnostic receipt activity](../diagnostic-validity/README.md). It replaces manual
condition/epoch/time reconciliation for a selected observation. The bundled
reader qualifies owned device **emulation**, not real silicon or instruments.

## First use

Saved-data review needs Python 3.10+ and the standard library. Run from
`modules/side-effect-access-order/profiles/bringup-observation`. Use a complete
retained collection at `.local/bringup-native`, or generate one on Linux with
existing **Ubuntu GCC 13.3.0**:

```sh
python examples/run_native.py .local/bringup-native --cxx /usr/bin/g++
```

Replace the compiler path if needed. The recipe installs nothing and needs a new
output. Eighteen bounded command-image runs cover cold-start and wake-entry
contexts with sticky status, POR/warm recovery, read effects and host capture.

Review a retained early response:

```sh
python bringup_review.py review .local/bringup-native .local/bringup-native/cold-start-early/capture-question.json --json-out .local/bringup-native/early-review.json --markdown-out .local/bringup-native/early-review.md
python bringup_review.py capture .local/bringup-native cold-start-early --output .local/bringup-native/recaptured-early.json
```

Expected review exit: **0**, `SUPPORTED_WITHIN_EMULATION`. The selected response
has applicable conditions, diagnostic provenance and source-read interval.
Capture exit 0 means valid intake, not a hardware-test pass.

Compare a later read after clearing recovery:

```sh
python bringup_review.py review .local/bringup-native .local/bringup-native/cold-start-late/capture-question.json --json-out .local/bringup-native/late-review.json --markdown-out .local/bringup-native/late-review.md
```

Expected exit: **2**, `INCONCLUSIVE`. Its later zero cannot establish the
earlier fault question. Wrong entry/image/revision/clock and unknown time-correlation
controls preserve different applicability/uncertainty causes.

Open Markdown for the bounded comparison and JSON for raw selected observation,
diagnostic answer, conditions, relative time interval, original captured question,
findings and gaps. Both report flags are required, with distinct new paths.
Retain the entire original run directory; intake executes no saved source/binary.

## Helper and independent request

| Operation | Contribution |
|---|---|
| `bringup_review.py capture ROOT RUN_REF --output FILE` | Validates original owned producer, command/image/context/execution and native diagnostic evidence. |
| `bringup_review.py review ROOT REQUEST --json-out JSON --markdown-out MD` | Composes the existing diagnostic epoch/receipt review with independent conditions and reset-relative source-time correspondence. |

[FORMAT.md](FORMAT.md) and the [owned fixture](examples/fixture.py) describe
the complete `opentools.bringup-request.v1`:

- Original claim/scope/owner, requirements, pre-silicon expectation and clock-mapping
  references.
- Expected original run, consumed source/context/invocation identities, device
  revision/fuses, image, board power/clock and entry/recovery/reset/read effects.
- Selected scalar cause, target epoch, required source prefix and actual read.
- Required reset-relative observation window, timestamp uncertainty and expected
  `present` or `absent_in_observed_prefix` answer.

Source the expectation and conditions independently of available read values.
Stronger unsupported fields remain unknown rather than being dropped.

The qualified package retains device source/configuration, bounded command image,
original executable, context/invocation, captured question, execution/compiler
and native stdout/stderr. The execution identity also binds the diagnostic engine
revision. Fault injection/reference knowledge remains separate from the selected
consumer read.

## Time and recovery interpretation

The diagnostic journal starts at actual post-entry state, then handles one later
recovery class. Ordered read/save/recovery receipts establish the source response's
epoch and origin. A later record load does not become the source-read time.

The supplied profile supports one monotonic counter and two affine clock anchors.
Time relative to the observed entry reset is compared in **ns**. Per-timestamp
uncertainty contributes twice to the relative interval; the entire interval must
fit the requested window. Missing mapping/uncertainty, partial overlap or late
capture is inconclusive.

A new sourced question may reuse retained facts while preserving both original
and new question identities. Do not edit the original captured question to make
an observation fit. Modeled timestamps and device identities are emulated
observations, not authenticated calibration.

## Integrate into a bring-up workflow

1. State the original pre-silicon expectation and receiving comparison question.
   Identify device/image/configuration and the reset-relative observation window.
2. Establish actual read/reset effects, entry/recovery history, logging/capture
   retention and consumer-visible source response.
3. Retain original native/instrument evidence and clock/time correspondence with
   uncertainty. Keep acquisition time separate from later report loading.
4. Review conditions, diagnostic provenance, timing and value in that order.
   Use this reader only for its owned format, or validate an exporter against
   your actual lab/instrument method.
5. Correct source/capture/time setup or collect missing evidence using the existing
   workflow. Do not call an unqualified zero a negative test.
6. Hand off original question/expectation, artifacts, comparison, missing evidence
   and receiving decision. Revalidate after image, device, reset or timing changes.

## AI-first adoption and outcome

Give a file/tool-enabled assistant [WORKFLOW.md](WORKFLOW.md), original expectation,
actual device/image/reset evidence and capture/time records:

> Establish whether this selected observation can answer the pre-silicon question.
> Trace actual source read and saved receipt, device/image/reset conditions and
> reset-relative time uncertainty. Preserve raw values while separating
> inapplicability, contradiction and inconclusive evidence.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module `side-effect-access-order` /
activity `bringup-observation`. Existing AI/lab methods suffice. Optional DVIT
intent/dependency context can relate the expected behavior and capture conditions
to original product/validation intent; independent use requires none.

| Review exit | Meaning |
|---:|---|
| 0 | Supported within the bounded owned emulation. |
| 1 | Inapplicable conditions/sources, contrary observation or diagnostic findings. |
| 2 | Inconclusive: missing premises, unusable or temporally incomparable evidence. |
| 3 | Invalid/changed native package or I/O. |

Argument errors use exit 2. Known differences retain gaps.

The native producer is a C++17 sampled, quiescent scalar device emulator interpreting
a command image, not firmware ISA execution. One cause, one post-entry recovery
class, host-retained capture and bounded counter define support. Real silicon/
instruments, calibration authority, physical reset/power, trace loss/wrap,
multi-clock synchronization, all-mode coverage and root cause need separately
qualified methods.

Set `OPENTOOLS_BRINGUP_NATIVE` to the retained collection and run:

```sh
python -m unittest discover -s tests -v
```

Native-corpus tests otherwise skip. Saved-data review needs no compiler or DVIT
connection.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
