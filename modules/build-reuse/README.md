# Build reuse

Use this module between resolving a simulation/build request and launching a new
compile or elaboration. It reviews whether an already built artifact can satisfy
the **current** request while retaining the required checking and instrumentation.
Simulation infrastructure, DV and build owners can use it without replacing their
existing runner or cache.

The gap is dependency and phase meaning. Two runs can have different seeds and
share a binary; two apparently identical commands can consume different generated
files, include resolutions, models or toolchains. A binary hash alone answers
neither question.

## Workflow fit

| Existing stage | What this review supplies |
|---|---|
| Compile/elaboration planning | Known build invalidators, runtime-only differences and missing eligibility evidence |
| Existing artifact cache | A source-bound review input before the cache's own selection, verification and publication rules |
| Instrumented regression setup | Check that requested trace, coverage and assertion capabilities belong to the captured build basis |
| Efficiency investigation | An explanation of avoidable or required rebuilds that can be compared with measured costs |

The helper can replace a manual comparison of fully captured build requests and
artifact hashes. It supplements the native dependency resolver, compiler and cache.
It does not launch builds, choose/publish/evict cache entries, coordinate concurrent
users or establish reuse of a simulation result.

## Use your existing AI agent

Start with the [workflow](SKILL.md), old build capture and newly resolved request:

> Investigate whether this request can use our existing compiled artifact. Inspect
> the runner's actual option consumers and dependency resolution. Preserve required
> trace, coverage and assertion capabilities. Distinguish build artifact, runtime
> invocation and result identity. Identify original consumed-byte evidence,
> unresolved dependencies and exact rebuild invalidators before proposing reuse.

The agent should first inspect existing native reuse facilities and capture.
It can use the optional helper where the records fit, or validate another company
method. For a reusable project setup, use [onboarding](../../ONBOARDING.md) with
module `build-reuse`, workflow `default`. [AI_USAGE.md](AI_USAGE.md) gives additional
review guidance. No extra model account or DVIT connection is required.

## First run: a runtime-only seed change

Saved-record comparison needs Python 3.10+ and its standard library. From the
clone root, enter `modules/build-reuse`; an installed package has the same folder.

```sh
cd modules/build-reuse
python -c "from pathlib import Path; Path('.local').mkdir(exist_ok=True)"
python examples/create_example.py .local/reuse-seed
python build_reuse.py compare .local/reuse-seed/baseline.json .local/reuse-seed/requested.json .local/reuse-seed/profile.json --artifact-root .local/reuse-seed --json-out .local/reuse-seed/comparison.json --markdown-out .local/reuse-seed/comparison.md
```

Expected exit: **0**, `eligible_within_declared_scope`. The supplied synthetic
profile has evidence that seed is consumed at runtime; seeds 17 and 29 differ
without changing the build basis. The baseline artifact's actual bytes are
verified. The artifact is plain demonstration data, not an executable.

The requested run still needs its own execution and result. An eligible binary
does not make the previous seed's test outcome applicable.

Exercise artifact verification with another new directory:

```sh
python examples/create_example.py .local/reuse-corrupt
python -c "from pathlib import Path; Path('.local/reuse-corrupt/sim.bin').write_bytes(b'changed')"
python build_reuse.py compare .local/reuse-corrupt/baseline.json .local/reuse-corrupt/requested.json .local/reuse-corrupt/profile.json --artifact-root .local/reuse-corrupt --json-out .local/reuse-corrupt/comparison.json --markdown-out .local/reuse-corrupt/comparison.md
```

Expected exit: **1**, `artifact_unavailable`. Matching declared build inputs do
not repair the mismatched retained artifact. Generators and report paths must be
new; the comparator never overwrites an input, report or declared artifact.

## Helper: `build_reuse.py`

| Operation / feature | What it does |
|---|---|
| `compare BASELINE REQUESTED PROFILE` | Compare build basis using an evidenced option-phase profile and preserve all unknowns |
| Build/runtime classification | Include build options in the key; report evidenced runtime changes separately; unknown phases block eligibility |
| Ordered dependency comparison | Retain command/argument, dependency and toolchain order rather than treating them as unordered sets |
| `--artifact-root DIR` | Verify every declared baseline artifact under an explicit root; missing/corrupt files are unavailable |
| `--json-out` / `--markdown-out` | Save exact differences, unknowns, build/input digests and per-file artifact observations |
| `inspect-verilator MANIFEST` | Read a supported saved Verilator inventory without launching Verilator or reading its listed dependencies |

The build-key digest is an aid to the comparison, not independent authorization:
unknown closure, unsupported phase rules or unavailable artifacts can still block
reuse even when keys match.

## Inputs and prerequisites for a real decision

| Input | What the owner must supply |
|---|---|
| Baseline build record | Original consumed source/configuration/toolchain capture, completed build and immutable artifact set |
| Requested build record | Freshly resolved request, including relevant search namespaces, generated inputs and required capabilities |
| Phase profile | Which exact options this runner consumes during build, runtime or an unknown phase, with source evidence |
| Artifact root | The existing baseline files to verify; compilation is not performed by the comparator |

Records use `opentools.build-record.v1`; the profile is
`opentools.build-profile.v1`. Both records bind the reviewed profile's canonical
digest. Build basis includes commands/argv, ordered dependencies and hashes,
configuration, relevant environment, toolchain/ABI and named options.
[FORMAT.md](FORMAT.md) defines the complete schemas and fingerprint algorithm.

Capture recursive filelists, generated inputs/generators, include and library
search order, linked DPI/models and instrumentation settings. A newly shadowing
include can change resolution without changing any previously listed file.
Original consumed bytes need original capture; hashing today's files cannot
reconstruct an old build's inputs.

Seed, test, firmware and parameter options have the phase their actual consumer
implements. Do not assume an option is runtime-only from its name. Null,
unclassified or unsupported values remain unresolved; explicit completeness
declarations need their own evidence.

## Integrate with your runner or cache

1. Identify the requested binary and required outputs/checks. Measure compile,
   queue and simulation work separately before deciding where reuse helps.
2. Reuse the runner's original capture or immutable build snapshot. Resolve the
   new request with the native build system and review dependency closure.
3. Establish the phase profile from actual scripts/native option semantics.
   Preserve trace, coverage, assertions, linked models and toolchain requirements.
4. Compare the records with the live baseline artifact root. Return exact rebuild
   causes, runtime differences, unknowns and artifact condition to the runner owner.
5. Validate proposed reuse with a fresh checked build of the same request and
   compare the required observable outputs. Keep run and result identities distinct.
6. Let the existing cache apply its own atomic publication, leases, concurrent-use
   and retention policies. This helper performs none of those cache actions.

A useful handoff states which artifact is eligible, the evidence supporting that
scope, which requests remain different, required checking and the invalidation
conditions. Revalidate on source/resolution, generated inputs, toolchain/ABI,
build flags, profile rules or artifact changes.

## Saved Verilator inventory

For a retained Verilator **5.020** `__verFiles.dat`:

```sh
python build_reuse.py inspect-verilator existing/obj_dir/Vtop__verFiles.dat --producer-version 5.020 --output native-inventory.json
```

The reader preserves the native flattened command, source/target inventory and
stat fields. The caller supplies the producer version because the file does not
contain it. It does **not** reconstruct argv, original content hashes or complete
C++/link/toolchain dependencies. The inventory is supporting evidence, not a
complete normalized build record or cache key. [FORMAT.md](FORMAT.md) lists the
accepted grammar and rejected cases.

## Results and validation

| Exit | Meaning / next action |
|---|---|
| `0` | Eligible within captured scope; apply the existing runner/cache policy |
| `1` | Known build difference or unavailable/corrupt artifact; inspect the retained cause |
| `2` | Unknown eligibility; resolve missing phase, dependency, capture or artifact evidence |
| `3` | Invalid input or I/O failure; repair the record/path before using the report |

Known build differences take precedence while preserving unknowns. Result reuse
is explicitly `not_established`. No status claims verification equivalence or a
production speedup. Measure comparable tasks, including collection/report overhead,
before making an efficiency claim.

Run `python -m unittest discover -s tests -v` for local checks. The optional Linux
native inventory test uses `OPENTOOLS_REUSE_NATIVE` pointing to Verilator 5.020,
`VERILATOR_ROOT`, GCC 13.3 and Make 4.3. See [record.template.json](record.template.json)
and [example.json](example.json) for review records.

[DVIT](../../DVIT.md) can retain the dependency and intent relationships used by
later reuse decisions. Standalone/company evidence remains sufficient when it
answers the task; [context consumption](../../CONTEXT_PORT.md) is optional.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
