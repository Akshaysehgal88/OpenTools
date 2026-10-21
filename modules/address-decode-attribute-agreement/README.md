# Address decode and attribute agreement

Compare resolved hardware and software byte maps by initiator, route, permission
and memory attribute. Identify address overlaps, required-decode gaps and aliases
that lack a matching scoped policy. Python 3.10+; standard library only.

Use [SKILL.md](SKILL.md) with your existing AI agent to establish what each view
means and inspect source/native evidence. See [AI_USAGE.md](AI_USAGE.md).

## Quick start

From this module directory:

```sh
python examples/create_example.py demo
python address_review.py compare demo/hardware.json demo/software.json demo/policy.json --json-out demo/review.json --markdown-out demo/review.md
```

Expected exit: **1**. The synthetic hardware view allows device writes while the
software effective map forbids them. The processor's separate alias remains
allowed under its own policy. Use new directories and report paths.

Other example cases: `--case valid`, `overlap`, `hole` and `paired`. The paired
case moves a window in both views and updates its required range.

## Native evidence

The [native recipe](examples/NATIVE.md) generates an owned two-initiator RTL decoder
and compiles/reads an owned C map table. It runs both initiators through selected
bytes/boundaries, operations and security inputs, then compares actual RTL results
with an independent expanded-byte reference and the native software export.

```sh
python examples/run_native.py native-demo --verilator /path/to/verilator
```

Qualified native environment: Linux, Verilator **5.020**, GCC **13.3.0** targeting
`x86_64-linux-gnu`, Make 4.3. Add `--verilator-root` for an extracted kit.
No tool is installed automatically. This is an owned generator/table profile,
not a generic RTL, C, device-tree or IOMMU extractor.

## Interpretation and status

`0` agrees within declared scope; `1` view/overlap/alias/required-range review;
`2` incomplete, stale, foreign or unsupported evidence; `3` invalid input/I/O.
Known findings retain other gaps. Argument errors use 2. Outputs never replace files.

The policy binds both exact views, effective-map meaning, explicit correspondence
and required ranges. Full-span target aliases require an exact initiator/pair rule
and explicit allowed attribute differences. A rule cannot hide address overlap.
Unknown fields stay unknown. See [FORMAT.md](FORMAT.md).

Agreement does not prove complete translations, decode priority, interconnect
security or coherency. Native execution validates only the owned query population.

```sh
python -m unittest discover -s tests -v
```

Enable native tests with `OPENTOOLS_ADDRESS_NATIVE`; see the recipe. The workflow
works with ordinary exports through the [project-local installer](../../INSTALL.md).
DVIT and [context sources](../../CONTEXT_PORT.md) are optional.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
