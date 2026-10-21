# Configuration semantic consistency

Use this activity before generated hardware/software configuration handoff, and
after changing defaults, overrides, units, feature selection or mode values.
It compares **resolved values against independent intent**, rather than merely
checking that two generated files contain the same number.

This fits between generation/elaboration/compilation and configuration acceptance.
RTL, generator, firmware and integration owners can use it alongside the parent
[descriptor layout check](../../README.md). It supplements build/generator checks
and replaces manual reconciliation of selected parameter/constant roles.
Configuration agreement does not establish binary-layout or protocol agreement.

A requested override is not proof of the elaborated value. Two views can agree
on the wrong default. Equal raw values can disagree after unit conversion.
These are the gaps this activity makes explicit.

## First use without native tools

Python 3.10+ and the standard library suffice for the supplied reference fixtures.
Run from `modules/descriptor-layout-check/profiles/configuration-consistency`:

```sh
python examples/create_example.py .local/config-stale --case payload-stale-default
python configuration_review.py .local/config-stale/hardware.json .local/config-stale/software.json .local/config-stale/contract.json --output .local/config-stale/review.json
```

Expected exit: **1**, `review_required`. The independent request requires
64 bits; software's omitted override leaves an effective 4-byte default, or
32 bits. The report retains raw and canonical values, source/configuration
bindings and the required value for each selected role.

Compare the explicit conversion control:

```sh
python examples/create_example.py .local/config-matched --case payload-matched
python configuration_review.py .local/config-matched/hardware.json .local/config-matched/software.json .local/config-matched/contract.json --output .local/config-matched/review.json
```

Expected exit: **0**, `within_selected_contract`: 64 bits equals 8 bytes under
the sourced exact rule. The generator labels these as `reference-fixture`
facts; they do not claim native elaboration or compilation.

Other cases include `payload-same-number` (64 bits versus 64 bytes),
`storage-agree-wrong-default` (both views agree but miss the requirement),
stale depth/feature/mode and a nonintegral 66-bit-to-byte conversion. Example
directories and report files must be new; the generator also saves `report.json`.

## Helpers and supported checks

| Helper or option | Responsibility |
|---|---|
| `configuration_review.py HARDWARE SOFTWARE CONTRACT` | Validates original export/source/configuration/method/phase bindings, maps selected facts to semantic roles, applies explicit unit rules and compares both peers and independent requirements. |
| `--output FILE` | Saves JSON to a new file; omit it to print JSON. |
| Parent `layout_check.py capture-hardware --parameter-fact NAME` | Opt-in capture of the actual resolved integral parameter/local-parameter value from Slang, not an echoed override. Repeat for the selected names. |
| Parent `layout_check.py capture-software --constant NAME` | Opt-in compiler-evaluated C integral constants, separate from field enum vocabulary. Repeat for selected names. |

The parent [capture library](../../layout_capture.py) implements those native
facts. Without the opt-in options, the existing layout export behavior is unchanged.
Select one to five unique plain identifiers; values must fit signed 64-bit
integers.

## Prepare the contract and evidence

[FORMAT.md](FORMAT.md) defines the comparator's two
`opentools.record-layout.v1` exports and independent
`opentools.configuration.contract.v1`.

Each contract states project/configuration/family/mode, original requirements and
source revision. Its hardware/software view bindings include export digest,
source/configuration/interface/frontend identity and expected fact kind/phase.

Each selected semantic role specifies:

- Its canonical unit and independent required value, obtained from the original
  configuration request.
- The hardware and software fact names, their units and explicit rule references.
  Different names can represent the same role; the same fact cannot silently
  stand for two distinct roles.
- An identity or exact rational scale rule with its source evidence. Units and
  numerator/denominator are explicit; conversion must divide exactly.

There is no guessed conversion, expression evaluation, rounding or automatic
repair. Unknown transforms, required values, units or applicability remain gaps,
even when captures agree. Reference fixtures and native facts retain distinct
method identities.

Native provenance includes selected fact names, resolved values/references,
source inventory and elaboration/compile phase. The source identity includes
capture selection. Requested overrides and textual parameter renderings are
not fallback observations. A layout's `fields_complete` flag describes its
struct members, not every configuration parameter in the design.

## Native example and integration

The [native recipe](examples/NATIVE.md) uses existing **pyslang 12.0.0** and
**GCC 13.3.0 x86_64-linux-gnu LP64** on Linux. From this profile directory:

```sh
python -m pip install -r ../../requirements-hardware.txt
python examples/run_native.py .local/config-native
```

It creates ten generated pairs, retains independent requests/selected and default
headers, observes four roles through the parent frontends, and checks a separate
compiled consumer's actual dimensions and feature/mode values. Payload and storage
families use different native symbol names mapped to the same workflow roles.
No tool is installed by the recipe itself.

To adopt the activity:

1. Identify the original accepted configuration request and the stage at which
   each value becomes effective. Include defaults and generator inputs.
2. Ask the RTL/firmware owners which resolved parameters or constants actually
   govern the consumer, including mode and feature selection.
3. Capture those values using the qualified frontends, or supply independently
   validated native exports. Retain complete declared dependencies and source
   identities rather than comparing requested argument strings.
4. Write the semantic-role and unit contract from the requirement, not from the
   observed values. Review exact conversion rules and applicability.
5. Run the review. Route stale defaults, peer disagreement, wrong requirements
   or nonintegral conversion to the owning source/generator/configuration stage.
6. Regenerate, elaborate/compile and revalidate after correction. Keep the request,
   captures/evidence, contract, report and receiving owner's decision together.

Use [REVIEW.md](REVIEW.md) for the interpretation and handoff beyond numeric
comparison.

## AI-led setup and result interpretation

Give a file/tool-enabled assistant [WORKFLOW.md](WORKFLOW.md), the original
request and consumed generator/RTL/header/build sources:

> Find the effective values that control this interface in the selected mode.
> Trace defaults and overrides through elaboration and compilation. Map native
> symbols to independently required roles and units, and distinguish agreement
> from correctness. Ask for missing source/phase/conversion evidence.

Use [ONBOARDING.md](../../../../ONBOARDING.md), module `descriptor-layout-check` /
activity `configuration-consistency`. Existing AI hosts and company-native
methods remain usable beyond the helper. Optional DVIT intent/dependency context
can expose stale requirement/configuration relationships; it is not required.

| Exit | Meaning |
|---:|---|
| 0 | Within the selected configuration contract. |
| 1 | Known required-value, peer or conversion finding; concurrent gaps remain visible. |
| 2 | Incomplete or unqualified evidence without a known finding. |
| 3 | Invalid record, source binding or I/O. |

Argument errors use exit 2. Foreign/stale views are not interpreted as valid
current facts. Matching selected values does not qualify generator closure,
whole layout, runtime feature interactions, protocol behavior or formal/DFT/STA
constraints. Other frontends, ABIs and wider transformations need their own
qualified evidence.

```sh
python -m unittest discover -s tests -v
```

Use `OPENTOOLS_CONFIG_NATIVE=1` in the qualified native environment to include
the native tests; ordinary reference review needs no compiler or simulator.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
