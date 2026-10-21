# Records and support

`opentools.bringup-request.v1` records claim/scope, owner, requirements, pre-silicon
expectation and clock-mapping references; the original selected run; source/context/
invocation bindings; target epoch, required prefix, selected read and scalar cause;
condition values with independent sources; reset-relative window, uncertainty and
expected `present` or `absent_in_observed_prefix`. See the
[owned fixture](examples/fixture.py) for the complete structure. Required conditions
include model, device revision/fuses, image, board power, clock, entry/recovery resets
and diagnostic effects. Additional stronger fields remain unknown.

Each run preserves `device.cpp`, `device.cfg`, `firmware.txt`, `device` binary,
`context.json`, `command.json`, `capture-question.json`, `execution.json`, compiler
version and original stdout/stderr. Execution binds consumed sources, context,
command, captured question, binary/native artifact bytes and diagnostic-engine
revision. An optional independent reference is test-oracle evidence, not a selected
consumer read. Source hashes identify bytes, not authority or measurement accuracy.

The qualified example is an owned C++17 scalar sticky-cause device emulator built
with **Ubuntu GCC 13.3.0**. It interprets an explicit bounded command image, not a
firmware ISA. Native model properties, accepted responses, read-clear effects, reset
epochs, host-retained captures, counter ticks and modeled host timestamps are saved.
The reader requires current qualified producer bytes, complete original artifacts
and a completion marker; exit zero alone is insufficient. It executes no saved
binary, source or adapter.

The existing diagnostic engine is unchanged. Its journal starts from the actual
post-entry state and contains one later recovery class, matching its one-effect
boundary. Fault injection stays separate oracle knowledge. Ordered read/save/
recovery receipts establish the selected source read's epoch and origin; the
expectation is not inferred from injection commands or current status.

One monotonic counter and two affine clock anchors are qualified. Source-read
time relative to the actual entry reset is compared in ns. Per-timestamp
uncertainty contributes twice to the relative interval; the entire interval must
fit the requested window. Missing mapping/uncertainty, partial overlap or late
capture is inconclusive. A later record load does not replace capture time.

`SUPPORTED_WITHIN_EMULATION` and `CONTRADICTED_WITHIN_EMULATION` concern only the
bounded question under corresponding conditions. `INAPPLICABLE` preserves known
condition/source differences; `REVIEW_REQUIRED` preserves diagnostic findings;
`INCONCLUSIVE` retains missing premises and unusable or temporally incomparable
evidence. Known differences take precedence while retaining gaps. Raw values,
diagnostic answer, conditions, time interval and original captured question remain
in JSON. Markdown presents the comparison. A new sourced question may reuse saved
evidence; both question identities are retained and a changed-question flag is set.

Limits: sampled quiescent model, one scalar cause, one post-entry recovery class,
host capture retention and bounded monotonic counter. No real instrument or
silicon qualification, physical power/reset verification, ISA execution, calibration
authentication, trace-loss/wrap handling, multi-clock synchronization, all-mode
coverage, root-cause inference or release approval. Use existing native/lab methods
for broader claims and keep their qualification separate.
