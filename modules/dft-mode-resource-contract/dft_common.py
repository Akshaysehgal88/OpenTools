"""Local record primitives shared by the DFT resource reader and review."""
import hashlib,json
from pathlib import Path,PurePosixPath
def require(value,message):
    if not value:raise ValueError(message)
def text(value):return isinstance(value,str) and bool(value.strip())
def shape(value,keys):require(isinstance(value,dict) and set(value)==set(keys),'Expected fields: '+', '.join(sorted(keys)))
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(value):return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()
def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
    return h.hexdigest()
def read_json(path):
    def unique(items):
        result={}
        for k,v in items:require(k not in result,'Duplicate JSON key: '+k);result[k]=v
        return result
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),object_pairs_hook=unique,parse_constant=lambda v:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
def contained(root,relative):
    require(text(relative) and '\\' not in relative and ':' not in relative,'Use relative POSIX evidence paths');p=PurePosixPath(relative)
    require(not p.is_absolute() and all(v not in ('','.','..') for v in relative.split('/')),'Evidence path escapes root');root=Path(root).resolve();target=root
    for part in p.parts:target/=part;require(not target.is_symlink(),'Linked evidence unsupported')
    require(target.resolve().is_relative_to(root),'Evidence path escapes root');return target
def known(value):
    if value is None or isinstance(value,str) and not text(value):return False
    if isinstance(value,dict):return bool(value) and all(known(v) for v in value.values())
    if isinstance(value,list):return all(known(v) for v in value)
    return True
