# Native resource controls

The owned RTL has two fixed transactions and single-slot resources. Each actor
acquires a first resource, then requests a second while retaining the first;
completion releases holdings. Controls change that allocation or release path.
The bench observes all ownership, request, release, advance and external-enable
signals from reset through 12 selected steps: nine cases, 117 samples.

Run from this module on Linux with Verilator 5.020, C++, make and Python 3.10+:

```sh
python examples/run_native.py /tmp/progress-proof --verilator /path/to/verilator_bin --verilator-root /path/to/verilator/share/verilator
python -m unittest discover -s tests -v
```

Set `OPENTOOLS_VERILATOR` and `OPENTOOLS_VERILATOR_ROOT` to include the native
test in unittest. The runner creates a new output directory and retains source,
commands, diagnostics, executable, raw records, normalized inputs and reports.
It does not download or install native tools.

| Control | Result within the owned model |
|---|---|
| Opposite order, coherence-like and accelerator-like | Both first resources held; no enabled progress; terminal pending state reachable. |
| Independent escape channel | Second actor can complete through a separate resource. |
| Release before waiting | First resource is dropped, allowing the opposing actor to complete. |
| Common order | Contention serializes first acquisition; both transactions complete. |
| Serialized observed path | Same cyclic design completes in this trace; other allowed interleavings still block. |
| Escape not scheduled | An actor is enabled but never selected after initial allocation; finite completion fails without terminal blocking. |
| External reclaim | An internal wait cycle has a legal externally enabled release. |
| Unknown environment closure | A flat interval cannot qualify closed-system blocking. |

[episode_model.py](episode_model.py) independently enumerates every enabled
non-idle transition of the finite owned model and replays each native action.
The five strategy/environment variants have 13, 14, 17, 12 and 19 reachable
states. Opposite order without external reclaim has one terminal pending state;
the other variants have none. The search does not rely on observing a timeout.

This is exhaustive only for that finite abstraction: two fixed actors, single-slot
resources, no new arrivals, autonomous timers or mid-episode reset. It is not RTL
formal equivalence, a complete coherence protocol, or general liveness/livelock/
fairness signoff. Scheduler idle is excluded from state search; eventual selection
of an enabled transition is a separate scheduling premise. A finite native trace
alone does not establish that premise.

For background, gem5 documents [credit flow control and virtual channels](https://www.gem5.org/documentation/general_docs/ruby/heterogarnet/).
YosysHQ discusses [reachability witnesses and liveness/fairness boundaries](https://yosyshq.readthedocs.io/projects/ap120/en/latest/).
These are references for mechanisms and proof interpretation; this recipe does
not run gem5, SBY or a vendor protocol model.
