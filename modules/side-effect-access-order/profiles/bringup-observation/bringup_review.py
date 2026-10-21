"""Review saved device-emulation observations against an independent expectation."""
import argparse,sys
from pathlib import Path
from bringup_common import read_json,require,save
from native_bringup import load
from bringup_core import markdown,review
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    a=s.add_parser('capture');a.add_argument('root',type=Path);a.add_argument('run_ref');a.add_argument('--output',type=Path,required=True)
    a=s.add_parser('review');a.add_argument('root',type=Path);a.add_argument('request',type=Path);a.add_argument('--json-out',type=Path,required=True);a.add_argument('--markdown-out',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        outputs=[a.output] if a.action=='capture' else [a.json_out,a.markdown_out];require(len({v.resolve() for v in outputs})==len(outputs) and all(not v.exists() for v in outputs),'Choose distinct new outputs')
        if a.action=='capture':r=load(a.root,a.run_ref);code=0
        else:r=review(a.root,read_json(a.request));code=r['exit_code']
        save(outputs[0],r)
        if len(outputs)>1:
            with outputs[1].open('x',encoding='utf-8') as f:f.write(markdown(r))
        print(r.get('status','CAPTURED'));return code
    except (ValueError,OSError,KeyError,TypeError) as e:print('Invalid input: '+str(e),file=sys.stderr);return 3
if __name__=='__main__':raise SystemExit(main())
