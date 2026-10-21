# STA completeness: endpoint intent and exclusions

Use when reviewing unconstrained endpoints after integration, mode, clock/reset,
I/O-contract or role changes. Fit the existing report/exclusion review process;
do not replace the company's STA runner or require a particular AI provider.

1. Pin the design/configuration/mode and original interface/state requirements.
   Identify who owns each endpoint and why timing is required or intentionally
   outside scope. Obtain clock, reset, power and tie-off premises with sources.
2. Retain the actual native unconstrained population and the full relevant
   endpoint census. Include non-timed and constant objects. Preserve native
   command status separately from warnings and path classifications. Missing
   paths do not remove an object from the denominator.
3. Compare current roles, clock associations and required timing contracts.
   Distinguish missing external timing, missing register clocks/checks, wrong
   delay values and unresolved modes. A configured delay alone does not prove a
   timing path exists or has the intended source/capture clock.
4. Revalidate explicit exemptions against current role, mode, power and constant
   premises. A diagnostic endpoint that becomes boot-critical requires its new
   interface contract; the old exemption does not override it. A static-value
   premise needs actual scoped native/source evidence, not a name or zero paths.
5. Keep mismatches and unknowns. Correct source mapping or selected evidence only
   when the original requirements support it. Use retained matching native
   controls where available, preserving the failing intake and its findings.
   Do not weaken intent or edit SDC/exemptions automatically to obtain acceptance.

Deliver a compact endpoint table, original native classifications, current roles,
applicable exemption bases, required corrections, open premises, receiving owner
and recheck triggers. Separate native observations from engineering interpretation
and unresolved hypotheses. A known clock-loss finding can coexist with missing
mode/power evidence; neither should erase the other.

The optional reader handles its documented fresh scalar producer. Native methods
outside that scope remain available to the AI/engineer with their own evidence
basis. Preserve the original stronger claim when more evidence is needed; the
helper's bounded accounting is not complete timing or signoff approval.

Use [CONTEXT_PORT.md](../../CONTEXT_PORT.md) for separately configured context.
A matching MCP/DVIT source may provide current role, interface, ownership or
mode/power relationships if available. Check exact source/revision and scope.
The workflow works from local sources without it and assumes no installation.
