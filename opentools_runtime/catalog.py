"""Discover independently packaged workflows without a fixed module count."""
import re
from pathlib import Path

from .common import read_json, relative_file, require, shape, text

ROOT = Path(__file__).resolve().parents[1]


def module_catalog(root=ROOT):
    result = []
    for path in sorted((Path(root) / "modules").glob("*/module.json")):
        require(not path.is_symlink() and not path.parent.is_symlink(), "Module packages may not be symlinks")
        record = read_json(path)
        shape(record, {"format", "id", "title", "description", "stages", "workflow", "helpers", "files"})
        require(record["format"] == "opentools.module.v1" and text(record["id"]) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", record["id"]), "Invalid module identity")
        require(record["id"] == path.parent.name, "Module ID must match its folder")
        require(text(record["title"]) and text(record["description"]), "Module title/description required")
        require(isinstance(record["stages"], list) and record["stages"] and all(text(v) for v in record["stages"]), "Engineering stages required")
        workflow = relative_file(path.parent, record["workflow"])
        require(workflow.name == "SKILL.md", "Portable workflow must be a SKILL.md")
        skill = workflow.read_text(encoding="utf-8")
        require(re.search(r"(?m)^name:\s*" + re.escape(record["id"]) + r"\s*$", skill), "Skill name must match module ID")
        require(isinstance(record["helpers"], list), "helpers must be a list")
        require(isinstance(record["files"], list) and record["files"] and all(text(v) for v in record["files"])
                and len(set(record["files"])) == len(record["files"]), "Declare unique distributable module files")
        require(record["workflow"] in record["files"], "Workflow must be in the package file list")
        for relative in record["files"]:
            relative_file(path.parent, relative)
        for helper in record["helpers"]:
            shape(helper, {"path", "purpose", "requirements"})
            relative_file(path.parent, helper["path"])
            require(helper["path"] in record["files"], "Helper must be in the package file list")
            require(text(helper["purpose"]) and isinstance(helper["requirements"], list)
                    and all(text(v) for v in helper["requirements"]), "Helper purpose and requirements required")
        result.append(record)
    return result


def select_modules(catalog, selected):
    names = {item["id"] for item in catalog}
    if not selected or selected == ["all"]:
        return catalog
    require("all" not in selected and len(set(selected)) == len(selected) and set(selected) <= names,
            "Select unique available module IDs, or all")
    return [item for item in catalog if item["id"] in selected]
