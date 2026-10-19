#!/usr/bin/env python3
"""Check saved checkpoint compatibility and qualify selected restored observations."""
import argparse
import json
from pathlib import Path
import sys

from replay_core import check, qualify, exit_code, markdown, read_json, require


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ('check','qualify'):
        command=commands.add_parser(name)
        for argument in ('checkpoint','request','profile'):
            command.add_argument(argument)
        if name=='qualify':
            command.add_argument('control'); command.add_argument('restored')
        command.add_argument('--artifact-root')
        command.add_argument('--json-out'); command.add_argument('--markdown-out')
    args=parser.parse_args(argv)
    try:
        paths=[args.checkpoint,args.request,args.profile]
        if args.command=='qualify':
            paths += [args.control,args.restored]
        records=[read_json(path) for path in paths]
        outputs=[Path(p).resolve() for p in (args.json_out,args.markdown_out) if p]
        inputs={Path(p).resolve() for p in paths}
        if args.artifact_root:
            inputs|={ (Path(args.artifact_root)/item['path']).resolve() for item in
                      records[0]['artifacts']+[records[1]['binary']]+records[1]['prefix_files'] }
        require(len(outputs)==len(set(outputs)) and not set(outputs)&inputs,'Choose distinct outputs separate from inputs/artifacts')
        require(all(not p.exists() and p.parent.is_dir() for p in outputs),'Choose new output paths with existing parents')
        report=(check if args.command=='check' else qualify)(*records,artifact_root=args.artifact_root)
        for path,content in ((args.json_out,json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n'),(args.markdown_out,markdown(report))):
            if path:
                with Path(path).open('x',encoding='utf-8',newline='\n') as stream:
                    stream.write(content)
        print(markdown(report),end='')
        return exit_code(report)
    except (ValueError,OSError,TypeError,KeyError,UnicodeError) as error:
        print('error: '+str(error),file=sys.stderr)
        return 3


if __name__=='__main__':
    sys.exit(main())
