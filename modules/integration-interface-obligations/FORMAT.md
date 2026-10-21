# Selected native port facts

The exporter reads selected ordinary input/output ports from the Slang elaborated
model. It does not infer protocol meaning or parse HDL with text matching.

## Inputs

`--parameters` is an object of integer top-module overrides. Each override is
verified against the elaborated port parameter; booleans/unknown names fail.

`--scope` contains exact nonempty `project_ref`, `interface_ref`,
`configuration_ref` and `mode_ref`. Those labels are caller declarations; source
hashes and actual parameters remain separate native collection evidence.

`--selection` uses this shape:

```json
{
  "format": "opentools.port-selection.v1",
  "links": [
    {"id":"receipt","source":"worker.accepted_o","sink":"client.accepted_i"}
  ]
}
```

IDs are unique. Paths are plain `instance.port` identifiers relative to the chosen
top; deeper ordinary instance paths are allowed. Generate/array paths, interface
ports, wildcard selectors and semantic correspondence guesses are outside scope.
Every requested instance/port must resolve or capture fails with no complete report.

## Native profile and output

`opentools.interface-connections.v1` retains scope, links, findings, gaps,
provenance and limits. For each endpoint it retains direction, port width, the
resolved net/variable identity and width, expression kind and source reference.
It reads actual port connections, not matching names across declarations.

Only supported direct references can establish `directly_connected`. Different
resolved nets, directions or widths produce a finding. Expressions requiring
another interpretation remain `needs_evidence`; they are not guessed equal or
declared electrically broken. No flattening across arbitrary aliases is claimed.

Provenance retains the selected top, actual requested/verified overrides, original
selection, declared input hashes and frontend version. Sources/dependencies are
hashed before and after elaboration. Repeat `--dependency` to declare other input
files; this is not automatic include/dependency discovery.

Overall status is `review_required` when known findings exist, otherwise
`incomplete` for unsupported/missing declared input basis, otherwise
`connected_within_profile`. Known findings retain other gaps. The `.evidence`
directory retains native diagnostics and the capture; failed compilation leaves
diagnostics. Outputs and evidence directories must be new.

## Engineering review

Use [RECORD.md](RECORD.md) to join these native facts with source-backed endpoint
roles, event meanings, mode and clock/reset assumptions. Keep original native
status and independent interpretation separate. Existing run identity, source
hashes, tool/configuration and the actual observed interface must correspond.
Stale or foreign-scope facts cannot support a current integration conclusion.

The reader does not authenticate intent, scope names or completeness. It does not
compare protocol semantics or interpret event journals; the AI/native engineering
workflow handles those with references. A source-named `ack` can mean receipt,
completion or something else. Use the actual applicable contract.

Reference: [Slang elaboration](https://www.sv-lang.com/user-manual.html).
