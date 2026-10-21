# Reset sequencing and state continuity

Review what a selected reset clears, what survives, and which prerequisites must
hold before restart. Use the [AI workflow](SKILL.md) with native reset/state
exports, restart source and a transition journal. Your current AI host and tools
are sufficient; DVIT is optional.

The optional Python 3.10+ helper produces a state-by-owner table and checks
clearing, preservation, observed reset application, release prerequisites and
pending work that survives cleared consumer context. Explicitly permitted retained
event replay is a separate case. No external Python packages are required.

```sh
python examples/create_example.py /tmp/reset-example --case warm-partial
python reset_review.py review /tmp/reset-example/inventory.json /tmp/reset-example/journal.json /tmp/reset-example/policy.json
```

The partial-reset example leaves a producer pending while its consumer loses
context; a post-release orphan is observed. `warm-reset-both` and `warm-drain`
are valid controls. `watchdog-fresh-start` rejects old work; `watchdog-replay`
explicitly permits and observes retained-event replay. These are profiles of the
same review activity, not separate IP-specific tools.

Use new paths with `--json-out` and `--markdown-out` to retain reports. Exit codes:
0 within the supplied sampled reset contract, 1 review required, 2 incomplete,
3 invalid input or I/O error. Findings retain accompanying gaps. Inputs are never
overwritten.

## Inputs and limits

Supply exact reset event/mode, selected state owners and reset domains, actual
samples, clearing/retention intent and replay authority. [FORMAT.md](FORMAT.md)
defines the records. [Native controls](examples/NATIVE.md) exercise an owned RTL
channel and an independent reset/delivery reference.

The helper reviews four sampled phases, scalar state and explicit pending/context
relationships. It does not extract arbitrary reset trees, infer transaction
ownership, validate synchronizers or prove exhaustive restart behavior. Reset
deassertion alone does not establish software initialization. Analog
recovery/removal and RDC signoff require their native methods.

Inspect source even after a favorable report. Wrong state normalization or a
policy that permits an unowned completion can manufacture agreement. A warm or
local reset is not interchangeable with power-on reset merely because both
restart software.

Install through the repository's project-local installer. Optional
[context sources](../../CONTEXT_PORT.md) may supply scoped state ownership,
retention intent and dependent restart assumptions. Nothing installs or downloads
DVIT. [OpenTitan reset-manager operation](https://opentitan.org/book/hw/top_earlgrey/ip_autogen/rstmgr/doc/theory_of_operation.html)
provides a concrete example of event-dependent reset effects; its reset rules are
not universal assumptions of this tool.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
