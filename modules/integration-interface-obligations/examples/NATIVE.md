# Native connected-handshake recipe

Requirements: Linux, Python 3.11+, pyslang **12.0.0**, Verilator **5.020**, GCC 13.3, Make 4.3.
Run from the module directory:

```sh
python examples/run_native.py native-demo --verilator /path/to/verilator
```

Add `--verilator-root /path/to/share/verilator` for an extracted kit. Choose a new
output directory with an existing parent. The recipe builds only the supplied
owned design. It uses an owned space-free `/tmp` source/runtime alias and retains
native inputs, executables, commands, logs, selected-port reports and event journals.

The client contract treats completion as permission to consume the finished effect.
The worker's receipt merely accepts the request. It commits on its second active
step and completes on its fourth. Cancellation before commit can produce an explicit
discard; after commit it is best effort and cannot promise no effect.

Pulse and level request profiles each run four configurations:

| Case | Expected engineering observation |
|---|---|
| Valid late cancellation | Work already committed completes; client waits for actual completion. |
| Receipt as completion | Client completion is premature despite matching port connections. |
| Cancel request as discard | Client claims discard after irreversible commit. |
| Valid early cancellation | Worker explicitly discards before commit; no committed effect follows. |

An independent event schedule checks all nine observed steps and the native
counter results. All eight cases have matching direct ports; those facts remain
separate from the behavioral findings. The source hierarchy captured by Slang is
the actual hierarchy simulated by Verilator, with the same parameter values.

The profile has one clock, initial state and one outstanding request. Reset recovery,
arbitrary protocols, CDC/RDC, retries and multi-outstanding traffic are unqualified.
The recipe proves no production completeness or general user-benefit claim.

For the integration test set `OPENTOOLS_INTERFACE_NATIVE` to the native executable
and `VERILATOR_ROOT` when needed. Optional `OPENTOOLS_INTERFACE_OUTPUT` retains the
test's eight case directories at a new chosen path. Ordinary AI review can use
existing native artifacts without any simulator installation.
