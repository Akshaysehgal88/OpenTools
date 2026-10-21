# Native configuration controls

Qualified recipe: Linux, Python3.10+, pyslang12.0.0 and GCC13.3.0 x86_64-linux-gnu
LP64. Install the parent's optional hardware dependency explicitly if needed.
From this profile directory:

```sh
python -m pip install -r ../../requirements-hardware.txt
python examples/run_native.py /tmp/configuration-proof
OPENTOOLS_CONFIG_NATIVE=1 python -m unittest discover -s tests -v
```

Nothing downloads/installs tools automatically. Each generated pair retains the
independent request, actual parameter arguments, generated selected/default headers,
source inventory, native capture/probe evidence, compiled consumer and reports.

Slang observes WORD_BITS, DEPTH, FEATURE and MODE directly from resolved parameter
symbols. GCC observes WORD_BYTES, DEPTH, FEATURE and MODE as separate constants.
The storage context uses CELL_BITS/CELL_BYTES, ROW_TOTAL, BANK_ON and ACCESS_MODE;
the contract maps these distinct native names to the same reusable semantic roles.
The consumer measures actual byte-array dimensions, returns feature/mode values
and confirms CHAR_BIT=8. The RTL has WORD_BITS-wide storage entries; a byte-rounded
scalar carrier satisfies the existing layout export format. For logical66 bits,
the carrier is72 bits in64+8-bit fields. It does not turn66/8 into an exact byte
count or supply a replacement logical width.

| Control | Configuration result |
|---|---|
| Payload64 bits / software8 bytes | Supported explicit conversion. |
| Omitted software width override | Effective4-byte default disagrees. |
| Equal raw64 in bits and bytes | Canonical64 versus512 mismatch. |
| Stale feature or mode default | Independently required role disagrees. |
| Storage32 bits /4 bytes, depth64 | Second family control. |
| Stale storage depth | Effective16 disagrees with required64. |
| Both views use a wrong default | Peer agreement32 does not satisfy required64. |
| Wider storage64 bits /8 bytes | Additional valid control. |
| Logical66-bit word | Exact bits-to-bytes conversion fails; no rounding. |

Ten cases use four selected roles. Effective-default reference tables, resolved
carrier size and a separate compiled consumer cross-check exported facts. This
does not qualify generator closure, whole binary layout, transaction behavior,
functional mode selection, feature interactions or formal/DFT/STA constraints.
Mode indices are owned configuration values, not native timing/test signoff.

[OpenTitan generation](https://opentitan.org/book/util/topgen/index.html) and
[register configuration](https://opentitan.org/book/util/reggen/index.html) are
review references. The recipe executes neither OpenTitan generators nor a
production company's configuration flow.
