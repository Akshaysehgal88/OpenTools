"""Portable STA mode-contract records; separate from availability closure."""
import hashlib,json,math,re
from pathlib import Path
IDENTITY=('run_ref','scope_ref','design_ref','configuration_ref','mode_ref')
BASIS=('mode_basis_ref','clock_availability_ref','reset_basis_ref','power_basis_ref','consumer_basis_ref','lineage_basis_ref','timing_basis_ref','owner_ref')
CLAIMS=('functional_clock_availability','waveform_safety','CDC_RDC_signoff','timing_signoff','all_modes_coverage')
def require(ok,message):
    if not ok:raise ValueError(message)
def text(v,label):require(isinstance(v,str) and v.strip() and len(v)<=2048,'Invalid '+label);return v
def identifier(v,label):text(v,label);require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_/-]*',v) is not None,'Unsupported '+label);return v
def number(v,label):require(type(v) in (int,float) and math.isfinite(v),'Invalid '+label);return v
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def parse(s):
    def unique(pairs):
        out={}
        for k,v in pairs:require(k not in out,'Duplicate JSON key: '+k);out[k]=v
        return out
    return json.loads(s,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
def read_json(path):return parse(Path(path).read_text(encoding='utf-8'))
def save(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2,allow_nan=False)+'\n')
def file(root,name):
    root=Path(root);p=root/name;require(Path(name).name==name and not root.is_symlink() and not p.is_symlink() and p.is_file() and p.resolve().parent==root.resolve(),'Missing/linked evidence file: '+name);return p
def folder(root,ref):
    identifier(ref,'run reference');require('/' not in ref,'Flat run directory required');p=Path(root)/ref
    require(not p.is_symlink() and p.is_dir() and p.resolve().parent==Path(root).resolve(),'Missing/linked run directory');return p
def exit_code(r):return 1 if r['findings'] else 2 if r['gaps'] else 0
def config(ctx):
    require(ctx.get('format')=='opentools.sta-lineage-context.v1','Unsupported context')
    for k in IDENTITY:text(ctx.get(k),k)
    identifier(ctx['run_ref'],'run reference')
    for k in BASIS:
        if ctx.get(k) is not None:text(ctx[k],k)
    s=ctx['setup'];require(set(s)=={'root','generated','cases','propagate','trace','data_port','endpoint'},'Unsupported setup')
    r=s['root'];require(set(r)=={'name','port','period_ns'} and number(r['period_ns'],'root period')>0,'Invalid root')
    for k in ('name','port'):identifier(r[k],k)
    for k in ('data_port','endpoint'):identifier(s[k],k)
    for k in ('propagate','trace'):require(type(s[k]) is bool,'Explicit '+k+' required')
    seen={r['name']};generators=[]
    for g in s['generated']:
        require(set(g)=={'name','target_pin','reference_source','reference_kind','master','divide_by'},'Unsupported generated-clock setup')
        require(g['name'] not in seen,'Duplicate clock definition');seen.add(g['name'])
        for k in ('name','target_pin','reference_source'):identifier(g[k],k)
        require(g['reference_kind'] in ('port','pin') and type(g['divide_by']) is int and g['divide_by']>0,'Invalid generation setup')
        master='NONE' if g['master'] is None else identifier(g['master'],'master clock')
        generators.append('{'+ ' '.join(str(v) for v in (g['name'],g['target_pin'],g['reference_source'],g['reference_kind'],master,g['divide_by']))+'}')
    for p,v in s['cases'].items():identifier(p,'case port');require(v is None or (type(v) is int and v in (0,1)),'Binary case or null required')
    lines=['set '+k+' '+str(v) for k,v in [('run_ref',ctx['run_ref']),('root_name',r['name']),('root_port',r['port']),('root_period',r['period_ns']),('data_port',s['data_port']),('endpoint',s['endpoint']),('propagate',int(s['propagate'])),('trace_enabled',int(s['trace']))]]
    lines+=['set generators {'+' '.join(generators)+'}', 'set phase_cases {'+' '.join(p+' '+str(v) for p,v in sorted(s['cases'].items()) if v is not None)+'}',
            'set inspected_case_ports {'+' '.join(sorted(s['cases']))+'}']
    return '\n'.join(lines)+'\n'
