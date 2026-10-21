"""Data-only scenario records; reuse the parent result applicability audit."""
import json,math,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from applicability_core import audit,canonical,digest,exit_code as result_exit,file_hash as sha,read_json,require
VERSION='v2.0-17598-ga008522d8'
PROFILE='opentools.sta-scenario-selected-setup.v1'
IDENTITY=('run_ref','scope_ref','design_ref','configuration_ref','scenario_ref')
REQUIRED_FIELDS={'scope.identity','implementation.source_sha256','library.source_sha256','physical_library.source_sha256','library.pvt','scenario.mode','scenario.corner','power.state','native.cases','clock.definition','rc.view','profile'}
def text(v):return isinstance(v,str) and bool(v.strip()) and len(v)<=2048
def shape(v,keys):require(isinstance(v,dict) and set(v)==set(keys),'Expected fields: '+', '.join(sorted(keys)))
def token(v):require(text(v) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',v),'Unsupported flat native name');return v
def number(v):require(type(v) in (int,float) and math.isfinite(v),'Finite number required');return float(v)
def save(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2,allow_nan=False)+'\n')
def file(root,name):
    root=Path(root);p=root/name;require(Path(name).name==name and not root.is_symlink() and not p.is_symlink() and p.is_file() and p.resolve().parent==root.resolve(),'Missing/linked original: '+name);return p
def folder(root,ref):
    require(text(ref) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*',ref),'Flat run reference required');p=Path(root)/ref
    require(not p.is_symlink() and p.is_dir() and p.resolve().parent==Path(root).resolve(),'Missing/linked run directory');return p
def config(ctx):
    shape(ctx,{'format',*IDENTITY,'scenario','setup'})
    require(ctx['format']=='opentools.sta-scenario-context.v1' and all(text(ctx[k]) for k in IDENTITY),'Explicit scenario identities required')
    require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*',ctx['run_ref']),'Flat run reference required')
    s=ctx['scenario'];shape(s,{'mode','corner','power_state','mode_basis_ref','corner_basis_ref','power_basis_ref','rc_basis_ref','clock_basis_ref'})
    for k in ('mode','corner','power_state'):require(text(s[k]),'Explicit semantic scenario identity required')
    for k in ('mode_basis_ref','corner_basis_ref','power_basis_ref','rc_basis_ref','clock_basis_ref'):require(s[k] is None or text(s[k]),'Invalid scenario source reference')
    x=ctx['setup'];shape(x,{'clock_name','clock_port','period_ns','cases','operating_condition','from_cell','to_cell'})
    for k in ('clock_name','clock_port','operating_condition','from_cell','to_cell'):token(x[k])
    require(number(x['period_ns'])>0 and isinstance(x['cases'],dict) and 1<=len(x['cases'])<=16,'Explicit period and cases required')
    for k,v in x['cases'].items():token(k);require(v is None or type(v) is int and v in (0,1),'Binary case or null required')
    return '\n'.join(['set '+k+' '+str(v) for k,v in [('run_ref',ctx['run_ref']),*[(k,x[k]) for k in ('clock_name','clock_port','period_ns','operating_condition','from_cell','to_cell')]]]+['set phase_cases {'+' '.join(k+' '+str(v) for k,v in sorted(x['cases'].items()) if v is not None)+'}','set inspected_cases {'+' '.join(sorted(x['cases']))+'}'])+'\n'
