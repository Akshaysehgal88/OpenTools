# Event delivery and acknowledgement review

Follow one event through source assertion, interrupt retention/delivery/service,
source clearing, and the separate wake route. Use the [AI workflow](SKILL.md) with
native traces, route configuration and handler/sleep-sequence source. Your current
AI host and engineering tools are sufficient; DVIT is optional.

The optional Python 3.10+ helper reviews an isolated event in a bounded observation
window. It checks required stages, declared ordering and availability prerequisites.
It does not emulate an interrupt controller or infer stage meaning from names.

```sh
python examples/create_example.py /tmp/event-example --case clear-before-wake
python event_review.py review /tmp/event-example/topology.json /tmp/event-example/journal.json /tmp/event-example/policy.json
```

The example observes service and source clearing before any wake capture.
`retain-before-service` is the valid control. Other examples cover a pulse missed
by a stopped interrupt gateway, a held-source control, wake-only intent and service
without source clearing. See [native controls](examples/NATIVE.md).

Use new paths with `--json-out` and `--markdown-out` to retain reports. Exit codes:
0 within the supplied observed contract, 1 review required, 2 incomplete,
3 invalid input or I/O error. Findings retain accompanying gaps; inputs are never
overwritten. A stage absent from this window is not proof it can never occur.

## Supply the route and obligation

Identify source persistence, exact consumers and separate interrupt/wake routes.
Supply actual observations and independently sourced required stages/order;
[FORMAT.md](FORMAT.md) defines the records. A successful wake request does not
establish interrupt delivery, and service acknowledgement does not establish source
clearing. Some events intentionally require only wake; retain that intent.

The owned example uses a sampled-high-once gateway, sticky wake capture and digital
clock gating. It is not a reference PLIC, CDC circuit or production clock gate.
No native controller/firmware parser is provided. Use existing native exports or
reviewed normalization, keeping the original artifact and sampling basis.

## Boundaries

This profile handles one isolated cause and settled stage observations. Pending
work before the prefix, overlapping causes, merging, priority/affinity changes,
virtualization, pulse width, CDC and unbounded delivery need their native methods.
It does not infer that a sleep entry must complete: an applicable abort/fall-through
path may change the obligation and must be reviewed separately.

Inspect raw evidence even after a favorable report. Wrong stage aliases or weaker
caller policy can manufacture agreement. Install using the repository's
project-local installer. Optional [context sources](../../CONTEXT_PORT.md) may
supply scoped ownership, route applicability and acknowledgement intent; nothing
installs or downloads DVIT.

Concrete controller/sequence references:
[OpenTitan PLIC](https://opentitan.org/book/hw/top_earlgrey/ip_autogen/rv_plic/doc/theory_of_operation.html),
[OpenTitan power manager](https://opentitan.org/book/hw/top_earlgrey/ip_autogen/pwrmgr/doc/theory_of_operation.html).
Their implementation rules are design-specific.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
