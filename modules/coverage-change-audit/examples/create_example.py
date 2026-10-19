#!/usr/bin/env python3
"""Create the 180/200 -> 180/180 example, optionally via actual PyUCIS XML."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def normalized(current=False):
    return {"format": "opentools.coverage-snapshot.v1", "metric": "coverpoint-instance-bin-fraction",
            "run_id": "current" if current else "baseline", "scope": "synthetic opcode coverage",
            "configuration_ref": "synthetic-config-v1", "model_ref": "model-with-exclusions" if current else "model-v1",
            "tool_ref": "synthetic-generator-v1", "source_ref": "create_example.py", "population_complete": True,
            "points": [{"id": "top/cg_i/opcode", "definition": "sample opcode iff valid; per-instance; model-v1",
                        "definition_evidence": "create_example.py#normalized", "at_least": 1, "weight": 1, "goal": 100,
                        "evidence_ref": "synthetic-model#opcode",
                        "bins": [{"id": f"b{i:03}", "kind": "ignore" if current and i >= 180 else "regular",
                                  "count": 1 if i < 180 else 0, "definition": f"opcode == {i}",
                                  "definition_evidence": "create_example.py#normalized", "evidence_ref": f"synthetic-model#b{i:03}"}
                                 for i in range(200)]}]}


def write_ucis(path, current=False, instances=1):
    from ucis import UCIS_OTHER, UCIS_DU_MODULE, UCIS_INSTANCE, UCIS_CVGBIN, UCIS_IGNOREBIN
    from ucis.mem.mem_factory import MemFactory
    from ucis.xml.xml_factory import XmlFactory
    db = MemFactory.create()
    du = db.createScope("work.top", None, 1, UCIS_OTHER, UCIS_DU_MODULE, 0)
    top = db.createInstance("top", None, 1, UCIS_OTHER, UCIS_INSTANCE, du, 0)
    cg = top.createCovergroup("opcode_cg", None, 1, UCIS_OTHER)
    for n in range(instances):
        instance = cg.createCoverInstance(f"cg_i{n}", None, 1, UCIS_OTHER)
        cp = instance.createCoverpoint("opcode", None, 1, UCIS_OTHER)
        cp.setGoal(100)
        cp.setAtLeast(1)
        for i in range(200):
            cp.createBin(f"b{i:03}", None, 1, int(i < 180), f"opcode == {i}",
                         UCIS_IGNOREBIN if current and i >= 180 else UCIS_CVGBIN)
    # PyUCIS emits synthetic range placeholders; semantic context below is separate.
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        XmlFactory.write(db, stream)


def context_for(path, current=False):
    from ucis_import import context_template, inspect_xml
    context = context_template(inspect_xml(path))
    base = normalized(current)
    context.update({k: base[k] for k in ("run_id", "scope", "configuration_ref", "model_ref", "tool_ref", "population_complete")})
    for point in context["points"]:
        point.update(definition=base["points"][0]["definition"], definition_evidence="create_example.py#normalized")
        for bin_ in point["bins"]:
            i = int(bin_["id"][1:])
            bin_.update(definition=f"opcode == {i}", definition_evidence="create_example.py#normalized")
    return context


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory")
    parser.add_argument("--ucis", action="store_true", help="Exercise the optional PyUCIS XML path")
    args = parser.parse_args()
    out = Path(args.output_directory)
    out.mkdir(parents=True, exist_ok=False)
    for current in (False, True):
        name = "current" if current else "baseline"
        snapshot = normalized(current)
        if args.ucis:
            from ucis_import import import_xml
            path = out / f"{name}.xml"
            write_ucis(path, current)
            context = context_for(path, current)
            (out / f"{name}.context.json").write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
            snapshot = import_xml(path, context)
        (out / f"{name}.json").write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(f"Created synthetic baseline and current evidence in {out}")


if __name__ == "__main__":
    main()
