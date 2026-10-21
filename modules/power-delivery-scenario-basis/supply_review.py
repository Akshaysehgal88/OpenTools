#!/usr/bin/env python3
"""Review saved static IR evidence against an independent scenario request."""
import argparse,json,sys
from supply_common import folder,read_json,save
from native_supply import capture
from supply_core import review
def load(root,ref):
    path=folder(root,ref);ctx=read_json(path/'context.json')
    if ctx['run_ref']!=ref:raise ValueError('Run directory/context mismatch')
    return capture(path,ctx)
def evaluate(root,policy):
    if policy.get('format')!='opentools.supply-policy.v1':raise ValueError('Unsupported policy')
    selected=load(root,policy['selected_ref']);r=review(selected,policy['request'],policy['selected_binding']);r['cached_review']=None
    if policy.get('cached_ref'):
        cached=load(root,policy['cached_ref']);q=review(cached,policy['request'],policy.get('cached_binding'));r['cached_review']=q
        if r['exit_code']!=0 and q['exit_code']==0:r['next_actions'].insert(0,{'action':'use_matching_retained_static_result','run_ref':policy['cached_ref']})
    return r
def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('capture');q.add_argument('root');q.add_argument('run_ref');q.add_argument('--output')
    q=s.add_parser('review');q.add_argument('root');q.add_argument('policy');q.add_argument('--output');a=p.parse_args()
    try:
        r=load(a.root,a.run_ref) if a.command=='capture' else evaluate(a.root,read_json(a.policy))
        if a.output:save(a.output,r)
        else:print(json.dumps(r,indent=2,allow_nan=False))
        return 0 if a.command=='capture' else r['exit_code']
    except (OSError,ValueError,TypeError,KeyError,IndexError,AttributeError) as e:
        print('Invalid supply evidence: '+str(e),file=sys.stderr);return 3
if __name__=='__main__':raise SystemExit(main())
