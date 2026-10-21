# Records and native boundary

`opentools.interface-budget-contract.v1` binds one original allocation to
`upstream`, `downstream` and `top` views. It records scope, owner, requirements,
clock mapping, latency and projection references; handoff deadline/load,
capture requirement and launch arrival; one-to-one cell maps and boundary pins.
Each view binds its original run identity, six consumed-source hashes, invocation
hash and requested result fields. The [owned fixture](examples/fixture.py) shows
the complete structure. A null relationship or selected run remains unresolved.

Each saved run contains `context.json`, `command.json`, `execution.json`, tool
version, original stdout/stderr and six consumed sources: `design.v`, `cells.lib`,
`cells.lef`, `config.tcl`, `loader.tcl`, `export_budget.tcl`. Execution binds the consumed
sources, original context/invocation, pre-execution contract digest, tool binary
hash and native artifacts:
`native.jsonl`, `path.txt`, `bridge-net.txt`, `sink-net.txt`, `native.odb` and
`consumed.sdc`. Sources and original reports must remain available. Hashes bind
bytes; they do not authenticate authority or prove report sufficiency.

The Linux producer is qualified with OpenROAD **v2.0-17598-ga008522d8** for one
fresh flat, single-library/single-clock mapped scalar buffer interface. The top
contains those two complete cones plus launch/capture state. Source and target
edges come from the actual expanded-clock path report. Selected path deadlines,
arrivals and margins, native case values, selected operating conditions, clock
waveform, external port capacitance and native connectivity are exported.
`report_net` supplies actual integrated boundary capacitance and driver/load
counts. Output delay and register setup margin retain their different meanings.
Time is ns and capacitance pF; unknown cases remain null.

Reporting can invalidate native PathEnd handles. The exporter acquires them
after report searches and consumes them before another search. Original marker,
version, producer, setup, source and artifact checks must all pass; exit zero
alone is insufficient. Saved-data intake executes no archived Tcl.

The helper composes the unchanged parent applicability audit per view with
`any_observed`, retaining failed outcomes. It then checks complete mapped cone
connectivity and explicit budget/load relationships. Known model or identity
differences prevent cross-view composition. An added stronger requested field
is preserved as unknown, not silently dropped.

`BOUNDED_INTERFACE_AGREEMENT` concerns the stated selected views and allocation.
`BUDGET_REVIEW_REQUIRED` preserves actual timing debt or known correspondence
findings. `INCOMPLETE` preserves absent or unresolved premises and quarantined
evidence. JSON includes all three native outcomes, projection, timeline,
relationships, findings, gaps and recheck triggers; Markdown is the review view.

Limits: one max-setup path per view, one driver/load and zero annotated wire
capacitance at the boundary; owned examples use fixed scalar cells. No automatic
SDC generation, job scheduling, model authentication, functional-equivalence
proof, macro/multicycle support, mixed libraries, hold/OCV/derates, extracted RC
or full STA signoff. Qualify a different exporter or use the existing native flow
for broader work; do not infer unsupported values from labels.
