"""Portable endpoint intent and original native evidence primitives."""
import hashlib,json,math,re
from pathlib import Path
VERSION='v2.0-17598-ga008522d8'
IDENTITY=('run_ref','scope_ref','design_ref','configuration_ref','mode_ref')
PROFILE='opentools.sta-endpoint-census.v1'
def require(ok,message):
    if not ok:raise ValueError(message)
def text(v):return isinstance(v,str) and bool(v.strip()) and len(v)<=2048
def shape(v,keys):require(isinstance(v,dict) and set(v)==set(keys),'Expected fields: '+', '.join(sorted(keys)))
def token(v):require(text(v) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',v),'Unsupported flat native name');return v
def number(v):require(type(v) in (int,float) and math.isfinite(v),'Finite number required');return float(v)
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def parse(s):
    def pairs(values):
        out={}
        for k,v in values:require(k not in out,'Duplicate JSON key');out[k]=v
        return out
    return json.loads(s,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
def read_json(path):return parse(Path(path).read_text(encoding='utf-8'))
def save(path,v):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
def file(root,name):
    root=Path(root);p=root/name;require(Path(name).name==name and not root.is_symlink() and not p.is_symlink() and p.is_file() and p.resolve().parent==root.resolve(),'Missing/linked original: '+name);return p
def config(ctx):
    shape(ctx,{'format',*IDENTITY,'power_ref','mode_basis_ref','power_basis_ref','setup'})
    require(ctx['format']=='opentools.sta-endpoint-context.v1' and all(text(ctx[k]) for k in (*IDENTITY,'power_ref')),'Explicit run/mode/power identities required')
    require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*',ctx['run_ref']),'Flat run reference required')
    for k in ('mode_basis_ref','power_basis_ref'):require(ctx[k] is None or text(ctx[k]),'Invalid mode/power source')
    s=ctx['setup'];shape(s,{'clock_name','clock_port','period_ns','cases','input_delays','output_delays'})
    token(s['clock_name']);token(s['clock_port']);require(number(s['period_ns'])>0,'Positive period required')
    require(isinstance(s['cases'],dict) and 1<=len(s['cases'])<=16,'Explicit case ports required')
    for k,v in s['cases'].items():token(k);require(v is None or type(v) is int and v in (0,1),'Binary case or null required')
    delays={}
    for kind in ('input_delays','output_delays'):
        require(isinstance(s[kind],dict) and len(s[kind])<=64,'Explicit bounded delay map required');items=[]
        for port,value in sorted(s[kind].items()):token(port);items.extend([port,str(number(value))])
        delays[kind]=' '.join(items)
    return '\n'.join(['set '+k+' '+str(v) for k,v in [('run_ref',ctx['run_ref']),('clock_name',s['clock_name']),('clock_port',s['clock_port']),('period_ns',s['period_ns'])]]+
      ['set phase_cases {'+' '.join(k+' '+str(v) for k,v in sorted(s['cases'].items()) if v is not None)+'}','set inspected_cases {'+' '.join(sorted(s['cases']))+'}']+['set '+k+' {'+v+'}' for k,v in delays.items()])+'\n'
