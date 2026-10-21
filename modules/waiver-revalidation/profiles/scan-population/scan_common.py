"""Shared local file checks; reuse the parent waiver record primitives."""
import hashlib
from pathlib import Path,PurePosixPath
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from waiver_core import canonical,compare,digest,read_json,require
def text(v):return isinstance(v,str) and bool(v.strip())
def shape(v,keys):require(isinstance(v,dict) and set(v)==set(keys),'Expected fields: '+', '.join(sorted(keys)))
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def relative(root,name):
    require(text(name) and '\\' not in name and ':' not in name,'Relative POSIX path required');p=PurePosixPath(name)
    require(not p.is_absolute() and all(v not in ('','.','..') for v in name.split('/')),'Path escapes artifact root');root=Path(root).resolve();target=root
    for part in p.parts:target/=part;require(not target.is_symlink(),'Linked evidence unsupported')
    require(target.resolve().is_relative_to(root),'Path escapes artifact root');return target
def known(v):return v is not None and (not isinstance(v,str) or text(v))
