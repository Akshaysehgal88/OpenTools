#!/usr/bin/env python3
"""Review saved experiment plans/history/results without launching or rewriting runs."""
import argparse
import json
from pathlib import Path
import sys

from experiment_core import audit,review_result,exit_code,read_json,require


def main(argv=None):
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    plan=commands.add_parser('audit-plan');plan.add_argument('plan');plan.add_argument('--prior',action='append',default=[])
    result=commands.add_parser('review-result');result.add_argument('plan');result.add_argument('result')
    for command in (plan,result):command.add_argument('--output')
    args=parser.parse_args(argv)
    try:
        inputs=[args.plan]+(args.prior if args.command=='audit-plan' else [args.result])
        if args.output:
            output=Path(args.output).resolve()
            require(output not in {Path(p).resolve() for p in inputs} and not output.exists() and output.parent.is_dir(),
                    'Choose a new output path separate from the original records')
        report=audit(read_json(args.plan),[read_json(p) for p in args.prior]) if args.command=='audit-plan' else review_result(read_json(args.plan),read_json(args.result))
        content=json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        if args.output:
            with Path(args.output).open('x',encoding='utf-8',newline='\n') as stream:stream.write(content)
        print(content,end='')
        return exit_code(report)
    except (ValueError,OSError,TypeError,KeyError,UnicodeError) as error:
        print('error: '+str(error),file=sys.stderr)
        return 3


if __name__=='__main__':
    sys.exit(main())
