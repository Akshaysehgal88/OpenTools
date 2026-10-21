# Generated decoder and native software table

The Linux recipe uses Verilator **5.020**, GCC **13.3.0** targeting
`x86_64-linux-gnu`, GNU Make 4.3 and Python 3.10+. From the module directory:

```sh
python examples/run_native.py native-demo --verilator /path/to/verilator
```

Add `--verilator-root /path/to/share/verilator` for an extracted kit. Choose a new
directory with an existing parent. The recipe creates only owned example sources,
builds under an owned space-free `/tmp` directory and retains generated HDL/C,
commands, binaries, compiler/tool identities, map records and native observations.
No dependencies are downloaded.

An owned C table is compiled and read by a native probe; it is not reconstructed
by a C text parser. The generated hardware manifest identifies the exact HDL bytes.
The recipe tests actual compiled decode/permission/attribute outputs against an
independent byte-entry reference, then against the native software map.

Both initiators exercise every byte in the selected hardware/software windows,
their immediate boundaries, three operations and secure/nonsecure inputs. This
is a retained query population, not the whole 32-bit address space.

| Case | Expected result |
|---|---|
| Valid | Processor alias is allowed; both views agree. |
| Overlap | A moved alias overlaps the original decode and leaves an intended range uncovered. |
| Permission | Device writes differ between hardware and software views. |
| Hole | A required device window is absent from the generated decoder. |
| Paired | Both views move the device window and its requirement together. |

The same activity handles both initiator spaces; the processor alias rule does
not grant device permissions. Decoded route, allowed operation and reported
attributes are separate native observations. A denied operation is not a missing
route, and a shared target alone does not establish coherency or security.

Enable the integration test with `OPENTOOLS_ADDRESS_NATIVE` and, when needed,
`VERILATOR_ROOT`. Optional `OPENTOOLS_ADDRESS_OUTPUT` retains its five case
directories at a new path. Other generators, C layouts, dynamic translations and
production flows need their own qualified exports and source review.
