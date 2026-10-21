"""Read original native DFT, mode and finite scan behavior evidence without execution."""
import math,re,xml.etree.ElementTree as ET
from dft_common import canonical,contained,file_hash,read_json,require,shape,text
PROFILE='openroad-a008522d8-verilator-5.020-one-reset-chain.v1'
OPENROAD_VERSION='v2.0-17598-ga008522d8'
SOURCES=('seed.v','scanned.v','cells.lib','cells.lef','cells_model.sv','top.sv','ports.hpp','main.cpp')
INPUT_ROLES={'fclk','tclk','por','functional_reset','test_mode','manufacturing','debug','power','isolation','shift_request','serial_in','parallel_data'}
OUTPUT_ROLES={'reset_level','scan_enable','chain_clock','raw_state','visible_state','serial_out'}
BUILD=['--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','top','--Mdir','obj','top.sv','scanned.v','cells_model.sv','main.cpp']
XML=['--xml-only','-Wno-fatal','--top-module','top','--xml-output','model.xml','top.sv','scanned.v','cells_model.sv']
STEP_FIELDS=('serial_in','parallel_data','tclk','fclk','reset_level','scan_enable','chain_clock','serial_before','raw_state','visible_state','expected_state','expected_serial','failures')
CHAIN={'module','scan_master','instances','pin_map','clock_port','reset_port','enable_port','scan_in_port','scan_out_port','data_port','state_port','clock_name','reset_released'}
BASES={'mapping_basis_ref','instrumentation_basis_ref','model_basis_ref','supply_basis_ref','policy_basis_ref','timing_basis_ref','dependency_basis_ref'}
def context(c):
    shape(c,{'format','run_ref','scope_ref','configuration_ref','design_ref','mode_ref','domain_ref','chain','role_map','wrapper_instance','dependencies_complete'}|BASES)
    require(c['format']=='opentools.dft-resource-context.v1' and all(text(c[k]) for k in ('run_ref','scope_ref','configuration_ref','design_ref','mode_ref','domain_ref','wrapper_instance')),'Original DFT selectors required')
    require(all(c[k] is None or text(c[k]) for k in BASES) and (c['dependencies_complete'] is None or type(c['dependencies_complete']) is bool),'Invalid source bases')
    m=c['role_map'];require(isinstance(m,dict) and set(m)==INPUT_ROLES|OUTPUT_ROLES and len(set(m.values()))==len(m) and all(re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',v or '') for v in m.values()),'Explicit distinct behavior port roles required')
    s=c['chain'];shape(s,CHAIN);require(isinstance(s['instances'],list) and 1<=len(s['instances'])<=32 and len(set(s['instances']))==len(s['instances']) and all(text(v) for v in s['instances']),'Select1..32distinct native scan instances')
    shape(s['pin_map'],{'clock','reset','enable','scan_in','scan_out','data'});require(len(set(s['pin_map'].values()))==6 and all(text(v) for v in s['pin_map'].values()),'Explicit scan cell pin mapping required')
    require(type(s['reset_released']) is int and s['reset_released'] in (0,1) and all(text(s[k]) for k in CHAIN-{'instances','pin_map','reset_released'}),'Invalid chain selectors')
def resources(content):
    data={'cells':{},'pins':{},'ports':{},'clocks':{},'cases':{},'leaf_sim':{},'module':None};lines=content.splitlines()
    require(lines and lines[0]=='FORMAT opentools.openroad-dft-resources.v1' and lines[-1]=='OPENTOOLS_NATIVE_RESOURCE_EXPORT_COMPLETE','Native resource boundaries missing')
    for line in lines[1:-1]:
        p=line.split();require(p,'Empty native resource record');tag=p[0]
        if tag=='MODULE':require(len(p)==2 and data['module'] is None,'Duplicate native module');data['module']=p[1]
        elif tag=='CELL':require(len(p)==3 and p[1] not in data['cells'],'Duplicate native cell');data['cells'][p[1]]=p[2];data['pins'][p[1]]={}
        elif tag=='PIN':require(len(p)==4 and p[1] in data['pins'] and p[2] not in data['pins'][p[1]],'Duplicate/foreign native pin');data['pins'][p[1]][p[2]]=p[3]
        elif tag=='PORT':require(len(p)==4 and p[1] not in data['ports'] and p[2] in ('INPUT','OUTPUT'),'Invalid native boundary port');data['ports'][p[1]]={'direction':p[2],'net':p[3]}
        elif tag=='CLOCK':
            require(len(p)==3 and p[1] not in data['clocks'],'Duplicate native clock');v=float(p[2]);require(math.isfinite(v) and v>0,'Invalid native period');data['clocks'][p[1]]=v
        elif tag in ('CASE','LEAF_SIM'):
            require(len(p)==4 and p[3] in ('0','1','X') and p[1] in ('shift','capture','unload'),'Invalid native mode value');key='cases' if tag=='CASE' else 'leaf_sim';values=data[key].setdefault(p[1],{});require(p[2] not in values,'Duplicate native mode pin');values[p[2]]=p[3]
        else:raise ValueError('Unknown native resource record')
    return data
def chain_view(r,s,verilog,log):
    names=set(s['instances']);require(set(r['cells'])==names and all(v==s['scan_master'] for v in r['cells'].values()),'Native selected scan population/master differs')
    require(r['module']==s['module'] and re.findall(r'\bmodule\s+([A-Za-z_][A-Za-z_0-9]*)\s*\(',verilog)==[s['module']],'Stitched native module differs')
    mapping=s['pin_map'];ports=r['ports'];pins=r['pins'];common={}
    for role,selector in [('clock','clock_port'),('reset','reset_port'),('enable','enable_port'),('scan_in','scan_in_port'),('scan_out','scan_out_port')]:
        require(s[selector] in ports and ports[s[selector]]['direction']==('OUTPUT' if role=='scan_out' else 'INPUT'),'Selected native boundary absent/different direction');common[role]=ports[s[selector]]['net']
    for name in names:
        p=pins[name];require(set(p)==set(mapping.values()),'Native cell is outside six-functional-pin profile')
        require(all(p[mapping[k]]==common[k] for k in ('clock','reset','enable')),'Native scan cells do not share selected root clock/reset/enable')
        pattern=r'\b'+re.escape(s['scan_master'])+r'\s+'+re.escape(name)+r'\s*\((.*?)\);';matches=re.findall(pattern,verilog,re.S);require(len(matches)==1,'Selected instance absent/ambiguous in original stitched netlist')
        pairs=re.findall(r'\.([A-Za-z_][A-Za-z_0-9]*)\s*\(\s*([A-Za-z_][A-Za-z_0-9]*(?:\[\d+\])?)\s*\)',matches[0]);require(len(pairs)==6 and dict(pairs)==p,'Native ODB export differs from stitched Verilog pin connections')
    by_in={p[mapping['scan_in']]:n for n,p in pins.items()};require(len(by_in)==len(names),'Scan input branches/duplicates outside profile');order=[];net=common['scan_in']
    while net in by_in:
        name=by_in[net];require(name not in order,'Scan connectivity cycle');order.append(name);net=pins[name][mapping['scan_out']]
    require(set(order)==names and net==common['scan_out'],'Selected chain is incomplete or ends at another boundary')
    reports=re.findall(r"Scan chain '([^']+)' has (\d+) cells \((\d+) bits\)",log);require(len(reports)==1 and int(reports[0][1])==int(reports[0][2])==len(names),'Native DFT plan differs from stitched population')
    reported=[line.strip().split()[0] for line in log.splitlines() if line.strip() and line.strip().split()[0] in names];require(reported==order,'Native preview order differs from actual stitched chain')
    return {'order':order,'width':len(order),'boundary_nets':common,'native_plan':reports[0][0]}
def xml_bindings(content,c,width):
    require('<!DOCTYPE' not in content and '<!ENTITY' not in content,'XML entities unsupported')
    try:r=ET.fromstring(content)
    except ET.ParseError as exc:raise ValueError('Malformed native XML') from exc
    mods={n.get('name'):n for n in r.findall('./netlist/module')};require(r.tag=='verilator_xml' and 'top' in mods and mods['top'].get('topModule')=='1','Native behavior top absent')
    types={n.get('id'):n for n in r.findall('./netlist/typetable/basicdtype')};vars={n.get('name'):n for n in mods['top'].findall('var') if n.get('dir') in ('input','output')}
    for role,name in c['role_map'].items():
        require(name in vars,'Behavior role absent from native XML');v=vars[name];t=types.get(v.get('dtype_id'));require(t is not None and t.get('signed','false') in ('false','0'),'Unsupported signed/aggregate native role')
        bits=abs(int(t.get('left','0'))-int(t.get('right','0')))+1;wanted=width if role in ('parallel_data','raw_state','visible_state') else 1
        require(bits==wanted and v.get('dir')==('input' if role in INPUT_ROLES else 'output'),'Behavior role width/direction differs')
    instances=[n for n in mods['top'].findall('instance') if n.get('name')==c['wrapper_instance']];require(len(instances)==1 and instances[0].get('defName')==c['chain']['module'],'Behavior does not instantiate selected stitched module')
    ports={n.get('name'):n for n in instances[0].findall('port')};s=c['chain'];links={s['clock_port']:'chain_clock',s['reset_port']:'reset_level',s['enable_port']:'scan_enable',s['scan_in_port']:'serial_in',s['data_port']:'parallel_data',s['state_port']:'raw_state'}
    for pin,role in links.items():require(pin in ports and len(ports[pin])==1 and ports[pin][0].tag=='varref' and ports[pin][0].get('name')==c['role_map'][role],'Observed role does not bind the stitched instance pin')
    return {'wrapper_instance':c['wrapper_instance'],'module':s['module'],'direct_port_links':links}
def behavior(content,width):
    config=None;steps=[];terminal=None;checks=failures=0
    for line in content.splitlines():
        p=line.split();require(p and terminal is None,'Native behavior empty/post-terminal record')
        if p[0]=='CONFIG':
            require(config is None and not steps and len(p)==10 and all(v.isdigit() for v in p[1:]),'Invalid behavior context');config=dict(zip(('width','load_word','capture_word','test_mode','manufacturing','debug','functional_reset','power','isolation'),map(int,p[1:])));require(config['width']==width and all(v in (0,1) for k,v in config.items() if k not in ('width','load_word','capture_word')) and all(config[k]<2**width for k in ('load_word','capture_word')),'Behavior context exceeds native width')
        elif p[0]=='STEP':
            require(config is not None and len(p)==16 and p[1].isdigit() and p[2] in ('shift','capture','unload') and all(v.isdigit() for v in p[3:]),'Invalid scan sample');row={'tick':int(p[1]),'phase':p[2],**dict(zip(STEP_FIELDS,map(int,p[3:])))}
            require(row['tick']==len(steps)+1 and all(row[k] in (0,1) for k in ('serial_in','tclk','fclk','reset_level','scan_enable','chain_clock','serial_before','expected_serial')) and all(row[k]<2**width for k in ('parallel_data','raw_state','visible_state','expected_state')),'Scan sample identity/width invalid')
            checks+=1;failures+=row['raw_state']!=row['expected_state']
            if row['phase']=='unload':checks+=1;failures+=row['serial_before']!=row['expected_serial']
            require(row['failures']==failures,'Native comparison actions contradict cumulative failure count');steps.append(row)
        elif p[0]=='NATIVE_RESULT':
            require(len(p)==4 and all(v.isdigit() for v in p[1:]),'Native result invalid');terminal=dict(zip(('steps','checks','failures'),map(int,p[1:])))
        else:raise ValueError('Unknown native behavior record')
    require(config is not None and steps and terminal=={'steps':len(steps),'checks':checks,'failures':failures},'Complete native behavior result missing/contradictory');return config,steps,terminal
def capture(root,workdir,c):
    context(c);hashes={}
    def read(name,parsed=False):
        rel=workdir+'/'+name;p=contained(root,rel);require(p.is_file(),'Missing native artifact: '+rel);hashes[rel]=file_hash(p);return read_json(p) if parsed else p.read_text(encoding='utf-8')
    require(read('openroad-version.txt').strip()==OPENROAD_VERSION,'Unqualified DFT version');vv=read('verilator-version.txt').strip();require(vv.startswith('Verilator 5.020 '),'Unqualified simulation version')
    for name in SOURCES:read(name)
    for name in ('dft.tcl','export.tcl','mode.sdc','replaced.v','scanned.def'):read(name)
    odb=contained(root,workdir+'/scanned.odb');require(odb.is_file(),'Original native database missing');hashes[workdir+'/scanned.odb']=file_hash(odb)
    for label,marker in [('dft','OPENTOOLS_NATIVE_DFT_COMPLETE'),('mode','OPENTOOLS_NATIVE_RESOURCE_EXPORT_COMPLETE')]:
        cmd=read(label+'.command.json',True);require(isinstance(cmd,list) and len(cmd)==4 and all(text(v) for v in cmd) and cmd[1:]==['-exit','-no_init','dft.tcl' if label=='dft' else 'export.tcl'],'Native DFT/mode command differs')
        log=read(label+'.stdout.txt');errors=read(label+'.stderr.txt');require(log.count(marker)==1 and not any(s in log+errors for s in ('[ERROR','Error:','Signal 11','initialization failed')),'Native DFT/mode task did not complete')
    r=resources(read('resources.txt'));chain=chain_view(r,c['chain'],read('scanned.v'),read('dft.stdout.txt'));binding=xml_bindings(read('model.xml'),c,chain['width'])
    # Macros bind the original logger's roles, rather than assuming a counter label describes a signal.
    macros=dict(re.findall(r'^#define P_([A-Z_]+) ([A-Za-z_][A-Za-z_0-9]*)$',read('ports.hpp'),re.M));require(all(macros.get(k.upper())==v for k,v in c['role_map'].items()),'Original logger role map differs')
    for label,expected in [('build',BUILD),('xml',XML)]:
        cmd=read(label+'.command.json',True);require(isinstance(cmd,list) and cmd[1:]==expected and text(cmd[0]),'Original simulation command differs');read(label+'.stdout.txt');read(label+'.stderr.txt')
    binary=contained(root,workdir+'/Vtop');require(binary.is_file(),'Original native executable missing')
    with binary.open('rb') as f:require(f.read(4)==b'\x7fELF','Original Linux ELF missing')
    hashes[workdir+'/Vtop']=file_hash(binary);ex=read('execution.json',True);shape(ex,{'dft_exit','mode_exit','build_exit','xml_exit','run_exit','binary_sha256'})
    require(all(type(ex[k]) is int and ex[k]==0 for k in ('dft_exit','mode_exit','build_exit','xml_exit')) and type(ex['run_exit']) is int and ex['run_exit'] in (0,1) and ex['binary_sha256']==hashes[workdir+'/Vtop'],'Original execution identity incomplete')
    cmd=read('run.command.json',True);require(isinstance(cmd,list) and cmd and all(text(v) for v in cmd),'Original behavior command missing');require(not read('run.stderr.txt').strip(),'Native behavior diagnostic unresolved')
    config,steps,counts=behavior(read('run.stdout.txt'),chain['width']);require(ex['run_exit']==int(counts['failures']>0),'Native behavior outcome contradicts checker actions')
    return {'format':'opentools.dft-resource-evidence.v1','context':c,'sources':{n:hashes[workdir+'/'+n] for n in SOURCES},'mode_sdc_sha256':hashes[workdir+'/mode.sdc'],'command_sha256':hashes[workdir+'/run.command.json'],
            'inventory':r,'chain':chain,'behavior_binding':binding,'config':config,'steps':steps,'native':{'status':'FAIL' if counts['failures'] else 'PASS','counts':counts,'execution':ex,'openroad_version':OPENROAD_VERSION,'verilator_version':vv},
            'provenance':{'reader':PROFILE,'workdir':workdir,'integrity_files':hashes,'limits':'Explicit root case values, native same-net connectivity and finite observed pin values are separate evidence. Unknown native propagated values remain unknown. Source/model/policy/dependency references are supplied, not authenticated. No timing, analog-power, ATPG, security-policy or signoff proof.'}}
def revalidate(evidence,root):
    p=evidence.get('provenance',{});require(p.get('reader')==PROFILE and isinstance(p.get('integrity_files'),dict),'Unsupported native resource receipt')
    for rel,sha in p['integrity_files'].items():require(file_hash(contained(root,rel))==sha,'Changed native artifact: '+rel)
    require(canonical(capture(root,p.get('workdir'),evidence.get('context')))==canonical(evidence),'Normalized record differs from original native evidence')
