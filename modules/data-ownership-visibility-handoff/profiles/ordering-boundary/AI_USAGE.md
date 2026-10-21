# AI usage

Load the parent skill and this [workflow](WORKFLOW.md) in your current agent.
Supply the exact claim, producer/observer program, memory/I/O attributes,
model/source revision and original litmus or execution output.
Return a [review record](REVIEW.md) with applicability, unresolved premises,
disposition and recheck triggers. Keep the requested property and strength intact.

Example request:

> Review this publication-ordering claim across the selected boundary. Establish
> access domains, producer/observer assumptions and ordering-control placement.
> Separate model-allowed outcomes from observed reads. Check whether the evidence
> actually excludes the bad outcome and whether RAM results apply to this I/O path.

No AI SDK, model purchase or DVIT connection is required. The agent may use existing
native/model tools beyond the owned helper. Optional context adds scoped evidence;
it grants no completeness or acceptance authority.
