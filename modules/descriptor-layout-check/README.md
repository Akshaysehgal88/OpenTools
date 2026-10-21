# Descriptor layout check

For generated parameter values, units and defaults, use the
[configuration-consistency profile](profiles/configuration-consistency/README.md).
It reuses the native frontends with opt-in resolved parameter/constant capture.

Compare hardware and firmware representations of a shared binary record. The
portable comparator checks field bit addresses, widths, signedness, encodings,
size and alignment, and writes JSON and Markdown. Use [SKILL.md](SKILL.md) for the
AI workflow and [AI_USAGE.md](AI_USAGE.md) for review guidance.

## Quick start

The native example requires Linux, Python 3.11+, pyslang **12.0.0** and GCC
**13.3.0 targeting x86_64-linux-gnu**. Hardware capture also runs on Windows.
From the repository root:

```sh
python -m pip install -r modules/descriptor-layout-check/requirements-hardware.txt
python modules/descriptor-layout-check/layout_check.py capture-hardware --source modules/descriptor-layout-check/examples/descriptor.sv --top descriptor_top --type descriptor_t --interface-ref synthetic-descriptor-v1 --configuration-ref example-default --complete-inputs --output .local/descriptor-hw.json
python modules/descriptor-layout-check/layout_check.py capture-software --header modules/descriptor-layout-check/examples/descriptor.h --struct descriptor --profile modules/descriptor-layout-check/examples/c-profile.json --interface-ref synthetic-descriptor-v1 --configuration-ref example-default --complete-inputs --complete-fields --output .local/descriptor-c.json
python modules/descriptor-layout-check/layout_check.py compare .local/descriptor-hw.json .local/descriptor-c.json modules/descriptor-layout-check/examples/pairing.json --json-out .local/descriptor-audit.json --markdown-out .local/descriptor-audit.md
```

Expected exit: **0**. Five fields match at byte addresses 0, 8, 12, 16 and 20;
total size is 24 bytes. The declared mapping places the packed record's least
significant byte at address zero. Declaration order is not used as a shortcut.

Capture retains commands, diagnostics and C probe source in a sibling `.evidence`
directory. Outputs must be new. Repeat `--source`/`--dependency` for non-system
inputs. Completeness flags are caller declarations; capture checks file stability.

## Native profile

Slang provides elaborated packed type facts. `--parameters parameters.json` applies
and verifies integer top-module overrides. GCC compiles and executes a layout
probe for the explicit member list and selected encoding constants.

The C profile is LP64, little endian, 8-bit bytes, binary two's-complement integers
and `-fno-short-enums`. `--complete-fields` declares a complete member list; the
probe does not discover every member or enumerator. Other target ABIs can use
independently extracted normalized records with the portable comparator.

## Supported limits

- Flat packed SystemVerilog structs and ordinary C integral scalar fields, with
  byte-aligned widths of 8–64 bits. Nested records, unions, arrays, C bitfields,
  pointers, booleans, sub-byte fields and ascending/nonzero HDL ranges are rejected.
- Explicit pairing of every field and declared encoding, interface/configuration
  identities, byte ordering and guaranteed minimum alignment.
- `direct-object-copy` representation only. An explicit serializer returns incomplete;
  its wire layout needs a separate interpretation.

Padding is reported separately from named reserved fields. Matching layout does
not establish reserved-value rules, four-state conversion, cache coherency or
runtime protocol correctness. See [FORMAT.md](FORMAT.md) for exact mapping rules.

## Status and tests

`0` matched within scope; `1` mismatch; `2` incomplete/unsupported serialization;
`3` invalid input, capture or I/O error. Incomplete takes precedence while retaining
known mismatches. Argument errors use exit 2.

```sh
python -m unittest discover -s modules/descriptor-layout-check/tests -v
```

Native tests skip without their frontend environment. The [manual template](record.template.json)
and [manual mismatch example](example.json) are separate from executable formats.
