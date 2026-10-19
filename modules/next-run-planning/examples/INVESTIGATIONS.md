# Representative investigations

Generate executable-helper examples with `create_example.py`. They are synthetic
records; none of these examples dispatches a job.

| Case | One adequate next step | Evidence/decision boundary |
|---|---|---|
| Timeout with an existing full correlated journal | Inspect it first | Acceptance with no completion directs attention in flight; no acceptance requires complete relevant history; completion challenges checker/attribution assumptions |
| Only a late trace | Establish its coverage, then ask for earlier correlated evidence | No handshake inside that window is not proof of nonacceptance; the inconclusive result leaves both explanations unresolved |
| Original observation replay proposed | Keep it unexecuted until actual collection | State fixed/intended/uncontrolled factors and map failure, incomplete evidence and changed reproduction before running |
| Replay differs despite fixed inputs/seed | Preserve the changed execution | Scheduling/external state or instrumentation can matter; repair correspondence or label a separate exploratory branch |
| Same design appears in prior history | Inspect prior outcomes and replication purpose | Exact repetition can be useful for nondeterminism; repeating an inadequate window without repairing it does not discriminate the explanations |
| Loader/checkpoint execution fails | Retain failure and scoped facts | A load error can inform an infrastructure hypothesis, while the original hardware question remains unanswered |

For each, review whether the observations are attainable with the actual installed
tools. A generic “rerun with debug” instruction is insufficient. Existing native
journals/counters may be cheaper and more conclusive than another trace; a new
run may be necessary when required facts were never recorded. Do not choose fewer
runs at the cost of weaker evidence.

The helper verifies bindings, declared controls/completeness and mapping structure.
It intentionally cannot determine whether a free-text condition is true or whether
the explanations are falsifiable. The AI/engineer must inspect original evidence
and keep semantic corrections separate from unchanged original records.
