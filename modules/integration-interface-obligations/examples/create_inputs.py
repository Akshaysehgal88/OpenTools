"""Create selected-port input records and a short integration review record."""
import argparse
import json
from pathlib import Path


def inputs():
    return {"parameters": {"BAD_ACK": 0, "BAD_CANCEL": 0, "PULSE_REQUEST": 0, "CANCEL_CYCLE": 3},
            "scope": {"project_ref": "owned-example", "interface_ref": "single-outstanding",
                      "configuration_ref": "direct-ports", "mode_ref": "functional"},
            "selection": {"format": "opentools.port-selection.v1", "links": [
                {"id": "request", "source": "client.req_o", "sink": "worker.req_i"},
                {"id": "receipt", "source": "worker.accepted_o", "sink": "client.accepted_i"},
                {"id": "completion", "source": "worker.completed_o", "sink": "client.completed_i"},
                {"id": "discard", "source": "worker.discarded_o", "sink": "client.discarded_i"}]}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    args = parser.parse_args()
    directory = Path(args.directory)
    directory.mkdir(exist_ok=False)
    for name, value in inputs().items():
        (directory / (name + ".json")).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
