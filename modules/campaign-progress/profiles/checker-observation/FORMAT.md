# Records and native boundary

JSON fields are exact; duplicate keys reject. Unknown references use `null` and
remain gaps. Independent intent is not inferred from the observed run.

## Context and intent

`opentools.checker-observation-context.v1` uses
[capture-context.template.json](capture-context.template.json): run/campaign/scope,
configuration/model, checker/source, clock/reset, dependency, instrumentation,
expected-data and window references. `port_map` assigns eleven explicit top ports.
`edge=positive`, `sampling=stable_preedge` and `reset_active=0|1` are required.
Scope/review/oracle/dependency references are supplied, not authenticated. Missing
bases prevent qualified exposure.

`opentools.checker-observation-intent.v1` uses `claim_id`, `claim`, `owner_ref`,
`basis_ref`, `expected`, `required_modes`, `mode_basis_ref`, `policy_ref`.
`expected` independently records run/campaign/scope/configuration/model, clock,
edge/sampling, reset/polarity, checker, port map and four original source hashes.
Required modes are sorted unique 0, 1 or both, or unknown. Obligations apply at
completion; acceptance mode is retained. Use [intent.template.json](intent.template.json).
Agreeing records do not authenticate an original requirement.

## Retained Verilator journal

The reader accepts Verilator 5.020, one flat top and one positive-edge clock.
Controls are scalar; paired unsigned IDs/data have matching widths of 1..32 bits.
Qualification fixtures use 8-bit IDs and 16-bit data. Role names and reset polarity
must match original `ports.hpp` and native XML.
Additional ports remain in the native inventory. Retain their original configuration
evidence when relevant; this journal does not measure unselected inputs. Fixture
fault injection and expected-model constants are not required observation roles.

Retain `top.sv`, `ports.hpp`, `checker.hpp`, `main.cpp`, `model.xml`, `Vtop`,
`version.txt`, build/XML command JSON and stdout/stderr, run command JSON and
stdout/stderr, and `execution.json`. The last contains `build_exit`, `xml_exit`,
`run_exit`, `binary_sha256`. Build/XML must complete; run 0/1 must agree with
actual comparison actions. Every review hashes and reparses critical artifacts,
including the Linux ELF. Imported commands are never executed.

[examples/run_native.py](examples/run_native.py) gives exact build/XML commands.
The original C++ loop journals settled ports before rising edges:

```text
EDGE tick reset mode enabled req_valid req_ready req_id req_data rsp_valid rsp_ready rsp_id rsp_data clock
CHECK tick id expected observed ok
FINAL stimulus accepted completed checked failures
```

Values are unsigned integers. EDGE ticks are contiguous from zero and sampled
clock is zero. CHECK belongs to the preceding EDGE; `ok` equals its actual
expected/observed comparison. FINAL must agree with the full journal. Truncated,
aggregate-only or contradictory exports reject.

Acceptance/completion are valid AND ready outside reset. This contract excludes
same-edge zero-latency completion. IDs are unique while pending; reuse after
completion is a new acceptance sequence. Sampled reset cancels pending work and
starts a new epoch. Window-end pending work remains unresolved. Source review
must establish instrumentation and expected-data meaning. The reader does not
attest arbitrary C++, hardware reset correctness or oracle adequacy.

## Output and accounting

`opentools.checker-observation-evidence.v1` preserves context, sources, ports,
all EDGE/CHECK actions, native result and integrity receipt.
`opentools.checker-observation-review.v1` preserves differences, gaps, identities,
per-mode obligations, native status and parent campaign accounting.

The existing campaign summarizer counts unique event ranges. Stimulus, accepted
and completed cover the retained window; qualified checked exposure includes
matching completions in requested modes. Raw checker-action counts stay separate.
Mode selection participates in the measurement basis. Zero exposure targets are
accounting placeholders, not acceptance criteria. Wall-clock time is unknown;
ticks/file times do not establish interval rates or campaign completeness.

Statuses are `observation_consistent_with_declared_contract`, `review_required`,
`incomplete`. A caught functional failure can have valid observation. Positive
stimulus or equal counts alone cannot establish it. References/hashes establish
declared correspondence, not authenticity or verification completeness.

Native connection mechanics follow the [Verilator model interface](https://verilator.org/guide/latest/connecting.html).
Actual 5.020 artifacts define support; current documentation does not qualify
other versions or arbitrary UVM logs.
