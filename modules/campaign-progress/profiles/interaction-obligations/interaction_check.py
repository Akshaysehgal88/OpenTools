"""Import saved native evidence and audit an existing explicit interaction roster."""
import argparse,json
from pathlib import Path
from saved_native import capture,file_hash,read_json,require
from interaction_core import exit_code,markdown,review
def write_new(path,content):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:f.write(content)
def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('capture');c.add_argument('root',type=Path);c.add_argument('workdir');c.add_argument('context',type=Path);c.add_argument('--output',type=Path,required=True)
    r=sub.add_parser('review');r.add_argument('plan',type=Path);r.add_argument('corpus',type=Path);r.add_argument('--json-out',type=Path);r.add_argument('--markdown-out',type=Path);a=p.parse_args()
    try:
        if a.command=='capture':
            require(not a.output.exists(),'Output exists');e=capture(a.root,a.workdir,read_json(a.context));write_new(a.output,json.dumps(e,indent=2)+'\n');print(json.dumps({'native_status':e['native']['status'],'receipt_sha256':file_hash(a.output)}));return 0
        require(all(v is None or not v.exists() for v in (a.json_out,a.markdown_out)),'Output exists');require(not a.json_out or not a.markdown_out or a.json_out.resolve()!=a.markdown_out.resolve(),'Select distinct outputs')
        e=review(read_json(a.plan),read_json(a.corpus),a.corpus.parent);content=json.dumps(e,indent=2)+'\n'
        if a.json_out:write_new(a.json_out,content)
        if a.markdown_out:write_new(a.markdown_out,markdown(e))
        print(content,end='');return exit_code(e)
    except (ValueError,OSError,KeyError,TypeError) as exc:p.exit(3,str(exc)+'\n')
if __name__=='__main__':raise SystemExit(main())
