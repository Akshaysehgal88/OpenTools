# Integration interface obligations

Use this module when connecting blocks or reviewing a bridge/client/worker
interface. It asks whether endpoints agree on **what an event authorizes**:
receipt, irreversible commit, completion, cancellation or acknowledged discard.

This belongs after structural integration and before accepting behavior, then
again after protocol, parameter, clock/reset or cancellation changes. Integration,
RTL and DV owners can use it alongside elaboration/lint and native simulation.
A source called `ack` might mean request receipt while its consumer treats it as
permission to use completed data.

The workflow supplements connectivity checks and scoreboards. It replaces manual
reconciliation of selected endpoint contracts and native evidence. The bundled
port helper establishes structural facts only; it does not implement a protocol
checker.

| Activity | What to review |
|---|---|
| Default: interface obligations | Explicit port facts plus source-backed event meanings, persistence, completion/cancellation and mode/clock/reset assumptions. |
| [Transition obligations](profiles/transition-obligations/README.md) | Typed source/transaction/epoch receipts, transient ownership, accepted grants and actual consumer effects. |

## First use: capture selected connections

Use Python 3.11+ and optional **pyslang 12.0.0**. From
`modules/integration-interface-obligations`:

```sh
python -m pip install -r requirements-native.txt
python -c "from pathlib import Path; Path('.local').mkdir(exist_ok=True)"
python examples/create_inputs.py .local/interface-first-use
python port_capture.py --source examples/handshake.sv --top behavior_top --parameters .local/interface-first-use/parameters.json --selection .local/interface-first-use/selection.json --scope .local/interface-first-use/scope.json --complete-inputs --output .local/interface-first-use/connections.json
```

Expected exit: **0**, `connected_within_profile`, for four selected direct
request/receipt/completion/discard links. The design is elaborated, not executed.
Inspect `connections.json` for each endpoint's native net, direction, width,
expression and source reference. The sibling `connections.evidence` directory
retains diagnostics and the captured record.

The input generator's parent must exist. Output and evidence paths must be new.
Optional dependency installation belongs in your own Python environment.
Existing native tool exports can support the AI review if this frontend is absent.

## What the helper establishes

`port_capture.py` reads selected ordinary input/output ports from Slang's
elaborated hierarchy. It confirms supplied integer top-module overrides and
compares actual direct net/variable references, directions and widths.
It does not pair endpoints by matching declaration names.

Prepare the [format](FORMAT.md) inputs:

| Input | Meaning |
|---|---|
| `--source`, repeated as needed | Consumed RTL source files; `--dependency` adds declared other input files. This is not automatic closure discovery. |
| `--parameters` | Integer top-module overrides; actual elaborated port parameters must confirm them. |
| `--selection` | Nonempty unique link IDs with explicit source/sink `instance.port` paths relative to top. Ordinary deeper instance paths are allowed. |
| `--scope` | Independent project/interface/configuration/mode identities. |
| `--complete-inputs` | Caller declaration after inspecting the source/configuration inventory. File hashes are checked before/after elaboration. |

A direct same net with matching output/input directions and widths can establish
`directly_connected`. Different nets, directions or widths produce findings.
Unsupported expressions remain `needs_evidence`, rather than being guessed
equal or declared electrically broken. Missing requested objects fail capture;
they are never silently dropped.

Slices, inversion, concatenation, interfaces, generate/array paths, wildcard
selection and arbitrary aliases/bridges need another native interpretation.
This reader does not flatten arbitrary connectivity or discover all required links.

## Add the behavioral review

Use [RECORD.md](RECORD.md) to join native facts to the original interface contract:

1. Identify the original producer offer and consumer requirement for each event.
   Establish whether a pulse must be retained and what clock/reset/mode applies.
2. Trace receipt, commit, completion and acknowledged discard in the actual
   bridge/client/worker sources. A cancellation request is not proof that work
   was discarded, especially after irreversible commit.
3. Capture the selected native links in the consumed configuration and retain
   source identity. Confirm native simulation uses the same hierarchy/parameters.
4. Observe the actual event sequence and consumer effect. Keep the native outcome
   separate from the independent interpretation.
5. Review disagreements with endpoint owners, correct the original interface or
   consumer assumption, then rerun the native behavior and structural review.
6. Hand off source-backed obligations, original captures/journals, findings,
   missing evidence and receiving decisions. Repeat after relevant changes.

A structurally favorable report can accompany a behavioral failure. Do not turn
`connected_within_profile` into completion, cancellation or CDC/RDC approval.

## Native behavioral control

The [native recipe](examples/NATIVE.md) uses Linux, Verilator **5.020**, GCC 13.3,
Make 4.3 and the Slang environment above:

```sh
python examples/run_native.py .local/interface-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Choose a new directory with an existing parent. It installs nothing. Pulse and
level request profiles each run four cases through the captured hierarchy:
valid delayed completion, receipt used as completion, cancellation after commit
misreported as discard, and valid early discard. All eight have matching direct
ports. Independent event scheduling checks actual behavior separately.

The owned single-clock, single-outstanding example does not qualify reset
recovery, arbitrary protocols, CDC/RDC, retries or multi-outstanding traffic.
Other company-native artifacts can still be reviewed through the AI workflow.

## AI-first adoption

Give a file/tool-enabled assistant [SKILL.md](SKILL.md),
[AI_USAGE.md](AI_USAGE.md), the original endpoint specifications and consumed sources:

> Find the selected interface and map its actual native connections. For each
> acknowledgement, establish whether it means receipt, commit, completion or
> discard, and what the consumer does with it. Check persistence and cancellation
> across the selected mode/clock/reset boundary. Ask for missing behavioral evidence.

Use [ONBOARDING.md](../../ONBOARDING.md), module
`integration-interface-obligations` / activity `default`. Your current AI and
engineering tools suffice; optional DVIT/context evidence can add scoped
interface intent, ownership and dependent-consumer relationships. It is not
required or automatically installed.

## Capture outcome

| Exit | Meaning |
|---:|---|
| 0 | Selected direct connections established within the native profile. |
| 1 | Known net, direction or width finding. |
| 2 | Incomplete input basis or unsupported direct interpretation; findings retain gaps. |
| 3 | Invalid selection, native capture or I/O. |

Argument errors use exit 2. Scope names, completeness and source authority are
caller declarations; hashes do not establish semantic compatibility.

```sh
python -m unittest discover -s tests -v
```

The native guide explains `OPENTOOLS_INTERFACE_NATIVE` and related opt-in
variables. Run the transition activity's tests separately; it needs no Slang
dependency.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
