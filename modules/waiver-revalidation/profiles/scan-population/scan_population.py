"""Data-only scan population capture, membership review and exclusion drift."""
import argparse,json,sys
from pathlib import Path
from scan_common import read_json,require
from native_inventory import capture
from population_core import drift,markdown,review
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    a=s.add_parser('capture');a.add_argument('root',type=Path);a.add_argument('workdir');a.add_argument('context',type=Path);a.add_argument('--output',required=True,type=Path)
    a=s.add_parser('review');a.add_argument('root',type=Path);a.add_argument('contract',type=Path);a.add_argument('evidence',type=Path);a.add_argument('--json-out',required=True,type=Path);a.add_argument('--markdown-out',required=True,type=Path)
    a=s.add_parser('drift');a.add_argument('root',type=Path);a.add_argument('baseline',type=Path);a.add_argument('current',type=Path);a.add_argument('--output',required=True,type=Path)
    a=p.parse_args(argv)
    try:
        outputs=[a.json_out,a.markdown_out] if a.action=='review' else [a.output]
        require(len({v.resolve() for v in outputs})==len(outputs) and all(not v.exists() for v in outputs),'Choose distinct new output files')
        if a.action=='capture':value=capture(a.root,a.workdir,read_json(a.context));code=0
        elif a.action=='review':value=review(read_json(a.contract),read_json(a.evidence),a.root);code=value['exit_code']
        else:value=drift(read_json(a.baseline),read_json(a.current),a.root);code={'unchanged_within_scope':0,'review_required':1,'incomplete':2}[value['status']]
        contents=[json.dumps(value,indent=2)+'\n']+([markdown(value)] if a.action=='review' else [])
        for path,content in zip(outputs,contents):
            with path.open('x',encoding='utf-8') as f:f.write(content)
        print(value.get('status',value.get('audit',{}).get('status','CAPTURED')));return code
    except (ValueError,OSError,KeyError,TypeError) as exc:print('Invalid input: '+str(exc),file=sys.stderr);return 3
if __name__=='__main__':raise SystemExit(main())
