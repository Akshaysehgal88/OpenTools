# Memory test/repair handoff

Review the stage where memory test and repair return ownership to functional
consumers. Start with the [AI workflow](AI_USAGE.md), the team's native artifacts
and the receiving owner's requirements. Use the [review record](review-record.json)
with existing company tools; Python and DVIT are optional.

Check geometry and byte lanes, test/functional address views, repair loading,
initialization under the current mapping, ECC enable, ownership and first access.
Keep the original requirements when reports omit a required bank, word or consumer.
Return findings, missing evidence, corrective actions and revalidation triggers
to the memory-test, wrapper and receiving owners.

The optional helper covers one owned 32/39 SECDED command-port model, one optional
spare-row mapping and one test-to-functional transition. It reads actual retained
Verilator 5.020 XML, original sources/binary, commands and transaction records.
The native result and receiving contract remain separate.

```sh
python handoff.py review trial/run trial/context.json trial/receiving-policy.json
python handoff.py capture trial/run trial/context.json --output captured.json
```

Exit codes: 0 aligned within the supplied contract, 1 findings, 2 incomplete,
3 invalid input. `--output` creates a new file. A review always recaptures the
retained native files; saved commands are data and are never executed by it.
See [formats and native reproduction](FORMAT.md).

The four-word and eight-word examples exercise different addresses, reset
polarities, data and top-level names. They are qualification contexts for this
workflow, not separate tools. Controls cover wrong mapping, premature release,
stale ECC, late repair loading, reversed byte lanes, test-port leakage, invalid
payload, disabled ECC and a test that passes on the wrong physical rows.
Valid no-repair loading and a denied early release are positive controls.

Other macros, fuse layouts, MBIST algorithms, multiple repair entries, reset
retention, physical X/power behavior and timing need their own native evidence.
The helper does not certify production fault coverage or memory signoff. Use the
same workflow with the team's tools and preserve unsupported claims as open items.
