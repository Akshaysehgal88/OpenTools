import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(MODULE / "examples"))
from address_core import compare, digest, exit_code, read_json, uncovered
from create_example import maps, policy


class AddressTests(unittest.TestCase):
    def case(self, name="valid"):
        hardware, software = maps(name)
        return compare(hardware, software, policy(hardware, software))

    def test_valid_alias_is_not_an_address_overlap(self):
        result = self.case()
        self.assertEqual(exit_code(result), 0)
        self.assertEqual(result["aliases"][0]["status"], "allowed_under_supplied_policy")
        self.assertFalse(result["findings"])

    def test_allowed_alias_does_not_hide_overlapping_address_decode(self):
        result = self.case("overlap")
        self.assertEqual(exit_code(result), 1)
        self.assertTrue(any(f["kind"] == "address_overlap" for f in result["findings"]))

    def test_per_initiator_permission_difference_is_retained(self):
        result = self.case("permission")
        difference = next(f for f in result["findings"] if f["path"] == "permissions.write")
        self.assertTrue(difference["hardware_value"])
        self.assertFalse(difference["software_value"])
        self.assertEqual(difference["hardware"], "device-main")

    def test_coordinated_address_change_is_a_valid_control(self):
        self.assertEqual(exit_code(self.case("paired")), 0)

    def test_required_decode_missing_in_complete_and_partial_export(self):
        hardware, software = maps("hole")
        complete = compare(hardware, software, policy(hardware, software))
        self.assertEqual(exit_code(complete), 1)
        self.assertTrue(any(f["kind"] == "required_decode_gap" for f in complete["findings"]))
        hardware["inputs_complete"] = False
        partial = compare(hardware, software, policy(hardware, software))
        self.assertEqual(exit_code(partial), 2)
        self.assertFalse(partial["findings"])

    def test_independent_requirement_survives_agreeing_missing_views(self):
        hardware, software = maps()
        hardware["windows"].pop()
        software["windows"].pop()
        result = compare(hardware, software, policy(hardware, software))
        self.assertEqual(exit_code(result), 1)
        self.assertTrue(any(f["kind"] == "required_decode_gap" for f in result["findings"]))

    def test_stale_unused_alias_rule_is_not_silently_accepted(self):
        hardware, software = maps()
        rules = policy(hardware, software)
        rules["aliases"].append({"initiator_ref": "device", "windows": ["absent-a", "absent-b"],
                                 "allow_differences": [], "evidence_ref": "old-policy"})
        self.assertEqual(exit_code(compare(hardware, software, rules)), 2)

    def test_alias_rule_is_scoped_to_exact_initiator_and_pair(self):
        hardware, software = maps()
        rules = policy(hardware, software)
        rules["aliases"][0]["initiator_ref"] = "device"
        result = compare(hardware, software, rules)
        self.assertTrue(any(f["kind"] == "unreviewed_target_alias" for f in result["findings"]))

    def test_alias_attribute_differences_need_explicit_policy(self):
        hardware, software = maps()
        for view in (hardware, software):
            view["windows"][1]["attributes"]["cacheable"] = False
        rules = policy(hardware, software)
        result = compare(hardware, software, rules)
        self.assertEqual(exit_code(result), 1)
        self.assertTrue(any(f["kind"] == "alias_attribute_difference" for f in result["findings"]))
        rules["aliases"][0]["allow_differences"] = ["attributes.cacheable"]
        self.assertEqual(exit_code(compare(hardware, software, rules)), 0)

    def test_partial_target_alias_does_not_receive_full_alias_verdict(self):
        hardware, software = maps()
        for view in (hardware, software):
            view["windows"][1]["target_base"] = 8
        result = compare(hardware, software, policy(hardware, software))
        self.assertEqual(exit_code(result), 2)
        self.assertFalse(result["aliases"])

    def test_stale_foreign_and_different_semantic_basis_block_requested_verdict(self):
        for change in ("hash", "scope", "basis"):
            hardware, software = maps("permission")
            rules = policy(hardware, software)
            if change == "hash":
                rules["hardware_sha256"] = "0" * 64
            elif change == "scope":
                rules["scope"]["project_ref"] = "other"
            else:
                rules["basis_ref"] = "requested-rather-than-effective-permissions"
            result = compare(hardware, software, rules)
            self.assertEqual(exit_code(result), 2)
            self.assertFalse(result["findings"])

    def test_nulls_remain_unknown_and_false_values_are_known(self):
        for key in ("base", "size", "target_base", "target_ref", "initiator_ref", "evidence_ref"):
            hardware, software = maps()
            hardware["windows"][0][key] = None
            result = compare(hardware, software, policy(hardware, software))
            self.assertNotEqual(exit_code(result), 0, key)
            self.assertTrue(result["gaps"], key)
        hardware, software = maps()
        hardware["windows"][2]["permissions"]["write"] = None
        self.assertEqual(exit_code(compare(hardware, software, policy(hardware, software))), 2)
        self.assertEqual(exit_code(self.case()), 0)

    def test_reversed_ambiguous_and_empty_correspondence_rejected(self):
        for wrong in ("duplicate", "empty"):
            hardware, software = maps()
            rules = policy(hardware, software)
            if wrong == "duplicate":
                rules["pairs"].append(copy.deepcopy(rules["pairs"][0]))
            else:
                rules["pairs"] = []
            with self.assertRaises(ValueError):
                compare(hardware, software, rules)

    def test_unknown_map_population_and_unmapped_windows_are_not_passes(self):
        hardware, software = maps()
        rules = policy(hardware, software)
        rules["pairs"].pop()
        self.assertEqual(exit_code(compare(hardware, software, rules)), 2)
        rules = policy(hardware, software)
        rules["population_complete"] = False
        self.assertEqual(exit_code(compare(hardware, software, rules)), 2)

    def test_invalid_intervals_attribute_types_and_duplicate_ids_rejected(self):
        for key, value in (("size", 0), ("base", -1), ("base", True), ("size", 1.5)):
            hardware, software = maps()
            hardware["windows"][0][key] = value
            with self.assertRaises(ValueError):
                compare(hardware, software, policy(hardware, software))
        hardware, software = maps()
        hardware["windows"].append(copy.deepcopy(hardware["windows"][0]))
        with self.assertRaises(ValueError):
            compare(hardware, software, policy(hardware, software))
        hardware, software = maps()
        hardware["windows"][0]["permissions"]["read"] = 1
        with self.assertRaises(ValueError):
            compare(hardware, software, policy(hardware, software))

    def test_required_range_union_matches_independent_byte_set(self):
        populations = [[], [(0, 3)], [(0, 3), (2, 7)], [(1, 2), (4, 2), (6, 1)], [(0, 12), (3, 2)]]
        for segments in populations:
            windows = [{"base": first, "size": count} for first, count in segments]
            for base in range(8):
                actual = uncovered(base, 5, windows)
                expected = set(range(base, base + 5)) - set().union(*(set(range(a, a + n)) for a, n in segments))
                expanded = set().union(*(set(range(a, b)) for a, b in actual))
                self.assertEqual(expanded, expected, (segments, base))

    def test_cli_actual_example_unicode_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="map space ") as tmp:
            area = Path(tmp) / "demo"
            subprocess.run([sys.executable, str(MODULE / "examples/create_example.py"), str(area)], check=True)
            output = Path(tmp) / "review-é.json"
            command = [sys.executable, str(MODULE / "address_review.py"), "compare", str(area / "hardware.json"),
                       str(area / "software.json"), str(area / "policy.json"), "--json-out", str(output)]
            process = subprocess.run(command, capture_output=True)
            self.assertEqual(process.returncode, 1, process.stderr)
            self.assertEqual(read_json(output)["status"], "review_required")
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 3)

    def test_duplicate_keys_and_nonfinite_data_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            for data in ('{"base":1,"base":2}', '{"base":NaN}'):
                path.write_text(data, encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_json(path)


@unittest.skipUnless(os.environ.get("OPENTOOLS_ADDRESS_NATIVE"), "Opt-in native GCC/Verilator recipe is disabled")
class NativeMapTests(unittest.TestCase):
    def test_generated_decoder_and_native_software_map_controls(self):
        spec = importlib.util.spec_from_file_location("address_native", MODULE / "examples/run_native.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            directory = os.environ.get("OPENTOOLS_ADDRESS_OUTPUT") or str(Path(tmp) / "native")
            results = module.run_native(directory, os.environ["OPENTOOLS_ADDRESS_NATIVE"], os.environ.get("VERILATOR_ROOT"))
            self.assertEqual(len(results), 5)
            self.assertEqual(sum(r["disagreements"] > 0 for r in results), 3)
            self.assertTrue(all(r["queries"] > 0 for r in results))


if __name__ == "__main__":
    unittest.main()
