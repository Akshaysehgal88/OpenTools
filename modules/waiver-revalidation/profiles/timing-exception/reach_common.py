"""Portable records for the selected native setup-exception population."""
import hashlib,json,math,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from waiver_core import compare,digest,read_json,require

IDENTITY=('run_ref','scope_ref','design_ref','configuration_ref','mode_ref')
VERSION='v2.0-17598-ga008522d8'
PROFILE='opentools.sta-false-path-setup.v1'

def text(v):return isinstance(v,str) and bool(v.strip()) and len(v)<=2048
def shape(v,keys):require(isinstance(v,dict) and set(v)==set(keys),'Expected fields: '+', '.join(sorted(keys)))
def token(v,glob=False):
    require(text(v) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_*?]*' if glob else r'[A-Za-z_][A-Za-z0-9_]*',v),'Unsupported flat native name/pattern');return v
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2,allow_nan=False)+'\n')
def file(root,name):
    root=Path(root);p=root/name
    require(Path(name).name==name and not root.is_symlink() and not p.is_symlink() and p.is_file() and p.resolve().parent==root.resolve(),'Missing/linked original: '+name);return p
def parse(line):
    def pairs(items):
        out={}
        for k,v in items:require(k not in out,'Duplicate JSON key');out[k]=v
        return out
    return json.loads(line,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Non-finite JSON')))
def config(ctx):
    shape(ctx,{'format',*IDENTITY,'setup'})
    require(ctx['format']=='opentools.sta-exception-context.v1' and all(text(ctx[k]) for k in IDENTITY),'Explicit context identities required')
    require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*',ctx['run_ref']),'Flat run reference required')
    s=ctx['setup'];shape(s,{'clocks','cases','from_pattern','to_pattern','trace'})
    require(type(s['trace']) is bool and isinstance(s['clocks'],list) and 1<=len(s['clocks'])<=4,'Bounded explicit clock setup required')
    clocks=[];seen=set()
    for c in s['clocks']:
        shape(c,{'name','port','period_ns'});token(c['name']);token(c['port'])
        require(c['name'] not in seen and type(c['period_ns']) in (int,float) and math.isfinite(c['period_ns']) and c['period_ns']>0,'Distinct clocks and positive periods required');seen.add(c['name']);clocks.append('{'+f"{c['name']} {c['port']} {c['period_ns']}"+'}')
    require(isinstance(s['cases'],dict) and 1<=len(s['cases'])<=16,'Explicit mode/reset ports required')
    for k,v in s['cases'].items():token(k);require(v is None or type(v) is int and v in (0,1),'Binary case or null required')
    for k in ('from_pattern','to_pattern'):token(s[k],True)
    return '\n'.join(['set run_ref '+ctx['run_ref'],'set clocks {'+' '.join(clocks)+'}',
      'set phase_cases {'+' '.join(k+' '+str(v) for k,v in sorted(s['cases'].items()) if v is not None)+'}',
      'set case_ports {'+' '.join(sorted(s['cases']))+'}','set from_pattern '+s['from_pattern'],'set to_pattern '+s['to_pattern'],'set trace_enabled '+str(int(s['trace']))])+'\n'
