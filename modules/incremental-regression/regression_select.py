#!/usr/bin/env python3
"""Plan a transparent first regression stage or review retained actual feedback."""
import argparse
import json
from pathlib import Path
import sys
from selection_core import read_json,plan,feedback,exit_code,require,fingerprint


def main(argv=None):
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    digest=commands.add_parser('digest');digest.add_argument('file')
    for name in ('plan','review'):
        command=commands.add_parser(name)
        for key in ('universe','changes','mapping','policy'):command.add_argument('--'+key,required=True)
        command.add_argument('--output')
        if name=='review':
            command.add_argument('--results',required=True);command.add_argument('--full-results')
    args=parser.parse_args(argv)
    try:
        if args.command=='digest':
            print(json.dumps({'canonical_sha256':fingerprint(read_json(args.file))}));return 0
        paths=[getattr(args,k) for k in ('universe','changes','mapping','policy')]
        if args.command=='review':paths +=[args.results]+([args.full_results] if args.full_results else [])
        if args.output:
            out=Path(args.output).resolve()
            require(not out.exists() and out not in {Path(v).resolve() for v in paths} and out.parent.is_dir(),'Choose a new report path separate from inputs')
        records=[read_json(v) for v in paths]
        report=plan(*records) if args.command=='plan' else feedback(*records)
        content=json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        if args.output:
            with Path(args.output).open('x',encoding='utf-8',newline='\n') as stream:stream.write(content)
        print(content,end='');return exit_code(report)
    except (ValueError,OSError,TypeError,KeyError,UnicodeError) as error:
        print('error: '+str(error),file=sys.stderr);return 3


if __name__=='__main__':sys.exit(main())
