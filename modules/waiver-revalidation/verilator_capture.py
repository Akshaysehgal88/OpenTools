"""Native differential suppression capture for Verilator 5.020 text diagnostics."""

from __future__ import annotations

import hashlib
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from waiver_core import InputError, SNAPSHOT_FORMAT, digest, require, validate_snapshot


PROFILE = "verilator-text-5.020.v1"
HEADER = re.compile(r"^%Warning-([A-Z0-9_]+):\s*(.*)$")
LOCATION = re.compile(r"^(.+?):(\d+):(?:(\d+):)?\s*(.*)$")
DEFINE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_diagnostics(log, cwd, evidence_ref):
    """Read native warning headers. Original multiline evidence remains in the log."""
    findings, issues = {}, []
    for line in log.splitlines():
        if line.startswith("%Error"):
            issues.append(line)
        if not line.startswith("%Warning"):
            continue
        header = HEADER.fullmatch(line)
        if not header:
            issues.append(f"Unsupported warning header: {line}")
            continue
        rule, remainder = header.groups()
        location = LOCATION.fullmatch(remainder)
        if location:
            filename, row, column, message = location.groups()
            source = Path(filename)
            if not source.is_absolute():
                source = Path(cwd) / source
            try:
                filename = source.resolve().relative_to(Path(cwd).resolve()).as_posix()
            except ValueError:
                filename = source.resolve().as_posix()
            obj = f"{filename}:{row}:{column or '0'}"
        else:
            obj, message = f"global:{rule}", remainder
        identity = digest({"object": obj, "rule": rule, "message": message})
        finding = {"id": identity, "object": obj, "rule": rule,
                   "message": message, "evidence_ref": evidence_ref}
        if identity in findings:
            issues.append(f"Duplicate native diagnostic identity: {obj}/{rule}")
        findings[identity] = finding
    return findings, issues


def validate_waiver_file(path):
    """Restrict the input to suppression directives, leaving matching to Verilator."""
    try:
        lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as exc:
        raise InputError(f"Cannot read waiver file: {exc}") from exc
    saw_directive = False
    saw_config = False
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        if stripped == "`verilator_config":
            require(not saw_config and not saw_directive, "Unexpected/repeated verilator_config")
            saw_config = True
            continue
        require(saw_config and re.match(r"^lint_off(?:\s|$)", stripped),
                f"Unsupported waiver line {number}; only plain lint_off directives and // comments are supported")
        require("`" not in stripped and "/*" not in stripped,
                f"Preprocessing/block comments are outside this capture profile (line {number})")
        try:
            tokens = shlex.split(stripped, posix=True)
        except ValueError as exc:
            raise InputError(f"Invalid quoting on waiver line {number}: {exc}") from exc
        position = 1
        seen_options = set()
        while position < len(tokens):
            option = tokens[position]
            if option.startswith("//"):
                break
            require(option in ("-rule", "-file", "-match", "-contents", "-lines"),
                    f"Unsupported control token on waiver line {number}: {option}")
            require(option not in seen_options, f"Repeated control option on line {number}: {option}")
            seen_options.add(option)
            position += 1
            require(position < len(tokens) and bool(tokens[position]),
                    f"Missing {option} value on line {number}")
            value = tokens[position]
            if option == "-rule":
                require(re.fullmatch(r"[A-Z0-9_]+", value) is not None,
                        f"Invalid rule identifier on line {number}")
            if option == "-lines":
                require(value.isdecimal() and int(value) > 0, f"Invalid line number on line {number}")
            position += 1
            if option == "-lines" and position < len(tokens) and tokens[position] == "-":
                position += 1
                require(position < len(tokens) and tokens[position].isdecimal()
                        and int(tokens[position]) >= int(value), f"Invalid line range on line {number}")
                position += 1
        saw_directive = True
    require(saw_config and saw_directive, "Waiver file needs verilator_config and at least one lint_off")


def _run(command, cwd, timeout):
    try:
        process = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=timeout,
                                 shell=False)
        return {"argv": command, "returncode": process.returncode,
                "stdout": process.stdout, "stderr": process.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InputError(f"Verilator invocation failed: {exc}") from exc


def capture(*, executable, sources, waiver_file, waiver_id, configuration, scope,
            run_id, evidence_dir, top, dependencies=(), include_dirs=(),
            complete_inputs=False, timeout=120, cwd=None):
    """Capture one waiver-file population using the native suppression engine.

    Completeness is limited to emitted diagnostics under this fixed profile and
    requires the caller's explicit dependency-closure declaration.
    """
    cwd = Path(cwd or Path.cwd()).resolve()
    def local_path(value):
        path = Path(value)
        return (path if path.is_absolute() else cwd / path).resolve()

    resolved = shutil.which(str(executable))
    require(resolved is not None, f"Verilator executable not found: {executable}")
    executable = str(Path(resolved).resolve())
    version_run = _run([executable, "--version"], cwd, timeout)
    version = version_run["stdout"].strip()
    require(version_run["returncode"] == 0 and re.match(r"^Verilator 5\.020(?:\s|$)", version),
            f"This native adapter supports Verilator 5.020; observed: {version or version_run['stderr']}")
    require(isinstance(configuration, dict), "Configuration must be a flat JSON object of macro definitions")
    require(isinstance(top, str) and DEFINE.fullmatch(top), "A simple top-module identifier is required")
    require(isinstance(scope, str) and bool(scope.strip()), "scope must be nonempty")
    require(isinstance(run_id, str) and bool(run_id.strip()), "run_id must be nonempty")
    require(isinstance(waiver_id, str) and bool(waiver_id.strip()), "waiver_id must be nonempty")
    defines = []
    for key, value in sorted(configuration.items()):
        require(isinstance(key, str) and DEFINE.fullmatch(key), f"Unsupported macro name: {key}")
        require(type(value) in (str, int, bool), f"Macro {key}: use string, integer, or boolean")
        rendered = str(int(value)) if type(value) is bool else str(value)
        require(rendered and not any(c in rendered for c in "\r\n\x00"), f"Invalid macro value: {key}")
        defines.append(f"-D{key}={rendered}")
    source_paths = [local_path(path) for path in sources]
    require(bool(source_paths), "At least one HDL source is required")
    require(all(path.is_file() and path.suffix.lower() in (".v", ".sv") for path in source_paths),
            "Sources must be existing .v/.sv files; additional control files are unsupported")
    waiver_file = local_path(waiver_file)
    validate_waiver_file(waiver_file)
    inputs = sorted(set(source_paths + [local_path(path) for path in dependencies] + [waiver_file]))
    require(all(path.is_file() for path in inputs), "A declared dependency is unavailable")
    input_before = {str(path): file_digest(path) for path in inputs}
    evidence_dir = local_path(evidence_dir)
    require(not evidence_dir.exists(), f"Evidence directory already exists: {evidence_dir}")
    # Only generated temporary output is placed here; the HDL/control files are read in place.
    evidence_dir.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="verilator-", dir=evidence_dir) as temp:
        common = [executable, "--lint-only", "-Wall", "-Wno-fatal", "--top-module", top,
                  "--Mdir", temp, *defines]
        for directory in include_dirs:
            directory = local_path(directory)
            require(directory.is_dir(), f"Include directory unavailable: {directory}")
            common.append(f"-I{directory}")
        baseline = _run([*common, *map(str, source_paths)], cwd, timeout)
        selected = _run([*common, str(waiver_file), *map(str, source_paths)], cwd, timeout)
    for label, invocation in (("without-waiver", baseline), ("with-waiver", selected)):
        (evidence_dir / f"{label}.log").write_text(invocation["stdout"] + invocation["stderr"], encoding="utf-8")
    raw, raw_issues = parse_diagnostics(baseline["stdout"] + baseline["stderr"], cwd,
                                       str(evidence_dir / "without-waiver.log"))
    retained, selected_issues = parse_diagnostics(selected["stdout"] + selected["stderr"], cwd,
                                                 str(evidence_dir / "with-waiver.log"))
    issues = raw_issues + selected_issues
    if baseline["returncode"] != 0 or selected["returncode"] != 0:
        issues.append("A native lint invocation did not finish successfully.")
    if set(retained) - set(raw):
        issues.append("Applying the selected waiver introduced new diagnostic identities; differential attribution is unresolved.")
    input_after = {str(path): file_digest(path) for path in inputs}
    if input_before != input_after:
        issues.append("A declared input changed during capture.")
    if not complete_inputs:
        issues.append("The caller has not declared the input/dependency inventory complete.")
    complete = not issues
    snapshot = {"format": SNAPSHOT_FORMAT, "run_id": run_id, "scope": scope,
                "tool": {"name": "verilator", "version": version, "ruleset": PROFILE + ":Wall"},
                "configuration": configuration, "configuration_ref": "sha256:" + digest(configuration),
                "configuration_basis": "command-line-macro-inputs",
                "identity_basis": "native-rule-location-header.v1", "population_complete": complete,
                "waivers": [{"id": waiver_id, "definition_sha256": input_before[str(waiver_file)],
                             "complete": complete,
                             "findings": [raw[key] for key in sorted(set(raw) - set(retained))]}],
                "capture": {"profile": PROFILE, "top": top, "cwd": str(cwd), "declared_inputs": input_before,
                            "dependency_completeness_basis": "caller-declared" if complete_inputs else "undeclared",
                            "issues": issues, "invocations": [baseline, selected],
                            "population_basis": "Diagnostics observable without this selected external waiver, under the fixed native lint profile. Other inline suppressions remain in effect."}}
    validate_snapshot(snapshot)
    return snapshot
