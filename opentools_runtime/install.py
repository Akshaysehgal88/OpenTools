"""Self-contained project-local skill export; no package/model/DVIT installation."""
from pathlib import Path
import os
import shutil
import tempfile

from . import __version__
from .catalog import ROOT, module_catalog, select_modules
from .common import file_hash, inside, read_json, require, shape, write_json

HOST_DIRS = {"codex": ".agents/skills", "claude": ".claude/skills", "generic": ".opentools/skills"}
RECEIPT = "opentools-install.json"
ROOT_FILES = ("LICENSE", "NOTICE", "BRANDING.txt",
              "opentools.py", "SKILL.md", "USING_THE_GUIDES.md", "ARCHITECTURE.md", "INSTALL.md", "CONTEXT_PORT.md",
              "opentools_runtime/__init__.py", "opentools_runtime/common.py", "opentools_runtime/catalog.py",
              "opentools_runtime/install.py", "opentools_runtime/context.py", "opentools_runtime/cli.py",
              "context_examples/provider.py", "context_examples/create_demo.py",
              "ONBOARDING.md", "INTENT.md", "DVIT.md", "opentools_runtime/onboarding.py",
              "opentools_runtime/intent.py", "opentools_runtime/onboard_cli.py")


def package_files(root, modules):
    root = Path(root).resolve()
    paths = [root / name for name in ROOT_FILES]
    for module in modules:
        base = root / "modules" / module["id"]
        paths.append(base / "module.json")
        for relative in module["files"]:
            path = base / relative
            require(not any(p.startswith(".") for p in Path(relative).parts)
                    and path.suffix not in (".pyc", ".pyo") and "__pycache__" not in path.parts,
                    "Refusing hidden/generated module payload")
            paths.append(path)
    for path in paths:
        require(path.is_file() and not path.is_symlink() and inside(path, root), "Missing or unsafe package file")
    return {path.relative_to(root).as_posix(): file_hash(path) for path in sorted(set(paths))}


def bundle_path(project, host):
    require(host in HOST_DIRS, "Unknown host; use codex, claude or generic")
    project = Path(project).resolve()
    require(project.is_dir(), "Project directory must already exist")
    target = project / HOST_DIRS[host] / "opentools"
    require(inside(target, project), "Install target escapes the chosen project")
    return target


def install(project, host, selected=None, dry_run=False, root=ROOT):
    modules = select_modules(module_catalog(root), selected)
    require(modules, "No available AI workflows selected")
    files = package_files(root, modules)
    target = bundle_path(project, host)
    receipt = {"format": "opentools.install.v1", "version": __version__, "host": host,
               "modules": [item["id"] for item in modules], "files": files}
    result = {"target": str(target), "modules": receipt["modules"], "file_count": len(files),
              "status": "planned" if dry_run else "installed", "workflow": str(target / "SKILL.md")}
    if target.exists():
        existing = verify_install(project, host)
        require(existing == receipt, "Existing package differs; preserve local edits and uninstall/reinstall explicitly")
        result["status"] = "unchanged"
        return result
    if dry_run:
        return result
    target.parent.mkdir(parents=True, exist_ok=True)
    # Parent directories can already exist as links; recheck their resolved target.
    require(inside(target, Path(project).resolve()), "Install parent redirects outside the project")
    staging = Path(tempfile.mkdtemp(prefix=".opentools-stage-", dir=target.parent))
    require(inside(staging, target.parent), "Unsafe staging directory")
    try:
        for relative in files:
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(root) / relative, destination)
            require(file_hash(destination) == files[relative], "Source changed while packaging")
        write_json(staging / RECEIPT, receipt)
        require(not target.exists(), "Install destination appeared during packaging")
        os.rename(staging, target)
    except BaseException:
        # Remove only this newly created, verified staging tree, never a user tree.
        require(inside(staging, target.parent) and staging.name.startswith(".opentools-stage-"), "Unsafe cleanup target")
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return result


def verify_install(project, host):
    target = bundle_path(project, host)
    require(target.is_dir() and not target.is_symlink(), "No owned installation at target")
    receipt = read_json(target / RECEIPT)
    shape(receipt, {"format", "version", "host", "modules", "files"})
    require(receipt["format"] == "opentools.install.v1" and receipt["host"] == host and isinstance(receipt["files"], dict), "Invalid install receipt")
    actual = set()
    for path in target.rglob("*"):
        require(not path.is_symlink(), "Installation contains a symlink")
        if path.is_file():
            if "__pycache__" in path.parts and path.suffix == ".pyc":
                continue
            actual.add(path.relative_to(target).as_posix())
    require(actual == set(receipt["files"]) | {RECEIPT}, "Installation contains missing or additional user files")
    for relative, expected in receipt["files"].items():
        path = target / relative
        require(inside(path, target) and path.is_file() and file_hash(path) == expected, "Installed file was modified")
    return receipt


def uninstall(project, host):
    target = bundle_path(project, host)
    receipt = verify_install(project, host)
    # No recursive delete: verify ownership/content first and remove only files
    # from the receipt and generated Python caches inside this exact bundle.
    require(inside(target, Path(project).resolve()) and target.name == "opentools", "Unsafe uninstall target")
    paths = list(target.rglob("*"))
    for path in paths:
        require(inside(path, target) and not path.is_symlink(), "Unsafe uninstall entry")
    for path in paths:
        if path.is_file():
            path.unlink()
    for path in sorted((p for p in paths if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        path.rmdir()
    target.rmdir()
    return {"status": "uninstalled", "target": str(target), "modules": receipt["modules"]}
