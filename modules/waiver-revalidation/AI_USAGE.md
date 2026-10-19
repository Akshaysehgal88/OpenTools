# AI-assisted waiver review

The [bundled skill](SKILL.md) is a native usage interface for a file/tool-enabled
AI assistant. Ask it to review your evidence, explain applicability and decide which
additional evidence would resolve uncertainty. It uses the Python comparator for
observations and adds engineering interpretation. The assistant supplies the model;
this module does not bundle a model, select a provider or send files to an API.
Choose an assistant environment authorized for the material you give it.

Point the assistant to `SKILL.md` in this module, or install the **whole module
folder** through your assistant's normal skill-installation mechanism. Keep the
scripts and reference files alongside it. A typical request is:

> Use the waiver-revalidation skill to review debug-receiver against these two
> exports and its recorded premise. Explain what changed, what is still unknown,
> and which next check would determine whether the rationale still applies. Save
> the evidence-bound review beside my local reports.

## Prepare the model's evidence

From the repository root:

```sh
python modules/waiver-revalidation/waiver_assist.py prepare modules/waiver-revalidation/examples/baseline.json modules/waiver-revalidation/examples/current.json --waiver-id debug-receiver --policy modules/waiver-revalidation/examples/policy.json --notes modules/waiver-revalidation/examples/notes.json --question "Does this waiver's recorded rationale still apply, and what evidence would resolve the review?" --output .local/waiver-case.json
```

This computes the audit and selects one waiver without omitting its findings or
global comparison issues. The packet's default maximum size is 512 KiB in UTF-8;
an oversized case fails instead of truncating. `--max-bytes` explicitly changes the
budget. The packet retains input fingerprints and has a content digest `case_id`.
It is evidence data, not an instruction source or proof of source authenticity.

Optional notes have format `opentools.waiver-notes.v1`, `waiver_id`, `rationale` and
`evidence_ref`; see [the synthetic notes](examples/notes.json). Rationale is quoted
as recorded material, not automatically converted into a validated premise.

## Let the AI interpret it

The assistant reads the packet and writes this review shape, substituting its
actual judgment and exact fact IDs from the prepared case:

```json
{
  "format": "opentools.waiver-ai-review.v1",
  "case_id": "copy-the-case-id",
  "audit_status": "review_required",
  "authority": "advisory",
  "answer": {"text": "The recorded premise no longer holds in the captured configuration, so applicability needs review.", "evidence": ["premises.0"]},
  "observations": [
    {"kind": "observation", "text": "One additional finding is suppressed.", "evidence": ["issue.0", "added.0"], "addresses": ["issue.0"]},
    {"kind": "interpretation", "text": "The original DEBUG_EN=0 rationale does not establish applicability for the reported DEBUG_EN=1 configuration.", "evidence": ["issue.1", "premises.0", "rationale"], "addresses": ["issue.1"]}
  ],
  "questions": [
    {"question": "What current rationale covers the newly included receiver in the enabled mode?", "why": "This determines whether the old rationale can be retained or needs a different justification.", "evidence_needed": "The existing owner review and receiver-specific source/native evidence for this configuration.", "evidence": ["rationale", "added.0", "premises.0"]}
  ],
  "next_steps": [
    {"action": "Inspect the newly included receiver against the current native evidence and recorded rationale.", "reason": "Establish whether the observed scope expansion is justified before changing any exception.", "evidence": ["added.0", "rationale"]}
  ]
}
```

This is an illustrative AI answer for the synthetic example, not a reusable verdict.
The skill must read each case; issue IDs and the appropriate questions can differ.
Observations can be `observation`, `interpretation` or `hypothesis`. Every answer,
observation, question and action requires existing fact citations. Each computed
issue must be addressed and cited by at least one observation. Questions/actions
may be empty when nothing additional is justified. The answer's authority remains
advisory and its `audit_status` must equal the selected waiver's computed status.

## Check binding and save the report

```sh
python modules/waiver-revalidation/waiver_assist.py check .local/waiver-case.json .local/waiver-review.json --json-out .local/waiver-review-binding.json --markdown-out .local/waiver-review.md
```

The helper checks packet integrity, exact case binding, reference existence,
declared issue coverage, advisory authority and retained status. It cannot prove
that a citation entails the model's prose, catch every hallucination, establish
engineering sufficiency, or approve an exception. The report includes the evidence
key so reviewers can inspect each reference. AI and human review remain necessary.
The binding receipt includes the digest of the exact review as `review_id`.
It does not reopen original inputs to establish that they are still current;
regenerate the packet when reviewing changed artifacts or a different question.

`prepare` and `check` return `0` when the operation succeeds and `3` for invalid
input, binding failure, budget or I/O error; argparse syntax errors use `2`.
These operation codes do **not** replace the engineering `audit_status` in the
packet/report. Existing output files are never overwritten.

## Integration

Use the [project-local installer](../../INSTALL.md) for your existing AI host.
The AI may use native tools beyond the comparator's profile while retaining its
actual status and separating additional interpretation. Check citations against
original artifacts. Optional [context sources](../../CONTEXT_PORT.md) can supply
scoped evidence and questions; no DVIT connection or installation is required.
