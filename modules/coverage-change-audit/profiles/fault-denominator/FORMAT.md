# Owned finite fault-campaign format

Saved-data capture/review uses the Python 3.10+ standard library. Native generation
uses Linux, a C++ compiler and Verilator 5.020:

```sh
python examples/run_native.py /tmp/fault-trials --verilator /path/to/verilator_bin --verilator-root /path/to/verilator/runtime
OPENTOOLS_FAULT_NATIVE=/tmp/fault-trials python -m unittest discover -s tests
```

One build per logic network serves ten selected plans. Each native execution
records a healthy response and each single-site SA0/SA1 response over every legal
combinational input. That full-space audit supplies finite detectability and
response-equivalence evidence. The selected campaign's classification uses only
its pattern mask and budget; additional full-space audit vectors are not counted
as selected-pattern detections.

## Retained native directory

Keep `fault_network.sv`, `top.sv`, `main.cpp`, `plans.hpp`, `model.xml`, original
`Vtop` ELF, `version.txt`, `plan.json`, `execution.json` and build/xml/run command
JSON and stdout/stderr files. Sources and plans are frozen before execution.
The reader checks the exact owned network/logger source, selected compiled plan,
native parameter-specialized instance, direct role connections and widths.
Hash bindings retain supplied byte identity; they do not authenticate execution,
freshness or acceptance.

`context.json` uses `opentools.fault-context.v1`. Identity fields are `run_ref`,
`scope_ref`, `design_ref`, `configuration_ref`, `fault_model_ref`, `objective_ref`.
Also supply selected `unit_instance`, `unit_type`, `family`, distinct `role_map`
and model/constraint/pattern/exclusion/owner basis references. Unavailable basis
references remain null and keep the review open.

The qualified model is `opentools.owned-site-stuck-at.v1`. Native XML establishes
the selected output-vector injection-site census and port geometry. This census
does not include arbitrary RTL/netlist pins or implicit physical faults.
Fault ID `2*site + stuck_value` identifies each original owned obligation.
The functional observation target is the mapped `observed` port. Raw/driven site
ports are instrumentation, not extra detection outputs for this objective.

## Native records and classification

- `CONFIG`: selected plan, native input/site/output widths, mode, legal-input
  mask/value, selected-pattern mask, budget, exclusion mask, optional unclassified
  fault, metric and population basis.
- `GOLD`: actual input/mode, raw/driven site vectors and healthy output.
- `ORACLE`: fault/site/polarity, actual input/mode, raw/driven site vectors,
  observed output and native healthy output.
- `FAULT`: original ID, native class, sampled count, first selected witness or -1,
  finite legal detectability, representative ID and exclusion flag.
- `GROUP`: representative, member/included counts, detected and all-UT flags.
- `RESULT`: original/collapsed totals and integer numerators/denominators.
  `NATIVE_CHECKS` closes the export and preserves driver input-identity checks.

DT means a sampled selected pattern has an observable output difference. AB means
no detection was observed before the selected-pattern budget expired. UT means a
completed selected campaign found no detection and the full finite legal oracle
has no possible difference. UD means selected tests missed a finite-detectable
fault. UNKNOWN is the native exporter's explicit unclassified state and remains
unknown even when a numeric score is available. These are owned rules, not
translations of commercial ATPG class names.

Collapse groups contain identical complete output response vectors over the exact
legal mode/input space. The reader checks every mapping against those retained
native responses. Another legal space can produce another map.

Metric 0 is DT divided by nonexcluded entries. Metric 1 also removes UT entries
from that denominator. Population basis 0 counts original faults; basis 1 counts
collapse groups. A group is included when any member is nonexcluded, detected
when any included member is DT, and UT only when all included members are UT.
Original native classes remain visible regardless of group or exclusion status.
Zero denominator is null. Unlike definitions receive no percentage delta.

## Independent objective and comparison

`policy.json` uses `opentools.fault-policy.v1`:

- `baseline`, `current`: independently accepted `identity`, `source_sha256`,
  `plan_sha256`, `run_command_sha256` and `binary_sha256` bindings.
- `required_original_faults`: complete independent roster of `id`, `site`, `stuck`,
  `source_ref`. Do not derive this from the smaller reported denominator.
- `reviewed_exclusions`: `fault_id`, `source_ref`, `reason_ref`, `owner_ref` for
  supplied current decisions. References are declarations, not authenticated approval.
- `source_ref`, `owner_ref`, `inputs_complete`: original objective and receiving basis.

The comparison retains both native measurements and all original rows, class and
exclusion changes, newly selected-test detected faults, resolved classifications,
gaps, owner and recheck triggers. Source/model/objective or legal-mode changes
limit detection-progress attribution. A later DT after UNKNOWN/AB is reported as
resolved classification rather than proof that the earlier campaign did not detect it.

`examples/reference_model.py` independently checks every native gate response and
collapse signature. The parent functional coverage implementation is unchanged;
its threshold/bin/UCIS semantics are not used for fault scoring.
