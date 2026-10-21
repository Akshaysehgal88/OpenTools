"""Read saved finite interaction journals without executing imported commands."""
import hashlib,re,sys
from pathlib import Path,PurePosixPath
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from progress_core import canonical,read_json,require,shape,text
PROFILE='verilator-5.020-scalar-interaction-journal.v1'
ROLES={'clock','reset','hold','retain','event','ack','pending','visible'}
SOURCES=('top.sv','ports.hpp','main.cpp')
BUILD=['--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','top','--Mdir','obj','top.sv','main.cpp']
XML=['--xml-only','-Wno-fatal','--top-module','top','--xml-output','model.xml','top.sv']
FIELDS=('tick','reset','hold','event','ack','retain','pre_pending','pre_visible','post_pending','post_visible','enabled','pre_clock','post_clock')
def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for b in iter(lambda:stream.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def contained(root,relative):
    require(text(relative) and '\\' not in relative and ':' not in relative,'Use relative POSIX evidence paths');p=PurePosixPath(relative)
    require(not p.is_absolute() and all(v not in ('','.','..') for v in relative.split('/')),'Evidence path escapes root');root=Path(root).resolve();target=root
    for v in p.parts:target/=v;require(not target.is_symlink(),'Linked evidence unsupported')
    require(target.resolve().is_relative_to(root),'Evidence path escapes root');return target
def context(c):
    shape(c,{'format','run_ref','scope_ref','configuration_ref','model_ref','scenario_ref','scenario_basis_ref','clock_ref','reset_ref','reset_active','port_map','window_ref','instrumentation_review_ref','oracle_ref','scope_basis_ref','dependencies_complete','dependency_basis_ref'})
    require(c['format']=='opentools.interaction-capture-context.v1','Unsupported context')
    require(all(text(c[k]) for k in ('run_ref','scope_ref','configuration_ref','model_ref','scenario_ref','clock_ref','reset_ref','window_ref')),'Original run/scope selectors required')
    require(all(c[k] is None or text(c[k]) for k in ('scenario_basis_ref','instrumentation_review_ref','oracle_ref','scope_basis_ref','dependency_basis_ref')),'Invalid basis reference')
    require(type(c['reset_active']) is int and c['reset_active'] in (0,1) and (c['dependencies_complete'] is None or type(c['dependencies_complete']) is bool),'Invalid reset/dependency scope')
    m=c['port_map'];require(isinstance(m,dict) and set(m)==ROLES and all(text(v) and re.fullmatch('[A-Za-z_][A-Za-z_0-9]*',v) for v in m.values()) and len(set(m.values()))==len(ROLES),'Explicit distinct scalar top-port roles required')
    require(c['clock_ref']=='top.'+m['clock'] and c['reset_ref']=='top.'+m['reset'],'Native clock/reset selector differs')
def xml_ports(content,mapping):
    require('<!DOCTYPE' not in content and '<!ENTITY' not in content,'XML entities unsupported')
    try:r=ET.fromstring(content)
    except ET.ParseError as exc:raise ValueError('Malformed native XML') from exc
    mods=r.findall('./netlist/module');require(r.tag=='verilator_xml' and len(mods)==1 and mods[0].get('name')=='top' and mods[0].get('topModule')=='1','Qualified native model is one flat top')
    top=mods[0];types={v.get('id'):v for v in r.findall('./netlist/typetable/basicdtype')};ports={}
    for v in top.findall('var'):
        if v.get('dir') not in ('input','output'):continue
        dtype=types.get(v.get('dtype_id'));require(dtype is not None and dtype.get('name') in ('logic','bit') and dtype.get('signed','false') in ('false','0'),'Unsupported port type')
        width=abs(int(dtype.get('left','0'))-int(dtype.get('right','0')))+1;require(1<=width<=32,'Port width outside native profile');ports[v.get('name')]={'direction':v.get('dir'),'width':width}
    require(set(mapping.values())<=set(ports),'Mapped native port absent')
    for role,name in mapping.items():require(ports[name]=={'direction':'output' if role in ('pending','visible') else 'input','width':1},'Mapped role is not a scalar port of the required direction')
    senses=top.findall('.//senitem');require(senses and all(s.get('edgeType')=='POS' and len(s)==1 and s[0].tag=='varref' and s[0].get('name')==mapping['clock'] for s in senses),'Native clock outside single-positive-edge profile')
    return ports
def journal(content):
    frames=[];checks=[];last=None;seen=set();result=None
    for line in content.splitlines():
        p=line.split();require(p and p[0] in ('FRAME','CHECK','RESULT') and result is None,'Unknown/truncated/post-terminal native record')
        if p[0]=='FRAME':
            require(len(p)==len(FIELDS)+1 and all(re.fullmatch(r'\d+',v) for v in p[1:]),'Native frame fields invalid');row=dict(zip(FIELDS,map(int,p[1:])))
            require(row['tick']==len(frames) and all(row[k] in (0,1) for k in FIELDS if k!='tick') and row['pre_clock']==0 and row['post_clock']==1,'Missing/noncontiguous positive-edge frame');frames.append(row);last=row['tick']
        elif p[0]=='CHECK':
            require(len(p)==6 and re.fullmatch(r'\d+',p[1]) and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9.:-]*',p[2]) and all(v in ('0','1') for v in p[3:]),'Native checker record invalid')
            row={'tick':int(p[1]),'id':p[2],'expected':int(p[3]),'observed':int(p[4]),'ok':int(p[5])};key=(row['tick'],row['id'])
            require(row['tick']==last and key not in seen and row['ok']==int(row['expected']==row['observed']),'Detached/duplicate/contradictory checker action');seen.add(key);checks.append(row)
        else:
            require(len(p)==4 and all(re.fullmatch(r'\d+',v) for v in p[1:]),'Native RESULT invalid');result=dict(zip(('frames','checks','failures'),map(int,p[1:])))
    require(frames and result=={'frames':len(frames),'checks':len(checks),'failures':sum(1-v['ok'] for v in checks)},'Complete native result contradicts journal or is missing')
    return frames,checks,result
def capture(root,workdir,c):
    context(c);hashes={}
    def read(name,parsed=False):
        relative=workdir+'/'+name;p=contained(root,relative);require(p.is_file(),'Missing native artifact: '+relative);hashes[relative]=file_hash(p)
        return read_json(p) if parsed else p.read_text(encoding='utf-8')
    version=read('version.txt').strip();require(version.startswith('Verilator 5.020 '),'Unqualified native version')
    for name in SOURCES:read(name)
    macros={}
    for line in read('ports.hpp').splitlines():
        m=re.fullmatch(r'#define ([A-Z_]+) ([A-Za-z_0-9]+)',line);require(m is not None and m[1] not in macros,'Unsupported native role macro');macros[m[1]]=m[2]
    require({'M_'+r.upper() for r in ROLES}|{'RESET_ACTIVE'}<=set(macros) and all(macros['M_'+r.upper()]==c['port_map'][r] for r in ROLES) and macros['RESET_ACTIVE']==str(c['reset_active']),'Compiled role/reset selection differs')
    ports=xml_ports(read('model.xml'),c['port_map'])
    for label,expected in (('build',BUILD),('xml',XML)):
        cmd=read(label+'.command.json',True);require(isinstance(cmd,list) and len(cmd)==len(expected)+1 and text(cmd[0]) and cmd[1:]==expected,'Native build/XML command outside profile');read(label+'.stdout.txt');read(label+'.stderr.txt')
    binary=contained(root,workdir+'/Vtop');require(binary.is_file(),'Original Linux binary missing')
    with binary.open('rb') as f:require(f.read(4)==b'\x7fELF','Original Linux ELF missing')
    hashes[workdir+'/Vtop']=file_hash(binary);ex=read('execution.json',True);shape(ex,{'build_exit','xml_exit','run_exit','binary_sha256'})
    require(all(type(ex[k]) is int for k in ('build_exit','xml_exit','run_exit')) and ex['build_exit']==ex['xml_exit']==0 and ex['run_exit'] in (0,1) and ex['binary_sha256']==hashes[workdir+'/Vtop'],'Original execution/binary unresolved')
    cmd=read('run.command.json',True);require(isinstance(cmd,list) and cmd and all(text(v) for v in cmd),'Native command identity missing');require(not read('run.stderr.txt').strip(),'Native diagnostic unresolved')
    frames,checks,result=journal(read('run.stdout.txt'));require(ex['run_exit']==int(result['failures']>0),'Native result contradicts original comparison actions')
    return {'format':'opentools.interaction-native-evidence.v1','context':c,'sources':{n:hashes[workdir+'/'+n] for n in SOURCES},'ports':ports,'frames':frames,'checks':checks,
            'native':{'status':'FAIL' if result['failures'] else 'PASS','counts':result,'command_sha256':hashes[workdir+'/run.command.json'],'execution':ex,'version':version},
            'provenance':{'reader':PROFILE,'workdir':workdir,'integrity_files':hashes,'limits':'Source/instrumentation/oracle/applicability references are supplied, not authenticated. Original C++ semantics and expected-model adequacy require source review; not arbitrary measurement attestation or verification completeness.'}}
def revalidate(e,root):
    p=e.get('provenance',{});require(p.get('reader')==PROFILE and isinstance(p.get('integrity_files'),dict),'Unsupported native receipt')
    for relative,sha in p['integrity_files'].items():require(file_hash(contained(root,relative))==sha,'Changed native artifact: '+relative)
    require(canonical(capture(root,p.get('workdir'),e.get('context')))==canonical(e),'Normalized record differs from original native evidence')
