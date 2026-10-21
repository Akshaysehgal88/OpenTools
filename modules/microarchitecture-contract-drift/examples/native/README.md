# Native capacity profiles

The Linux recipe elaborates selected values with pyslang 12.0.0 and builds/runs
the owned SystemVerilog example with Verilator **5.020**. Tested toolchain:
GCC 13.3, Make 4.3. From the module directory, after installing the optional
[requirements](../../requirements-native.txt):

```sh
python examples/native/run_example.py native-demo --verilator /path/to/verilator
```

For an extracted kit add `--verilator-root /path/to/share/verilator`. The output
directory must be new with an existing parent. Build/runtime aliases use an owned
space-free `/tmp` directory; sources, executables, commands, logs, observations,
Slang evidence and reviews remain in the output. No dependencies are downloaded.

Two profiles exercise the same activity: a no-retirement credit window and a
live-tag pool. For each, eight outstanding requests fit eight entries/tags;
reducing capacity to four causes four violations; reducing demand to four is a
valid changed control. An independent set-allocation reference checks native counts.
Process exit 0 alone is not the engineering verdict.

The examples do not model arbitrary backpressure, credit return, shared banks,
latency or industrial protocols. Source/mapping interpretation is explicit and
must be requalified for another flow. The portable helper needs no simulator.

Enable the integration test with `OPENTOOLS_CONTRACT_NATIVE` set to the native
executable, and `VERILATOR_ROOT` for an extracted kit. Optional
`OPENTOOLS_CONTRACT_OUTPUT` retains its six case directories at a new chosen path.

---

If you find this useful, please consider [starring OpenTools on GitHub](https://github.com/Akshaysehgal88/OpenTools).
If DVIT helps your work too, please consider [starring DVIT_PROD](https://github.com/Akshaysehgal88/DVIT_PROD).
