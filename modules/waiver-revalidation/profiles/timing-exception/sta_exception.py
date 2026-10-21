"""Capture saved native evidence or review a selected setup-exception activity."""
import argparse,sys
from pathlib import Path
from reach_common import read_json,require,save
from native_reach import capture
from reach_core import drift,inspect,markdown

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    a=s.add_parser('capture');a.add_argument('run_dir',type=Path);a.add_argument('context',type=Path);a.add_argument('--output',type=Path,required=True)
    a=s.add_parser('review');a.add_argument('run_dir',type=Path);a.add_argument('contract',type=Path);a.add_argument('evidence',type=Path);a.add_argument('--json-out',type=Path,required=True);a.add_argument('--markdown-out',type=Path,required=True)
    a=s.add_parser('drift')
    for side in ('baseline','current'):
        for key in ('run','contract','evidence'):a.add_argument('--'+side+'-'+key,type=Path,required=True)
    a.add_argument('--identity-map',type=Path);a.add_argument('--json-out',type=Path,required=True);a.add_argument('--markdown-out',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        outputs=[a.output] if a.action=='capture' else [a.json_out,a.markdown_out]
        require(len({p.resolve() for p in outputs})==len(outputs) and all(not p.exists() for p in outputs),'Choose distinct new outputs')
        if a.action=='capture':r=capture(a.run_dir,read_json(a.context));code=0
        elif a.action=='review':r=inspect(read_json(a.contract),read_json(a.evidence),a.run_dir);code=r['exit_code']
        else:r=drift(read_json(a.baseline_contract),read_json(a.baseline_evidence),a.baseline_run,read_json(a.current_contract),read_json(a.current_evidence),a.current_run,read_json(a.identity_map) if a.identity_map else None);code=r['exit_code']
        save(outputs[0],r)
        if len(outputs)==2:
            with outputs[1].open('x',encoding='utf-8') as f:f.write(markdown(r))
        print(r.get('status','CAPTURED'));return code
    except (ValueError,OSError,KeyError,TypeError) as exc:print('Invalid input: '+str(exc),file=sys.stderr);return 3
if __name__=='__main__':raise SystemExit(main())
