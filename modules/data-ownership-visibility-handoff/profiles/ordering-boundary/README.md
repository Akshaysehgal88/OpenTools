# Ordering boundary review

Use this activity when reviewing a claim such as “once the consumer sees the
publication flag, it must see the preceding payload.” It ties that claim to the
**actual producer program, access domains, control placement and observation
boundary**.

This fits in hardware/firmware integration and publication-protocol review,
especially after changing RAM/MMIO paths, attributes, compiler/firmware sequencing
or ordering controls. Platform, firmware, architecture and DV owners can use it
alongside the parent [visibility/ownership activity](../../README.md).

It supplements your ISA/platform memory-model tools and native tests. It replaces
manual reconciliation of the selected claim with program/path/model evidence.
The supplied helper reviews one owned implementation family, not arbitrary
processor memory ordering. Coherence, cache maintenance, ordering and device
completion remain separate premises.

## First use

Python 3.10+ and the standard library suffice. Run from
`modules/data-ownership-visibility-handoff/profiles/ordering-boundary`:

```sh
python examples/create_example.py .local/ordering-ww --case mmio-ww
python ordering_review.py .local/ordering-ww/contract.json .local/ordering-ww/evidence.json .local/ordering-ww/claim.json --output .local/ordering-ww/review.json
```

Expected exit: **1**, `review_required`. In the owned buffered path, W→W covers
a normal-memory flag, but the selected publication uses an **O** output domain.
The control does not cover that boundary; a stale flag-1/payload-0 outcome is
permitted. Inspect `control_covers_boundary`, `model_permits_stale`,
`model_witness` and actual `observations` in the JSON.

Compare the domain-specific control:

```sh
python examples/create_example.py .local/ordering-wo --case mmio-wo
python ordering_review.py .local/ordering-wo/contract.json .local/ordering-wo/evidence.json .local/ordering-wo/claim.json --output .local/ordering-wo/review.json
```

Expected exit: **0**, `within_selected_owned_model`. This owned W→O control
gates publication until payload commit. It is not a universal MMIO fence recipe.

The `ram-selected-good` case has a favorable selected observation while its
complete model still permits a stale outcome. Other controls cover no ordering,
full masks, wrong predecessor and controls placed before payload or after
publication. Choose new example directories and report files; the generator also
writes its own `report.json` and `enumeration.json`.

## Helper features and records

`ordering_review.py CONTRACT EVIDENCE CLAIM` checks the selected binding,
program order, domains and attributes, validates the owned three-event enumeration,
and keeps permitted outcomes separate from observed executions. `--output` saves
JSON to a new file; omit it to print JSON. It launches no simulator.

[FORMAT.md](FORMAT.md) defines the exact schemas:

| Input | What to source independently |
|---|---|
| Contract | Model/source revision, producer and observer contracts, ordered program, payload/publication attributes and visibility/instruction scope. |
| Evidence | Matching model result and legal-order witnesses, plus original observations with their method, model/program identity and actual read validity. |
| Claim | Intended property and strength, original payload/publication/control events, required domains and path/attribute identities. |

The qualified program issues payload value 1 through W, optionally applies a
control, then publishes value 1 through W or O. Both values start at 0. A control
requires the matching predecessor/successor domains **and** placement between
payload and publication. The owned ordered observer polls then conditionally
reads payload without speculation.

The three model events are payload commit, publication commit and observe.
A complete result must enumerate every legal order. A partial stale witness can
show that a stale outcome is permitted; missing orders cannot show it forbidden.
The helper validates this finite graph and supplied outcomes. A final memory value
never replaces an earlier consumer response.

`payload: null` when flag is 0 means no payload read occurred. With flag 1,
a null payload is an unknown response. Blocked propagation attempts can retain
`all_steps_enabled: false`; they are partial schedules, not automatic ordering
violations or liveness proof.

Scope, program digest, model revision and exact payload/publication attributes
bind the result. RAM evidence cannot acquire MMIO applicability because values
happen to match. Hashes bind content, not the truth of the source interpretation.

## Integrate into a platform review

1. State the original consumer guarantee and its strength: selected implementation,
   ISA-level or hardware-wide. Obtain the actual platform/model contract.
2. Inspect producer sequencing, compiler/firmware evidence and observer behavior.
   Establish actual memory/I/O classification, cacheability, shareability and
   mapping revision for both accesses.
3. Trace where the ordering mechanism acts. Check predecessor, successor and
   placement separately from cache cleaning and device-completion semantics.
4. Retain native observations with actual read responses. Obtain model-allowed
   outcomes from the existing qualified method for the claimed domain.
5. Review permitted versus observed outcomes separately. A favorable run cannot
   exclude a legal stale model witness.
6. Correct the original sequence, domain mapping or sourced claim, then rerun the
   relevant native/model review. Keep the claim, source basis, observations,
   witnesses and receiving owner's decision together.

The [REVIEW.md](REVIEW.md) record supports this correction/handoff/revalidation
cycle even when native evidence is outside the bundled reader.

## AI-led adoption

Give a file/tool-enabled assistant [WORKFLOW.md](WORKFLOW.md), actual source,
platform/ISA contract and observation evidence:

> Check this publication guarantee at the intended RAM or I/O boundary. Trace
> actual access classification, producer/observer ordering and control placement.
> Separate model permission from observed executions, and ordering from coherence,
> maintenance and completion. Ask for missing platform or model evidence before
> recommending a fence sequence.

Install the parent module using [ONBOARDING.md](../../../../ONBOARDING.md), then
select `data-ownership-visibility-handoff` / `ordering-boundary`. Your existing
AI host can use qualified company methods beyond the supplied finite helper.
Optional [context sources](../../../../CONTEXT_PORT.md), including DVIT, can
relate the selected claim to path, ordering and completion intent. They are not
required.

## Native controls, results and limits

The [native guide](examples/NATIVE.md) uses Linux, Verilator 5.020 and a C++/Make
toolchain. It actually gates publication through two owned propagation queues,
trying ten configurations and 55 schedules. An independent enumerator checks
legal orders and every observed state/action. It installs no tools.

| Exit | Meaning |
|---:|---|
| 0 | Within the selected owned model and supplied claim. |
| 1 | Known boundary, permitted-outcome or observation findings; accompanying gaps remain. |
| 2 | Incomplete or unqualified scope/model/claim strength. |
| 3 | Invalid input or I/O. |

Argument errors use exit 2. Only `publication_implies_payload` at
`selected_model` strength is qualified. Atomicity, ISA and hardware-wide claims
remain gaps. The single-bit sentinel model has no cache protocol, architectural
access widths, speculation, compiler/ISA execution, mixed-width behavior, atomics
or translation maintenance. It is neither RVWMO execution nor a processor test.

```sh
python -m unittest discover -s tests -v
```

The native guide explains opt-in tool environment variables. Broader models,
commercial tools and production platform claims require their own qualification.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
