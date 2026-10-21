# CDC/RDC premise applicability

Use this activity when the data-stability or reset-readiness premise behind an
existing crossing waiver may have changed. It keeps **the structural finding
separate from observed premise evidence**.

This fits in CDC/RDC waiver maintenance after configuration, wake/mode, source-
update or reset-sequence changes. Crossing, reset and DV owners can use it alongside
their native structural analysis. Equal destination samples do not establish
continuous source stability; deasserted reset does not establish initialized data.

The activity supplements native CDC/RDC and the parent
[waiver comparator](../../README.md). It replaces manual selected-premise
reconciliation, not crossing discovery, exception approval or physical CDC/RDC
signoff.

## First use

Python 3.10+ and the standard library suffice. From
`modules/waiver-revalidation/profiles/crossing-premises`:

```sh
python examples/create_example.py .local/crossing-live --case live-update
python crossing_capture.py .local/crossing-live/population.json .local/crossing-live/journal.json --out .local/crossing-live/captured.json
python ../../waiver_revalidate.py compare .local/crossing-live/baseline.json .local/crossing-live/captured.json --policy .local/crossing-live/policy.json --json-out .local/crossing-live/review.json --markdown-out .local/crossing-live/review.md
```

Expected capture and comparison exits: **1**. A source configuration change is
observed during the required stability window, invalidating the recorded premise.
The original structural population is unchanged and remains visible.

Compare the stable control:

```sh
python examples/create_example.py .local/crossing-stable --case stable
python crossing_capture.py .local/crossing-stable/population.json .local/crossing-stable/journal.json --out .local/crossing-stable/captured.json
python ../../waiver_revalidate.py compare .local/crossing-stable/baseline.json .local/crossing-stable/captured.json --policy .local/crossing-stable/policy.json --json-out .local/crossing-stable/review.json --markdown-out .local/crossing-stable/review.md
```

Expected exits: **0** within the declared journal/premises. `ordered-reset` is a
readiness control; `early-reset` contradicts readiness while data stays stable.
Directories and captured/report paths must be new. The generator's structural
population is explicitly **synthetic**, not a CDC tool result.

## Helper and evidence features

`crossing_capture.py POPULATION JOURNAL --out SNAPSHOT` preserves the original
waiver/native metadata and adds two observed flat configuration premises:

- `crossing:<waiver_id>:<finding_id>:stable_in_window`
- `crossing:<waiver_id>:<finding_id>:source_ready_before_destination`

The existing `waiver_revalidate.py compare` reviews those sourced values against
the existing premise policy. Capture also retains role mapping, input digests,
contrary witnesses and gaps. It refuses to overwrite existing premise keys.

[FORMAT.md](FORMAT.md) defines the inputs:

| Input | Required source |
|---|---|
| Population | Existing normalized native waiver snapshot and selected finding, or explicitly synthetic fixture. Preserve original tool/version/ruleset and finding census. |
| Crossing map | Exact source/destination, width 1–64, clocks/reset domains and source evidence for their roles. |
| Journal | Exact population digest/identity, selected waiver/finding, closed settled-event window and actual source/update/readiness/destination observations. |
| Parent policy | Independently sourced expected premise values using the generated exact keys. |

Record inactive prefix/suffix, window entry/exit, all relevant source updates and
actual destination sampling. A source change while either adjacent window state
is active is contrary evidence; close the window before a later permitted update.
Unknown boundaries do not establish where a change occurred.

Readiness means source reset inactive and source ready whenever the selected
destination is active. Source review must establish what ready means. This is
the supplied waiver premise, not a universal protocol rule.

Known contrary values remain false even with incomplete coverage. Otherwise
gaps leave values null and mark collection/selected waiver incomplete, preventing
an unchanged result. This does not claim the structural population changed.

## Integrate into crossing-waiver review

1. Obtain the original finding/exception, rationale, exact endpoint/clock/reset
   roles and current mode from the native analysis and owner.
2. Source when stability is required, who may update the source and what prevents
   updates through wake/debug/test or mode changes.
3. Inspect reset release through actual source readiness and destination activity.
   Include partial resets and alternate paths.
4. Retain complete relevant source events, not only destination samples. Normalize
   and bind the journal to the original population; capture and compare.
5. Review changed premises with the existing waiver owner. A contrary premise is
   not itself metastability, a functional defect or permission to delete an exception.
6. Correct the original setup/rationale or collect missing native evidence, then
   revalidate. Hand off structural finding, old/current premise, affected mode,
   witnesses, unknowns and owner action together.

Challenge favorable evidence with wrong roles, narrowed windows, forced-ready
values or updates returning to the same value between destination samples.
Completeness flags are declarations, not continuous-waveform proof.

## AI-first adoption and native controls

Give a file/tool-enabled assistant [GUIDE.md](GUIDE.md), original waiver rationale,
native report, source/reset sequence and event evidence:

> Review this selected crossing's original stability/readiness premises. Trace
> actual source updates and destination activity across the full relevant window,
> including reset and mode transitions. Preserve structural findings and unknown
> coverage; ask for missing role or readiness evidence before interpreting applicability.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module `waiver-revalidation` /
activity `crossing-premises`. Existing AI/native methods suffice. Optional
[context sources](../../../../CONTEXT_PORT.md), including DVIT, can supply scoped
premise/owner relationships; independent operation requires none.

The native recipe in `GUIDE.md` uses Linux, Verilator 5.020 and C++/Make.
An independent event schedule checks 32 actual functional rows. The structural
population remains synthetic; Verilator supplies no CDC/RDC findings. The direct
bus is an observation fixture, not a synchronizer reference.

## Outcomes and tests

| Capture exit | Meaning |
|---:|---|
| 0 | Observed premises hold within the complete declared journal. |
| 1 | Known contrary stability/readiness observation, retaining gaps. |
| 2 | Incomplete without a known contrary witness. |
| 3 | Invalid binding/input or I/O. |

The parent comparator has its own status precedence: incomplete evidence returns
2 while `review_required` retains known issues. Read both capture witnesses and
the final audit. Argument errors use exit 2.

No parser for arbitrary proprietary structural reports/event logs is supplied.
Glitches, X behavior, metastability, pulse width, synchronizers, analog reset and
physical RDC need their qualified native methods.

```sh
python -m unittest discover -s tests -v
```

The guide explains opt-in native tool variables. No output approves or revokes a
waiver.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
