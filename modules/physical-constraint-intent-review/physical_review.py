#!/usr/bin/env python3
"""Review retained physical proposals without running their source scripts."""
import argparse,json,sys
from physical_common import folder,read_json,save
from native_region import capture
from physical_core import review

def load(root,ref):
    path=folder(root,ref);ctx=read_json(path/'context.json')
    if ctx['run_ref']!=ref:raise ValueError('Run directory/context identity mismatch')
    return capture(path,ctx)

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('capture');q.add_argument('root');q.add_argument('run_ref');q.add_argument('--output')
    q=s.add_parser('review');q.add_argument('root');q.add_argument('policy');q.add_argument('--output');a=p.parse_args()
    try:
        if a.command=='capture':r=load(a.root,a.run_ref)
        else:
            policy=read_json(a.policy);r=review(load(a.root,policy['before']),load(a.root,policy['after']),policy)
        if a.output:save(a.output,r)
        else:print(json.dumps(r,indent=2,allow_nan=False))
        return r['exit_code'] if a.command=='review' else 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AttributeError) as e:
        print('Invalid physical evidence: '+str(e),file=sys.stderr);return 3
if __name__=='__main__':raise SystemExit(main())
