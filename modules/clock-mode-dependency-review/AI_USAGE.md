# AI usage

Load [SKILL.md](SKILL.md) in your current agent. Supply the consumed RTL/clock
export, selected mode and relevant firmware/controller wait paths.

Example request:

> Review this clock-mode change. Trace each readiness wait to its producer and
> the clock/reset/power prerequisites of that producer. Check independent wake
> paths and initial state. Use existing native observations where applicable;
> distinguish model findings, bounded stalls and unresolved temporal claims.

The agent can use native/company tools beyond the optional helper's abstraction.
No AI API or DVIT connection is required. A separately configured context adapter
may add scoped relationships; it does not grant approval or prove completeness.
