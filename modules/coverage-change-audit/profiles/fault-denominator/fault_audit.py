#!/usr/bin/env python3
"""Review a fault-coverage change without conflating native metric definitions."""
import argparse,json,sys
from fault_common import exit_code,read_json,save
from native_fault import capture
from fault_core import compare

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('capture');p.add_argument('native_directory');p.add_argument('context');p.add_argument('--output')
    p=sub.add_parser('compare')
    for k in ('baseline_directory','baseline_context','current_directory','current_context','policy'):p.add_argument(k)
    p.add_argument('--output');a=parser.parse_args()
    try:
        if a.command=='capture':report=capture(a.native_directory,read_json(a.context))
        else:report=compare(capture(a.baseline_directory,read_json(a.baseline_context)),capture(a.current_directory,read_json(a.current_context)),read_json(a.policy))
        if a.output:save(a.output,report)
        else:print(json.dumps(report,indent=2,allow_nan=False))
        return exit_code(report) if a.command=='compare' else 0
    except (OSError,ValueError,KeyError,TypeError,IndexError,StopIteration) as e:
        print('Invalid fault-campaign input: '+str(e),file=sys.stderr);return 3
if __name__=='__main__':raise SystemExit(main())
