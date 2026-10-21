# Next-run planning

Record what another investigation step should establish before spending simulation
time. Use [SKILL.md](SKILL.md) with existing evidence, prior attempts, your runner
and your AI subscription. [RECORD.md](RECORD.md) is a short Markdown form; structured
JSON and the ledger helper are optional. See [AI_USAGE.md](AI_USAGE.md).

## Quick start

Python 3.10+; standard library only. From this module directory:

```sh
python examples/create_example.py demo
python experiment_ledger.py audit-plan demo/inspect-plan.json
python experiment_ledger.py review-result demo/inspect-plan.json demo/inspect-result.json --output demo/review.json
python experiment_ledger.py audit-plan demo/replay-plan.json --prior demo/inspect-plan.json
python experiment_ledger.py review-result demo/replay-plan.json demo/unexecuted-result.json
```

The examples include evidence-only inspection, unexecuted replay, an inadequate
late trace and divergent replay. The unexecuted/inconclusive cases return **2**;
divergence returns **1**. The helper launches no jobs. Use a new output directory.

## Plan and review

1. State the observation, plausible explanations and decision to make.
2. Inspect existing artifacts and prior attempts before requesting a run.
3. Record the original binary/configuration/input basis, fixed controls and intended
   intervention. Define attainable observations that distinguish the explanations.
4. Map plausible outcomes to next actions, including an inconclusive result and
   a stopping condition.
5. Append actual execution, observations, costs and interpretation to the original plan.

Same seed alone does not establish reproduction. Changed stimulus, forced signals
or timeout changes need an explicit relationship to the original execution.
A failed or exploratory run can inform an investigation without becoming a passing
verification result.

## Helper boundary

The ledger checks exact plan/result binding, declared controls, source/completeness
fields and outcome maps. Repeated `--prior` inputs expose identical declared plans;
intentional replication remains possible. The AI/engineer must assess hypothesis
plausibility, semantic novelty, observation adequacy and source truth.

Keep failed, unexecuted, inconclusive and divergent attempts. Repeating an
inadequate collection without a changed observation plan does not resolve it.
See [FORMAT.md](FORMAT.md), [investigations](examples/INVESTIGATIONS.md),
[plan template](record.template.json) and [result template](result.template.json).

## Status and tests

`0` structurally complete plan or recorded outcome; `1` contradiction, failed
execution or divergence; `2` missing/unexecuted/inconclusive; `3` invalid input/I/O.
A zero status does not establish that an interpretation is true or another run useful.

```sh
python -m unittest discover -s tests -v
```

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
