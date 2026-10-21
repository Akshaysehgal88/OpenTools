"""Portable interface-budget records and the unchanged parent result audit."""
import json,math,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from applicability_core import audit,canonical,digest,exit_code as result_exit,file_hash as sha,read_json,require
VERSION='v2.0-17598-ga008522d8'
PROFILE='opentools.sta-interface-budget.v1'
VIEWS=('upstream','downstream','top')
IDENTITY=('run_ref','packet_ref','scope_ref','design_ref','configuration_ref','mode_ref','corner_ref','view')
def text(v):return isinstance(v,str) and bool(v.strip()) and len(v)<=2048
def shape(v,keys):require(isinstance(v,dict) and set(v)==set(keys),'Expected fields: '+', '.join(sorted(keys)))
def token(v):require(text(v) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',v),'Unsupported flat native name');return v
def pin_name(v):require(text(v) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*/[A-Za-z_][A-Za-z0-9_]*',v),'Flat instance/pin required');return v
def number(v):require(type(v) in (int,float) and math.isfinite(v),'Finite number required');return float(v)
def save(path,v):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
def file(root,name):
    root=Path(root);p=root/name;require(Path(name).name==name and not root.is_symlink() and not p.is_symlink() and p.is_file() and p.resolve().parent==root.resolve(),'Missing/linked original: '+name);return p
def folder(root,ref):
    require(text(ref) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*',ref),'Flat run reference required');p=Path(root)/ref;require(not p.is_symlink() and p.is_dir() and p.resolve().parent==Path(root).resolve(),'Missing/linked run');return p
def config(ctx):
    shape(ctx,{'format',*IDENTITY,'setup'})
    require(ctx['format']=='opentools.interface-budget-context.v1' and all(text(ctx[k]) for k in IDENTITY) and ctx['view'] in VIEWS,'Explicit native view identity required');require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*',ctx['run_ref']),'Flat run reference required')
    s=ctx['setup'];shape(s,{'clock_name','clock_port','period_ns','input_port','output_port','input_delay_ns','output_delay_ns','output_fall','load_pF','from_kind','from','to_kind','to','bridge_net','sink_net','cases'})
    for k in ('clock_name','input_port','output_port','bridge_net','sink_net'):
        if s[k] is not None:token(s[k])
    if s['clock_port'] is not None:token(s['clock_port'])
    require(number(s['period_ns'])>0 and type(s['output_fall']) is bool,'Explicit period/reference edge required')
    for k in ('input_delay_ns','output_delay_ns','load_pF'):
        if s[k] is not None:number(s[k])
    for prefix in ('from','to'):
        require(s[prefix+'_kind'] in ('port','pin'),'Native point kind required');(token if s[prefix+'_kind']=='port' else pin_name)(s[prefix])
    require(isinstance(s['cases'],dict) and s['cases'],'Explicit operating cases required')
    for k,v in s['cases'].items():token(k);require(v is None or type(v) is int and v in (0,1),'Binary case or null required')
    values={'run_ref':ctx['run_ref'],'view':ctx['view'],**{k:('NONE' if v is None else int(v) if type(v) is bool else v) for k,v in s.items() if k!='cases'}}
    return '\n'.join(['set '+k+' '+str(v) for k,v in values.items()]+['set phase_cases {'+' '.join(k+' '+str(v) for k,v in sorted(s['cases'].items()) if v is not None)+'}','set inspected_cases {'+' '.join(sorted(s['cases']))+'}'])+'\n'
