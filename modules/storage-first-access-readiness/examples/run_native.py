#!/usr/bin/env python3
"""Run the owned RAM wrapper, optionally against a separately supplied pinned codec."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
from ecc39 import decode, encode


def require(condition, message):
    if not condition: raise ValueError(message)


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def observe(output, verilator, verilator_root, reference_dir=None):
    output = Path(output).resolve();output.mkdir(parents=True, exist_ok=False)
    sources = ['ecc_profile.sv', 'codec_probes.sv', 'ram_wrapper.sv', 'storage_tb.sv']
    hashes = {}
    for name in sources:
        shutil.copyfile(MODULE/'examples'/name, output/name)
        hashes[name] = hashlib.sha256((output/name).read_bytes()).hexdigest()
    manifest = json.loads((MODULE/'examples/reference_manifest.json').read_text(encoding='utf-8'))
    reference_files = []
    if reference_dir is not None:
        for name, entry in manifest['files'].items():
            source = Path(reference_dir)/name
            require(hashlib.sha256(source.read_bytes()).hexdigest() == entry['sha256'], 'Pinned reference hash differs: '+source.name)
            shutil.copyfile(source, output/source.name)
            if source.suffix == '.sv': reference_files.append(source.name)
    version = subprocess.run([verilator, '--version'], check=True, capture_output=True, text=True).stdout.strip()
    require(version.startswith('Verilator 5.020'), 'This recipe is qualified with Verilator 5.020')
    with tempfile.TemporaryDirectory(prefix='opentools-storage-') as temporary:
        scratch = Path(temporary);runtime = scratch/'runtime'
        runtime.symlink_to(Path(verilator_root).resolve(), target_is_directory=True)
        env = os.environ.copy();env['VERILATOR_ROOT'] = str(runtime)
        for name in sources + reference_files: shutil.copyfile(output/name, scratch/name)
        command = [verilator, '--binary', '--timing', '-Wno-fatal', '--top-module', 'storage_top', '--Mdir', str(scratch/'obj')]
        if reference_dir is not None: command.append('+define+OPENTOOLS_ECC_REFERENCE')
        command += [str(scratch/name) for name in sources+reference_files]
        save(output/'build.command.json', command)
        build = subprocess.run(command, cwd=scratch, env=env, capture_output=True, text=True, timeout=180)
        (output/'build.stdout.txt').write_text(build.stdout, encoding='utf-8');(output/'build.stderr.txt').write_text(build.stderr, encoding='utf-8')
        require(build.returncode == 0, 'Native build failed; inspect retained diagnostics')
        binary = scratch/'obj/Vstorage_top';shutil.copy2(binary, output/'Vstorage_top')
        result = subprocess.run([str(binary)], cwd=scratch, env=env, capture_output=True, text=True, timeout=30)
        (output/'native.stdout.txt').write_text(result.stdout, encoding='utf-8');(output/'native.stderr.txt').write_text(result.stderr, encoding='utf-8')
        require(result.returncode == 0, 'Native execution failed; inspect retained diagnostics')
    count = 0;done = None
    for line in result.stdout.splitlines():
        if line.startswith('CODEC '):
            values = [int(v) for v in line.split()[1:]]
            require(len(values) == 9, 'Invalid codec columns')
            index, data, fault, word, observed, ce, ue, syndrome, odd = values
            expected = decode(word)
            require(index == count and word == encode(data)^fault, 'Native encoding/probe order differs')
            require([observed, ce, ue, syndrome, odd] == [expected[k] for k in ('data','correctable','uncorrectable','syndrome','overall_odd')], 'Native decoder differs from Python column model')
            count += 1
        elif line.startswith('CODEC_DONE '): done = int(line.split()[1])
    require(count == done == 2375, 'Codec probe population incomplete')
    for name, checksum in hashes.items(): require(hashlib.sha256((output/name).read_bytes()).hexdigest() == checksum, 'Retained source changed')
    summary = {'verilator': version, 'source_sha256': hashes, 'codec_probes': count,
               'pinned_reference': manifest if reference_dir is not None else None}
    save(output/'observation.json', summary)
    return summary


def run(output, verilator, verilator_root, reference_dir=None):
    summary = observe(output, verilator, verilator_root, reference_dir)
    from create_example import from_native
    summary['cases'] = from_native(Path(output))
    save(Path(output)/'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('directory')
    parser.add_argument('--verilator', required=True);parser.add_argument('--verilator-root', required=True)
    parser.add_argument('--reference-dir', help='Pre-fetched files matching reference_manifest.json; no download performed')
    args = parser.parse_args()
    print(json.dumps(run(args.directory, args.verilator, args.verilator_root, args.reference_dir), indent=2))


if __name__ == '__main__': main()
