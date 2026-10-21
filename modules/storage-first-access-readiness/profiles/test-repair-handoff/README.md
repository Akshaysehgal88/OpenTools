# Memory test/repair handoff

Use this activity when memory test/repair returns ownership to functional
consumers. It reviews **physical test coverage, loaded repair mapping,
initialization in the current mapping epoch and first functional access** as
one handoff lifecycle.

This fits between memory-test completion, repair loading and functional release.
DFT/memory-test, wrapper, initializer and receiving owners can use it alongside
their native test/repair reports. A passing test can cover the wrong physical rows;
raw test writes do not establish functional data/ECC initialization.

The workflow supplements MBIST/repair and the parent
[first-access activity](../../README.md). It replaces manual test-to-functional
mapping/ownership reconciliation for the selected profile. It does not implement
MBIST, certify fault coverage or approve memory signoff.

## First use

Saved-data review needs Python 3.10+ and the standard library. Run from
`modules/storage-first-access-readiness/profiles/test-repair-handoff`. Use a
complete retained collection at `.local/repair-native`, or generate one on Linux
with existing **Verilator 5.020**, C++ and Make:

```sh
python examples/run_native.py .local/repair-native --verilator /path/to/verilator_bin --verilator-root /path/to/share/verilator
```

Replace native tool/runtime paths. The recipe installs nothing. One build per
four/eight-word geometry serves twelve fixed plans. Sources and plans are frozen
before execution; the output directory must be new.

Capture and review the good handoff:

```sh
python handoff.py capture .local/repair-native/word-bank-good/run .local/repair-native/word-bank-good/context.json --output .local/repair-native/word-bank-good/recaptured.json
python handoff.py review .local/repair-native/word-bank-good/run .local/repair-native/word-bank-good/context.json .local/repair-native/word-bank-good/receiving-policy.json --output .local/repair-native/word-bank-good/new-review.json
```

Expected review exit: **0**, `aligned`. Inspect the JSON for original native
PASS/FAIL, admitted initialization, handoff/access observations, findings,
gaps, owner and recheck triggers.

Compare mismatched mapping:

```sh
python handoff.py review .local/repair-native/word-bank-mapping-mismatch/run .local/repair-native/word-bank-mapping-mismatch/context.json .local/repair-native/word-bank-mapping-mismatch/receiving-policy.json --output .local/repair-native/word-bank-mapping-mismatch/new-review.json
```

Expected exit: **1**, `findings`. Other controls cover premature release,
stale ECC, late repair loading, reversed byte lanes, test-owner leakage, invalid
payload, disabled ECC and a test passing on wrong physical rows. No-repair loading
and denied early release are positive controls.

Outputs must be new. Review always recaptures original files; it does not consume
a trusted cached receipt. Capture exit 0 means valid intake, not receiving acceptance.
Saved commands/binaries are never executed.

## Helper and receiving contract

| Operation | Contribution |
|---|---|
| `handoff.py capture NATIVE_DIRECTORY CONTEXT` | Reads original XML/source/binary/plan/command and transaction evidence; retains actual geometry, role binding, state continuity and native result. |
| `handoff.py review NATIVE_DIRECTORY CONTEXT POLICY` | Checks original identities, independent required test/init/access populations and ownership/release against current mapping/ECC state. |
| `--output FILE` | Saves JSON to a new path; omit it to print JSON. |

[FORMAT.md](FORMAT.md) describes the exact artifacts and
`opentools.repair-context.v1` / `opentools.repair-policy.v1`.

The context identifies original run/scope/design/configuration/memory/init epoch/
transition, selected instance/type/array, explicit roles, reset polarity and ECC
profile with source bases. Native XML supplies actual specialized definition,
direct port bindings, widths, physical array and logical-readiness geometry.

The independent receiving policy retains accepted source/plan/command/binary
identities, logical/physical words, data/codeword bits, byte lanes/base/order,
repair requirement/payload, required physical test rows, required initialized
words/data, release event and accepted functional reads/expected data.
Do not derive those populations from whichever coverage was exported.

The owned repair ABI is a single optional spare-row map, not a foundry fuse format.
Every accepted load advances its epoch, even when the valid bit disables remapping.
Raw test writes grant no initialization credit. Only admitted full data/ECC
initialization under the **current** mapping supplies release credit.
Full functional writes can initialize without an old read; partial writes read/
merge old data, while zero masks do neither.

## Integrate into the memory lifecycle

1. Source the original receiving geometry, required physical test population,
   repair policy and first-consumer obligations.
2. Retain actual native test/repair/wrapper artifacts, decoded mapping and role
   correspondence. Check logical and physical address views independently.
3. Trace loaded repair payload/epoch, ECC enable and initialization coverage with
   the test, repair and initializer owners.
4. Review functional release and first accesses, preserving original native verdict
   separately from the receiving contract. Keep omitted required banks/words/
   consumers open rather than shrinking intent.
5. Correct the original test target, repair loading, initialization, byte mapping
   or ownership path; recollect and revalidate.
6. Hand off original requirements, native artifacts, report, owner corrections and
   recheck triggers. Repeat after mapping, payload, ECC or consumer changes.

Current helper access obligations are reads; preserve other required consumer
behavior in the AI/native workflow instead of claiming it was checked.
[review-record.json](review-record.json) captures the broader handoff.

## AI-first adoption and outcomes

Give a file/tool-enabled assistant [AI_USAGE.md](AI_USAGE.md), original receiving
requirements and native memory-test/repair/wrapper evidence:

> Reconcile the actual test and functional address views, repair epoch and byte
> lanes. Establish who owns memory, when ECC/data become initialized and what
> release authorizes. Preserve independent required physical rows and functional
> accesses; ask for missing mapping or owner evidence.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module
`storage-first-access-readiness` / activity `test-repair-handoff`. Existing AI
and company tools suffice. Optional DVIT intent/dependency context can connect
repair/mapping changes to receiving obligations; independent use requires none.

| Review exit | Meaning |
|---:|---|
| 0 | Aligned within the selected supplied receiving contract. |
| 1 | Known geometry/mapping/ECC/ownership/release/access finding. |
| 2 | Incomplete or quarantined source/scope attribution. |
| 3 | Invalid/changed native package or I/O. |

Argument errors use exit 2. Known findings retain gaps and original native result.
Hashes establish supplied identity, not trusted execution or production authority.

The reader pins one owned 32/39 SECDED command-port model, one optional spare map
and one transition. Independent physical-memory/ownership/byte-vector replay uses
the parent Python oracle; native encoding/decoding is separate. Other macros,
fuse layouts, repair populations, test algorithms, reset retention and physical
X/power/timing need their own qualification.

Set `OPENTOOLS_REPAIR_NATIVE` to the retained collection and run:

```sh
python -m unittest discover -s tests -v
```

Saved-data review needs no simulator. The same workflow can use broader native
methods while keeping unsupported claims open.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
