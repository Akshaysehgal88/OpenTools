# AI usage

Load [SKILL.md](SKILL.md) in your existing agent. Supply the actual reset event,
consumed state/reset sources, native transition journal and restart intent.

Example request:

> Review this partial reset. Identify each state owner and which state clears or
> survives. Follow pending work through restart, check release prerequisites and
> deliberate replay policy, and cite raw native observations for actual effects.
> Keep missing scope, sampling and temporal evidence visible.

The optional helper needs no AI SDK. The agent may use native/company tools and
source relationships beyond its bounded scalar profile. An optional configured
context adapter may supply more evidence; it does not grant approval or attest
to completeness. Standalone use requires no DVIT connection.
