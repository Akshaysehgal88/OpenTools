#!/usr/bin/env python3
"""Review a bound resource wait graph and finite observation window."""
import argparse
import json
from pathlib import Path
import sys
from progress_core import exit_code,read_json,review


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('model','journal','policy'):parser.add_argument(key)
    parser.add_argument('--output');args=parser.parse_args()
    try:
        result=review(*(read_json(getattr(args,key)) for key in ('model','journal','policy')))
        encoded=json.dumps(result,indent=2,allow_nan=False)+'\n'
        if args.output:
            with Path(args.output).open('x',encoding='utf-8') as stream:stream.write(encoded)
        else:print(encoded,end='')
        return exit_code(result)
    except (OSError,ValueError,TypeError,KeyError) as error:print(str(error),file=sys.stderr);return 3


if __name__=='__main__':sys.exit(main())
