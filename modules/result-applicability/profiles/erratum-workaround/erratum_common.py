"""Portable erratum review records and the unchanged parent result comparator."""
import math,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
from applicability_core import audit,canonical,digest,exit_code as audit_exit,file_hash as sha,known,read_json,require,shape,text,validate_fields
IDENTITY=('run_ref','scope_ref','configuration_ref','mode_ref','model_ref')
MODEL='opentools.owned-erratum-model.v1'
def compiler_ok(v):return re.search(r'\(Ubuntu 13\.3\.0[^)]*\) 13\.3\.0(?:\n|$)',v) is not None
def uint(v,maximum=1000):require(type(v) is int and 0<=v<=maximum,'Bounded unsigned integer required');return v
def save(p,v):
    import json
    with Path(p).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
def file(root,name):
    p=Path(root)/name;require(Path(name).name==name and not Path(root).is_symlink() and not p.is_symlink() and p.is_file() and p.resolve().parent==Path(root).resolve(),'Missing/linked original: '+name);return p
def folder(root,ref):
    require(text(ref) and re.fullmatch(r'[a-z][a-z0-9-]*',ref),'Flat run reference required');p=Path(root)/ref;require(p.is_dir() and not p.is_symlink() and p.resolve().parent==Path(root).resolve(),'Missing/linked native run');return p
def context(c):
    shape(c,{'format',*IDENTITY})
    require(c['format']=='opentools.erratum-context.v1' and all(text(c[k]) for k in IDENTITY),'Original identity required')
    require(re.fullmatch(r'[a-z][a-z0-9-]*',c['run_ref']),'Flat run reference required');return c
