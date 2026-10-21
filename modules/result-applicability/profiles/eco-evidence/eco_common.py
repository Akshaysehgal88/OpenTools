"""Scoped ECO evidence primitives; parent result semantics remain unchanged."""
import re,sys
from pathlib import Path
PARENT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PARENT))
from applicability_core import audit,canonical,digest,exit_code as result_exit,file_hash,read_json,require,validate_snapshot
IDENTITY=('run_ref','scope_ref','design_ref','configuration_ref','phase_ref')
BASIS=('change_basis_ref','identity_basis_ref','functional_intent_ref','clock_scope_ref','test_scope_ref','power_scope_ref','approval_basis_ref','owner_ref')
ROLES=('clock','reset','a','b','da','db','gclk','q0','q1')
REPORTS=('sta','clock')
CLAIMS=('complete_equivalence','parasitic_validity','route_legality','power_behavior','complete_ECO_signoff')
PRIMITIVES={'ECO_AND':('A','B'),'ECO_OR':('A','B'),'ECO_INV':('A',),'ECO_BUF':('A',)}
def text(value,label):
    require(isinstance(value,str) and value.strip() and len(value)<=2048,'Invalid '+label);return value
def identifier(value,label):
    text(value,label);require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_/-]*',value) is not None,'Unsupported '+label);return value
def uint(value,maximum,label):
    require(type(value) is int and 0<=value<=maximum,'Invalid '+label);return value
def folder(root,ref):
    identifier(ref,'run directory');require('/' not in ref,'Flat run directory required')
    root=Path(root);p=root/ref;require(not root.is_symlink() and not p.is_symlink() and p.is_dir() and p.resolve().parent==root.resolve(),'Missing/linked run directory');return p
def data_file(root,name,optional=False):
    path=Path(root)/name;require(Path(name).name==name and not path.is_symlink(),'Invalid/linked evidence filename')
    if optional and not path.exists():return None
    require(path.is_file() and path.resolve().parent==Path(root).resolve(),'Missing native file: '+name);return path
def save(path,value):
    import json
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2,allow_nan=False)+'\n')
def header(ctx):
    return '\n'.join(['#define P_'+k.upper()+' '+ctx['ports'][k] for k in ROLES]+['#define RESET_ASSERTED '+str(ctx['reset_asserted']),'#define MODE_A '+str(ctx['mode_a']),'#define MODE_B '+str(ctx['mode_b']),'#define CYCLES '+str(ctx['cycles']),''])
def config(ctx):
    p=ctx['ports'];pairs=[('run_ref',ctx['run_ref']),('clock_name',ctx['clock_name']),('clock_port',p['clock']),('period',ctx['period']),('data_a',p['da']),('data_b',p['db']),('capture_cell',ctx['cells']['capture'])]
    return '\n'.join('set '+k+' '+str(v) for k,v in pairs)+'\nset phase_cases {'+' '.join(map(str,(p['reset'],1-ctx['reset_asserted'],p['a'],ctx['mode_a'],p['b'],ctx['mode_b'])))+'}\n'
