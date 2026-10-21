#!/usr/bin/env python3
"""Review one bound storage initialization and first-access window."""
import argparse
import json
import sys
from pathlib import Path
from storage_core import exit_code, read_json, review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inventory','journal','policy'): parser.add_argument(name)
    parser.add_argument('--output');args = parser.parse_args()
    try:
        result = review(*(read_json(getattr(args,k)) for k in ('inventory','journal','policy')))
        encoded = json.dumps(result, indent=2, allow_nan=False)+'\n'
        if args.output:
            with Path(args.output).open('x', encoding='utf-8') as stream: stream.write(encoded)
        else: print(encoded, end='')
        return exit_code(result)
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(str(error), file=sys.stderr);return 3


if __name__ == '__main__': sys.exit(main())
