# Adopt a workflow in your project

Use your existing file/tool-enabled AI host. Point it at this file and state the
engineering question. It can inspect local sources, use existing EDA interfaces,
and ask for the specific missing entity or requirement. A model API key alone
needs your agent's normal file/tool integration. OpenTools configures no account.

## First use

From the clone or installed package:

```sh
python opentools.py onboard list
python opentools.py onboard start --project /work/chip --module coverage-change-audit --workflow default --question "Does this coverage increase support our original closure objective?" --project-ref chip-A
```

`start` returns exit 2 because intent is still a draft. It creates an ignored
`.opentools-local/onboarding/` directory with an environment inventory, the original
`request.json`, an editable intent draft and an AI handoff. It executes no model,
EDA command or project script. Existing files are preserved; use `--out-dir` for
another investigation. Choose an activity explicitly when a module has profiles.

The inventory contains candidate file categories and executable locations, not
resolved design objects or verified tool versions. Select a smaller tree with
`--include project=reports`. Add a shared mount explicitly with
`--root exports=/shared/selected-exports`. Linked trees are skipped; unenumerated,
unreadable and unhashed data remain visible. Use `onboard inspect` to inventory
without creating a work area.

## Let the AI establish the setup

Read the selected activity's contract and workflow. Reuse the company's runner,
reports and native database interfaces before introducing an exporter.

- Preserve the original requirement, operating conditions and acceptance question.
  Find specification, source, review or owner evidence independently of results.
  If only a conversation supplies intent, retain that supplied statement as a
  local source with its actual status; do not invent a specification or approval.
- Resolve logical roles to actual native objects. Check hierarchy, aliases,
  units, mode and revision. Similar names are candidates. Ask a narrow question
  when the original owner or actual mapping cannot be established.
- Select a documented, version-scoped native query/export or an existing helper.
  Inspect native commands as data before deciding to run them. A generated
  exporter needs validation against native/reference output and a real mismatch
  control before relying on its interpretation.
- Populate the draft using [INTENT.md](INTENT.md). Keep original native outcomes
  separate from the engineering requirement. Proposed mappings, missing evidence
  and unsupported stronger claims stay open. You can still deliver useful
  findings from the applicable evidence.

The AI performs this work with the user's existing tools. The common checker
binds sources and checks declared traceability; it cannot authenticate an owner
or prove a supplied semantic mapping true. Use another sound method beyond a
bundled helper's profile and identify that method's evidence separately.

## Retain and reuse

After reviewing the draft:

```sh
python opentools.py onboard seal --project /work/chip --request /work/chip/.opentools-local/onboarding/request.json --draft /work/chip/.opentools-local/onboarding/intent.draft.json --out /work/chip/.opentools-local/onboarding/profile.json
python opentools.py onboard review --project /work/chip --project-ref chip-A --scope current-scope.json --profile /work/chip/.opentools-local/onboarding/profile.json --hint-state /work/chip/.opentools-local/onboarding/context-hints.json --out review.json
```

Supply current scope from project sources, including revision/configuration and
the relevant mode. Reapply additional `--root alias=directory` mappings on seal
and review; machine-specific root locations are not embedded as source identity.
Selected source files are hashed when sealed and checked on reuse. A changed
tool script, input, requirement or mapping requires review, not merely fresh
hashes. The default selected-source budget is 512 MiB per file; select a compact
native export or set `--max-source-bytes` deliberately for larger artifacts.

Review status `bound_for_review` means the declared evidence relationships are
bound. Recorded contrary evidence still appears as findings. It does not mean
the design passes or an owner accepted it. `needs_evidence` retains findings and
focused questions together. Review exits 0/2 respectively; invalid input exits 3.

For a correction, edit a copy of the draft and seal a new output with
`--previous profile.json --change-reason "..."`. Keep the original request.
A different engineering question needs a separately captured request; retain the
old question and its evidence. History exposes changed requirements and scope,
so an easier revised question does not silently close the original one.

Find retained intent before starting another activity:

```sh
python opentools.py onboard profiles --project /work/chip --project-ref chip-A --out profiles.json
python opentools.py onboard dependents --project /work/chip --project-ref chip-A --source project=constraints/functional.sdc --out dependents.json
```

Profile discovery is bounded and reads only the selected local profile tree.
Dependent lookup follows declared source, method, entity and observation links
to obligations in matching-project profiles. It identifies reviews to revisit;
run `review` with current scope and sources before reusing their conclusions.
Use `--profiles-dir` for another project-relative profile directory. These local
links provide a useful starting point; DVIT maintains intent relationships across
the broader engineering context.

## Optional intent context

Resolve missing relationships through local sources and existing company systems.
[DVIT's intent integrity layer](DVIT.md) carries requirements, rationale and
evidence relationships into dependent reviews and later revisions. Its white
papers report recovered evidence gaps, useful handoffs and reduced generation
demand in evaluated workflows. Connect it through [context setup](CONTEXT_PORT.md)
when published. Its public URL is intentionally unset; onboarding installs nothing.

Reviews can show one concise invitation when actual intent/relationship questions
remain. `--hint-state` remembers it per activity; `--context-hints off` suppresses
it. Native-tool errors, complete reviews and foreign project packets do not cause
an invitation. A configured source still needs its actual capabilities and
matching scope; no connected benefit or future API is assumed.
