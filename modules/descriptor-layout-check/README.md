# Descriptor layout check

Use this module before handing a shared binary record from RTL to firmware, or
after changing a packed type, C definition, target ABI, parameter or encoding.
It compares the **bit addresses actually used by both representations**, alongside
width, signedness, encodings, total size and alignment.

This fits in descriptor/interface integration and generated-header review.
RTL, firmware and DV owners can use it alongside elaboration, compiler checks and
runtime protocol tests. It replaces manual offset spreadsheets and declaration-order
comparisons. A same-size record can still put fields or value bits at different
addresses.

| Activity | What it establishes |
|---|---|
| Default: binary layout | Correspondence under an explicit direct-object-copy representation and complete field/encoding pairing. |
| [Configuration consistency](profiles/configuration-consistency/README.md) | Agreement of selected resolved parameters/constants with independent requirements, units, phases and source/configuration bindings. |

Configuration agreement and binary-layout agreement are separate questions.

## First use with the native frontends

The complete native example uses Linux, Python 3.11+, **pyslang 12.0.0** and
**GCC 13.3.0 targeting x86_64-linux-gnu**. Hardware capture also runs on Windows.
The normalized comparator requires only Python 3.10+.

Run from `modules/descriptor-layout-check` with the required compiler already
installed. Install the optional hardware frontend into your own Python environment:

```sh
python -m pip install -r requirements-hardware.txt
python layout_check.py capture-hardware --source examples/descriptor.sv --top descriptor_top --type descriptor_t --interface-ref synthetic-descriptor-v1 --configuration-ref example-default --complete-inputs --output .local/descriptor-hw.json
python layout_check.py capture-software --header examples/descriptor.h --struct descriptor --profile examples/c-profile.json --interface-ref synthetic-descriptor-v1 --configuration-ref example-default --complete-inputs --complete-fields --output .local/descriptor-c.json
python layout_check.py compare .local/descriptor-hw.json .local/descriptor-c.json examples/pairing.json --json-out .local/descriptor-audit.json --markdown-out .local/descriptor-audit.md
```

Expected exit: **0**, `matched_within_scope`. Five fields begin at byte addresses
0, 8, 12, 16 and 20; total size is 24 bytes. The pairing explicitly places the
packed record's least-significant byte at address zero. The tool uses elaborated
and compiled facts rather than assuming declaration order implies compatibility.

Capture creates sibling `.evidence` directories with commands, diagnostics and,
for C, generated probe source and execution evidence. Outputs/evidence directories
must be new. Choose another filename for a repeat capture.

If your machine lacks the native frontend, obtain both complete normalized exports
from your flow owner and run only `compare`. The records are portable; the native
capture adapters' ABI/tool qualification remains specific.

## Helpers and features

| Entry point | What it contributes |
|---|---|
| `layout_check.py capture-hardware` | Uses Slang elaboration to capture the selected packed type's actual offsets, widths, signedness and enumerators. Integer top overrides use `--parameters FILE` and are checked after elaboration. |
| `layout_check.py capture-software` | Compiles and executes a GCC probe for the explicit member/encoding list, obtaining actual sizes, offsets, alignment, scalar representation and selected constants. |
| `layout_check.py compare HARDWARE SOFTWARE PAIRING` | Maps each value bit to its byte/bit address under the declared representation, then compares all paired fields and encodings. Reports padding separately. |
| `layout_capture.py` | The library implementing the two native capture paths; use the public CLI above rather than treating it as a separate command. |

`--json-out` and `--markdown-out` save detailed and readable comparisons.
JSON includes complete bit mappings for mismatches; Markdown shows a compact
first differing bit.

Repeat `--source` for hardware sources and `--dependency` for non-system
dependencies. Completeness flags assert an inspected inventory; the adapters
check declared-file stability, not dependency closure discovery.

## Define the representation before comparing

[FORMAT.md](FORMAT.md) specifies `opentools.record-layout.v1` exports and
`opentools.layout-pair.v1`. Start with the executable
[pairing](examples/pairing.json) and [C profile](examples/c-profile.json).

- Hardware offsets count from packed bit zero. Software offsets count from
  address-zero bytes. The pairing supplies hardware byte order; the C export
  records target byte order. The comparator maps the entire value-bit sequence.
- The pairing explicitly maps **every** field and encoding, including named
  reserved/padding members. Equal names do not create implicit correspondence.
- Interface revision, each side's configuration and the guaranteed minimum
  boundary alignment must be independently sourced.
- The C profile's field/encoding list is caller supplied. `--complete-fields`
  declares it complete; the probe does not discover omitted members/enumerators.
  Only complete inventories support compiler-padding interpretation.
- `direct-object-copy` is the qualified representation. A serializer receives
  an incomplete result because wire-format behavior needs another interpretation.

The C profile is LP64, little endian, 8-bit bytes and binary two's-complement
integers, using `-std=gnu11 -m64 -O0 -fno-short-enums`. It is not a cross compiler.
Other target ABIs can provide independently qualified normalized records where
their representation fits the comparator's assumptions.

## Integrate into a hardware/firmware handoff

1. Choose the original interface revision and actual transfer representation:
   direct copy, endian conversion or explicit serialization.
2. Identify the consumed RTL parameterization and firmware headers/compiler ABI.
   Inspect all source/configuration dependencies before claiming completeness.
3. Capture the elaborated type and compiled member facts. Retain native evidence;
   requested parameters or source text are not substitutes for resolved offsets.
4. Write the field/encoding pairing and alignment requirement from the interface
   contract. Keep the required vocabulary independent of the smaller export.
5. Compare and route offset/width/encoding findings to the RTL, generator or
   firmware owner. Review unknown inventories before accepting a matching subset.
6. Regenerate/recompile the corrected source and recompare. Hand off the original
   requirement, captures/evidence, pairing and report with the owner decision.

Repeat after type, parameter, generated header, compiler/ABI or representation
changes. A layout match does not establish reserved-value rules, four-state
conversion, coherency, ordering or runtime protocol correctness.

## AI-first setup

Give a file/tool-enabled assistant [SKILL.md](SKILL.md),
[AI_USAGE.md](AI_USAGE.md), the actual RTL/C sources and transfer contract:

> Establish how this record reaches the consumer, including endian and alignment
> assumptions. Locate the consumed parameter/configuration and target ABI, capture
> native layout facts where supported, and build an explicit complete pairing.
> Ask for missing dependencies or serializer behavior before claiming agreement.

Use [ONBOARDING.md](../../ONBOARDING.md), module `descriptor-layout-check` /
activity `default`. Your existing AI can inspect other native sources and adapt
validated capture methods. Optional DVIT intent/dependency context can relate a
layout change to interface consumers and revalidation obligations; local adoption
requires none.

## Outcomes and supported scope

| Exit | Meaning |
|---:|---|
| Compare 0 | Matched within the supplied representation and scope. |
| Compare 1 | Known mismatch. |
| Compare 2 | Incomplete inventory, binding or unsupported serialization; known mismatches remain in the report. |
| Capture 0 / 2 | Declared complete / incomplete input and field inventories. |
| 3 | Invalid input, native capture failure or I/O. |

Argument errors use exit 2. Comparison incompleteness takes status precedence;
`mismatch_found` remains independent.

The native profile supports flat packed SystemVerilog structs and ordinary C
integral scalar fields with byte-aligned widths of 8–64 bits. Nested records,
unions, arrays, C bitfields, pointers, booleans, sub-byte fields and ascending/nonzero
HDL ranges are rejected. Other frontends and commercial EDA flows need separately
validated exports; portable record syntax alone does not establish native support.

```sh
python -m unittest discover -s tests -v
```

Native tests skip without their frontend environment. The
[manual record](record.template.json) captures broader interpretation separately
from executable capture formats.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
