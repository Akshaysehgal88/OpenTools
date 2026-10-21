# Mode setup acceptance record

Use this record with the team's existing tools, including modes outside the
bundled native reader. Keep original artifacts and record exact locations.

| Field | Record |
|---|---|
| Review boundary | Design/configuration, test mode, domain, shift/capture/access phase sequence |
| Intended claim | What the receiving activity needs to rely on; required evidence strength |
| Required mode table | Independent source/version and owner; unresolved entries |
| Native artifacts | Tool/version, command/setup, source identities, run identity, relevant locations |
| Mapping | Hierarchy/pins, clock roots and gates, reset polarity/masks, enable controls |
| Power and access | Supply/isolation state and dependencies; lifecycle policy distinct from functional debug |
| Phase evidence | Required resource versus native constraint versus observed value for every phase |
| Witness usefulness | Load/capture/unload activity, serial observability and checker/model basis |
| Applicability | Current, missing, stale or foreign evidence; excluded modes and unresolved propagation |
| Findings | Failed prerequisite and downstream effect, including native failure retained |
| Correction | Supported control/setup change, responsible owner, expected discriminating rerun |
| Acceptance | Receiving owner decision and artifact reference, or pending |
| Recheck | Mode/control/netlist/library/policy/constraint changes that invalidate this record |

For multiple domains, keep their clocks, resets, access controls and power
dependencies distinct. Record sequencing between them. A local good trace cannot
close a global dependency or characterize physical behavior.
