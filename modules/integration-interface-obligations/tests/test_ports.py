import importlib.metadata
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
from port_capture import capture, read_json
from create_inputs import inputs


def has_slang():
    try:
        return importlib.metadata.version("pyslang") == "12.0.0"
    except importlib.metadata.PackageNotFoundError:
        return False


class RecordTests(unittest.TestCase):
    def test_duplicate_keys_and_nonfinite_json_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "input.json"
            for source in ('{"x":1,"x":2}', '{"x":Infinity}'):
                p.write_text(source, encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_json(p)

    def test_example_records_are_created_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "inputs"
            cmd = [sys.executable, str(MODULE / "examples/create_inputs.py"), str(output)]
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            self.assertEqual(read_json(output / "selection.json"), inputs()["selection"])
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)


@unittest.skipUnless(has_slang(), "Optional pyslang 12.0.0 is absent")
class NativePortTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="interface space ")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)

    def owned(self, parameters=None, complete=True):
        data = inputs()
        return capture([str(MODULE / "examples/handshake.sv")], [], "behavior_top", parameters or data["parameters"],
                       data["selection"], data["scope"], complete, self.path / "evidence")

    def custom(self, expression="n", direction=False, width=4):
        source = self.path / "ports.sv"
        source.write_text(f'''module producer(output logic [3:0] a);assign a=0;endmodule
module consumer(input logic [{width-1}:0] a);endmodule
module top;wire [3:0] n,m;producer u(.a(n));consumer v(.a({expression}));endmodule''', encoding="utf-8")
        selection = {"format": "opentools.port-selection.v1", "links": [
            {"id": "data", "source": "v.a" if direction else "u.a", "sink": "u.a" if direction else "v.a"}]}
        return capture([str(source)], [], "top", {}, selection, inputs()["scope"], True, self.path / "custom")

    def test_actual_selected_connectivity_widths_and_directions(self):
        report = self.owned()
        self.assertEqual(report["status"], "connected_within_profile")
        self.assertEqual(len(report["links"]), 4)
        for link in report["links"]:
            self.assertEqual(link["source"]["net"], link["sink"]["net"])
            self.assertEqual(link["source"]["width_bits"], 1)
            self.assertEqual(link["source"]["direction"], "Out")
            self.assertEqual(link["sink"]["direction"], "In")

    def test_behavioral_selector_change_does_not_change_port_fact_claim(self):
        report = self.owned({"BAD_ACK": 1, "BAD_CANCEL": 1, "PULSE_REQUEST": 1, "CANCEL_CYCLE": 3})
        self.assertEqual(report["status"], "connected_within_profile")
        self.assertEqual(report["provenance"]["parameters"]["BAD_ACK"], 1)

    def test_different_native_nets_remain_a_finding(self):
        report = self.custom("m")
        self.assertEqual(report["status"], "review_required")
        self.assertEqual(report["links"][0]["status"], "different_nets")

    def test_direction_mismatch_and_width_coercion_do_not_pass(self):
        self.assertEqual(self.custom(direction=True)["links"][0]["status"], "direction_mismatch")
        # Keep this second independent capture in a separate output directory.
        with tempfile.TemporaryDirectory() as tmp:
            self.path = Path(tmp)
            self.assertNotEqual(self.custom(width=8)["status"], "connected_within_profile")

    def test_inversion_is_unknown_direct_connection_not_equal_by_symbol_name(self):
        report = self.custom("~n")
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["links"][0]["status"], "needs_evidence")

    def test_partial_inventory_does_not_pass(self):
        report = self.owned(complete=False)
        self.assertEqual(report["status"], "incomplete")
        self.assertTrue(report["gaps"])

    def test_missing_instance_port_or_unconfirmed_override_fails(self):
        data = inputs()
        for i, endpoint in enumerate(("absent.req_o", "client.absent")):
            selection = json.loads(json.dumps(data["selection"]))
            selection["links"][0]["source"] = endpoint
            with self.assertRaises(ValueError):
                capture([str(MODULE / "examples/handshake.sv")], [], "behavior_top", {}, selection,
                        data["scope"], True, self.path / str(i))
        with self.assertRaises(ValueError):
            self.owned({"ABSENT": 1})

    def test_scope_selection_and_override_shapes_rejected(self):
        data = inputs()
        for key, bad in (("scope", {}), ("selection", {"format": "opentools.port-selection.v1", "links": []}),
                         ("parameters", {"BAD_ACK": True})):
            modified = dict(data)
            modified[key] = bad
            with self.assertRaises(ValueError):
                capture([str(MODULE / "examples/handshake.sv")], [], "behavior_top", modified["parameters"],
                        modified["selection"], modified["scope"], True, self.path / key)

    def test_invalid_native_source_retains_diagnostics(self):
        source = self.path / "invalid.sv"
        source.write_text("module invalid syntax ;", encoding="utf-8")
        data = inputs()
        with self.assertRaises(ValueError):
            capture([str(source)], [], "behavior_top", {}, data["selection"], data["scope"], True, self.path / "invalid")
        self.assertTrue((self.path / "invalid/diagnostics.json").is_file())

    def test_capture_cli_and_no_overwrite(self):
        data = inputs()
        for name, value in data.items():
            (self.path / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")
        command = [sys.executable, str(MODULE / "port_capture.py"), "--source", str(MODULE / "examples/handshake.sv"),
                   "--top", "behavior_top", "--parameters", str(self.path / "parameters.json"),
                   "--selection", str(self.path / "selection.json"), "--scope", str(self.path / "scope.json"),
                   "--complete-inputs", "--output", str(self.path / "connections.json")]
        result = subprocess.run(command, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 3)
        self.assertEqual(subprocess.run([sys.executable, str(MODULE / "port_capture.py")], capture_output=True).returncode, 2)


@unittest.skipUnless(os.environ.get("OPENTOOLS_INTERFACE_NATIVE"), "Opt-in native Verilator recipe is disabled")
class NativeBehaviorTests(unittest.TestCase):
    def test_connected_profiles_expose_receipt_completion_and_cancel_race(self):
        spec = importlib.util.spec_from_file_location("interface_native", MODULE / "examples/run_native.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            target = os.environ.get("OPENTOOLS_INTERFACE_OUTPUT") or str(Path(tmp) / "native")
            cases = module.run_native(target, os.environ["OPENTOOLS_INTERFACE_NATIVE"], os.environ.get("VERILATOR_ROOT"))
            self.assertEqual(len(cases), 8)
            self.assertTrue(all(c["port_status"] == "connected_within_profile" for c in cases))
            self.assertEqual(sum(c["behavior"]["premature_completion"] > 0 for c in cases), 2)
            self.assertEqual(sum(c["behavior"]["false_discard"] > 0 for c in cases), 2)


if __name__ == "__main__":
    unittest.main()
