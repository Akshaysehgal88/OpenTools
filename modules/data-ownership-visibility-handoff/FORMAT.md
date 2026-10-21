# Handoff records

UTF-8 JSON. Flags are booleans or explicit null; values/versions are unsigned
integers or explicit null. Duplicate keys/identities, boolean integers, nonfinite
values and out-of-order events are invalid. Use lossless integer tooling.
[create_example.py](examples/create_example.py) generates complete fixtures.

All records contain `format`, exact `scope` (`project`, `configuration`, `mode`,
`handoff_ref`), `basis_ref`, boolean `inputs_complete`. The basis names the consumed
source, platform contract and reviewed mapping/observation method.

## Inventory: `opentools.handoff.inventory.v1`

`mapping_epoch_ref`, distinct `producer_ref`, `consumer_ref`,
`maintenance_agent_ref` and `platform_contract_ref` are nonempty references.
`objects` contains 1–256 unique `id`, `role_ref`, `width_bits`, `physical_address`,
`line_bytes`, `evidence_ref`. Width is 8–4096 in whole bytes; line size is a power
of two up to 4096 bytes and contains the scalar. Addresses are aligned unsigned
64-bit byte addresses. Overlapping object definitions need reviewed alias identity;
they cannot silently become independent buffers. Shared-line effects are outside
the native profile.

`mappings` entries have unique `id`, `agent_ref`, `object_ref`, scalar-start byte
`address`, `mapping_epoch_ref`, `coherent` (boolean/null), `cacheability`
(`write-back/uncached/unknown`), `shareability_ref`, `path_ref`, `evidence_ref`.
Shareability/path may be null when unresolved. Epoch, object, path and attributes
remain explicit; the helper does not infer a coherent route from control allocation.
Mappings describe reviewed identity, not an executable IOMMU translation.

## Journal: `opentools.handoff.journal.v1`

`inventory_sha256`, `window_ref`, boolean/null `epoch_isolated`, `window_closed`,
`events_complete`, and `initial_owner_ref` (string/null) identify one observed
handoff. Initial ownership and complete coverage need source evidence.

`events` have unique `event_ref`, increasing unsigned `seq`, nondecreasing
unsigned `time_tick`, `actor_ref`, `object_ref`, `evidence_ref`, and:

- `kind`: `initial/write/clean_request/clean_complete/release_order/publish/read/complete/reclaim`.
- Explicit boolean/null `accepted`, `effect_observed`, `control_seen`. The latter
  applies to consumer reads; use null elsewhere. Effects come from actual native
  observations, not the desired operation alone.
- Explicit `mapping_ref`, `address`, `value`, `version`, `owner_after_ref`, using
  null when unknown/inapplicable. Mapped events identify the exact scalar start;
  no unaligned/range splitting is performed. Data fits the object's width;
  addresses/versions fit unsigned 64 bits. Ownership is an observed/reviewed role,
  not inferred OS or hardware exclusivity.
- `clean_complete` includes `request_ref`. Its captured object, mapping, value
  and version must match an earlier observed clean request. Use the captured
  writeback target, not a later command address. Completion grants visibility
  only after the receipt is observed; late completion cannot repair earlier use.
- `read` includes `control_mapping_ref`, observed control flag and actual payload
  value/version. Expected values or producer-cache snapshots are not responses.

`release_order` records the produced version covered by the platform's ordering
mechanism. It is separate from cache maintenance and does not imply a flush or
drain. Publication transfers the selected ownership to the consumer. Completion
must follow the required observed consumption; reclaim must follow that qualified
completion. Producer writes during consumer ownership remain findings even if
the consumer later reads the expected bytes.

## Policy: `opentools.handoff.policy.v1`

`inventory_sha256`, `journal_sha256`, exact `window_ref` bind evidence.
Independently specify `payload_ref`, `control_ref`, `payload_mapping_ref`,
`control_mapping_ref`, `producer_ref`, `consumer_ref`, `maintenance_agent_ref`,
`mapping_epoch_ref`, `ordering_contract_ref`, `completion_contract_ref`.
Mapping refs name the intended consumer paths.

`expected_write_ref`, `publish_ref`, `read_ref`, `completion_ref`, `reclaim_ref`
name required milestones. `expected_value` and `expected_version` are explicit
integers/null from the transfer intent, not whatever the read/current cache contains.
Boolean `require_release_order` records that platform obligation; coherence does
not automatically disable it. Unknown expectations remain gaps.

`required_objects` has unique `id`, `role_ref`, `width_bits`, `evidence_ref`.
`required_mappings` has unique `id`, `agent_ref`, `object_ref`,
`mapping_epoch_ref`, `coherent`, `path_ref`, `evidence_ref`. Keep these censuses
independent of imported definitions/observations. Missing or differing selected
definitions cannot shrink the intended handoff.

`start_seq`, `end_seq` select up to 4097 consecutive observed events. Missing
samples, required milestones or events outside that window remain gaps.

## Report

The report retains publications with separate payload coherence/order/completed
maintenance image, actual reads, replayed ownership, findings and gaps. Status is
`review_required` with findings, otherwise `incomplete` with gaps, otherwise
`within_observed_contract`. Earlier findings survive later successful maintenance
or reuse. Unknown data/receipts are not replaced with expected values.

Foreign/stale bindings supply no lifecycle evidence. Canonical SHA-256 uses sorted
keys, compact separators, UTF-8 and no nonfinite values (`handoff_core.digest`).
Hashes bind content, not physical identity, source roles, coverage or approval.
The core checks supplied scalar lifecycle evidence; it does not simulate arbitrary
caches or qualify the claimed DMA, barrier or coherence implementation.
