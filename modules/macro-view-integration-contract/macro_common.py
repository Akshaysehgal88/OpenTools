"""Data-only record primitives for macro-view intake."""
import hashlib,json,math
from pathlib import Path
IDENTITY=('run_ref','scope_ref','configuration_ref','macro_ref','revision_ref','corner_ref')
BASIS=('view_basis_ref','revision_basis_ref','corner_basis_ref','pin_correspondence_ref','supply_basis_ref','placement_basis_ref','access_basis_ref','wrapper_basis_ref','owner_ref')
def require(condition,message):
    if not condition:raise ValueError(message)
def text(value,label):
    require(isinstance(value,str) and value.strip() and len(value)<=2048,'Invalid '+label);return value
def integer(value,minimum,maximum,label):
    require(type(value) is int and minimum<=value<=maximum,'Invalid '+label);return value
def number(value,label):
    require(type(value) in (int,float) and math.isfinite(value),'Invalid '+label);return value
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):result.update(block)
    return result.hexdigest()
def parse(source):
    def unique(pairs):
        result={}
        for k,v in pairs:require(k not in result,'Duplicate JSON key: '+k);result[k]=v
        return result
    return json.loads(source,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON value')))
def read_json(path):return parse(Path(path).read_text(encoding='utf-8'))
def save(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')
def file(root,name):
    root=Path(root);path=root/name
    require(Path(name).name==name and not root.is_symlink() and not path.is_symlink() and path.is_file() and path.resolve().parent==root.resolve(),'Missing/linked native file: '+name)
    return path
def exit_code(report):return 1 if report['findings'] else 2 if report['gaps'] else 0
