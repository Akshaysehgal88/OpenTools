"""Read the timestamp inventory emitted by a declared Verilator 5.020 producer."""
import hashlib
from pathlib import Path
import re

from reuse_core import require


def inspect_manifest(path, producer_version):
    require(producer_version == '5.020', 'Qualified producer declaration must be 5.020')
    raw = Path(path).read_bytes()
    lines = raw.decode('utf-8').splitlines()
    require(lines and lines[0] == '# DESCRIPTION: Verilator output: Timestamp data for --skip-identical.  Delete at will.',
            'Unsupported Verilator timestamp header')
    command = None
    sources, targets = [], []
    seen = set()
    for line in lines[1:]:
        if not line.strip():
            continue
        if line.startswith('C "') and line.endswith('"'):
            require(command is None, 'Repeated command record')
            command = line[3:-1]
            continue
        match = re.fullmatch(r'([ST])\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+"([^"\\]+)"', line)
        require(match is not None, 'Unsupported native timestamp record/filename')
        kind, *values, name = match.groups()
        require((kind, name) not in seen, 'Duplicate native inventory entry')
        seen.add((kind, name))
        (sources if kind == 'S' else targets).append({'path': name, 'native_stat_fields': [int(v) for v in values]})
    require(command is not None and sources and targets, 'Native command, source and target inventory required')
    return {'format': 'opentools.verilator-build-evidence.v1', 'profile': 'Verilator-5.020.verFiles.v1',
            'source_file_sha256': hashlib.sha256(raw).hexdigest(), 'producer_version_declared': producer_version,
            'command_text': command, 'sources': sources, 'targets': targets,
            'consumed_content_hashes': 'not_present', 'dependency_closure': 'not_established',
            'limits': 'Timestamp inventory only; flattened command text is not argv. No dependency reads, C++/link closure, original-byte hashing or reuse verdict.'}
