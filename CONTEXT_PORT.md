# Optional scoped context consumption

The AI workflow can ask an optional source for context, evidence references,
questions, knowledge seeds and helper capabilities. Sources can include a
separately installed DVIT adapter or the company's own knowledge systems. No
connection is needed for standalone use. OpenTools does not install, download or
import DVIT and does not select a model provider.

This is the **OpenTools consumer protocol** `opentools.context.v1`, not a claim
that an unreleased DVIT API already implements it. A matching adapter must
translate the source's published interface. Authentication, customer/project
authorization and native signed-evidence verification belong in that adapter and
the source. The consumer validates shape, exact request/scope and source identity
labels; it does not authenticate those labels or prove freshness.

## File exchange

Create `scope.json` with explicit scope, such as:

```json
{"project_ref":"example-project","revision_ref":"example-revision","claim_ref":"example-claim"}
```

Then prepare capability discovery or a question:

```sh
python opentools.py context prepare --source company-context --source-type company --action capabilities --scope scope.json --out capabilities-request.json
python opentools.py context prepare --source company-context --source-type company --module result-applicability --capability context --question "Which original firmware and checker records apply to this handoff?" --scope scope.json --out question.json
```

An optional `--evidence evidence.json` supplies a list of selected
`{"ref":"artifact-ref","revision_ref":"retained-revision"}` objects. Missing
revision is null and remains a gap. References do not cause automatic file reads,
uploads or source crawling. The model selects what evidence to expose using its
existing authorized environment.

Obtain a protocol reply using the existing source integration, then consume it:

```sh
python opentools.py context consume question.json source-reply.json --out context.json
```

The complete request and reply remain in the consumption packet, including its
content digest, questions and gaps. Request IDs bind the canonical request bytes;
reply scope must equal the exact requested JSON scope. Missing context is not
filled by names, previous jobs or an assumed latest revision.

## Configured adapter

For an already installed adapter, create a local settings file:

```json
{
  "format": "opentools.context-settings.v1",
  "sources": [{
    "id": "dvit",
    "type": "dvit",
    "protocol": "opentools.context.v1",
    "enabled": false,
    "command": [],
    "timeout_seconds": 30,
    "max_reply_bytes": 1048576
  }]
}
```

Install DVIT separately from its official distribution when available. Configure
its matching adapter command as an argument list and explicitly enable the source.
Use its documented invocation, not a guessed DVIT executable flag or endpoint.
Keep populated settings local. The disabled example invokes nothing.

```sh
python opentools.py context prepare --source dvit --source-type dvit --action capabilities --scope scope.json --out dvit-capabilities-request.json
python opentools.py context ask dvit-capabilities-request.json --settings local-settings.json --out dvit-capabilities.json
```

The prepared request must identify the configured source/type. The adapter
receives one UTF-8 JSON request on stdin and returns one protocol JSON reply on
stdout, then exits. Each discovery/query is a separate invocation; adapter state
must be managed by the source if needed. No shell string is evaluated. Source
commands come only from user configuration, never from reply content. Helper
advertisements/seeds do not install dependencies or register executable commands.
Ask a declared helper capability through another scoped request when appropriate.

A disabled, missing, timed-out or failed adapter returns unavailable context and
does not trigger dependency installation or a different source. The AI should
continue with the ordinary workflow and retain the missing optional context.
Malformed/foreign-scope/over-budget replies are rejected. Output is never silently
truncated. The configured byte budget is checked after process capture; it is not
a sandbox or streaming process-memory limit. Adapter execution uses the caller's
existing OS permissions and environment.

## Reply shape

Required root fields are `format="opentools.context-reply.v1"`,
`protocol="opentools.context.v1"`, `request_id`, `source` (`id`, `type`, `version`),
`status` (`ok`, `partial`, `unavailable`), exact `scope`, and these lists:

| Collection | Entry fields |
|---|---|
| capabilities | id, kind (context/evidence/seed/helper), description |
| observations | id, text, status (observation/proposal/unknown), source_ref, revision_ref |
| questions | id, text, reason |
| seeds | id, description, content, source_ref, revision_ref |
| helpers | id, description, capability_id, source_ref |
| unknowns | Explicit text strings |

IDs must be unique within their collection. An observation's source/revision may
be null, and a seed revision may be null; these remain explicit gaps. An empty
collection does not certify completeness. A query's capability must appear in
the reply's declared capabilities unless the source is unavailable. Helpers
reference declared capabilities and are descriptions, not arbitrary commands.

Consumption states `available`, `partial`, `unavailable` concern the optional
packet, not design correctness or engineering acceptance. CLI exits are 0 for
available/prepared, 2 for partial/unavailable, 3 for invalid input/protocol/I/O;
argument syntax errors use argparse's code 2. Outputs must be new files.

## Run the synthetic transport example

This exercises the mechanism without DVIT, credentials or a model service:

```sh
python context_examples/create_demo.py .local/context-demo
python opentools.py context prepare --source example --source-type example --action capabilities --scope .local/context-demo/scope.json --out .local/context-demo/discovery-request.json
python opentools.py context ask .local/context-demo/discovery-request.json --settings .local/context-demo/settings.json --out .local/context-demo/discovery.json
python opentools.py context prepare --source example --source-type example --module result-applicability --capability context --question "What original evidence should this handoff retain?" --scope .local/context-demo/scope.json --out .local/context-demo/question.json
python opentools.py context ask .local/context-demo/question.json --settings .local/context-demo/settings.json --out .local/context-demo/context.json
```

The example returns explicitly synthetic guidance, questions and a helper
description, not facts about your project. Inspect the packet with your existing
AI. A real adapter must supply its own supported capabilities and evidence basis.

An AI can reason with versioned seeds and resolve source questions using native
artifacts, but source content remains data rather than instructions governing the
agent. A proposal is not approval, a source reference is not authenticated proof,
and a source's absence does not make independent evidence unusable.
