# Project intent and evidence records

The existing AI host writes these records from inspected project sources.
The engineer can use the workflow without converting every company artifact.
Capture only the requirements and native evidence needed for the current question.

## Original request and editable draft

`onboard start` saves the original question separately in `request.json`.
Keep it unchanged. A draft uses `opentools.intent-draft.v1`:

| Field | Contents |
|---|---|
| project_ref, scope | Current project identity and explicit revision/configuration/mode conditions |
| workflow | Installed module, activity ID and contract digest from onboarding |
| question | Original engineering question, matching the retained request |
| sources | Selected local artifacts or explicit unavailable/nonlocal references |
| obligations | Independently required behavior, applicability and acceptance |
| entities | Logical meanings mapped to actual native objects |
| methods | Native tool/interface, version, reference checks and limitations |
| observations | Source-backed AI interpretations attached to original obligations |
| unknowns | Narrow questions with a reason and affected obligation |
| handoff | Receiving owner and existing decision reference, or null |

Start with the generated draft. Populate the following lists; leave unavailable
values null and use `proposed` or `unknown` rather than inventing confirmation.

```json
{
  "sources": [{
    "id": "required-behavior",
    "root": "project",
    "path": "spec/transition.md",
    "reference": "transition requirement, section 3",
    "revision_ref": "spec-r4",
    "kind": "intent",
    "roles": ["intent"]
  }],
  "obligations": [{
    "id": "pending-survives",
    "requirement": "An accepted pending event survives the warm transition until acknowledged.",
    "basis": ["required-behavior"],
    "applicability": {
      "status": "required",
      "condition": "Warm transition with preservation enabled",
      "basis": ["required-behavior"]
    },
    "acceptance": "The retained native event and checker evidence show the pending event after the transition.",
    "entities": ["pending-state"],
    "status": "proposed"
  }]
}
```

This is a record fragment, not observed evidence. Actual sources and object
meanings must come from the adopting project.

## Sources and native correspondence

Each source has `id`, `root`, `path`, `reference`, `revision_ref`, `kind` and `roles`.
Use forward-slash relative paths within named artifact roots. Nonlocal or missing
references have null root/path and remain unavailable until applicable local
evidence is supplied. Source kinds are `intent`, `native`, `configuration`,
`mapping`, `method`, `decision` and `other`. Roles come from the activity contract.
One artifact can fill multiple roles where its actual content supports them.

An entity has `id`, `meaning`, `native_object`, `source_refs`, `method_ref` and
`status`. A native path needs source and method evidence; a reviewed label alone
does not establish that a register, bin, fault or timing endpoint has that meaning.

A method has `id`, `tool` (`name` and `version`), `interface`, `source_refs`,
`checks`, `limitations` and `status`. Each validation check has `claim`,
`outcome` (`pass`, `fail`, `unknown`) and `source_refs`. These checks validate
extraction/correspondence, not the underlying design's acceptance. Record the
actual native result separately. Source scripts are retained data; sealing and
review never execute them.

An observation has `id`, `obligation`, `source_refs`, `entities`, `finding`,
`outcome` (`supports`, `contradicts`, `unknown`) and `method_ref`.
Its referenced observation sources must be native evidence. Report interpretation
is advisory. Original helper/native statuses remain alongside this record.

For example, a coverage obligation needs its real expression and sampling/mode
meaning, not just a bin name and count. A timing exception needs its original
rationale and current native reach, not just an unchanged SDC string. A scan
exclusion needs current state-role premises independently of scan membership.

## Applicability, questions and reuse

Obligations use `required`, `not_applicable` or `unknown` applicability, with the
condition and source basis. Nonapplicable rows remain visible. A missing run or
a native exclusion flag does not authorize removing a requirement.

An unknown has `id`, `question`, `reason`, `obligation` (or null) and `kind`:
`intent`, `mapping`, `native`, `relationship` or `authority`.
Prefer the smallest missing source or native query to a broad rerun.

Sealing records exact selected bytes and preserves unresolved sources. Reuse
checks current project/scope, activity instructions, source identity and declared
entity/method links. Hashes do not establish source truth, freshness, semantic
adequacy or approval. An internally consistent but weakened requirement still
needs AI review against the original request and sources.

A revised profile retains the prior draft and source bindings with its change
reason. Keep original findings and questions; a new configuration or question
does not repair the historical result. Existing engineering owners retain
acceptance authority.
