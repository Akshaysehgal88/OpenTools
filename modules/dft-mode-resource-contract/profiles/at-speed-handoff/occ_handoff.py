"""Data-only capture and review of native at-speed handoff evidence."""
import argparse,json,sys
from pathlib import Path
from occ_common import read_json,require
from native_occ import capture
from occ_core import markdown,review
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    a=sub.add_parser('capture');a.add_argument('root',type=Path);a.add_argument('behavior_dir');a.add_argument('sta_dir');a.add_argument('context',type=Path);a.add_argument('--output',required=True,type=Path)
    a=sub.add_parser('review');a.add_argument('root',type=Path);a.add_argument('contract',type=Path);a.add_argument('evidence',type=Path);a.add_argument('--json-out',required=True,type=Path);a.add_argument('--markdown-out',required=True,type=Path)
    a=p.parse_args(argv)
    try:
        outputs=[a.output] if a.action=='capture' else [a.json_out,a.markdown_out];require(len({v.resolve() for v in outputs})==len(outputs) and all(not v.exists() for v in outputs),'Choose distinct new output files')
        if a.action=='capture':value=capture(a.root,a.behavior_dir,a.sta_dir,read_json(a.context));code=0
        else:value=review(read_json(a.contract),read_json(a.evidence),a.root);code=value['exit_code']
        contents=[json.dumps(value,indent=2)+'\n']+([markdown(value)] if a.action=='review' else [])
        for path,content in zip(outputs,contents):
            with path.open('x',encoding='utf-8') as f:f.write(content)
        print(value.get('status','CAPTURED'));return code
    except (ValueError,OSError,KeyError,TypeError) as exc:print('Invalid input: '+str(exc),file=sys.stderr);return 3
if __name__=='__main__':raise SystemExit(main())
