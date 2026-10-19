# Build evidence contract

JSON keys must be unique, numbers finite and fields exact. The optional record
`provenance` accepts uninterpreted JSON. Null means unknown. Represent a known
unset value explicitly, e.g. `{"state":"unset"}`. Completeness/evidence references
are supplied claims; the helper does not authenticate or assess their truth.

## Phase profile

`opentools.build-profile.v1` requires `format`, nonempty `id`, `evidence_ref` and
`rules`. Rules have unique `name`, `phase` (`build`, `runtime`, `unknown`) and
`evidence_ref` (string/null). Records bind the entire profile's canonical SHA-256:
UTF-8 JSON, sorted object keys, compact separators, Unicode unescaped and finite
numbers. `reuse_core.fingerprint` implements it. Changes require reviewing and
rebinding both records. Missing bindings/evidence and unclassified options block
eligibility. A fully asserted but incorrect profile can mislead the comparator.

## Build record

`opentools.build-record.v1` requires `format`, `record_ref`, `profile_sha256`,
`basis`, `coverage`, `capture`, `build`, `run_ref`, `result_ref`. Identity references
are nonempty strings; the profile digest is lowercase 64-character SHA-256 or null.
The two requests require distinct run and result identities. Optional `provenance`
affects the input fingerprint but has no interpreted authority.

`basis` has exactly six fields:

- `commands`: nonempty ordered array of `{cwd, argv, evidence_ref}`. `cwd` is
  string/null; `argv` is a nonempty ordered array of literal strings. Preserve
  actual build flags, source ordering and repeated switches. These are build
  invocations; runtime launch evidence belongs with runtime options.
- `dependencies`: ordered array of `{path, role, sha256, evidence_ref}`. Paths are
  unique nonempty identity strings; roles are nonempty flow-specific labels.
  Digests are lowercase SHA-256 or null. No automatic aliasing, sorting, path
  substitution, timestamp inference or repository-revision shortcut occurs.
- `configuration`, `environment`: objects/null carrying captured relevant settings
  and resolution/search order. Nested null remains unknown. Avoid credentials;
  use an appropriate non-secret identity and state any resulting capture limits.
- `toolchain`: array of unique-name `{name, identity, evidence_ref}` entries.
  Identity is string/null. Include relevant compiler/elaborator, ABI, plugins,
  runtime headers/libraries and environment identity. Version text alone may be
  inadequate; the helper does not infer toolchain completeness.
- `options`: array of unique-name `{name, value, evidence_ref}` entries. Each name
  binds a profile rule; values are JSON. Use ordered value arrays for repeated
  values and preserve cross-switch order in `commands.argv`. Null anywhere in an
  option value blocks eligibility, including runtime inputs.

Every evidence reference above is a nonempty string or null. Missing references
block eligibility. Empty dependency/toolchain inventories also block eligibility.

`coverage` requires `sources`, `filelists`, `includes`, `generated`, `configuration`,
`linked_models`, `toolchain`, `environment`, `resolution`, `options`, `artifacts`.
Each is `{complete: true|false|null, evidence_ref: string|null}`. All must be true
and sourced for both records, including explicit N/A declarations. Resolution
covers negative lookups/search namespaces: a newly shadowing include/library can
change a request without changing any old listed dependency. Artifacts covers the
required immutable set, including companions needed by the requested invocation.

`capture` requires `consumed_bytes` and `request_resolved`, each the same
completeness fact shape. The baseline needs original consumed-byte evidence; live
hashes collected after an old build are insufficient. The request needs a newly
resolved complete boundary; it need not already have been built. Back these claims
with a suitable snapshot, native build system or qualified collection method.

`build` requires `complete` (boolean/null), `exit_code` (integer/null),
`evidence_ref` and `artifacts` (array of `{path, sha256, evidence_ref}`). Baseline
eligibility requires sourced true completion, invocation exit 0 and a nonempty
artifact set. This is not verification outcome interpretation. Artifact paths are
unique relative POSIX paths without empty/dot/parent components, colon or backslash.
Each declared file must currently match its original digest under `--artifact-root`.
Missing files, symlink components and resolved escapes are unavailable; missing
hashes/evidence or no supplied root are unknown. No lease, authenticity or future
stability proof is provided. Operational reuse belongs to the existing cache policy.

## Comparison

`opentools.build-comparison.v1` retains status, record labels, canonical input and
build-key digests, exact known build differences, separate runtime differences,
all unknowns, per-file artifact observations, limits and
`result_reuse: not_established`.

The build key preserves commands/dependencies/toolchain order and complete
configuration/environment, including only evidenced bound build options. Evidence
locations do not alter the build key; they do alter the input fingerprint.
Unclassified options are excluded from the key and always block eligibility.
Therefore equal key digests alone must never authorize reuse or serve as a cache
key. Runtime option presence/value changes remain separate observations.

Known differences return `rebuild_required` (1), retaining unknowns. Otherwise an
unavailable/corrupt artifact returns `artifact_unavailable` (1), remaining unknowns
return `unknown_eligibility` (2), and only no differences/unknowns plus verified
artifacts returns `eligible_within_declared_scope` (0). Null-versus-known means
unknown, not an asserted mismatch. Invalid inputs/I/O return 3. Output paths must
be new, distinct and separate from input/artifact files. Sequential report writes
are not a transactional cache operation.

## Native inventory

`Verilator-5.020.verFiles.v1` reads a declared 5.020 `__verFiles.dat`, verifies its
exact header, one `C` command and `S`/`T` records with six nonnegative native stat
integers and a quoted filename. UTF-8 names with spaces are retained. Names with
quote/backslash/line break, unknown records and duplicate kind/path records fail
closed. No listed dependency is read; no shell expansion or execution occurs.

`opentools.verilator-build-evidence.v1` retains the input-file byte SHA-256, declared
producer version, flattened command text, source/target arrays and native stat
fields. It explicitly reports consumed content hashes absent and closure not
established. The source-file digest is not a dependency/artifact digest, command
text is not argv, and this format does not identify its producer version itself.
The reader does not infer C++/link closure or automatically export a complete
normalized record. Timestamps cannot qualify a reuse verdict.
