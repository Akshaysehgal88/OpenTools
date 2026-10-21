"""Data-only reader for retained single-clock Verilator handshake journals."""
from pathlib import Path,PurePosixPath
import hashlib,re,sys,xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from progress_core import canonical,read_json,require,shape,text

PROFILE='verilator-5.020-preedge-handshake-journal.v1'
ROLES={'clock','reset','mode','req_valid','req_ready','req_id','req_data','rsp_valid','rsp_ready','rsp_id','rsp_data'}
OUTPUTS={'req_ready','rsp_valid','rsp_id','rsp_data'}
SOURCES=('top.sv','ports.hpp','checker.hpp','main.cpp')
BUILD=['--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','top','--Mdir','obj','top.sv','main.cpp']
XML=['--xml-only','-Wno-fatal','--top-module','top','--xml-output','model.xml','top.sv']
CONTEXT={'format','run_ref','campaign_ref','scope_ref','configuration_ref','model_ref','clock_ref','edge','sampling','reset_ref','reset_active',
         'checker_ref','checker_source_ref','scope_basis_ref','instrumentation_review_ref','oracle_ref','dependencies_complete','dependency_basis_ref','port_map','window_ref'}
EDGE_KEYS=('tick','reset','mode','enabled','req_valid','req_ready','req_id','req_data','rsp_valid','rsp_ready','rsp_id','rsp_data','clock')
def file_hash(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def contained(root,relative):
    require(text(relative) and '\\' not in relative and ':' not in relative,'Use relative POSIX evidence paths')
    p=PurePosixPath(relative);require(not p.is_absolute() and all(v not in ('','.','..') for v in relative.split('/')),'Evidence path escapes root')
    root=Path(root).resolve();target=root
    for part in p.parts:target/=part;require(not target.is_symlink(),'Linked evidence unsupported')
    require(target.resolve().is_relative_to(root),'Evidence path escapes root');return target
def context(value):
    shape(value,CONTEXT);require(value['format']=='opentools.checker-observation-context.v1','Unsupported context')
    required=('run_ref','campaign_ref','scope_ref','configuration_ref','model_ref','clock_ref','reset_ref','checker_ref','checker_source_ref','window_ref')
    require(all(text(value[k]) for k in required),'Explicit native identity/scope selectors required')
    require(all(value[k] is None or text(value[k]) for k in ('scope_basis_ref','instrumentation_review_ref','oracle_ref','dependency_basis_ref')),'Invalid basis reference')
    require(value['edge']=='positive' and value['sampling']=='stable_preedge' and type(value['reset_active']) is int and value['reset_active'] in (0,1),'Qualified sampling is stable before a positive edge with explicit reset polarity')
    require(value['dependencies_complete'] is None or type(value['dependencies_complete']) is bool,'Invalid dependencies')
    m=value['port_map'];require(isinstance(m,dict) and set(m)==ROLES and len(set(m.values()))==len(ROLES) and all(text(v) and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',v) for v in m.values()),'Select explicit distinct top-port roles')
    require(value['clock_ref']=='top.'+m['clock'] and value['reset_ref']=='top.'+m['reset'],'Clock/reset reference differs from selected native port')
def xml_ports(content,mapping):
    require('<!DOCTYPE' not in content and '<!ENTITY' not in content,'XML entities unsupported')
    try:root=ET.fromstring(content)
    except ET.ParseError as exc:raise ValueError('Malformed native XML: '+str(exc)) from exc
    require(root.tag=='verilator_xml','Unsupported native XML');mods=root.findall('./netlist/module');require(len(mods)==1 and mods[0].get('name')=='top' and mods[0].get('topModule')=='1','Qualified native model has one flat top')
    top=mods[0];types={n.get('id'):n for n in root.findall('./netlist/typetable/basicdtype')};ports={}
    for n in top.findall('var'):
        if n.get('dir') not in ('input','output'):continue
        dtype=types.get(n.get('dtype_id'));require(dtype is not None and dtype.get('name') in ('logic','bit') and dtype.get('signed','false') in ('false','0'),'Unsigned native top ports required')
        width=abs(int(dtype.get('left','0'))-int(dtype.get('right','0')))+1;require(1<=width<=32,'Port widths1..32 supported');ports[n.get('name')]={'direction':n.get('dir'),'width':width}
    require(set(mapping.values())<=set(ports),'A selected observation role is absent from native ports')
    for role,name in mapping.items():
        require(ports[name]['direction']==('output' if role in OUTPUTS else 'input'),'Native port direction differs: '+role)
        if role not in ('req_id','rsp_id','req_data','rsp_data'):require(ports[name]['width']==1,'Control role must be scalar')
    for a,b in (('req_id','rsp_id'),('req_data','rsp_data')):require(ports[mapping[a]]['width']==ports[mapping[b]]['width'],'Accepted/completion widths differ')
    senses=top.findall('.//senitem');require(senses and all(s.get('edgeType')=='POS' and len(s)==1 and s[0].tag=='varref' and s[0].get('name')==mapping['clock'] for s in senses),'Native clock is outside the single-positive-edge profile')
    return ports
def journal(content,ctx,ports):
    edges=[];checks=[];final=None;last=None
    for line in content.splitlines():
        values=line.split();require(values and values[0] in ('EDGE','CHECK','FINAL'),'Unknown/truncated native journal record')
        require(all(re.fullmatch(r'\d+',v) for v in values[1:]),'Native journal requires unsigned integer fields')
        nums=list(map(int,values[1:]));require(final is None,'Records after native FINAL')
        if values[0]=='EDGE':
            require(len(nums)==len(EDGE_KEYS),'Native EDGE population differs');row=dict(zip(EDGE_KEYS,nums));require(row['tick']==len(edges) and row['clock']==0,'Missing/noncontiguous positive-edge pre-samples')
            for role,value in row.items():
                if role=='tick':continue
                width=1 if role=='enabled' else ports[ctx['port_map'][role]]['width'];require(value<2**width,'Native sample exceeds port width')
            edges.append(row);last=row['tick']
        elif values[0]=='CHECK':
            require(len(nums)==5 and nums[0]==last,'Checker sample is detached from its actual pre-edge sample')
            row=dict(zip(('tick','id','expected','observed','ok'),nums));require(row['id']<2**ports[ctx['port_map']['rsp_id']]['width'] and row['expected']<2**ports[ctx['port_map']['rsp_data']]['width'] and row['observed']<2**ports[ctx['port_map']['rsp_data']]['width'] and row['ok'] in (0,1),'Checker record width invalid')
            require(row['ok']==int(row['expected']==row['observed']),'Native comparison action/result contradictory');checks.append(row)
        else:require(len(nums)==5 and edges,'Native FINAL invalid');final=dict(zip(('stimulus','accepted','completed','checked','failures'),nums))
    require(final is not None,'Complete native FINAL missing')
    active=[e for e in edges if e['reset']!=ctx['reset_active']]
    actual={'stimulus':sum(e['req_valid'] for e in active),'accepted':sum(e['req_valid'] and e['req_ready'] for e in active),
            'completed':sum(e['rsp_valid'] and e['rsp_ready'] for e in active),'checked':len(checks),'failures':sum(not c['ok'] for c in checks)}
    require(actual==final,'Native aggregate contradicts complete event journal');return edges,checks,final
def capture(root,workdir,ctx):
    context(ctx);hashes={}
    def read(name,parsed=False):
        relative=workdir+'/'+name;p=contained(root,relative);require(p.is_file(),'Missing native artifact: '+relative);hashes[relative]=file_hash(p)
        return read_json(p) if parsed else p.read_text(encoding='utf-8')
    version=read('version.txt').strip();require(version.startswith('Verilator 5.020 '),'Unqualified native version')
    for name in SOURCES:read(name)
    mapping=ctx['port_map'];macros={}
    for line in read('ports.hpp').splitlines():
        m=re.fullmatch(r'#define ([A-Z_]+) ([A-Za-z_0-9]+)',line);require(m is not None and m[1] not in macros,'Unsupported/duplicate native port macro');macros[m[1]]=m[2]
    require({'M_'+r.upper() for r in ROLES}|{'RESET_ACTIVE'}<=set(macros) and all(macros['M_'+r.upper()]==mapping[r] for r in ROLES) and macros['RESET_ACTIVE']==str(ctx['reset_active']),'Compiled role/reset mapping differs from context')
    ports=xml_ports(read('model.xml'),mapping)
    for label,expected in (('build',BUILD),('xml',XML)):
        command=read(label+'.command.json',True);require(isinstance(command,list) and len(command)==len(expected)+1 and text(command[0]) and command[1:]==expected,'Native '+label+' command outside qualified profile')
        read(label+'.stdout.txt');read(label+'.stderr.txt')
    binary=contained(root,workdir+'/Vtop');require(binary.is_file(),'Original Linux ELF missing')
    with binary.open('rb') as stream:require(stream.read(4)==b'\x7fELF','Original Linux ELF missing')
    hashes[workdir+'/Vtop']=file_hash(binary)
    execution=read('execution.json',True);shape(execution,{'build_exit','xml_exit','run_exit','binary_sha256'})
    require(type(execution['build_exit']) is int and execution['build_exit']==0 and type(execution['xml_exit']) is int and execution['xml_exit']==0 and type(execution['run_exit']) is int and execution['run_exit'] in (0,1) and execution['binary_sha256']==hashes[workdir+'/Vtop'],'Native build/run incomplete or binary differs')
    command=read('run.command.json',True);require(isinstance(command,list) and command and all(text(v) for v in command),'Original native run command missing')
    require(not read('run.stderr.txt').strip(),'Native execution diagnostic unresolved')
    edges,checks,counts=journal(read('run.stdout.txt'),ctx,ports);require(execution['run_exit']==int(counts['failures']>0),'Native checker outcome contradicts comparison actions')
    return {'format':'opentools.checker-observation-evidence.v1','context':ctx,'source_sha256':{n:hashes[workdir+'/'+n] for n in SOURCES},'ports':ports,
            'edges':edges,'checks':checks,'native':{'status':'FAIL' if counts['failures'] else 'PASS','counts':counts,'execution':execution,'command':command,'version':version},
            'provenance':{'reader':PROFILE,'workdir':workdir,'integrity_files':hashes,'declarations':'Original source/instrumentation/expected-model and dependency references are supplied, not authenticated. Native journal correspondence is not arbitrary C++ instrumentation attestation or verification completeness.'}}
def revalidate(evidence,root):
    p=evidence.get('provenance',{});require(p.get('reader')==PROFILE and isinstance(p.get('integrity_files'),dict),'Unsupported native observation receipt')
    for relative,sha in p['integrity_files'].items():require(file_hash(contained(root,relative))==sha,'Changed native artifact: '+relative)
    require(canonical(capture(root,p.get('workdir'),evidence.get('context')))==canonical(evidence),'Normalized evidence differs from original native files/context')
