"""A qualified PyUCIS XML path; no database reader is implemented here."""
from __future__ import annotations

import hashlib
import io
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from coverage_core import definition, indexed, require, text, validate

PYUCIS_VERSION = "0.2.0.22787133465"


def inspect_xml(path):
    try:
        installed = version("pyucis")
        require(installed == PYUCIS_VERSION, f"Qualified PyUCIS version is {PYUCIS_VERSION}; found {installed}")
        from lxml import etree
        from ucis.xml.xml_factory import XmlFactory
        from ucis.scope_type_t import ScopeTypeT as S
        from ucis.cover_type_t import CoverTypeT as C
    except (ImportError, PackageNotFoundError) as exc:
        raise ValueError("UCIS import requires the optional requirements-ucis.txt dependencies") from exc
    raw = Path(path).read_bytes()
    # Sanitize the document before handing it to the existing schema validator/reader.
    tree = etree.parse(io.BytesIO(raw), etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, remove_comments=True, remove_pis=True))
    require(not tree.docinfo.doctype, "DTD/entity declarations are not supported")
    for element in tree.iter():
        require(isinstance(element.tag, str), "XML comments/processing instructions are outside this import profile")
        element.tag = etree.QName(element).localname
    # This preflight detects shapes the qualified library would otherwise truncate
    # or default. The library still owns XML validation and database interpretation.
    for cp in tree.iter("coverpoint"):
        options = cp.find("options")
        require(options is not None and all(k in options.attrib for k in ("at_least", "weight", "goal")),
                "Coverpoint options must explicitly include at_least, weight and goal")
        for b in cp.findall("coverpointBin"):
            require(b.get("type") in ("bins", "ignore", "illegal"), "Default/unspecified bin types are not supported")
            ranges = b.findall("range")
            require(len(ranges) == 1 and not b.findall("sequence") and len(ranges[0].findall("contents")) == 1,
                    "Only one range/count per bin is supported; sequence/multi-range bins are outside this profile")
    db = XmlFactory.read(io.BytesIO(etree.tostring(tree)))
    digest = hashlib.sha256(raw).hexdigest()
    points = []

    def segment(kind, name):
        return (kind + ":" + name).replace("~", "~0").replace("/", "~1")

    def walk(scope, path_parts=(), in_instance=False):
        for child in scope.scopes(-1):
            kind = child.getScopeType()
            parts = path_parts + (segment(kind.name, child.getScopeName()),)
            instance = in_instance or kind == S.COVERINSTANCE
            if kind == S.COVERPOINT and instance:
                point_id = "/".join(parts)
                bins = list(child.coverItems(C.CVGBIN | C.IGNOREBIN | C.ILLEGALBIN))
                for nested in child.scopes(S.CVGBINSCOPE | S.IGNOREBINSCOPE | S.ILLEGALBINSCOPE):
                    bins.extend(nested.coverItems(C.CVGBIN | C.IGNOREBIN | C.ILLEGALBIN))
                converted = []
                for bin_ in bins:
                    data = bin_.getCoverData()
                    converted.append({"id": bin_.getName(), "kind": {C.CVGBIN: "regular", C.IGNOREBIN: "ignore", C.ILLEGALBIN: "illegal"}[data.type],
                                      "count": data.data, "definition": None, "definition_evidence": None,
                                      "evidence_ref": f"sha256:{digest}#{point_id}/{segment('BIN', bin_.getName())}"})
                points.append({"id": point_id, "at_least": child.getAtLeast(), "weight": child.getWeight(), "goal": child.getGoal(),
                               "definition": None, "definition_evidence": None, "bins": converted,
                               "evidence_ref": f"sha256:{digest}#{point_id}"})
            walk(child, parts, instance)

    walk(db)
    indexed(points, "imported points")
    require(points, "No supported per-instance coverpoints were found")
    return {"format": "opentools.coverage-inventory.v1", "database_sha256": digest,
            "reader": f"PyUCIS {installed}", "points": points,
            "limits": ["Counts/kinds/options are from PyUCIS; definitions are deliberately unknown.",
                       "Only coverpoint instances are inventoried; cross/type/code-coverage totals are outside scope."]}


def context_template(inventory):
    return {"format": "opentools.coverage-context.v1", "database_sha256": inventory["database_sha256"],
            "run_id": "replace-with-run-id", "scope": "replace-with-selected-scope", "configuration_ref": "replace-with-configuration-id",
            "model_ref": "replace-with-model-revision", "tool_ref": "replace-with-producer-and-version",
            "population_complete": False,
            "points": [{"id": p["id"], "definition": None, "definition_evidence": None,
                        "bins": [{"id": b["id"], "definition": None, "definition_evidence": None} for b in p["bins"]]}
                       for p in inventory["points"]]}


def import_xml(path, context):
    inventory = inspect_xml(path)
    require(isinstance(context, dict) and context.get("format") == "opentools.coverage-context.v1", "Unsupported context format")
    require(set(context) <= {"format", "database_sha256", "run_id", "scope", "configuration_ref", "model_ref", "tool_ref", "population_complete", "points"}, "Unsupported context field")
    require(context.get("database_sha256") == inventory["database_sha256"], "Context is bound to a different XML digest")
    selected = indexed(context.get("points"), "context points")
    require(selected, "Select at least one point in the context")
    available = indexed(inventory["points"], "inventory points")
    require(selected.keys() <= available.keys(), "Context references an absent point")
    points = []
    for point_id, metadata in selected.items():
        require(set(metadata) <= {"id", "definition", "definition_evidence", "bins"}, "Context point can supply only identity and semantic metadata")
        point = available[point_id]
        definitions = indexed(metadata.get("bins"), "context bins")
        require(definitions.keys() == indexed(point["bins"], "native bins").keys(), "Context must list every bin of each selected point exactly once")
        definition(metadata)
        point.update({k: metadata.get(k) for k in ("definition", "definition_evidence")})
        for b in point["bins"]:
            require(set(definitions[b["id"]]) <= {"id", "definition", "definition_evidence"}, "Context bin can supply only identity and semantic metadata")
            definition(definitions[b["id"]])
            b.update({k: definitions[b["id"]].get(k) for k in ("definition", "definition_evidence")})
        points.append(point)
    snapshot = {"format": "opentools.coverage-snapshot.v1", "metric": "coverpoint-instance-bin-fraction",
                "source_ref": "sha256:" + inventory["database_sha256"], "points": points,
                **{k: context.get(k) for k in ("run_id", "scope", "configuration_ref", "model_ref", "tool_ref", "population_complete")}}
    validate(snapshot)
    return snapshot
