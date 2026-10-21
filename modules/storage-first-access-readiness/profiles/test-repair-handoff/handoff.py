#!/usr/bin/env python3
"""Capture or review an owned test/repair-to-functional memory transition."""
import argparse
import json
import sys
from native_repair import capture
from handoff_core import review
from repair_common import exit_code,read_json,save

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('capture','review'):
        p=sub.add_parser(name);p.add_argument('native_directory');p.add_argument('context')
        if name=='review':p.add_argument('policy')
        p.add_argument('--output')
    args=parser.parse_args()
    try:
        evidence=capture(args.native_directory,read_json(args.context))
        result=review(evidence,read_json(args.policy)) if args.command=='review' else evidence
        if args.output:save(args.output,result)
        else:print(json.dumps(result,indent=2,allow_nan=False))
        return exit_code(result) if args.command=='review' else 0
    except (OSError,ValueError,KeyError,TypeError,IndexError) as error:
        print('Invalid handoff input: '+str(error),file=sys.stderr);return 3

if __name__=='__main__':raise SystemExit(main())
