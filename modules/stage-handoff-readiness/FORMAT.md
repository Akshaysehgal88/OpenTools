# Handoff records

UTF-8 JSON with strict booleans/null and unsigned 64-bit addresses/values. No
duplicate keys, boolean integers or nonfinite values. [Examples](examples/create_example.py)
produce records; they do not supply production trace semantics.

All inputs contain `format`, exact `scope` (`project`, `configuration`,
`handoff_ref`, `mode`), `basis_ref`, boolean `inputs_complete`. Journal and policy
contain `inventory_sha256`; policy also binds `journal_sha256`. Canonical digests
use sorted keys, compact separators, UTF-8 and no nonfinite values. Foreign/stale
bindings supply no event interpretation. Hashes certify content identity only.

## Inventory: `opentools.stage.inventory.v1`

`source_kind`, `method_ref`, `source_revision_ref` preserve evidence provenance.
`image` contains lowercase `sha256`, unsigned `entry`, `evidence_ref` and nonempty
resolved `segments`: unsigned `start`, positive `size`, unique `permissions`
(`R/W/X`) and `evidence_ref`. Ranges are half-open and cannot overflow. Source
meaning and loaded-address applicability require native/AI review.

The optional ELF reader emits `opentools.stage.image.v1` with those fields, machine
and file offset/size. It supports at most 64 MiB, static ET_EXEC x86-64 ELF64 LE,
ordinary program headers, identity-mapped nonoverlapping PT_LOAD ranges and an
executable entry. Dynamic/interpreter, relocated, extended headers and other
architectures/formats are unqualified. It reads metadata; it does not execute input.

## Journal: `opentools.stage.journal.v1`

`events_complete` is boolean/null, a caller coverage declaration. `events` have
strictly increasing unsigned `seq`, `kind`, `evidence_ref`:

- `fact`: `id`, boolean/null `value`, observed in order.
- `image_load`: `image_sha256` of bytes actually loaded.
- `handoff`: one per journal; `successor_ref`, `image_sha256`, unsigned `entry`,
  `initial_sp`, `state` mapping prerequisite IDs to boolean/null at transfer.
- `access`: `actor_ref`, `purpose` (`stack/data/fetch`), `operation`
  (`read/write/execute`), unsigned `address`, positive `size`, boolean/null
  `successful`. The record describes the actual observed access result.
- `result`: `actor_ref`, unsigned/null `value`.

The snapshot establishes observed transfer state; later facts never overwrite it.
With complete event capture, prior known facts must agree with the snapshot.
Missing snapshot facts remain gaps, even when an earlier/later event is favorable.
Foreign actor events supply no successor outcome credit. Reload after transfer
requires further review. One scoped transfer and one result observation are the
bounded profile; multi-stage/reentrant histories need separate scoped reviews.

## Policy: `opentools.stage.policy.v1`

Independent `successor_ref`, `requirements_ref`, `source_revision_ref`, required
`image_sha256`, unsigned `entry`, `initial_sp`, `stack_region` (`start`, `size`),
power-of-two `stack_alignment`, nonempty `requirements` mapping IDs to expected
booleans, and unsigned/null `expected_result`. A null expected result imposes no
value comparison. Evidence cannot choose or weaken the successor contract.

## Report

`obligations` preserve required/observed transfer states, prior and boundary source
references. `first_stack_access`, `observed_result`, findings and gaps remain
separate. A known false prerequisite, image/setup mismatch or failed actual access
retains review-required status alongside missing result or capture gaps. No first
stack observation is incomplete, not proof that none occurred.

Status: `within_observed_contract`, `review_required`, `incomplete`. CLI exits
0/1/2 respectively; invalid input/I/O exits3. `--output` creates a new file.
