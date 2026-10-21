# Side-effect and access-order review

Use this module when reviewing driver acknowledgements or diagnostic accesses
whose reads/writes can change state. It compares **resolved register semantics
with caller intent and actual accepted bus effects**.

This fits in register/driver integration, acknowledgement review and diagnostic
workflow validation. RTL, firmware and DV owners can use it alongside generated
register documentation and bus traces. A read-modify-write on W1C status can clear
another owner's pending cause; a diagnostic “peek” can consume read-clear evidence.

The activity supplements register generation and native verification. It replaces
manual per-access effect/mask/order reconciliation for the supported profile.
It does not infer driver control flow or prove every firmware/hardware interleaving.

| Activity | Question |
|---|---|
| Default: access effects | Did selected accepted accesses perform only intended clearing/observation, with required byte lanes and prerequisite ordering? |
| [Diagnostic validity](profiles/diagnostic-validity/README.md) | What can a selected read/saved capture establish after destructive reads, reset or loss of access? |
| [Bring-up observation](profiles/bringup-observation/README.md) | Does retained device/image/reset/source-time evidence correspond to a pre-silicon expectation? |

## First use

Python 3.10+ and the standard library suffice. From
`modules/side-effect-access-order`:

```sh
python examples/create_example.py .local/access-rmw --case rmw
python access_review.py review .local/access-rmw/spec.json .local/access-rmw/trace.json .local/access-rmw/policy.json --json-out .local/access-rmw/review.json --markdown-out .local/access-rmw/review.md
```

Expected exit: **1**, `review_required`. The caller intended to acknowledge
cause 0. Reading pending value 3 and writing both ones clears causes 0 **and** 1.
The report identifies unintended cause-1 clearing against the independent allowed
mask.

Compare the direct-mask control:

```sh
python examples/create_example.py .local/access-mask --case direct-mask
python access_review.py review .local/access-mask/spec.json .local/access-mask/trace.json .local/access-mask/policy.json --json-out .local/access-mask/review.json --markdown-out .local/access-mask/review.md
```

Expected exit: **0**, `within_observed_contract`. Write data 1 with the low byte
enabled clears cause 0 while cause 1 remains pending. This is the example's
contract, not blanket permission to clear any real register.

Other cases cover disabled low byte, destructive diagnostic peek and intentional
diagnostic consume. Open Markdown for per-access findings and JSON for exact
cleared masks, bindings and gaps. Example/report paths must be new with existing
report parents.

## Helpers and input records

| Helper | Responsibility |
|---|---|
| `access_review.py review SPEC TRACE POLICY` | Checks accepted access effects against resolved read/write semantics, actual masks/storage samples, independently allowed/required clears, observation-only intent and prerequisite sequence IDs. |
| `access_review.py digest RECORD` | Prints canonical JSON SHA-256 for spec/trace bindings. |
| `rdl_effects.py` | Optional SystemRDL frontend exporting effective properties of explicitly selected registers. It is independent of the trace reviewer. |
| `--json-out` / `--markdown-out` | Saves structured/readable access reports; Markdown is also printed. |

[FORMAT.md](FORMAT.md) defines:

- **Spec:** selected register byte addresses and 8/16/32/64-bit whole-register
  access widths; field locations, read/write rights, effective read/write side
  effects and reset values.
- **Trace:** increasing accepted/error-qualified read/write events, actual bus
  response/operands/byte and bit masks, selected-field storage before/after,
  inactive reset and hardware-quiescence observations.
- **Policy:** independent allowed/required clear masks, observation-only intent,
  prerequisite accepted sequence IDs and source evidence for every selected event.

Storage snapshots must come from field storage, not a second software read that
can itself clear status. Byte-enable bit 0 covers bits 7:0, bit 1 covers 15:8, etc.
Unknown lane mapping remains a gap; reserved bits receive no invented values.

Only accepted, error-free, quiescent accesses with inactive reset support field
effect attribution. Native errors remain findings. A required clear bit already
zero creates no false pending acknowledgement. Observation-only access must not
change selected field storage.

## Optional SystemRDL capture

With **systemrdl-compiler 1.32.2**, installed explicitly into your environment:

```sh
python -m pip install -r requirements-rdl.txt
python -c "from pathlib import Path; Path('.local').mkdir(exist_ok=True)"
python rdl_effects.py --source examples/effects.rdl --register effects.pending --register effects.diagnostic --project example --configuration two-causes --mode functional --address-space-ref register-offsets --basis-ref reviewed-effects-v1 --inputs-complete --out .local/effects-spec.json
```

This uses effective compiler properties, not text matching. Repeat `--source`
for declared source dependencies and `--register` for selected registers.
`--inputs-complete` is your inspected-scope declaration, not discovered closure.
The output must be new.

The reader accepts ordinary non-array, non-alias registers with whole-register
access. The helper supports ordinary assign, write-one-clear and read-clear
effects. Unknown/unsupported semantics remain gaps; use native methods for more
complex protocols.

## Integrate into driver/access review

1. Establish the caller's original acknowledgement/observation objective and
   ownership. Source allowed masks from that intent, not the resulting write data.
2. Obtain resolved register semantics for the consumed configuration, including
   actual side effects and byte-lane convention.
3. Retain accepted bus operations, response data and native storage samples with
   reset/concurrent-update context.
4. Write the per-access policy, bind spec/trace and review. Inspect unintended
   clearing, missing required acknowledgement, destructive observation and order.
5. Correct the original driver/access sequence or sourced intent, then rerun and
   revalidate in the existing native flow.
6. Hand off original request, spec source, trace, policy, report and owner decision.
   Repeat after register, byte-lane, driver or observation-policy changes.

The [native controls](examples/NATIVE.md) use SystemRDL 1.32.2,
PeakRDL-regblock 1.3.1, Verilator 5.020 and Linux C++/Make. Generated RTL supplies
actual storage/bus effects; an independent cause-ID model checks six accesses.
It does not qualify arbitrary generated blocks or concurrent hardware timing.

## AI-first adoption and outcomes

Give a file/tool-enabled assistant [SKILL.md](SKILL.md), actual driver source,
resolved register exports, caller intent and bus trace:

> Establish what each selected access may change. Trace effective side effects,
> ownership, masks and ordering, distinguishing observation from consumption.
> Ask for missing storage/quiescence or lane evidence before recommending an
> acknowledgement sequence.

Use [ONBOARDING.md](../../ONBOARDING.md), module `side-effect-access-order` /
activity `default`. Existing AI/native tools suffice. Optional
[context sources](../../CONTEXT_PORT.md), including DVIT, can add scoped intent,
ownership and applicability relationships; independent use requires none.

| Exit | Meaning |
|---:|---|
| 0 | Within the supplied observed access contract. |
| 1 | Known native error, unintended effect or required mask/order finding. |
| 2 | Incomplete semantics, observations or original intent. |
| 3 | Invalid input/capture or I/O. |

Argument errors use exit 2. Findings retain coexisting gaps. Hashes do not establish
policy truth or global driver safety.

Concurrent updates, split accesses, buffering, locks, shadow-write protocols and
unknown bus-endian mappings need separately qualified methods.

```sh
python -m unittest discover -s tests -v
```

Optional frontend tests skip without SystemRDL; the native guide explains opt-in
simulation variables. Run the two specialized activities' tests separately.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
