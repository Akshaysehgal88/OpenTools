# Protocol transition obligations

Review one transaction from request through accepted ownership/completion token
and actual consumer use. This profile extends [integration interface obligations](../../README.md).
Use the [AI workflow](WORKFLOW.md) with the protocol version, transient state,
source-tagged messages and actual permissions. Your existing AI host is sufficient;
DVIT is optional.

The optional Python 3.10+ helper maintains typed obligations by source, transaction
and epoch. Stable-state labels and numerical pending counts do not discharge them.
It checks accepted grant prerequisites, actual old/new permission overlap and
consumer data under an explicit exclusive-handoff contract.

Run from this profile directory:

```sh
python examples/create_example.py /tmp/transition-review --case directory-premature-grant
python transition_review.py /tmp/transition-review/model.json /tmp/transition-review/journal.json /tmp/transition-review/policy.json
```

`directory-complete` is the control. Other cases cover late data, duplicate and
stale acknowledgements, an offered token under backpressure, and an owned two-worker
ring reclamation subset. See [native controls](examples/NATIVE.md) and [records](FORMAT.md).
The profile needs no Slang dependency; the existing port reader remains separate.

Exit codes: 0 within supplied observed contract, 1 findings, 2 incomplete evidence,
3 invalid input or I/O error. `--output new.json` creates a report and refuses to
overwrite an existing file. Findings retain accompanying gaps.

## Supply the protocol contract

Keep required old holders, receipt classes, returned-data prerequisites and consumer
milestones independent of observations. Match source, resource, transaction ID and
epoch before granting credit. Inspect actual released rights, token acceptance and
consumer effects; a valid offer is not an accepted grant. Late receipts do not erase
earlier consumption while obligations were outstanding.

The owned directory and two-worker reclaim models qualify those subsets only.
They are not MSI/CHI/AXI implementations, arbitrary descriptor adapters or general
liveness proofs. Retry, cancellation, eviction and reset overlap require their own
source rules and native qualification. Use existing native/company methods beyond
this helper's explicit contract.

Install the parent `integration-interface-obligations` module through the repository's
project-local installer. Optional [context sources](../../../../CONTEXT_PORT.md) can
provide scoped protocol, owner and obligation relationships. Nothing installs DVIT.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
