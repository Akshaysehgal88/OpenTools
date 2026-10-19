# Descriptor layout formats

Executable inputs are UTF-8 JSON. They differ from the illustrative `record.template.json` review record. Duplicate JSON keys, non-finite values, booleans in integer fields, overlapping fields and unsupported field properties fail validation. References identify caller-supplied evidence and are not fetched.

## Layout: `opentools.record-layout.v1`

Both sides require `kind`, `basis`, `record`, `interface_ref`, `configuration_ref`, `source_ref`, `frontend_ref`, boolean `inputs_complete` and `fields_complete`, integer `size_bits`, and a nonempty `fields` array. A software layout also requires nonempty `target_abi`, `byte_order` (`little` or `big`), power-of-two `alignment_bytes`, and `integer_representation: "binary-twos-complement"` (binary integers without scalar padding bits). Optional `provenance` retains native capture details.

Hardware kind/basis are `hardware`/`packed-lsb`. Field offsets count from the least significant bit of the packed record, independently of address order. Complete packed records must account for every bit. Software kind/basis are `software`/`c-object`; offsets count from byte-address zero, with bit zero the byte's least significant bit. Compiler padding can occur between or after fields. If the field inventory is incomplete, gaps are not identified as padding.

Every field has this shape:

```json
{
  "name": "opcode",
  "offset_bits": 96,
  "width_bits": 32,
  "signed": false,
  "enum_values": {"OP_READ": 1, "OP_WRITE": 2},
  "evidence_ref": "source-content-id#descriptor.opcode"
}
```

Names must be unique. Widths are multiples of 8 from 8 through 64, offsets are nonnegative multiples of 8, and fields must fit the record. Non-enum fields use `{}` for `enum_values`. Values must be integers representable by that width and signedness. The native C adapter additionally limits supplied encoding constants to signed 64-bit arithmetic so conversion to its report cannot overflow.

`inputs_complete` declares the source/configuration input inventory complete for the chosen frontend profile. `fields_complete` separately declares every member is accounted for. The GCC probe requires the caller to supply the member list; it cannot discover an omitted member. Any completeness gap makes the comparison incomplete. A native capture's source reference hashes declared file identities/content and the selected parameters/profile, while provenance retains native commands and resolved configuration information. These declarations are evidence assumptions, not proofs of build provenance.

## Pairing: `opentools.layout-pair.v1`

See the executable [example](examples/pairing.json). Required references bind the interface revision and each side's configuration. `representation` must be `direct-object-copy` for a verdict; other representations receive an incomplete result and no object-layout mismatch finding. Direct copy requires:

- `hardware_byte_order`: `little` means packed bit zero is bit zero of byte address zero; `big` means it is bit zero of the last addressable byte of the record.
- `required_alignment_bytes`: the boundary's guaranteed minimum alignment, a power of two. It must satisfy the C object's alignment. Actual allocation/transfer behavior is not measured by this tool.
- `fields`: explicit one-to-one `{hardware, software}` field pairings, with optional `encodings` entries `{hardware, software}` mapping encoding names.
- `evidence_ref`: the authority for this representation and pairing policy.

Every exported field and encoding must be paired, including named reserved/padding members. Missing fields or incomplete vocabularies are incomplete evidence. Duplicate or ambiguous mappings are invalid input. Same names never create implicit correspondence. The C profile's encoding list is the caller's declared vocabulary; it does not imply that the compiler enumerated a complete C enum.

For a hardware field at packed offset `o`, value bit `k` maps to byte `(o+k)//8` for little ordering, or `record_bytes-1-(o+k)//8` for big ordering, with bit number `(o+k)%8`. A C scalar at byte offset `c` maps value bit `k` to byte `c+k//8` for little endian or `c+field_bytes-1-k//8` for big endian, bit `k%8`. The whole sequence must agree, alongside field width, signedness and mapped encoding values.

## Native C profile

See [c-profile.json](examples/c-profile.json): `fields` entries supply `name` and optional `encodings` mapping report labels to C constant identifiers. Optional `defines` maps macro identifiers to integer values. Source identifiers are validated before generating the probe. GNU C compiles with the selected header and uses its actual types; no offsets are inferred from source declaration order. C bitfields cannot supply `sizeof`/`offsetof` and fail compilation; other unsupported scalar categories fail static assertions or layout validation.

Only GCC 13.3.0 targeting x86_64-linux-gnu is qualified by this adapter. It uses `-std=gnu11 -m64 -O0 -fno-short-enums`, verifies LP64/byte order, compiles a retained local probe and executes it on that native host. Cross compilation and arbitrary compiler flags are outside this profile. Other ABI exports can use the normalized comparator when their representation fits the documented assumptions.

## Report: `opentools.layout-audit.v1`

The report retains both layouts and the pairing, field-level side-by-side positions, exact bit-address mismatches, enum/signedness/size/alignment differences, padding intervals, unknowns and limits. JSON retains full bit mappings for mismatches; Markdown displays a compact first differing bit. `mismatch_found` remains independent of `status`, which is `incomplete`, `mismatch` or `matched_within_scope` in that precedence order. A successful check is a result about the supplied representation and evidence; it is not a proof of hardware/software behavioral compatibility.
