# Event delivery and acknowledgement review

Use this module to follow one event from assertion through interrupt
retention/delivery/service, source clearing and the **separate wake route**.
It checks required occurrences, order and availability against the original
event obligation.

This fits in interrupt/wake integration, handler/sleep-sequence review and
revalidation after route, clock, mask or clear-policy changes. RTL, firmware,
low-power and DV owners can use it alongside interrupt-controller diagnostics
and native traces. It replaces manual reconstruction of one event's selected
route history; it does not emulate the controller or infer semantics from names.

A serviced interrupt does not establish source clearing. A successful wake request
does not establish interrupt delivery. Some events intentionally require only
wake; the review preserves that intent rather than imposing an interrupt goal.

## First use

Python 3.10+ and the standard library suffice. From
`modules/event-delivery-acknowledgement`:

```sh
python examples/create_example.py .local/event-clear --case clear-before-wake
python event_review.py review .local/event-clear/topology.json .local/event-clear/journal.json .local/event-clear/policy.json --json-out .local/event-clear/review.json --markdown-out .local/event-clear/review.md
```

Expected exit: **1**, `review_required`. The reference example services the
interrupt and clears the source before the late wake route captures it. The
independent sleep-window contract requires wake retention before source clearing.
The report identifies the absent wake stages and ordering problem.

Compare the retention control:

```sh
python examples/create_example.py .local/event-retained --case retain-before-service
python event_review.py review .local/event-retained/topology.json .local/event-retained/journal.json .local/event-retained/policy.json --json-out .local/event-retained/review.json --markdown-out .local/event-retained/review.md
```

Expected exit: **0**, `within_observed_event_contract`. Open Markdown for the
stage disposition and JSON for original references, observations, findings and
gaps. Example directories and report paths must be new; output parents must exist.

Other cases distinguish a pulse missed by a stopped interrupt gateway, a held
source surviving until service, wake-only intent and service without source clear.
These are source-defined reference fixtures, not execution of a production
controller or handler.

## Helper features and records

| Operation | Responsibility |
|---|---|
| `event_review.py review TOPOLOGY JOURNAL POLICY` | Checks original scope/bindings, clean prefix and event isolation; reviews required stages, their declared order and availability prerequisites. |
| `event_review.py digest RECORD` | Prints canonical JSON SHA-256 for topology/journal bindings. |
| `--json-out` / `--markdown-out` | Saves a structured handoff and readable report; Markdown is also printed. |

[FORMAT.md](FORMAT.md) defines the three inputs:

- **Topology:** source owner and persistence, plus independently named interrupt
  and wake routes/consumers. Physical sharing does not merge their logical roles.
- **Journal:** one bounded, isolated event window with increasing sequence and
  nondecreasing ticks. It retains occurrence markers for assertion, interrupt
  retention/delivery/service, source clear, wake retention/request; route/control
  availability; and separate source/pending levels.
- **Policy:** the independently required stages, ordering relationships and
  controls needed when a stage occurs, with source evidence and exact window/input
  bindings.

Stage fields are **occurrences**, not persistent state. A wake latch captures
once while pending can remain high. Native counter deltas can provide markers
only when reset, width and collection coverage are established. Clock evidence
must reflect actual sampling edges, not just a requested clock-enable command.

The first sample must establish a clean prefix with no selected cause/pending
state already active. More than one assertion needs a broader attribution method.
Missing observations stay null; they cannot be borrowed from another event.
The helper does no time conversion or subcycle analysis: same/earlier settled
samples satisfy a declared order.

## Integrate with interrupt and low-power flows

1. Identify the original event requirement and exact consumers. Decide whether
   interrupt service, wake, clearing or a valid sleep-abort path is required.
2. Inspect source persistence, handler/clear semantics, masks, routing and
   functional/always-on clock availability in the selected mode.
3. Retain native observations covering a clean prefix through the required
   terminal activity. Normalize actual occurrences and levels separately.
4. Build the required-stage/order policy from the source contract, not the
   observed successful route. Bind it to the original topology and journal.
5. Review absent stages and order/availability findings with the source, route,
   handler or sleep-sequence owner. An absent stage in a finite window is not a
   claim it can never occur.
6. Correct the original routing/sequence, instrumentation or sourced obligation;
   rerun and revalidate. Preserve original intent, native artifacts, normalized
   records, reports and owner decisions together.

The [native controls](examples/NATIVE.md) use Linux, Verilator 5.020 and a C++/Make
toolchain. A sampled-high-once gateway, sticky wake latch and digital gating
exercise six cases; independent state scheduling and counter expectations check
72 native rows. The example is not a PLIC, CDC or integrated clock-gate reference.

## AI-first adoption

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), handler/sleep-sequence
source, route configuration and original observations:

> Trace this isolated cause through interrupt service, source clear and wake
> independently. Establish persistence, selected consumers and actual clock/route
> availability. Check the original sleep-entry or abort obligation before
> interpreting missing wake. Ask for ambiguous stage mappings or incomplete prefix.

Use [ONBOARDING.md](../../ONBOARDING.md), module
`event-delivery-acknowledgement` / activity `default`. Your existing AI host can
review company-native artifacts or adapt a validated exporter. Optional
[context sources](../../CONTEXT_PORT.md), including DVIT, can connect scoped
route ownership, applicability and acknowledgement intent without being required.

## Outcomes and limits

| Exit | Meaning |
|---:|---|
| 0 | Within the supplied observed event contract. |
| 1 | Known missing required occurrence, order or availability finding. |
| 2 | Incomplete window, isolation, source or other required evidence. |
| 3 | Invalid input or I/O. |

Argument errors use exit 2. Known findings retain coexisting gaps. Wrong stage
aliases or a weaker caller policy can manufacture agreement, so inspect source
and raw evidence even after a favorable result.

This profile covers one isolated cause and settled observations. Overlapping
causes, preexisting pending work, merging, priorities/affinity, virtualization,
pulse width, CDC, physical delivery and unbounded liveness require native methods
with their own qualification. It grants no service authority or design signoff.

```sh
python -m unittest discover -s tests -v
```

The native guide explains opt-in tool variables. Ordinary saved-data review
requires no simulator.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
