# Diagnostic validity through recovery

Use this activity before drawing a fault conclusion from a status read or saved
capture taken around reset, destructive reads or loss of access. It asks **which
cause epoch the selected observation belongs to and what it can establish**.

This fits in crash/diagnostic capture, recovery review and firmware/DV handoff.
Register, firmware and validation owners can use it alongside existing logging
and native traces. A later zero cannot establish that the earlier fault never
occurred; a stale valid saved word is not automatically current-incident evidence.

The activity supplements the parent [access-effect review](../../README.md).
It replaces manual read/save/erasure provenance reconstruction for a selected
sticky cause. It does not bucket failures or infer silicon root cause.

## First use

Python 3.10+ and the standard library suffice. From
`modules/side-effect-access-order/profiles/diagnostic-validity`:

```sh
python examples/create_example.py .local/diagnostic-zero --case post-reset-zero
python diagnostic_review.py .local/diagnostic-zero/spec.json .local/diagnostic-zero/journal.json .local/diagnostic-zero/policy.json --output .local/diagnostic-zero/review.json
```

Expected exit: **1**, `review_required`. The selected later zero belongs to
status cleared by recovery and cannot support the requested pre-recovery absence.
Inspect raw selected value, source-read provenance, evidence answer, erasures,
findings and gaps in JSON.

Compare a captured pre-recovery response:

```sh
python examples/create_example.py .local/diagnostic-saved --case pre-reset-snapshot
python diagnostic_review.py .local/diagnostic-saved/spec.json .local/diagnostic-saved/journal.json .local/diagnostic-saved/policy.json --output .local/diagnostic-saved/review.json
```

Expected exit: **0**, `within_observed_evidence`. An actual earlier usable read
was saved with matching value/epoch and remains applicable to the selected cause.
The saved word comes from the response, not the already cleared live bank.

For an explicitly unresolved question:

```sh
python examples/create_example.py .local/diagnostic-unknown --case post-reset-undetermined
python diagnostic_review.py .local/diagnostic-unknown/spec.json .local/diagnostic-unknown/journal.json .local/diagnostic-unknown/policy.json --output .local/diagnostic-unknown/review.json
```

Expected exit: **2**. Uncertainty is retained without inventing a present/absent
conclusion. The `no-fault-control` supports absence only in its declared observed
clean prefix. Directories/reports must be new; the generator also writes
`report.json`.

## Helper and evidence records

`diagnostic_review.py SPEC JOURNAL POLICY` checks the selected read or capture,
accepted/quiescent access, read/reset effects, saved-read receipt and epoch/
coverage applicability. `--output` writes JSON to a new file; omit it to print
JSON. It executes no native command.

[FORMAT.md](FORMAT.md) defines:

| Input | Source and meaning |
|---|---|
| Spec | Original status identity/width, sticky-latch/read/reset effects and saved-record reset effect, with matching source revision. |
| Journal | Initial status/availability/record, ordered reads/saves/recovery/external-record events and declared access/erasure/capture and source-latching coverage. |
| Policy | Independent cause mask, target epoch, required prefix boundary, consumer/allowed capture actors, selected read and `present/absent/undetermined` claim. |

The selected cause mask has one bit within the 1–4096-bit status bank.
Unknown read/reset effects or state stay explicit. Source injection commands can
be retained as separate oracle evidence; they are not consumer observations.

An accepted clear-on-read response belongs to the preceding epoch, then status
enters a new clean epoch. A clearing recovery advances the status epoch; a
retaining recovery does not. A saved receipt must match a usable earlier read's
value/epoch and retain provenance. Initially valid or externally supplied records
do not gain invented capture history.

Hardware epoch tags can be unknown when complete ordered history derives the
basis. Conflicting known tags are rejected; unknown erasure effects or overflow
remain unqualified. Counters alone do not establish a real incident's identity.

## Integrate into capture/recovery review

1. Establish the original diagnostic question, cause and incident/prefix boundary
   before selecting a favorable read.
2. Inspect effective register/reset semantics, consumer access and capture-buffer
   retention with register/firmware owners.
3. Retain actual accepted responses and complete relevant read/save/clear/recovery
   history. An unavailable path's idle data is not a response.
4. Source the independent policy and bind the original spec/journal. Review
   returned bits separately from current-epoch applicability and negative coverage.
5. Correct the original capture sequence or sourced claim, recollect/revalidate
   and preserve any lost-evidence boundary.
6. Hand off original question, source effects, native history, report and owner
   decision. Repeat after reset, read effect, logging or capture-policy changes.

Negative support covers only the selected clean epoch's observed prefix through
its source read, with adequate source-latching/capture coverage and required
sequence boundary. It does not establish absence before/after that interval or
across other fault paths.

## AI-first adoption and native controls

Give a file/tool-enabled assistant [WORKFLOW.md](WORKFLOW.md), original question,
register/recovery source and selected native read/capture:

> Trace the selected observation to its actual response and cause epoch. Identify
> destructive reads, reset erasures, unavailable access and saved-capture provenance.
> Separate returned bits from incident applicability and bounded negative evidence.
> Ask for missing history rather than inferring absence from a later zero.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module `side-effect-access-order` /
activity `diagnostic-validity`. [REVIEW.md](REVIEW.md) records handoff actions.
Existing AI/native methods suffice. Optional DVIT context can connect scoped
recovery/capture requirements; independent operation requires none.

The [native controls](examples/NATIVE.md) use Linux, Verilator 5.020 and C++/Make.
Eleven controls/47 state-action observations are checked by an independent
cause-set/read-receipt model. Access-enable and synchronous recovery are logical
surrogates, not physical clock/power or reset-tree qualification.

## Outcomes and limits

| Exit | Meaning |
|---:|---|
| 0 | Within supplied observed evidence and claim. |
| 1 | Known provenance/epoch/effect or unsupported-conclusion finding. |
| 2 | Incomplete or explicitly undetermined evidence. |
| 3 | Invalid input or I/O. |

Argument errors use exit 2. Findings retain gaps. JSON distinguishes raw bits,
`selected_cause_bit_set`, `evidence_answer` and `negative_through_seq`.
A stale set bit need not establish current occurrence.

Concurrent/asynchronous faults, arbitrary capture engines, X/metastability,
physical retention, complete firmware logging and silicon diagnosis need their
own native methods and qualification.

```sh
python -m unittest discover -s tests -v
```

The native guide explains opt-in tool variables. Saved-data review needs no
simulator or SystemRDL package.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
