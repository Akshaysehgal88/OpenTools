#!/usr/bin/env python3
"""Run a tiny native SiliconCompiler/Verilator lint control, not an ECC test."""
import argparse
import os
from pathlib import Path
import shutil

from siliconcompiler import Project, Design, Flowgraph
from siliconcompiler.tools.verilator.lint import LintTask
import siliconcompiler


class ExampleLint(LintTask):
    def setup(self):
        super().setup()
        self.set_exe(os.environ["OPENTOOLS_EXAMPLE_VERILATOR"], clobber=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--verilator", default="verilator")
    args = parser.parse_args()
    if siliconcompiler.__version__ != "0.38.11":
        parser.error("This example is qualified with SiliconCompiler 0.38.11")
    binary = shutil.which(args.verilator)
    if binary is None:
        parser.error("Verilator executable not found")
    os.environ["OPENTOOLS_EXAMPLE_VERILATOR"] = str(Path(binary).resolve())
    target = Path(args.directory).resolve()
    target.mkdir(parents=True, exist_ok=False)
    (target / "top.sv").write_text("module top #(parameter ECC_EN=0)(input logic a, output logic y); assign y=a; endmodule\n", encoding="utf-8")
    design = Design("top")
    design.set_dataroot("local", path=str(target))
    design.add_file("top.sv", fileset="rtl", dataroot="local")
    design.set_topmodule("top", fileset="rtl")
    design.set("fileset", "rtl", "param", "ECC_EN", "0")
    flow = Flowgraph("example-lint")
    flow.node("lint", ExampleLint())
    project = Project()
    project.set_design(design)
    project.set_flow(flow)
    project.add_fileset("rtl")
    project.option.set_builddir(str(target / "build"))
    project.set("option", "hash", True)
    project.write_manifest(str(target / "before.pkg.json"))
    project.run()
    # This final job manifest contains node records. Saving the parent Project
    # again would put the executed job inside history instead of its root records.
    manifest = target / "build/top/job0/top.pkg.json"
    print(f"Native job manifest: {manifest}")
    print("This is a lint control with ECC_EN=0, not functional ECC verification.")


if __name__ == "__main__":
    main()
