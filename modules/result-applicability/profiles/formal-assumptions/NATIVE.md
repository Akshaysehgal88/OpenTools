# Native qualification

The Linux example needs an existing SBY checkout at revision
`85dd50b92a3acf170954a06f20f49e2162ce5273` (tag `yosys-0.33`), Yosys0.33
git `2584903a060` and Z3 4.8.12 64-bit. It checks checkout/executable identities.
Distribution builds may need their matching Tcl library and Yosys Python modules
in the prefix. The recipe downloads and installs nothing.

Upstream [installation guidance](https://yosyshq.readthedocs.io/projects/sby/en/latest/install.html)
describes SBY/Yosys/solver dependencies. This pinned combination is the tested
reader boundary; newer upstream releases are not implicitly qualified.

The wake consumer can lose a pulse while leaving sleep. The stream adapter's
output stability requires valid/data to be held during backpressure. Both compare
an activation-excluding premise, unrestricted inputs and supported hold behavior.
Producer guarantees are proved separately with no `$assume` cells. These are
synchronous logical models with an explicit initial one-cycle reset, not physical
reset/CDC checks or qualification of real protocol implementations.

Eighteen tasks cover eight consumer cases and two producer proofs. Retained data
includes source/header/configuration, census, logs, statuses and witnesses. An
independent finite-state reference enumerates these small models to a reachable
fixpoint and checks actual native witness values against the recurrence. This
reference is separate evidence, not a reading of bounded native cover failure.

Modes/depth follow the upstream
[task reference](https://yosyshq.readthedocs.io/projects/sby/en/latest/reference.html).
A bounded cover FAIL means no witness was reached in that attempt. A short BMC
PASS does not establish unbounded safety; the example's short wake BMC stops
before a longer run exposes a counterexample. See upstream
[formal statements](https://yosyshq.readthedocs.io/projects/sby/en/latest/verilog.html)
for assumptions, clocked history and cover semantics.

Saved-data tests work on Windows/Linux without running native configurations.
Synthetic parser fixtures test corrupt/missing/foreign evidence; only the native
example is solver execution. No whole-system composition, general vacuity,
fairness/liveness, signoff or connected-provider benefit is claimed.
