# Native campaign evidence

This Linux recipe compiles a small owned SystemVerilog handshake model and runs
nine native attempts. It exports actual DUT accepted counters, checker verdicts,
named payload goals, stimulus cycles and process wall observations, then reviews
completed cumulative exports offline. No scheduler or model service is used.

Requirements: Python 3.10+, installed Verilator, GCC C++17 and GNU Make. From the
module directory:

```sh
python examples/verilator/run_example.py native-demo --verilator /path/to/verilator
# Extracted verilator_bin also needs --verilator-root /path/to/share/verilator
```

Output must be new. A space-free owned `/tmp` directory holds the build; only that
scratch directory is cleaned up. Exact sources, binary, native argv/stdout/stderr/
exit/checker counts, exports, reports and scoped costs remain in the output.
No dependency is downloaded. Core/recipe/source/binary hashes identify the exercise.

The declared campaign requires three native checker passes, four named payload
goals and 192 checked handshakes. Its first two attempts hit the same three goals
but increase effective exposure 64 to 128; the remaining required run/exposure and
unhit goal remain explicit. A directed third attempt reaches the recorded targets
without establishing release criteria or stopping authority.

Three other attempts advance 64 stimulus cycles and 195 ticks each, yet accept zero
transactions because the driver disables the active path. They demonstrate genuine
ineffective execution for this explicit exposure objective. Changed configuration
is not pooled. A three-bin definition would display 100% against the earlier four-
bin population's 75%; it is not new comparable coverage. A deliberate checker
failure retains valid counter data but cannot count under passed-only policy. A
deliberately partial export preserves its missing-record gap and original journals.

Qualified with Verilator 5.020 on Linux. Coverage here is a source-defined Boolean
goal set, not UCIS/UVM functional coverage. Native Windows/macOS, commercial tools
and production campaigns are unqualified. Deterministic stimulus and a local checker do not establish independent trials
or reliability confidence. Event counts, resource costs and engineering decisions
remain separate. Ordinary offline use requires no simulator.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
