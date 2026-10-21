"""Create explicit two-initiator map records and a scoped alias policy."""
import argparse
import copy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from address_core import digest


def maps(case="valid"):
    def window(name, initiator, base, writable=True, cached=True):
        return {"id": name, "initiator_ref": initiator, "base": base, "size": 16,
                "target_ref": "owned-ram", "target_base": 0,
                "permissions": {"read": True, "write": writable, "execute": False},
                "attributes": {"cacheable": cached, "shareable": False, "secure_only": True},
                "evidence_ref": "owned-map:" + name}
    windows = [window("processor-main", "processor", 0x1000), window("processor-alias", "processor", 0x1100),
               window("device-main", "device", 0x2000, False, False)]
    scope = {"project_ref": "owned-example", "configuration_ref": case, "mode_ref": "functional"}
    software = {"format": "opentools.address-map.v1", "view_ref": "software-effective-map", "revision_ref": "owned-v1",
                "scope": scope.copy(), "address_unit": "bytes", "basis_ref": "effective-byte-route-and-permission-v1",
                "inputs_complete": True, "windows": windows}
    hardware = copy.deepcopy(software)
    hardware["view_ref"] = "generated-hardware-map"
    if case == "overlap":
        hardware["windows"][1]["base"] = 0x1008
    elif case == "permission":
        hardware["windows"][2]["permissions"]["write"] = True
    elif case == "hole":
        hardware["windows"].pop()
    elif case == "paired":
        hardware["windows"][2]["base"] = software["windows"][2]["base"] = 0x2100
    elif case != "valid":
        raise ValueError("Unknown owned example case")
    return hardware, software


def policy(hardware, software):
    # Consumer requirements are independent of the observed window census.
    # The paired fixture explicitly changes the requirement along with both views.
    device_base = 0x2100 if software["scope"]["configuration_ref"] == "paired" else 0x2000
    required = [("processor", 0x1000), ("processor", 0x1100), ("device", device_base)]
    return {"format": "opentools.address-policy.v1", "scope": software["scope"].copy(),
            "hardware_sha256": digest(hardware), "software_sha256": digest(software), "basis_ref": software["basis_ref"],
            "population_complete": True, "evidence_ref": "owned-map:integration-contract",
            "pairs": [{"hardware": name, "software": name, "evidence_ref": "owned-map:explicit-correspondence"}
                      for name in ("processor-main", "processor-alias", "device-main")],
            "aliases": [{"initiator_ref": "processor", "windows": ["processor-main", "processor-alias"],
                         "allow_differences": [], "evidence_ref": "owned-map:processor-alias-rationale"}],
            "required_decode": [{"initiator_ref": initiator, "base": base, "size": 16,
                                 "evidence_ref": "create_example.py:owned-consumer-requirements"} for initiator, base in required]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--case", choices=("valid", "overlap", "permission", "hole", "paired"), default="permission")
    args = parser.parse_args()
    directory = Path(args.directory)
    directory.mkdir(exist_ok=False)
    hardware, software = maps(args.case)
    for name, record in (("hardware", hardware), ("software", software), ("policy", policy(hardware, software))):
        (directory / (name + ".json")).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
