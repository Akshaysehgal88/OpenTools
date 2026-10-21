# Ordering boundary review

Associate one publication-ordering claim with its producer program, access domains,
ordering-control placement and selected outcomes. This profile extends
[data ownership and visibility handoff](../../README.md). Use the
[AI workflow](WORKFLOW.md) with the actual ISA/platform/model contract and native
evidence. Your existing AI host is sufficient; DVIT is optional.
The [review record](REVIEW.md) fits the team's existing claim/evidence review and
revalidation cycle, including native tools outside the bundled example.

The optional Python 3.10+ helper reviews one owned buffered-publication family.
It keeps model-allowed outcomes separate from observed executions and checks the
complete three-event enumeration before accepting an exclusion claim. A favorable
run does not prove an unobserved outcome forbidden. A RAM result does not transfer
to a different MMIO boundary.

Run from this profile directory:

```sh
python examples/create_example.py /tmp/ordering-review --case mmio-ww
python ordering_review.py /tmp/ordering-review/contract.json /tmp/ordering-review/evidence.json /tmp/ordering-review/claim.json
```

In the owned path, W→W orders the RAM flag but leaves the MMIO output unordered.
`mmio-wo` is its domain-specific control. Other examples cover no control, a full
mask, wrong predecessor, early/late placement and a favorable selected run.
See [native controls](examples/NATIVE.md) and [records](FORMAT.md).

Exit codes: 0 within the selected owned model, 1 findings, 2 incomplete/unqualified,
3 invalid input or I/O error. `--output new.json` creates a report and refuses to
overwrite an existing file. Known findings retain gaps.

## Keep the claim's basis explicit

Record selected model/source revision, producer/compiler or firmware sequencing,
observer rules, cache/interconnect attributes and actual memory/I/O classification.
Inspect predecessor and successor domains and where the ordering mechanism acts.
Coherence, cache maintenance, ordering and device completion are separate premises.

The bundled native path uses single-bit sentinels and two propagation queues. It
is an implementation example, not a new ISA memory model, RVWMO execution, processor
test or hardware-wide guarantee. It qualifies no architectural access width,
atomics, mixed-width or translation-maintenance behavior. Use existing native
tools for those claims; the AI workflow is broader than this helper's profile.

Install the parent `data-ownership-visibility-handoff` module through the repository's
project-local installer. Optional [context sources](../../../../CONTEXT_PORT.md) may
supply scoped model, path, ordering and completion relationships. Nothing installs DVIT.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
