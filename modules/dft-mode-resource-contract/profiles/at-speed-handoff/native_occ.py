"""Read original measured OCC behavior and native consumed STA evidence as data."""
import math,re,xml.etree.ElementTree as ET
from occ_common import canonical,contained,file_hash,read_json,require,shape,text
PROFILE='openroad-a008522d8-verilator-5.020-loc-window.v1';VERSION='v2.0-17598-ga008522d8'
IDENTITY=('run_ref','scope_ref','design_ref','configuration_ref','domain_ref','phase','recipe_ref','sta_run_ref','sta_scenario_ref')
MAPPING=('unit_module','unit_instance','role_map','clock_names','gate_pin','from_cell','to_cell','reset_released')
BASES=('mapping_basis_ref','model_basis_ref','instrumentation_basis_ref','timing_basis_ref','pattern_basis_ref')
ROLES=('clock','reset','shift','variant','start','data','scan_enable','serial_in','enable','generated_clock','launch','capture','reset_n','slot')
BSOURCES=('unit.v','top.sv','models.sv','ports.hpp','main.cpp');SSOURCES=('unit.v','cells.lib','cells.lef','sta.tcl')
BUILD=['--cc','--exe','--build','-j','2','--timescale','1ns/1ns','-Wno-fatal','--top-module','top','--Mdir','obj','unit.v','top.sv','models.sv','main.cpp']
XML=['--xml-only','--timescale','1ns/1ns','-Wno-fatal','--top-module','top','--xml-output','model.xml','unit.v','top.sv','models.sv']
FRAME=('clock','slot','enable','generated_clock','reset','reset_n','scan_enable','shift','variant','start','data','serial_in','launch','capture','expected_launch','expected_capture','checks','failures')
def number(v):
    value=float(v);require(math.isfinite(value),'Nonfinite native value');return value
def close(a,b):return math.isclose(a,b,rel_tol=0,abs_tol=0.00001)
def context(c):
    shape(c,{'format',*IDENTITY,*MAPPING,*BASES,'native_atpg_scenario_ref','native_atpg_basis_ref'})
    require(c['format']=='opentools.occ-context.v1' and all(text(c[k]) for k in IDENTITY) and c['phase'] in ('shift','capture'),'Explicit run/scenario/recipe identities required')
    require(all(c[k] is None or text(c[k]) for k in (*BASES,'native_atpg_scenario_ref','native_atpg_basis_ref')),'Invalid source references')
    require(type(c['reset_released']) is int and c['reset_released'] in (0,1),'Explicit reset polarity required')
    for k in ('unit_module','unit_instance','from_cell','to_cell'):require(isinstance(c[k],str) and re.fullmatch(r'[A-Za-z_]\w*',c[k]),'Simple selected native identifiers required')
    require(c['from_cell']!=c['to_cell'] and isinstance(c['gate_pin'],str) and re.fullmatch(r'[A-Za-z_]\w*/[A-Za-z_]\w*',c['gate_pin']),'Distinct selected cells and one gate/pin required')
    shape(c['role_map'],ROLES);require(len(set(c['role_map'].values()))==len(ROLES) and all(isinstance(v,str) and re.fullmatch(r'[A-Za-z_]\w*',v) for v in c['role_map'].values()),'Distinct explicit signal roles required')
    require(isinstance(c['clock_names'],list) and len(c['clock_names'])==len(set(c['clock_names']))==2 and all(text(v) for v in c['clock_names']),'Select root and generated clocks')

def resources(content):
    lines=content.splitlines();require(lines and lines[0]=='FORMAT opentools.occ-sta.v1' and lines[-1]=='OPENTOOLS_NATIVE_OCC_STA_COMPLETE','Native STA export boundaries missing')
    result={'labels':{},'clocks':{},'cases':{},'collections':{},'paths':None}
    for line in lines[1:-1]:
        p=line.split();require(p,'Empty native STA record');tag=p[0]
        if tag in ('RUN','SCENARIO','PHASE','MODULE'):require(len(p)==2 and tag not in result['labels'],'Duplicate native label');result['labels'][tag]=p[1]
        elif tag=='CLOCK':
            require(len(p)>=6 and p[1] not in result['clocks'] and p[3] in ('0','1') and p[4] in ('0','1') and p[5].isdigit() and len(p)==6+int(p[5]),'Invalid native clock export');period=number(p[2]);require(period>0,'Positive native period required');result['clocks'][p[1]]={'period_ns':period,'is_generated':int(p[3]),'waveform_valid':int(p[4]),'waveform_ns':[number(v) for v in p[6:]],'sources':None}
        elif tag=='SOURCES':require(len(p)>=3 and p[1] in result['clocks'] and result['clocks'][p[1]]['sources'] is None and p[2].isdigit() and len(p)==3+int(p[2]),'Invalid native clock source collection');result['clocks'][p[1]]['sources']=p[3:]
        elif tag=='CASE':require(len(p)==3 and p[2] in ('0','1','X') and p[1] not in result['cases'],'Duplicate/invalid native mode case');result['cases'][p[1]]=p[2]
        elif tag in ('FROM','TO'):require(tag not in result['collections'] and len(p)>=2 and p[1].isdigit() and len(p)==2+int(p[1]),'Invalid selected native collection');result['collections'][tag]=p[2:]
        elif tag=='PATHS':require(len(p)==3 and all(v.isdigit() for v in p[1:]) and result['paths'] is None,'Invalid native path probe');result['paths']={'without_selected_exception':int(p[1]),'with_consumed_constraints':int(p[2])}
        else:raise ValueError('Unknown native STA record')
    require(set(result['labels'])=={'RUN','SCENARIO','PHASE','MODULE'} and set(result['collections'])=={'FROM','TO'} and result['paths'] is not None and all(v['sources'] is not None for v in result['clocks'].values()),'Incomplete native STA export');return result

def consumed_sdc(content):
    # This is a deliberately small native writer profile, never a Tcl interpreter.
    result={'design':None,'source_clock':None,'generated_clock':None,'cases':{},'false_paths':[]}
    lines=[line.strip() for line in content.replace('\\\n',' ').splitlines() if line.strip() and not line.lstrip().startswith('#')]
    for line in lines:
        m=re.fullmatch(r'current_design ([A-Za-z_]\w*)',line)
        if m:require(result['design'] is None,'Duplicate current_design');result['design']=m[1];continue
        m=re.fullmatch(r'create_clock -name (\S+) -period (\S+) \[get_ports \{([^{}]+)\}\]',line)
        if m:require(result['source_clock'] is None,'Multiple native source clocks outside profile');result['source_clock']={'name':m[1],'period_ns':number(m[2]),'port':m[3]};continue
        m=re.fullmatch(r'create_generated_clock -name (\S+) -source \[get_ports \{([^{}]+)\}\] -divide_by (\d+) \[get_pins \{([^{}]+)\}\]',line)
        if m:require(result['generated_clock'] is None,'Multiple generated clocks outside profile');result['generated_clock']={'name':m[1],'source_port':m[2],'divide_by':int(m[3]),'pin':m[4]};continue
        m=re.fullmatch(r'set_case_analysis ([01]) \[get_ports \{([^{}]+)\}\]',line)
        if m:require(m[2] not in result['cases'],'Duplicate consumed case');result['cases'][m[2]]=m[1];continue
        m=re.fullmatch(r'set_false_path\s+-from \[get_cells \{([^{}]+)\}\]\s+-to \[get_cells \{([^{}]+)\}\]',line)
        if m:result['false_paths'].append({'from_cells':m[1].split(),'to_cells':m[2].split()});continue
        raise ValueError('Unsupported native consumed-SDC statement')
    require(result['design'] is not None and result['source_clock'] is not None and result['generated_clock'] is not None and len(result['false_paths'])<=1,'Incomplete/unsupported native SDC profile');return result

def xml_binding(content,c):
    require('<!DOCTYPE' not in content and '<!ENTITY' not in content,'XML entities unsupported')
    try:root=ET.fromstring(content)
    except ET.ParseError as exc:raise ValueError('Malformed native XML') from exc
    modules={v.get('name'):v for v in root.findall('./netlist/module')};require(root.tag=='verilator_xml' and 'top' in modules and modules['top'].get('topModule')=='1','Native behavior top absent')
    top=modules['top'];types={v.get('id'):v for v in root.findall('./netlist/typetable/basicdtype')};ports={v.get('name'):v for v in top.findall('var') if v.get('dir') in ('input','output')}
    for role,name in c['role_map'].items():
        require(name in ports,'Observed signal role missing from XML');v=ports[name];t=types.get(v.get('dtype_id'));require(t is not None and t.get('signed','false') in ('false','0'),'Unsupported signed/aggregate role');width=abs(int(t.get('left','0'))-int(t.get('right','0')))+1
        require(width==(2 if role=='variant' else 4 if role=='slot' else 1) and v.get('dir')==('input' if role in ROLES[:8] else 'output'),'Role width/direction differs')
    selected=[v for v in top.findall('instance') if v.get('name')==c['unit_instance']];require(len(selected)==1 and selected[0].get('defName')==c['unit_module'],'Behavior does not instantiate selected shared STA unit')
    links={v.get('name'):v for v in selected[0].findall('port')};roles=[k for k in ROLES if k not in ('variant','start','slot')]
    for role in roles:
        name=c['role_map'][role];require(name in links and len(links[name])==1 and links[name][0].tag=='varref' and links[name][0].get('name')==name,'Observed role does not directly bind shared unit port')
    unit=modules.get(c['unit_module']);require(unit is not None,'Shared unit XML missing');objects={v.get('name'):v for v in unit.findall('instance')};instances={name:v.get('defName') for name,v in objects.items()};gate,pin=c['gate_pin'].split('/');require(pin=='Y' and all(instances.get(c[k])=='SCANR_CELL' for k in ('from_cell','to_cell')) and instances.get(gate)=='AND_CELL','Selected native cells differ from behavior unit');m=c['role_map'];pin_roles={}
    def bind(name,wanted):
        ports={v.get('name'):v for v in objects[name].findall('port')};require(set(ports)==set(wanted),'Selected primitive port population differs')
        for port,signal in wanted.items():require(len(ports[port])==1 and ports[port][0].tag=='varref' and ports[port][0].get('name')==signal,'Selected primitive signal role differs')
        pin_roles[name]=wanted
    bind(gate,{'A':m['clock'],'B':m['enable'],'Y':m['generated_clock']})
    for field in ('from_cell','to_cell'):
        bind(c[field],{'CK':m['generated_clock'],'RN':m['reset_n'],'SE':m['scan_enable'],'D':m['data'] if field=='from_cell' else m['launch'],'SI':m['serial_in'] if field=='from_cell' else m['launch'],'Q':m['launch'] if field=='from_cell' else m['capture']})
    inverters=[name for name,master in instances.items() if master=='INV_CELL']
    if c['reset_released']==0:require(len(inverters)==1,'Active-high root requires selected inverter');bind(inverters[0],{'A':m['reset'],'Y':m['reset_n']})
    else:
        aliases=[n for n in unit.findall('contassign') if len(n)==2 and all(v.tag=='varref' for v in n) and [v.get('name') for v in n]==[m['reset'],m['reset_n']]];require(len(aliases)==1 and not inverters,'Active-low root/reset alias differs')
    require(len(objects)==3+int(c['reset_released']==0),'Other shared-unit cells require a qualified profile')
    return {'unit_instance':c['unit_instance'],'unit_module':c['unit_module'],'direct_roles':roles,'selected_cells':instances,'primitive_signal_roles':pin_roles}

def behavior(content,reset_released):
    lines=content.splitlines();require(len(lines)>=5 and lines[0]=='TIME_UNITS -9 -9','Measured1ns simulator precision required');p=lines[1].split();require(len(p)==10 and p[0]=='CONFIG' and all(v.isdigit() for v in p[1:]),'Invalid native behavior configuration');keys=('shift','variant','se_kind','reset_hold','fast_period_ns','source_period_ns','native_guard_ns','native_pulse_count','window_cycles');config=dict(zip(keys,map(int,p[1:])))
    require(config['shift'] in (0,1) and config['variant']<4 and config['se_kind']<4 and config['reset_hold'] in (0,1),'Invalid native flags');period=config['source_period_ns'];require(2<=config['fast_period_ns']<=1024 and config['fast_period_ns']%2==0 and period==config['fast_period_ns']*(4 if config['shift'] else 1) and config['native_guard_ns']==period//2 and config['native_pulse_count']==(9 if config['shift'] else 2) and config['window_cycles']==(9 if config['shift'] else 18),'Unsupported native phase/time profile')
    frames=[];pulses=[];checks=failures=last_reset=last_se=0;previous=None;terminal=None;pulse_record=None
    for line in lines[2:]:
        p=line.split();require(p and terminal is None,'Post-terminal/empty behavior record')
        if p[0]=='SAMPLE':
            require(pulse_record is None and len(p)==20 and all(v.isdigit() for v in p[1:]),'Invalid sampled behavior record');row={'tick_ns':int(p[1]),**dict(zip(FRAME,map(int,p[2:])))}
            require(row['tick_ns']==len(frames) and row['slot']<16 and row['variant']<4 and all(row[k] in (0,1) for k in FRAME if k not in ('slot','variant','checks','failures')),'Native frame sequence/width invalid')
            if previous is None:require(row['tick_ns']==0 and not row['generated_clock'] and row['checks']==row['failures']==0,'Initial observation missing')
            else:
                if row['reset']!=previous['reset']:last_reset=row['tick_ns']
                if row['scan_enable']!=previous['scan_enable']:last_se=row['tick_ns']
                if row['generated_clock'] and not previous['generated_clock']:
                    pulses.append(row['tick_ns']);checks+=3;failures+=int(row['launch']!=row['expected_launch'])+int(row['capture']!=row['expected_capture'])
                    valid=row['reset']==reset_released and row['reset_n']==1 and row['scan_enable']==config['shift'] and row['tick_ns']-last_reset>=config['native_guard_ns'] and row['tick_ns']-last_se>=config['native_guard_ns'];failures+=not valid
            require(row['checks']==checks and row['failures']==failures,'Native checker actions contradict cumulative counts');frames.append(row);previous=row
        elif p[0]=='PULSES':require(pulse_record is None and len(p)>=2 and all(v.isdigit() for v in p[1:]) and len(p)==2+int(p[1]),'Invalid native pulse record');pulse_record=list(map(int,p[2:]));require(pulse_record==pulses,'Native pulse list contradicts observed edges')
        elif p[0]=='NATIVE_RESULT':
            require(pulse_record is not None and len(p)==5 and all(v.isdigit() for v in p[1:]),'Native terminal missing/invalid');checks+=1;failures+=len(pulses)!=config['native_pulse_count']
            if config['shift']:
                for a,b in zip(pulses,pulses[1:]):checks+=1;failures+=b-a!=period
            elif len(pulses)==2:checks+=1;failures+=pulses[1]-pulses[0]!=period
            terminal=dict(zip(('samples','checks','failures','pulses'),map(int,p[1:])))
        else:raise ValueError('Unknown native behavior record')
    require(len(frames)==config['window_cycles']*period+1 and terminal=={'samples':len(frames),'checks':checks,'failures':failures,'pulses':len(pulses)},'Incomplete or contradictory native behavior result');return {'config':config,'frames':frames,'pulses_ns':pulses,'counts':terminal,'status':'FAIL' if failures else 'PASS'}

def capture(root,behavior_dir,sta_dir,c):
    context(c);hashes={}
    def read(folder,name,json=False):
        rel=folder+'/'+name;path=contained(root,rel);require(path.is_file(),'Missing original artifact: '+rel);hashes[rel]=file_hash(path);return read_json(path) if json else path.read_text(encoding='utf-8')
    sta_version=read(sta_dir,'version.txt').strip();version=read(behavior_dir,'version.txt').strip();require(sta_version==VERSION and version.startswith('Verilator 5.020 '),'Unqualified native versions')
    for n in SSOURCES:read(sta_dir,n)
    require(re.findall(r'\btime_unit\s*:\s*"([^"]+)"',read(sta_dir,'cells.lib'))==['1ns'],'This native profile requires an explicit1ns Liberty time unit')
    for n in BSOURCES:read(behavior_dir,n)
    cmd=read(sta_dir,'command.json',True);require(isinstance(cmd,list) and len(cmd)==4 and all(text(v) for v in cmd) and cmd[1:]==['-exit','-no_init','sta.tcl'],'Native STA command differs');execution=read(sta_dir,'execution.json',True);shape(execution,{'exit_code'});require(type(execution['exit_code']) is int and execution['exit_code']==0,'Native STA task incomplete')
    stdout=read(sta_dir,'stdout.txt');stderr=read(sta_dir,'stderr.txt');require(stdout.count('OPENTOOLS_NATIVE_OCC_STA_COMPLETE')==1 and not any(v in stdout+stderr for v in ('[ERROR','Error:','Signal 11','initialization failed')),'Native STA completion unresolved')
    native=resources(read(sta_dir,'resources.txt'));sdc=consumed_sdc(read(sta_dir,'consumed.sdc'));require(native['labels']['MODULE']==sdc['design'],'Native export/consumed design differs')
    require({k:v for k,v in native['cases'].items() if v!='X'}==sdc['cases'],'Native cases differ from consumed SDC')
    if sdc['false_paths']:require(sdc['false_paths'][0]=={'from_cells':native['collections']['FROM'],'to_cells':native['collections']['TO']},'Consumed exception differs from native resolved cells')
    for label,args in [('build',BUILD),('xml',XML)]:
        command=read(behavior_dir,label+'.command.json',True);require(isinstance(command,list) and command[1:]==args and text(command[0]),'Native build/XML command differs');read(behavior_dir,label+'.stdout.txt');read(behavior_dir,label+'.stderr.txt')
    binding=xml_binding(read(behavior_dir,'model.xml'),c);macros=dict(re.findall(r'^#define P_([A-Z_]+) ([A-Za-z_]\w*)$',read(behavior_dir,'ports.hpp'),re.M));require(all(macros.get(k.upper())==v for k,v in c['role_map'].items()),'Native logger role macros differ')
    binary=contained(root,behavior_dir+'/Vtop');require(binary.is_file(),'Original native executable missing')
    with binary.open('rb') as f:require(f.read(4)==b'\x7fELF','Original ELF required')
    hashes[behavior_dir+'/Vtop']=file_hash(binary);ex=read(behavior_dir,'execution.json',True);shape(ex,{'build_exit','xml_exit','run_exit','binary_sha256'});require(all(type(ex[k]) is int and ex[k]==0 for k in ('build_exit','xml_exit')) and type(ex['run_exit']) is int and ex['run_exit'] in (0,1) and ex['binary_sha256']==hashes[behavior_dir+'/Vtop'],'Original native execution identity differs')
    run=read(behavior_dir,'run.command.json',True);require(isinstance(run,list) and len(run)==5 and all(text(v) for v in run),'Native behavior command missing');require(not read(behavior_dir,'run.stderr.txt').strip(),'Native behavior diagnostic unresolved');observed=behavior(read(behavior_dir,'run.stdout.txt'),c['reset_released']);require(ex['run_exit']==int(observed['status']=='FAIL'),'Native exit/checks disagree')
    require(run[1:]==[str(observed['config'][k]) for k in ('shift','variant','se_kind','reset_hold')],'Original native flags differ');headers=read(behavior_dir,'ports.hpp');require(re.findall(r'^#define FAST_PERIOD (\d+)$',headers,re.M)==[str(observed['config']['fast_period_ns'])] and re.findall(r'^#define RESET_RELEASED ([01])$',headers,re.M)==[str(c['reset_released'])],'Native time/reset header differs')
    return {'format':'opentools.occ-evidence.v1','context':c,'behavior_sources':{n:hashes[behavior_dir+'/'+n] for n in BSOURCES},'sta_sources':{n:hashes[sta_dir+'/'+n] for n in SSOURCES},'run_command_sha256':hashes[behavior_dir+'/run.command.json'],'sta_command_sha256':hashes[sta_dir+'/command.json'],'sta':{'export':native,'consumed_sdc':sdc,'status':'COMPLETE','version':sta_version},'behavior':observed,'behavior_binding':binding,'provenance':{'reader':PROFILE,'behavior_workdir':behavior_dir,'sta_workdir':sta_dir,'integrity_files':hashes,'limits':'Cached STA scenarios and dynamic controller observations are separately retained and joined by explicit source/context. Supplied recipe, mapping and scenario labels are not authenticated.1ns ideal simulation and placeholder library timing do not establish native ATPG, physical pulse quality, characterized timing or fault coverage.'}}
def revalidate(e,root):
    p=e.get('provenance',{});require(p.get('reader')==PROFILE and isinstance(p.get('integrity_files'),dict),'Unsupported OCC receipt')
    for name,value in p['integrity_files'].items():require(file_hash(contained(root,name))==value,'Changed original artifact: '+name)
    require(canonical(capture(root,p.get('behavior_workdir'),p.get('sta_workdir'),e.get('context')))==canonical(e),'Normalized evidence differs from native originals')
