# Native selection comparison

This Linux recipe compiles four small owned SystemVerilog variants and runs six
native checker populations. Targeted and independently enumerated full campaigns
are separate native executions; full results are not a filtered selection. It
exercises local RTL, shared package, configuration, unmapped dependency, renamed
test and misleading mapping while retaining mandatory smoke/integration.

Requirements: Python 3.10+, installed Verilator, GCC C++17 and GNU Make. No package
is downloaded. From the module directory:

```sh
python examples/verilator/run_example.py native-demo --verilator /path/to/verilator
# Extracted verilator_bin also needs --verilator-root /path/to/share/verilator
```

The output must be new. The recipe builds in an owned space-free `/tmp` directory,
archives exact sources, binaries, argv/stdout/stderr/exit/checker counts and
per-attempt process wall observations, and removes only that scratch directory.
Four binaries serve seven scoped scenarios. Configuration 1 exposes a deliberate
fixture DMA defect; local/shared/glue variants introduce explicit defects. The C++
checker requires actual functional checks; exit alone is not a generic pass importer.

The local stage retains a smaller initial population with required omissions.
Shared/configuration/unknown impact broadens to all known tests. Renamed IDs need
review without guessed aliases. The misleading map is fully bound but falsely
classifies a shared edit as local and calls an incomplete map complete. Full results
expose failures outside selection: favorable plan status does not prove adequacy.

Qualified with Verilator 5.020, Linux, GCC 13.3 and Make 4.3. The fixture uses manual maps and deliberate defects; it does not establish
production dependency completeness or miss probability. Native Windows/macOS,
UVM, commercial simulators and DVSim export adaptation are not qualified. The
portable selector requires no simulator.
