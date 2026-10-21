"""Data-only CLI. Never executes a simulator, Tcl file or received command."""
import argparse,json,sys
from pathlib import Path
from dft_common import read_json,require
from native_capture import capture
from resource_core import markdown,review

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    c=sub.add_parser('capture');c.add_argument('root',type=Path);c.add_argument('workdir');c.add_argument('context',type=Path);c.add_argument('--output',required=True,type=Path)
    c=sub.add_parser('review');c.add_argument('root',type=Path);c.add_argument('contract',type=Path);c.add_argument('evidence',type=Path);c.add_argument('--json-out',required=True,type=Path);c.add_argument('--markdown-out',required=True,type=Path)
    a=p.parse_args(argv)
    try:
        outputs=[a.output] if a.action=='capture' else [a.json_out,a.markdown_out]
        require(len({v.resolve() for v in outputs})==len(outputs) and all(not v.exists() for v in outputs),'Outputs must be distinct new files')
        if a.action=='capture':value=capture(a.root,a.workdir,read_json(a.context));payloads=[json.dumps(value,indent=2)+'\n'];code=0
        else:value=review(read_json(a.contract),read_json(a.evidence),a.root);payloads=[json.dumps(value,indent=2)+'\n',markdown(value)];code=value['exit_code']
        for path,content in zip(outputs,payloads):
            with path.open('x',encoding='utf-8') as f:f.write(content)
        print(value.get('status','CAPTURED'));return code
    except (ValueError,OSError,KeyError,TypeError) as exc:print('Invalid input: '+str(exc),file=sys.stderr);return 3
if __name__=='__main__':raise SystemExit(main())
