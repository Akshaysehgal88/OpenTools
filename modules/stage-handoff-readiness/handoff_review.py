#!/usr/bin/env python3
"""Review one execution handoff with independently supplied successor intent."""
import argparse
import json
from pathlib import Path
import sys
from handoff_core import exit_code,read_json,review

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('inventory','journal','policy'):parser.add_argument(key)
    parser.add_argument('--output');args=parser.parse_args()
    try:
        report=review(*(read_json(getattr(args,key)) for key in ('inventory','journal','policy')))
        encoded=json.dumps(report,indent=2,allow_nan=False)+'\n'
        if args.output:
            with Path(args.output).open('x',encoding='utf-8') as stream:stream.write(encoded)
        else:print(encoded,end='')
        return exit_code(report)
    except (OSError,ValueError,TypeError,KeyError) as error:print(str(error),file=sys.stderr);return 3

if __name__=='__main__':sys.exit(main())
