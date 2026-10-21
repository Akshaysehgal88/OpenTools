# Configuration semantic consistency

Review selected generated configuration values before hardware/software handoff.
Use the [AI workflow](WORKFLOW.md) and [review record](REVIEW.md) with independent
requirements, native exports, source definitions and unit/phase relationships.
This profile extends [descriptor layout check](../../README.md); configuration
agreement and binary-layout agreement are separate questions.

Python3.10+ standard library, from this profile directory:

```sh
python examples/create_example.py /tmp/configuration-example --case payload-stale-default
python configuration_review.py /tmp/configuration-example/hardware.json /tmp/configuration-example/software.json /tmp/configuration-example/contract.json
python -m unittest discover -s tests -v
```

Expected review exit:1. Software uses an effective4-byte default against required
64 bits. `payload-matched` correctly relates64 bits to8 bytes. Equal raw64 values
in `payload-same-number` disagree after explicit conversion. Two sources agreeing
on the wrong default also fail the independent requirement.

The optional comparator covers one to five signed64 roles with explicit identity
or exact rational scale rules. It checks captured source/configuration/phase
bindings before comparing values. Unknown transforms or intent stay gaps; there
is no guessed conversion, rounding or automatic repair. [FORMAT.md](FORMAT.md)
defines records and limits. Reference fixtures are labeled separately from native
captures.

The parent capture CLI adds optional repeated `--parameter-fact NAME` for Slang
and `--constant NAME` for GCC. These observe resolved values, not requested inputs
or textual parameter renderings. See the [native recipe](examples/NATIVE.md).
Existing capture commands retain their original output when these options are absent.

Exits:0 within selected contract,1 known finding,2 incomplete without a known
finding,3 invalid input/I/O. Findings retain concurrent gaps. `--output` requires
a new file. Install the parent module with the project-local installer.
Your existing AI host is sufficient; optional [context sources](../../../../CONTEXT_PORT.md)
may add scoped relationships. Nothing installs DVIT or another model service.
