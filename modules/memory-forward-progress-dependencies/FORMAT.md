# Resource-episode records

UTF-8 JSON. Flags are booleans or explicit null; counts are unsigned integers or
explicit null. Duplicate keys/identities, boolean integers, nonfinite values and
out-of-order samples are invalid. [create_example.py](examples/create_example.py)
generates complete fixtures.

All records contain `format`, exact `scope` (`project`, `configuration`, `mode`,
`episode_ref`, `traffic_class_ref`), `basis_ref`, boolean `inputs_complete`.
The basis names the consumed source and reviewed resource/transition mapping.

## Model: `opentools.progress.model.v1`

`semantics` is `finite-retained-resource-episode`. `resources` and `actors` each
contain 1–64 entries with unique `id`, `role_ref` (string/null), `evidence_ref`.
Resources also have `capacity` (1–4096/null), `unit`. Counts refer to that same
unit; omitted or differently typed definitions cannot satisfy required coverage.

`waits` is an explicit list of at most 256 entries. Each has unique `id`,
`actor_ref`, `held_resource_ref`, `requested_resource_ref`, `mode_ref`,
`release_condition_ref`, `evidence_ref`, boolean/null `active` and
`retains_until_acquire`. Only known active, retained waits enter the static graph.
Unknown guards or retention semantics remain gaps. References identify source
meaning; the helper does not evaluate arbitrary mode expressions or RTL guards.

Exact boolean/null `premises`: `closed_resource_census`, `release_paths_complete`,
`autonomous_updates_absent`, `external_actions_absent`; plus
`premises_evidence_ref`. All four must be true for conditional closed-model
blocking. Known external actions are permitted, but prevent that qualification.
Unknown closure or incomplete release/census leaves a gap. `fair_scheduling` is a
separate boolean/null premise retained in the report, not an inferred guarantee
or a substitute for enabled-action evidence. No unbounded liveness is checked.

`external_actions` is an explicit list, possibly empty, with unique `id`,
nonempty `may_release` resource IDs and `evidence_ref`. Include legal reclaim,
timeout or other external progress in the appropriate native method. Declaring
absence while listing external actions is inconsistent.

## Journal: `opentools.progress.journal.v1`

`model_sha256`, `window_ref`, boolean/null `window_closed`,
`observations_complete`, `reachable_prefix_confirmed`, and string/null
`reachability_basis_ref` identify one reviewed native prefix/window. Reachability
is a supplied, source-reviewed declaration. The generic core does not validate
arbitrary transition semantics; the owned native runner checks its own prefix
against the independent state model.

`samples` have increasing unsigned `seq`, nondecreasing unsigned `time_tick`,
`evidence_ref`, `actors`, and `external_enabled` (action-ID to boolean/null).
Each observed actor has unique `actor_ref`, `state_ref`, `evidence_ref`, explicit
boolean/null `pending`, `complete`, `release_enabled`, `advance_enabled`, and
`held`/`requested` maps from every resource ID to count/null. Missing actors,
counts, release enables or external observations remain gaps.

Free capacity is total capacity minus all observed holdings. Progress is an
enabled release or a nonempty request whose quantities fit the available
resources. Compare that derived enable with the observed native enable. Active
retained waits must account for actual blocked hold/request edges. Negative free
capacity or conflicting enables cannot qualify a blocking snapshot.

A conditional blocking witness needs pending work, no enabled internal progress,
an actual retained-wait cycle, no enabled external action, complete local
observations and qualified global closure/reachability premises. The label is
conditional on those source meanings; it is not proof about an arbitrary design.
Additional or hidden owners, autonomous state updates and simultaneous multi-step
transactions require a broader model.

## Policy: `opentools.progress.policy.v1`

`model_sha256`, `journal_sha256`, exact `window_ref` bind inputs. Nonempty
`required_resources` independently lists unique `id`, `role_ref`, `unit`,
`evidence_ref`; `required_actors` lists unique `id`, `role_ref`, `evidence_ref`.
Do not derive this roster from the observation list. Missing definitions,
role/unit mismatch and unreviewed selected definitions remain gaps.

`start_seq`, `end_seq` select up to 4097 consecutive samples. Missing samples and
observations outside the window are gaps. `require_completion_at_end` is boolean;
when true, required actors must be observed complete at `end_seq`. Failure is a
finite completion finding, not an unbounded starvation/deadlock proof.

## Report

The report separates static `candidate_cycles`, per-sample availability/enables/
observed waits, conditional `blocking_witnesses`, findings and gaps. Status is
`review_required` with findings or static cycles, otherwise `incomplete` with
gaps, otherwise `within_observed_contract`. A serialized successful trace can
therefore retain candidate review without an observed blocking witness.

Known findings retain unrelated gaps. Stale/foreign binding supplies no observations
or witness. Canonical SHA-256 uses sorted keys, compact separators, UTF-8 and no
nonfinite values (`progress_core.digest`). Hashes establish content identity, not
truth, complete discovery, native applicability or owner approval.
