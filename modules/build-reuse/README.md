# Build reuse

Review whether a compiled/elaborated artifact matches a newly resolved request.
The helper compares build inputs, reports runtime changes separately and checks
artifact bytes. It leaves compilation and cache operations to your existing runner.
Use [SKILL.md](SKILL.md) for the AI workflow and [AI_USAGE.md](AI_USAGE.md) for review
inputs and outputs.

## Quick start

Python 3.10+; standard library only. From this module directory:

```sh
python examples/create_example.py demo
python build_reuse.py compare demo/baseline.json demo/requested.json demo/profile.json --artifact-root demo --json-out demo/comparison.json --markdown-out demo/comparison.md
```

Expected exit: **0**. The synthetic profile classifies seeds 17 and 29 as runtime
inputs while retaining the same build basis. Its artifact is plain demonstration
data, not an executable. Use a new directory.

## Capture the build basis

Retain resolved source/filelist order, include search order, defines, parameters,
generated inputs, linked libraries, toolchain and instrumentation. Classify each
option by the phase where the actual flow consumes it. A Git revision or command
string alone may omit generated/external inputs.

The helper needs a bound phase profile, explicit completeness declarations and
live artifacts under `--artifact-root`. Keep run IDs and result locations distinct.
A hash verifies captured bytes; it does not prove dependency completeness.
Trace, coverage and assertion options may change the build even when disabled
at runtime. See [FORMAT.md](FORMAT.md).

## Verilator inventory

```sh
python build_reuse.py inspect-verilator existing/obj_dir/Vtop__verFiles.dat --producer-version 5.020 --output native-inventory.json
```

The Verilator **5.020** reader retains native command text, inventories and stat
fields. It does not reconstruct argv, establish original consumed bytes or collect
complete C++/link/toolchain dependencies. The version is caller-declared because
the file does not contain it. This inventory alone cannot establish a build key.

Dependency files can omit system headers or new earlier include candidates.
Post-hoc hashes cannot establish old consumed bytes. Use original capture plus a
fresh resolution, then validate proposed reuse against a fresh checked build.
Cache publication, locking, eviction and test-result reuse are outside scope.

## Status and tests

`0` eligible within supplied scope; `1` build difference or unavailable/corrupt
artifact; `2` unknown eligibility; `3` invalid input/I/O. Known differences take
precedence while retaining unknowns. No status performs a cache action.

```sh
python -m unittest discover -s tests -v
```

Core tests run on Windows/Linux. Enable the native inventory test on Linux with
`OPENTOOLS_REUSE_NATIVE` pointing to Verilator 5.020 and `VERILATOR_ROOT` set to its
runtime directory. The native test environment uses GCC 13.3 and Make 4.3.
See the [manual record](record.template.json) and [example](example.json).

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
