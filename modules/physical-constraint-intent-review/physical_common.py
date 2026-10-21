"""Portable physical intervention records; no native code executes on import."""
import hashlib,json,math,re
from pathlib import Path
IDENTITY=('run_ref','scope_ref','design_ref','configuration_ref','phase_ref')
BASIS=('intent_basis_ref','constraint_rationale_ref','region_basis_ref','clock_domain_basis_ref','performance_basis_ref','power_basis_ref','correspondence_ref','owner_ref')
CLAIMS=('routed_wirelength_improvement','congestion_improvement','timing_improvement','throughput_latency','macro_pin_access_signoff','power_isolation','complete_physical_signoff')

def require(ok,message):
    if not ok:raise ValueError(message)
def text(value,label):
    require(isinstance(value,str) and value.strip() and len(value)<=2048,'Invalid '+label);return value
def identifier(value,label):
    text(value,label);require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_/-]*',value) is not None,'Unsupported '+label);return value
def integer(value,label):
    require(type(value) is int and -(1<<50)<value<(1<<50),'Invalid '+label);return value
def number(value,label):
    require(type(value) in (int,float) and math.isfinite(value),'Invalid '+label);return value
def box(value,label,degenerate=False):
    require(isinstance(value,list) and len(value)==4,'Invalid '+label)
    for v in value:integer(v,label)
    require(value[0]<=value[2] and value[1]<=value[3] and (degenerate or (value[0]<value[2] and value[1]<value[3])),'Empty/reversed '+label);return value
def overlap(a,b):return max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3])
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def parse(value):
    def unique(pairs):
        out={}
        for k,v in pairs:require(k not in out,'Duplicate JSON key: '+k);out[k]=v
        return out
    return json.loads(value,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
def read_json(path):return parse(Path(path).read_text(encoding='utf-8'))
def save(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2,allow_nan=False)+'\n')
def file(root,name):
    root=Path(root);path=root/name;require(Path(name).name==name and not root.is_symlink() and not path.is_symlink() and path.is_file() and path.resolve().parent==root.resolve(),'Missing/linked evidence file: '+name);return path
def folder(root,ref):
    identifier(ref,'run directory');require('/' not in ref,'Flat run directory required');p=Path(root)/ref
    require(not Path(root).is_symlink() and not p.is_symlink() and p.is_dir() and p.resolve().parent==Path(root).resolve(),'Missing/linked run directory');return p
def exit_code(report):return 1 if report['findings'] else 2 if report['gaps'] else 0

def config(ctx):
    require(ctx.get('format')=='opentools.physical-context.v1','Unsupported native context')
    for k in IDENTITY:text(ctx.get(k),k)
    identifier(ctx['run_ref'],'run reference')
    for k in BASIS:
        if ctx.get(k) is not None:text(ctx[k],k)
    s=ctx['setup'];require(set(s)=={'top','die_um','core_um','site','placements','blockages','clock','case_values','data_ports','endpoint','selected_net','interconnect'},'Unsupported setup')
    require(s['interconnect']=='none','Batch loader qualifies no interconnect RC model')
    for k in ('top','site','endpoint','selected_net'):identifier(s[k],k)
    for k in ('die_um','core_um'):box(s[k],k)
    clock=s['clock'];require(set(clock)=={'name','port','period_ns'},'Invalid clock declaration')
    for k in ('name','port'):identifier(clock[k],'clock '+k)
    require(type(clock['period_ns']) is int and 0<clock['period_ns']<100000,'Invalid clock period')
    require(s['placements'] and isinstance(s['placements'],dict),'Selected placements required')
    placements=[]
    for name,p in sorted(s['placements'].items()):
        identifier(name,'instance');require(set(p)=={'xy_dbu','orientation'} and len(p['xy_dbu'])==2 and p['orientation'] in ('R0','MX','MY','R180'),'Unsupported placement')
        for v in p['xy_dbu']:integer(v,'placement coordinate')
        placements.append('{'+name+' '+' '.join(map(str,p['xy_dbu']))+' '+p['orientation']+'}')
    for region in s['blockages']:box(region,'blockage')
    for p,v in s['case_values'].items():identifier(p,'case port');require(type(v) is int and v in (0,1),'Explicit case value required')
    require(s['data_ports'] and len(set(s['data_ports']))==len(s['data_ports']),'Distinct data ports required')
    for p in s['data_ports']:identifier(p,'data port')
    lines=['set '+k+' '+v for k,v in [('run_ref',ctx['run_ref']),('top',s['top']),('site',s['site']),('selected_net',s['selected_net']),('endpoint',s['endpoint']),('clock_name',clock['name']),('clock_port',clock['port']),('period_ns',str(clock['period_ns']))]]
    lines+=['set '+k+' {'+' '.join(map(str,s[k]))+'}' for k in ('die_um','core_um','data_ports')]
    lines+=['set placements {'+' '.join(placements)+'}', 'set blockages {'+' '.join('{'+ ' '.join(map(str,b))+'}' for b in s['blockages'])+'}',
            'set phase_cases {'+' '.join(p+' '+str(v) for p,v in sorted(s['case_values'].items()))+'}']
    return '\n'.join(lines)+'\n'
