"""Shared record primitives for the owned finite fault-campaign profile."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from coverage_core import read_json,require

MODEL='opentools.owned-site-stuck-at.v1'
ROLES=('stimulus','test_mode','fault_enable','fault_site','stuck_value','raw_sites','driven_sites','observed')
IDENTITY=('run_ref','scope_ref','design_ref','configuration_ref','fault_model_ref','objective_ref')
BASIS=('model_basis_ref','constraint_basis_ref','pattern_basis_ref','exclusion_basis_ref','owner_ref')
CLASSES=('DT','UD','UT','AB','UNKNOWN')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def uint(value,maximum,label):
    require(type(value) is int and 0<=value<=maximum,'Invalid '+label);return value
def text(value,label):
    require(isinstance(value,str) and value.strip() and len(value)<=1024,'Missing/invalid '+label);return value
def save(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2,allow_nan=False)+'\n')
def file(root,name):
    root=Path(root);p=root/name
    require(Path(name).name==name and not root.is_symlink() and not p.is_symlink() and p.is_file() and p.resolve().parent==root.resolve() and p.stat().st_size<=64*1024*1024,'Missing/linked/out-of-bounds native file: '+name)
    return p
def exit_code(report):return 1 if report['findings'] else 2 if report['gaps'] else 0
