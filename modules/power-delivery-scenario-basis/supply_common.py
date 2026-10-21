"""Portable scenario records and original-evidence bindings."""
import hashlib,json,math,re
from pathlib import Path
IDENTITY=('run_ref','scope_ref','design_ref','configuration_ref','scenario_ref')
BASIS=('topology_basis_ref','sources_basis_ref','corner_basis_ref','activity_basis_ref','state_basis_ref','concurrency_basis_ref','load_mapping_ref','owner_ref')
CLAIMS=('dynamic_IR','wake_sequence','EM_lifetime','full_chip_signoff','load_model_validity')
SETUP=('net','library_cell','corner','net_voltage_V','layer_resistance_argument','powers_W','source_rows_um_V')
SCENARIO=('activity_ref','state_ref','concurrency_ref','active_domains','instance_domains','time_basis')
def require(ok,message):
    if not ok:raise ValueError(message)
def text(v,label):require(isinstance(v,str) and v.strip() and len(v)<=2048,'Invalid '+label);return v
def identifier(v,label):text(v,label);require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_/-]*',v) is not None,'Unsupported '+label);return v
def number(v,label):require(type(v) in (int,float) and math.isfinite(v),'Invalid '+label);return v
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def parse(s):
    def unique(pairs):
        out={}
        for k,v in pairs:require(k not in out,'Duplicate JSON key: '+k);out[k]=v
        return out
    return json.loads(s,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
def read_json(p):return parse(Path(p).read_text(encoding='utf-8'))
def save(p,v):
    with Path(p).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
def file(root,name,optional=False):
    root=Path(root);p=root/name;require(Path(name).name==name and not root.is_symlink() and not p.is_symlink(),'Linked/invalid evidence file')
    if optional and not p.exists():return None
    require(p.is_file() and p.resolve().parent==root.resolve(),'Missing evidence file: '+name);return p
def folder(root,ref):
    identifier(ref,'run reference');require('/' not in ref,'Flat run directory required');p=Path(root)/ref
    require(not p.is_symlink() and p.is_dir() and p.resolve().parent==Path(root).resolve(),'Missing/linked run directory');return p
def exit_code(r):return 1 if r['findings'] else 2 if r['gaps'] else 0
def known(v):
    if v is None or (isinstance(v,str) and not v.strip()):return False
    if isinstance(v,dict):return all(known(x) for x in v.values())
    if isinstance(v,list):return all(known(x) for x in v)
    return True
def config(ctx):
    require(ctx.get('format')=='opentools.supply-context.v1','Unsupported context')
    for k in IDENTITY:text(ctx.get(k),k)
    identifier(ctx['run_ref'],'run reference')
    for k in BASIS:
        if ctx.get(k) is not None:text(ctx[k],k)
    s=ctx['setup'];require(set(s)==set(SETUP),'Unsupported static setup')
    for k in ('net','library_cell','corner'):identifier(s[k],k)
    require(0<number(s['net_voltage_V'],'net voltage')<=10,'Invalid voltage')
    require(s['layer_resistance_argument'] and s['powers_W'] and s['source_rows_um_V'],'Empty static basis')
    for k,v in s['layer_resistance_argument'].items():identifier(k,'layer');require(number(v,'native resistance argument')>0,'Resistance must be positive')
    for k,v in s['powers_W'].items():identifier(k,'instance');require(number(v,'power override')>=0,'Negative power')
    for row in s['source_rows_um_V']:
        require(isinstance(row,list) and len(row)==4,'Source rows need x,y,size,voltage')
        for v in row:number(v,'source value')
        require(row[2]>0 and row[3]>0,'Invalid source size/voltage')
    require(set(ctx['scenario'])==set(SCENARIO),'Static scenario declaration incomplete')
    lines=['set '+k+' '+str(v) for k,v in [('run_ref',ctx['run_ref']),('net',s['net']),('library_cell',s['library_cell']),('corner',s['corner']),('net_voltage',s['net_voltage_V'])]]
    lines+=['set layer_resistance {'+' '.join(k+' '+str(v) for k,v in sorted(s['layer_resistance_argument'].items()))+'}',
            'set instance_power {'+' '.join(k+' '+str(v) for k,v in sorted(s['powers_W'].items()))+'}']
    return '\n'.join(lines)+'\n'
def source_csv(ctx):return ''.join(','.join(map(str,row))+'\n' for row in ctx['setup']['source_rows_um_V'])
