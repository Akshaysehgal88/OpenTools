#!/usr/bin/env python3
"""Inspect native VCD declarations, assess a capture plan and preview a wrapper recipe."""
import argparse
import json
from pathlib import Path
import sys

from capture_core import assess, exit_code, read_json, render, require


def preflight(outputs,inputs):
    paths=[Path(p).resolve() for p in outputs if p]
    require(len(paths)==len(set(paths)) and not set(paths)&{Path(p).resolve() for p in inputs},'Choose distinct outputs separate from inputs')
    require(all(not p.exists() and p.parent.is_dir() for p in paths),'Choose new outputs with existing parent directories')


def write(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    inspect=commands.add_parser('inspect-vcd')
    inspect.add_argument('vcd');inspect.add_argument('--output',required=True);inspect.add_argument('--context-template')
    imp=commands.add_parser('import-vcd')
    imp.add_argument('vcd');imp.add_argument('context');imp.add_argument('--output',required=True)
    for name in ('assess','render'):
        command=commands.add_parser(name)
        command.add_argument('plan');command.add_argument('inventory');command.add_argument('--binary',required=True)
        command.add_argument('--output')
        if name=='render':
            command.add_argument('--waveform',required=True);command.add_argument('--viewer')
    args=parser.parse_args(argv)
    try:
        if args.command=='inspect-vcd':
            from native_vcd import inspect_header,context_template
            preflight([args.output,args.context_template],[args.vcd])
            report=inspect_header(args.vcd)
            write(args.output,report)
            if args.context_template:
                write(args.context_template,context_template(report))
            return 0
        if args.command=='import-vcd':
            from native_vcd import import_inventory
            preflight([args.output],[args.vcd,args.context])
            write(args.output,import_inventory(args.vcd,read_json(args.context)))
            return 0
        inputs=[args.plan,args.inventory,args.binary]
        outputs=[args.output]
        if args.command=='render':
            outputs += [args.viewer,args.waveform]
        preflight(outputs,inputs)
        plan,inventory=read_json(args.plan),read_json(args.inventory)
        assessment=assess(plan,inventory,args.binary)
        if args.command=='assess' or assessment['status']!='renderable':
            if args.output:
                write(args.output,assessment)
            print(json.dumps(assessment,indent=2,ensure_ascii=False))
            return exit_code(assessment)
        recipe=render(plan,inventory,args.binary,args.waveform)
        if args.viewer:
            from native_vcd import write_viewer
            write_viewer(recipe,args.viewer)
        if args.output:
            write(args.output,recipe)
        print(json.dumps(recipe,indent=2,ensure_ascii=False))
        return 0
    except (ValueError,OSError,TypeError,KeyError,UnicodeError) as error:
        print('error: '+str(error),file=sys.stderr)
        return 3


if __name__=='__main__':
    sys.exit(main())
