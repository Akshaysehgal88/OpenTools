#!/usr/bin/env python3
"""Capture or review one macro's physical, timing and logical view correspondence."""
import argparse,json,sys
from macro_common import exit_code,read_json,save
from native_views import capture
from view_core import review
def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    for name in ('capture','review'):
        q=s.add_parser(name);q.add_argument('native_directory');q.add_argument('context')
        if name=='review':q.add_argument('policy')
        q.add_argument('--output')
    a=p.parse_args()
    try:
        evidence=capture(a.native_directory,read_json(a.context));result=review(evidence,read_json(a.policy)) if a.command=='review' else evidence
        if a.output:save(a.output,result)
        else:print(json.dumps(result,indent=2,allow_nan=False))
        return exit_code(result) if a.command=='review' else 0
    except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError) as e:
        print('Invalid macro-view input: '+str(e),file=sys.stderr);return 3
if __name__=='__main__':raise SystemExit(main())
