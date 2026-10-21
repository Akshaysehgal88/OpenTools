"""Portable records and the existing diagnostic receipt/epoch engine."""
import hashlib,json,math,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'diagnostic-validity'))
from diagnostic_core import digest,read_json,require,review as diagnostic_review
IDENTITY=('run_ref','scope_ref','project_ref','configuration_ref','mode_ref','board_ref')
SELECTION=('target_epoch','required_through_tick','selected_read_tick','fault_mask')
MODEL='opentools.owned-bringup-emulation.v1'
def qualified_compiler(v):return re.search(r'\(Ubuntu 13\.3\.0[^)]*\) 13\.3\.0(?:\n|$)',v) is not None
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def text(v):return isinstance(v,str) and bool(v.strip())
def shape(v,keys):require(isinstance(v,dict) and set(v)==set(keys),'Unexpected record fields')
def number(v):require(type(v) in (int,float) and math.isfinite(v),'Finite number required');return v
def uint(v):require(type(v) is int and 0<=v<2**63,'Unsigned bounded integer required');return v
def known(v):
    if isinstance(v,dict):return all(known(x) for x in v.values())
    if isinstance(v,list):return all(known(x) for x in v)
    return v is not None
def save(p,v):
    with Path(p).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
def file(root,name):
    p=Path(root)/name;require(Path(name).name==name and not Path(root).is_symlink() and not p.is_symlink() and p.is_file() and p.resolve().parent==Path(root).resolve(),'Missing/linked original: '+name);return p
def folder(root,ref):
    require(text(ref) and re.fullmatch(r'[a-z][a-z0-9-]*',ref),'Flat run reference required');p=Path(root)/ref;require(p.is_dir() and not p.is_symlink() and p.resolve().parent==Path(root).resolve(),'Missing/linked native run');return p
def context(c):
    shape(c,{'format',*IDENTITY,'selection','recovery_kind','history_complete','latching_complete'})
    require(c['format']=='opentools.bringup-context.v1' and all(text(c[k]) for k in IDENTITY),'Explicit original identity required')
    require(re.fullmatch(r'[a-z][a-z0-9-]*',c['run_ref']) and c['recovery_kind'] in ('POR','WARM'),'Qualified run/reset class required')
    shape(c['selection'],SELECTION)
    for v in c['selection'].values():uint(v)
    require(c['selection']['fault_mask']==1,'First profile selects one scalar cause bit')
    for k in ('history_complete','latching_complete'):require(c[k] is None or type(c[k]) is bool,'Explicit coverage boolean/null required')
    return c
