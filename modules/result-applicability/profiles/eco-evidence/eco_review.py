#!/usr/bin/env python3
"""Review one bounded ECO and the exact saved reports selected for reuse."""
import argparse,json,sys
from eco_common import folder,read_json,save
from native_eco import capture
from eco_core import review
def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('capture');q.add_argument('root');q.add_argument('run_ref');q.add_argument('--output')
    q=s.add_parser('review');q.add_argument('root');q.add_argument('policy');q.add_argument('--output');a=p.parse_args()
    try:
        if a.command=='capture':path=folder(a.root,a.run_ref);result=capture(path,read_json(path/'context.json'))
        else:result=review(a.root,read_json(a.policy))
        if a.output:save(a.output,result)
        else:print(json.dumps(result,indent=2,allow_nan=False))
        return result['exit_code'] if a.command=='review' else 0
    except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError) as e:
        print('Invalid ECO evidence: '+str(e),file=sys.stderr);return 3
if __name__=='__main__':raise SystemExit(main())
