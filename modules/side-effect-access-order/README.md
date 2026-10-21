# Side-effect and access-order review

Review driver acknowledgements and diagnostic accesses against resolved register
semantics and caller intent. Use the [AI workflow](SKILL.md) with existing source,
register exports and bus traces. No AI service, simulator or DVIT installation is
required for the workflow.

For evidence capture through reset or destructive reads, use the
[diagnostic-validity profile](profiles/diagnostic-validity/README.md). It reviews
the selected consumer observation, saved-read provenance and recovery effects;
a later zero does not establish historical fault absence.

The optional Python 3.10+ helper checks selected, accepted accesses with sampled
field storage, inactive reset and no concurrent hardware update. It supports
ordinary read/write, write-one-clear and read-clear fields, explicit byte lanes,
per-access clearing intent and prerequisite sequence IDs.

```sh
python examples/create_example.py /tmp/access-example --case rmw
python access_review.py review /tmp/access-example/spec.json /tmp/access-example/trace.json /tmp/access-example/policy.json
```

The example reports an unintended clear of cause 1: the caller requested cause 0,
but a read-modify-write wrote both pending ones. `--case direct-mask` is the valid
control. `diagnostic-peek` demonstrates a destructive observation read;
`diagnostic-consume` declares intentional consumption. `disabled-low-byte` leaves
the requested acknowledgement pending.

Use new paths with `--json-out` and `--markdown-out` to retain reports. Exit codes:
0 within the supplied observed contract, 1 review required, 2 incomplete, 3 invalid
input or I/O error. Findings retain accompanying gaps. No output overwrites inputs.

## Native sources

An optional reader uses effective properties from SystemRDL compiler 1.32.2:

```sh
python -m pip install -r requirements-rdl.txt
python rdl_effects.py --source examples/effects.rdl --register effects.pending --register effects.diagnostic --project example --configuration two-causes --mode functional --address-space-ref register-offsets --basis-ref reviewed-effects-v1 --inputs-complete --out /tmp/effects-spec.json
```

Supply all source dependencies explicitly. `--inputs-complete` is your declaration
for the selected scope, not a compiler attestation. Keep native diagnostics and
the actual configuration. Review [FORMAT.md](FORMAT.md) before supplying traces
or intent. [Native controls](examples/NATIVE.md) exercise PeakRDL-generated RTL.

## Boundaries

The reader selects ordinary non-array, non-alias registers with whole-register
access widths. The helper does not infer driver control flow, bus endianness,
ownership, concurrent updates, split accesses, buffering, locks or shadow-write
protocols. Unsupported or missing field semantics remain gaps. Use native/company
methods outside this boundary and retain their applicability separately.

A matching hash cannot establish that a policy represents the caller's intent.
Inspect source even when the helper agrees. Sampled accesses do not prove all
firmware paths or every possible hardware interleaving.

Install this module using the repository's project-local installer. Optional
[context sources](../../CONTEXT_PORT.md) can supply scoped intent and applicability;
DVIT remains separately configured and optional. Nothing installs or downloads it.

## Bring-up observation comparison

Use the [bring-up observation profile](profiles/bringup-observation/README.md)
before comparing retained diagnostic evidence with a pre-silicon expectation.
It composes the existing receipt/epoch review with device/image/reset conditions
and source-read time correspondence. Raw values and comparison validity remain
separate; the native example qualifies owned emulation only.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
