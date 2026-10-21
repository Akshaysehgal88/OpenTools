# Memory forward-progress dependencies

Review retained resources, requested resources and release paths for one
transaction class. Use the [AI workflow](SKILL.md) with allocation source, credit
or queue ownership, arbitration premises and actual transaction observations.
Your existing AI host and tools are sufficient; DVIT is optional.

The optional Python 3.10+ helper reports candidate wait cycles separately from
conditional observed blocking. It checks quantities and available capacity,
enabled acquisition/release, external escapes and a finite completion obligation.
A cycle or a stalled waveform alone is not a deadlock proof.

```sh
python examples/create_example.py /tmp/progress-review --case coherence-opposite
python progress_review.py /tmp/progress-review/model.json /tmp/progress-review/journal.json /tmp/progress-review/policy.json
```

`coherence-escape` and `coherence-release-before-wait` are controls. Other cases
cover common acquisition order, a serialized path through the same cyclic
design, an enabled but unscheduled escape, external reclaim and unknown
environment closure. Coherence-like and accelerator-like profiles use the same
activity. See [native controls](examples/NATIVE.md) and [records](FORMAT.md).

Exit codes: 0 within the supplied observed contract, 1 findings or candidate
cycles, 2 incomplete evidence, 3 invalid input or I/O error. `--output new.json`
creates a report and refuses to overwrite an existing file. Findings retain gaps.

## Supply the allocation contract

Keep the required actor/resource roster independent of observed occupancy.
Identify resource units and capacity, who holds each unit, what is requested,
which condition releases it and which mode activates each dependency. Include
completion, early release, cancellation, timeout and external progress paths.
Preserve the reachable prefix and original native flags; do not manufacture
reachability or fairness from a snapshot.

The helper accepts explicit counts for up to 64 resources and actors. It does
not infer dependencies from arbitrary RTL or certify imported roles/completeness.
Use existing native/company methods beyond the owned finite profile. A caller's
closed-environment declaration needs source review; hashes only bind content.

The owned example has two fixed transactions and single-slot resources. Native
simulation and a separate exhaustive state model qualify those controls, not a
production coherence protocol, arbitrary RTL equivalence or unbounded liveness.
An available action left unscheduled is distinct from no enabled progress.

Install through the repository's project-local installer. Optional
[context sources](../../CONTEXT_PORT.md) may add scoped ownership, release and
mode relationships. Nothing downloads or installs DVIT.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
