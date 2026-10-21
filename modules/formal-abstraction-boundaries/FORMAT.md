# Finite boundary records

JSON uses strict keys, integers for unsigned values, explicit source references
and complete tuple populations. No implicit casting, unit conversion or inferred
interface mapping. Duplicate keys/tuples and non-finite numbers are rejected.

## Contract and evidence

`opentools.abstraction-boundary.v1` contains:

- `review_ref`, `claim`, `owner_ref`, `scope_ref`: independent review intent.
- `scope`: `boundary_ref`, `mode_ref`, `model_class` and `basis_ref`.
  The class is `finite_combinational_relation`.
- `domain`: ordered `{name, width}` items; at most12 total unsigned bits. A row
  has one integer per item in that order. Tuples are unique and sorted.
- `property`: independent `ref`, `basis_ref` and complete `allowed_rows` for the
  selected predicate, not a predicate inferred from the green report.
- `views`: `concrete` and `abstract`, each with original `run_ref`, `sources`
  (filename → SHA256) and independent `basis_ref`.
- `obligations`: every native abstract assumption's `cell_id`, `owner_ref` and
  correspondence `basis_ref`. Empty is valid only for no assumptions.

Substantive unknowns use `null`. Do not invent owners, completeness or a desired
truth relation. Required structural fields must be present.

`opentools.abstraction-evidence.v1` has `contract_sha256` (canonical sorted compact
JSON digest), `concrete` and `abstract` native snapshots or `null`. Paths are
relative to the directory containing the evidence file. Hashes identify bytes,
not authorship or semantic authority.

The review computes concrete-minus-abstract and abstract-minus-concrete tuples:
equal, conservative expansion, restrictive subset or incomparable. Any missing
concrete tuple blocks correspondence for the complete selected boundary. An
abstract failure witness is classified only against this concrete tuple relation;
it is not automatically a concrete design failure. Native outcome is checked
against the independently required predicate and retained separately.

## Qualified saved-Yosys reader

Tested Yosys0.33 git `2584903a060` on Linux; saved data rechecked on Windows.
The reader supports one stateless flat `top`, two-bit input `source`, two-bit
outputs `left`/`right`, and internal `boundary={right,left}`. One assertion;
concrete reference without assumptions/cuts. Native cut creates exactly the two
selected arbitrary output drivers. The wider12-bit relation algorithm is not a
qualification of wider/different native exports.

The fixed script reads `model.sv` with `selection.vh`, runs hierarchy/proc, writes
`before.json`, optionally runs `cutpoint w:boundary`, prepares `top`, writes
`after.json`, then retains a property SAT query and exhaustive SAT enumeration.
The exact recipe is in `yosys_capture.recipe`. Supported native cells are the
documented small combinational set in that reader; sequential/memory/hierarchical
or other native formats require another validated method.

Required files: `model.sv`, `selection.vh`, `run.ys`, `before.json`, `after.json`,
`native.log`, `property.log`, `relation.log`, and `witness.json` for native FAIL.
Enumeration must terminate with explicit exhaustion and agree with its tuple
count. Native decimal/hex/binary values and WaveJSON witnesses must agree.
Dedicated query logs must also match their original combined native log.
Before/after port identities, actual arbitrary drivers, formal-cell population
and bit-level property fan-in are retained. Cone membership does not establish
semantic sufficiency; optimization can eliminate a structural dependency.

Capture context supplies original run/scope/property references, command and
dependency completeness with a basis. They are declarations, not authenticated
measurements or automatic dependency closure. Critical files are hashed and
reparsed on every review; changed/missing/foreign results are quarantined.
Relative paths cannot escape the selected root; linked evidence is unsupported.
Imported scripts/logs are data and are never executed by the reader.

The native mechanism follows the upstream
[Yosys cutpoint reference](https://yosyshq.readthedocs.io/projects/yosys/en/v0.55/cmd/cutpoint.html):
ordinary formal cuts replace selected drivers with arbitrary values. That link
describes the mechanism; the local measured0.33 artifacts define this profile's
qualification. Pointwise finite inclusion is not a sequential simulation proof,
property sufficiency, physical check or release/proof acceptance.
