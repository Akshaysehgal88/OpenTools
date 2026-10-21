# Diagnostic validity through recovery

Review what a selected diagnostic read or saved capture can establish after
reset, destructive reads or loss of access. This profile extends
[side-effect and access-order review](../../README.md). Use the [workflow](WORKFLOW.md)
and [review record](REVIEW.md) with native source and the existing AI host.

Python 3.10+ standard library, from this profile directory:

```sh
python examples/create_example.py /tmp/diagnostic-example --case post-reset-zero
python diagnostic_review.py /tmp/diagnostic-example/spec.json /tmp/diagnostic-example/journal.json /tmp/diagnostic-example/policy.json
python -m unittest discover -s tests -v
```

Expected review exit: 1. The later zero belongs to a cleared status epoch and
cannot establish pre-recovery absence. `pre-reset-snapshot` preserves an actual
earlier read; `no-fault-control` supports absence only in its declared observed
prefix. `post-reset-undetermined` preserves an unknown answer and exits2.

The helper supports one sticky cause bit, known reset/read effects, quiescent
accepted reads and one saved-read receipt. Observed bits, epoch applicability and
negative coverage remain separate. An unavailable response is not zero evidence;
a stale valid record is not current-incident evidence. [FORMAT.md](FORMAT.md)
defines the reviewed inputs and limits. [Native controls](examples/NATIVE.md)
exercise an owned latch, response capture and recovery path under Verilator.

Exits: 0 within supplied observed evidence, 1 known finding, 2 incomplete without
a known finding, 3 invalid input/I/O. Findings retain accompanying gaps. `--output`
requires a new file. This is evidence-validity review, not fault bucketization or
silicon root-cause diagnosis. Use existing native tools beyond the helper profile.

Install the parent module through the project-local installer. Optional
[context sources](../../../../CONTEXT_PORT.md) may supply scoped evidence
relationships; the workflow works without DVIT and never installs it.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
