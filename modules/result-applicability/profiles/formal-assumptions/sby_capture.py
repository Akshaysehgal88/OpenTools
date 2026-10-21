"""Read a qualified saved SBY task; never execute its configuration."""
from __future__ import annotations

import re
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from applicability_core import InputError, canonical, file_hash, read_json, require, shape, text

SBY_REVISION = "85dd50b92a3acf170954a06f20f49e2162ce5273"
YOSYS_VERSION = "Yosys 0.33 (git sha1 2584903a060)"
SCOPE_KEYS = {"clock_ref", "reset_ref", "integration_mode_ref", "model_scope_ref"}


def contained(root, relative):
    require(text(relative) and "\\" not in relative and ":" not in relative,
            "Use a relative POSIX artifact path")
    value = PurePosixPath(relative)
    require(not value.is_absolute() and all(p not in ("", ".", "..") for p in relative.split("/")),
            "Artifact paths must stay within the evidence root")
    root = Path(root).resolve()
    result = (root / relative).resolve()
    require(result.is_relative_to(root), "Artifact path escapes the evidence root")
    # Reject links even when their current target is contained; the receipt is of files.
    current = root
    for part in value.parts:
        current /= part
        require(not current.is_symlink(), "Linked evidence files/directories are unsupported")
    return result


def sections(content):
    result, current = {}, None
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            require(current not in result, "Duplicate SBY section")
            result[current] = []
        else:
            require(current is not None, "SBY content outside a section")
            result[current].append(line)
    require(set(result) == {"options", "engines", "script", "files"}, "Unsupported SBY section set")
    return result


def configuration(content):
    parsed = sections(content)
    options = {}
    for line in parsed["options"]:
        parts = line.split()
        require(len(parts) == 2 and parts[0] not in options, "Invalid/duplicate SBY option")
        options[parts[0]] = parts[1]
    require(set(options) == {"mode", "depth"} and options["mode"] in ("prove", "bmc", "cover"),
            "Qualified options are mode prove/bmc/cover and depth")
    require(options["depth"].isdigit() and 1 <= int(options["depth"]) <= 1000000, "Invalid depth")
    require(parsed["engines"] == ["smtbmc z3"], "Qualified engine is one smtbmc z3 engine")
    require(parsed["files"] == ["model.sv", "selection.vh"], "Qualified source layout is model.sv + selection.vh")
    script = parsed["script"]
    require(len(script) == 3 and script[0] == "read -formal model.sv" and script[2] == "write_json cells.json",
            "Unsupported model-construction script")
    match = re.fullmatch(r"prep -top ([A-Za-z_][A-Za-z_0-9]*)", script[1])
    require(match is not None, "Qualified script requires one explicit prep top")
    return options["mode"], int(options["depth"]), match[1]


def census(model, top):
    require(model.get("creator") == YOSYS_VERSION, "Unqualified Yosys creator")
    require(isinstance(model.get("modules"), dict) and set(model["modules"]) == {top},
            "Qualified census requires a single prepared module; hierarchy is unsupported")
    cells = model["modules"][top].get("cells")
    require(isinstance(cells, dict), "Native cell inventory missing")
    result = []
    for name, cell in sorted(cells.items()):
        if cell.get("type") in ("$assert", "$assume", "$cover"):
            src = cell.get("attributes", {}).get("src")
            require(text(src), "Formal cell source is missing")
            result.append({"id": name, "type": cell["type"], "source": src})
    return result


def engine_status(content, expected):
    statuses = re.findall(r"\bStatus: (passed|failed|unknown)\b", content)
    require(statuses == [expected] and content.strip().splitlines()[-1].endswith("Status: " + expected),
            "Engine terminal status missing or contradictory")


def capture(root, workdir, context):
    """Produce a parent-compatible snapshot from files under one retained root."""
    shape(context, {"format", "run_ref", "manifest_ref", "command", "sby_revision", "solver_version",
                    "dependency_capture_complete", "dependency_evidence_ref", "scope"})
    require(context["format"] == "opentools.formal-capture-context.v1", "Unsupported capture context")
    require(all(text(context[k]) for k in ("run_ref", "manifest_ref", "solver_version")), "Run/tool references required")
    require(context["sby_revision"] == SBY_REVISION, "Unqualified SBY revision declaration")
    require(context["solver_version"] == "Z3 version 4.8.12 - 64 bit", "Unqualified solver version declaration")
    require(context["command"] is None or (isinstance(context["command"], list) and context["command"] and
            all(text(v) for v in context["command"])), "Original command must be an argument list or null")
    require(context["dependency_capture_complete"] is None or type(context["dependency_capture_complete"]) is bool,
            "Invalid dependency completeness")
    require(context["dependency_evidence_ref"] is None or text(context["dependency_evidence_ref"]), "Invalid dependency basis")
    shape(context["scope"], SCOPE_KEYS)
    require(all(v is None or text(v) for v in context["scope"].values()), "Scope values must be references or null")
    folder = contained(root, workdir)
    require(folder.is_dir(), "Retained work directory is missing")
    tracked = {}

    def read(relative, json=False):
        full = workdir + "/" + relative
        path = contained(root, full)
        require(path.is_file(), "Missing native artifact: " + full)
        tracked[full] = file_hash(path)
        return read_json(path) if json else path.read_text(encoding="utf-8")

    mode, depth, top = configuration(read("config.sby"))
    tokens = read("status").split()
    require(len(tokens) == 3 and tokens[0] in ("PASS", "FAIL", "UNKNOWN", "ERROR") and
            all(v.isdigit() for v in tokens[1:]), "Unsupported native status encoding")
    status, returncode = tokens[0], int(tokens[1])
    require(returncode == {"PASS": 0, "FAIL": 2, "UNKNOWN": 4, "ERROR": 16}[status], "Inconsistent native status/exit")
    log = read("logfile.txt")
    terminal = re.findall(r"DONE \((PASS|FAIL|UNKNOWN|ERROR), rc=(\d+)\)", log)
    require(terminal == [(status, str(returncode))], "Native terminal status missing or contradictory")
    model = read("src/cells.json", True)
    cells = census(model, top)
    sources = {}
    for name in ("model.sv", "selection.vh"):
        read("src/" + name)
        sources[name] = tracked[workdir + "/src/" + name]
    witnesses, semantics = [], "unresolved"
    observed = "unknown"
    completed = status in ("PASS", "FAIL")
    if completed:
        if mode == "prove":
            base = read("engine_0/logfile_basecase.txt")
            engine_status(base, "passed" if status == "PASS" else "failed")
            if status == "PASS":
                induction = read("engine_0/logfile_induction.txt")
                engine_status(induction, "passed")
                require("Temporal induction successful." in induction, "Complete induction evidence missing")
                semantics, observed = "proved_within_model", "pass"
            else:
                require("BMC failed!" in base and "Assert failed in " in base and "Status: failed" in base,
                        "FAIL is not a qualified safety counterexample")
                witnesses = ["engine_0/trace.vcd", "engine_0/trace.yw"]
                semantics, observed = "counterexample", "fail"
        else:
            engine = read("engine_0/logfile.txt")
            engine_status(engine, "passed" if status == "PASS" else "failed")
            if mode == "cover":
                if status == "PASS":
                    require("Reached cover statement at " in engine, "Cover witness not established")
                    witnesses = ["engine_0/trace0.vcd", "engine_0/trace0.yw"]
                    semantics, observed = "activation_witness", "pass"
                else:
                    steps = [int(v) for v in re.findall(r"Checking cover reachability in step (\d+)\.\.", engine)]
                    require(steps == list(range(depth)) and "Unreached cover statement at " in engine,
                            "Full requested bounded cover attempt is not established")
                    semantics, observed = "not_reached_within_depth", "fail"
            elif status == "PASS":
                steps = [int(v) for v in re.findall(r"Checking assertions in step (\d+)\.\.", engine)]
                require(steps == list(range(depth)), "Full requested BMC depth is not established")
                semantics, observed = "bounded_pass_only", "pass"
            else:
                require("BMC failed!" in engine and "Assert failed in " in engine, "Missing BMC counterexample")
                witnesses = ["engine_0/trace.vcd", "engine_0/trace.yw"]
                semantics, observed = "counterexample", "fail"
        for witness in witnesses:
            require(text(read(witness)), "Empty witness artifact")
    origin = workdir + "/config.sby"
    fields = {name: {"value": value, "evidence_ref": origin if name != "cells" else workdir + "/src/cells.json"}
              for name, value in {"mode": mode, "depth": depth, "top": top, "sources": sources,
                                  "cells": cells, "scope": context["scope"], "semantics": semantics}.items()}
    return {"format": "opentools.result-snapshot.v1", "run_ref": context["run_ref"], "manifest_ref": context["manifest_ref"],
            "execution": {"state": "completed" if completed else "unknown", "evidence_ref": workdir + "/logfile.txt",
                          "command": context["command"], "executable_ref": SBY_REVISION + "; " + YOSYS_VERSION,
                          "dependency_capture_complete": context["dependency_capture_complete"],
                          "dependency_evidence_ref": context["dependency_evidence_ref"]},
            "result": {"outcome": observed, "native_status": status, "complete": completed,
                       "producer_run_ref": context["run_ref"], "evidence_ref": workdir + "/status",
                       "artifact": {"path": workdir + "/status", "sha256": tracked[workdir + "/status"]}},
            "fields": fields,
            "provenance": {"reader": "opentools.sby-single-task.v1", "context": context,
                           "workdir": workdir, "integrity_files": tracked,
                           "witnesses": [workdir + "/" + p for p in witnesses],
                           "declarations": "Scope, original command, SBY/solver revision and dependency completeness are supplied evidence, not authenticated native measurements."}}


def revalidate(snapshot, root):
    provenance = snapshot.get("provenance", {})
    require(provenance.get("reader") == "opentools.sby-single-task.v1", "Unsupported native reader receipt")
    require(isinstance(provenance.get("integrity_files"), dict) and provenance["integrity_files"], "Native integrity inventory missing")
    for relative, checksum in provenance["integrity_files"].items():
        require(file_hash(contained(root, relative)) == checksum, "Changed native artifact: " + relative)
    rebuilt = capture(root, provenance.get("workdir"), provenance.get("context"))
    require(canonical(rebuilt) == canonical(snapshot), "Snapshot differs from its retained native/context evidence")
    return rebuilt
