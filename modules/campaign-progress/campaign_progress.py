#!/usr/bin/env python3
"""Review cumulative campaign exports against an independent objective contract."""
import argparse
import json
from pathlib import Path
import sys
from progress_core import read_json,review,markdown,exit_code,require,fingerprint


def main(argv=None):
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    digest=commands.add_parser('digest');digest.add_argument('file')
    summary=commands.add_parser('summarize');summary.add_argument('contract');summary.add_argument('before');summary.add_argument('after')
    summary.add_argument('--output');summary.add_argument('--markdown')
    args=parser.parse_args(argv)
    try:
        if args.command=='digest':print(json.dumps({'canonical_sha256':fingerprint(read_json(args.file))}));return 0
        inputs={Path(v).resolve() for v in (args.contract,args.before,args.after)}
        outputs=[Path(v).resolve() for v in (args.output,args.markdown) if v]
        require(len(set(outputs))==len(outputs) and all(v not in inputs and not v.exists() and v.parent.is_dir() for v in outputs),
                'Reports need new distinct paths separate from input records')
        report=review(read_json(args.contract),read_json(args.before),read_json(args.after))
        content=json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        for path,value in ((args.output,content),(args.markdown,markdown(report))):
            if path:
                with Path(path).open('x',encoding='utf-8',newline='\n') as stream:stream.write(value)
        print(content,end='');return exit_code(report)
    except (ValueError,OSError,TypeError,KeyError,UnicodeError) as error:
        print('error: '+str(error),file=sys.stderr);return 3


if __name__=='__main__':sys.exit(main())
