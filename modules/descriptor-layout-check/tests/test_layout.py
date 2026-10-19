import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
from layout_core import InputError, compare, fields, read_json
from layout_capture import hardware, software


def sample():
    common = {"format": "opentools.record-layout.v1", "record": "descriptor", "interface_ref": "synthetic-descriptor-v1",
              "configuration_ref": "example-default", "source_ref": "synthetic-source", "frontend_ref": "independent-test-oracle",
              "inputs_complete": True, "fields_complete": True, "size_bits": 192}
    fs = [{"name": name, "offset_bits": offset, "width_bits": width, "signed": False,
           "enum_values": {"OP_READ": 1, "OP_WRITE": 2} if name == "opcode" else {}, "evidence_ref": "oracle#" + name}
          for name, offset, width in (("address", 0, 64), ("length", 64, 32), ("opcode", 96, 32), ("reserved", 128, 32), ("padding", 160, 32))]
    h = {**common, "kind": "hardware", "basis": "packed-lsb", "fields": copy.deepcopy(fs)}
    s = {**common, "kind": "software", "basis": "c-object", "byte_order": "little", "alignment_bytes": 8,
         "integer_representation": "binary-twos-complement",
         "target_abi": "oracle LP64", "fields": copy.deepcopy(fs)}
    return h, s, read_json(MODULE / "examples/pairing.json")


class CoreTests(unittest.TestCase):
    def setUp(self): self.h, self.s, self.p = sample()
    def audit(self): return compare(self.h, self.s, self.p)

    def test_matching(self): self.assertEqual(self.audit()["status"], "matched_within_scope")

    def test_equal_size_swapped_fields(self):
        self.s["fields"][1]["offset_bits"], self.s["fields"][3]["offset_bits"] = 128, 64
        r = self.audit()
        self.assertEqual(r["status"], "mismatch")
        self.assertEqual(sum(m["property"] == "value_bit_address_mapping" for m in r["mismatches"]), 2)

    def test_encoding_difference(self):
        self.s["fields"][2]["enum_values"]["OP_WRITE"] = 3
        self.assertIn("encoding_value", [m["property"] for m in self.audit()["mismatches"]])

    def test_missing_encoding_is_incomplete(self):
        self.p["fields"][2]["encodings"].pop()
        self.assertEqual(self.audit()["status"], "incomplete")

    def test_signedness_difference(self):
        self.s["fields"][1]["signed"] = True
        self.assertIn("signed", [m["property"] for m in self.audit()["mismatches"]])

    def test_other_integer_representations_are_not_assumed_compatible(self):
        self.s["integer_representation"] = "sign-magnitude"
        with self.assertRaises(InputError): self.audit()

    def test_big_endian_numeric_mapping(self):
        self.p["hardware_byte_order"] = self.s["byte_order"] = "big"
        for f in self.s["fields"]:
            f["offset_bits"] = 192 - f["offset_bits"] - f["width_bits"]
        self.assertEqual(self.audit()["status"], "matched_within_scope")

    def test_equal_start_byte_different_scalar_endian(self):
        self.p["hardware_byte_order"] = "big"
        for f in self.s["fields"]:
            f["offset_bits"] = 192 - f["offset_bits"] - f["width_bits"]
        r = self.audit()
        self.assertTrue(all(row["hardware"]["lowest_address_byte"] == row["software"]["lowest_address_byte"] for row in r["fields"]))
        self.assertEqual(r["status"], "mismatch")

    def test_serializer_does_not_get_a_false_layout_defect(self):
        self.p["representation"] = "explicit-serializer"
        self.s["fields"][1]["offset_bits"], self.s["fields"][3]["offset_bits"] = 128, 64
        r = self.audit()
        self.assertEqual(r["status"], "incomplete")
        self.assertEqual(r["mismatches"], [])

    def test_alignment(self):
        self.p["required_alignment_bytes"] = 4
        self.assertIn("insufficient_boundary_alignment", [m["property"] for m in self.audit()["mismatches"]])

    def test_missing_config_or_fields_is_incomplete(self):
        self.h["configuration_ref"] = "other"
        self.assertEqual(self.audit()["status"], "incomplete")
        self.h["configuration_ref"] = "example-default"
        self.s["fields_complete"] = False
        self.assertIsNone(self.audit()["padding"]["software"])

    def test_unmapped_and_ambiguous_fields(self):
        self.p["fields"].pop()
        self.assertEqual(self.audit()["status"], "incomplete")
        self.p["fields"].append(copy.deepcopy(self.p["fields"][0]))
        with self.assertRaises(InputError): self.audit()

    def test_padding_reported_separately(self):
        self.s["size_bits"] = 256
        r = self.audit()
        self.assertEqual(r["padding"]["software"], [{"offset_bits": 192, "width_bits": 64}])
        self.assertTrue(r["mismatch_found"])

    def test_reject_overlap_bitfields_and_boolean_counts(self):
        for update in ({"offset_bits": 1}, {"width_bits": True}, {"width_bits": 7}, {"offset_bits": 0}):
            with self.subTest(update=update):
                h = copy.deepcopy(self.h); h["fields"][1].update(update)
                with self.assertRaises(InputError): fields(h)


class CliTests(unittest.TestCase):
    def test_compare_exit_states_and_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / n for n in ("h.json", "s.json", "p.json")]
            h, s, p = sample()
            def run():
                for path, value in zip(paths, (h, s, p)): path.write_text(json.dumps(value), encoding="utf-8")
                return subprocess.run([sys.executable, str(MODULE / "layout_check.py"), "compare", *map(str, paths)], capture_output=True).returncode
            self.assertEqual(run(), 0)
            s["fields"][1]["signed"] = True
            self.assertEqual(run(), 1)
            s["inputs_complete"] = False
            self.assertEqual(run(), 2)
            p["fields"].append(copy.deepcopy(p["fields"][0]))
            self.assertEqual(run(), 3)
            paths[0].write_text('{"x":1,"x":2}', encoding="utf-8")
            with self.assertRaises(InputError): read_json(paths[0])


@unittest.skipUnless(importlib.util.find_spec("pyslang"), "Optional Slang dependency is not installed")
class SlangTests(unittest.TestCase):
    def capture(self, tmp, source=None, parameters=None):
        return hardware([str(source or MODULE / "examples/descriptor.sv")], [], "descriptor_top", "descriptor_t", parameters or {},
                        "synthetic-descriptor-v1", "example-default", True, Path(tmp) / "hw-evidence")

    def test_actual_packed_offsets_enums(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = self.capture(tmp)
            expected, _, _ = sample()
            self.assertEqual([(f["name"], f["offset_bits"], f["width_bits"], f["enum_values"]) for f in sorted(h["fields"], key=lambda f:f["offset_bits"])],
                             [(f["name"], f["offset_bits"], f["width_bits"], f["enum_values"]) for f in expected["fields"]])

    def test_actual_parameter_changes_width_and_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = self.capture(tmp, parameters={"ADDR_W": 32})
            _, s, p = sample()
            self.assertEqual(h["size_bits"], 160)
            self.assertEqual(next(f["width_bits"] for f in h["fields"] if f["name"]=="address"), 32)
            self.assertEqual(compare(h, s, p)["status"], "mismatch")

    def test_unsupported_unpacked_union_nested_and_ascending(self):
        original = (MODULE / "examples/descriptor.sv").read_text()
        for changed in (original.replace("struct packed", "struct"), original.replace("struct packed", "union packed"),
                        original.replace("logic [31:0] padding", "logic [0:31] padding"),
                        original.replace("logic [31:0] padding", "struct packed { logic [31:0] value; } padding"),
                        original.replace("logic [31:0] padding", "logic [7:0][3:0] padding")):
            with self.subTest(), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "bad.sv"; path.write_text(changed)
                with self.assertRaises(InputError): self.capture(tmp, path)

    def test_missing_override_and_compile_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(InputError): self.capture(tmp, parameters={"MISSING": 3})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.sv"; path.write_text("module descriptor_top; invalid syntax here; endmodule")
            with self.assertRaises(InputError): self.capture(tmp, path)


HAS_GCC = sys.platform.startswith("linux") and shutil.which("gcc") is not None
@unittest.skipUnless(HAS_GCC, "Qualified GCC Linux environment is required")
class GccTests(unittest.TestCase):
    def capture(self, tmp, header=None, profile=None, complete=True):
        return software(str(header or MODULE / "examples/descriptor.h"), [], "descriptor", profile or read_json(MODULE / "examples/c-profile.json"),
                        "gcc", "synthetic-descriptor-v1", "example-default", True, complete, Path(tmp) / "c-evidence")

    def test_actual_compiler_offsets_and_encoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = self.capture(tmp)
            h, _, p = sample()
            self.assertEqual(compare(h, s, p)["status"], "matched_within_scope")
            self.assertEqual(s["alignment_bytes"], 8)

    def test_native_equal_size_negative_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            header = Path(tmp) / "descriptor with spaces.h"
            header.write_text((MODULE / "examples/descriptor.h").read_text().replace("uint32_t length;", "uint32_t temporary;").replace("uint32_t reserved;", "uint32_t length;").replace("uint32_t temporary;", "uint32_t reserved;"))
            s = self.capture(tmp, header)
            h, _, p = sample()
            self.assertEqual(s["size_bits"], 192)
            self.assertEqual(compare(h, s, p)["status"], "mismatch")

    def test_native_encoding_difference(self):
        with tempfile.TemporaryDirectory() as tmp:
            header = Path(tmp) / "bad.h"; header.write_text((MODULE / "examples/descriptor.h").read_text().replace("OP_WRITE = 2", "OP_WRITE = 3"))
            h, _, p = sample()
            self.assertIn("encoding_value", [m["property"] for m in compare(h, self.capture(tmp, header), p)["mismatches"]])

    def test_native_bitfields_pointers_arrays_and_bool_rejected(self):
        for declaration in ("unsigned length:32;", "uint32_t *length;", "uint32_t length[1];", "_Bool length;"):
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as tmp:
                header = Path(tmp) / "bad.h"; header.write_text((MODULE / "examples/descriptor.h").read_text().replace("uint32_t length;", declaration))
                with self.assertRaises(InputError): self.capture(tmp, header)

    def test_incomplete_field_inventory_remains_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = self.capture(tmp, complete=False)
            h, _, p = sample()
            self.assertEqual(compare(h, s, p)["status"], "incomplete")

    @unittest.skipUnless(importlib.util.find_spec("pyslang"), "Slang is required for combined native test")
    def test_combined_actual_frontends_cli_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp); base = [sys.executable, str(MODULE / "layout_check.py")]
            h, s, out = (tmp / name for name in ("h.json", "s.json", "audit.json"))
            common = ["--interface-ref", "synthetic-descriptor-v1", "--configuration-ref", "example-default", "--complete-inputs"]
            commands = [base + ["capture-hardware", "--source", str(MODULE / "examples/descriptor.sv"), "--top", "descriptor_top", "--type", "descriptor_t", "--output", str(h)] + common,
                        base + ["capture-software", "--header", str(MODULE / "examples/descriptor.h"), "--struct", "descriptor", "--profile", str(MODULE / "examples/c-profile.json"), "--complete-fields", "--output", str(s)] + common,
                        base + ["compare", str(h), str(s), str(MODULE / "examples/pairing.json"), "--json-out", str(out)]]
            for command in commands:
                r = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(read_json(out)["status"], "matched_within_scope")
            self.assertEqual(subprocess.run(commands[-1], capture_output=True).returncode, 3)


if __name__ == "__main__": unittest.main()
