"""Data-only native changed-object, scope and original report capture."""
import math,re,xml.etree.ElementTree as ET
from pathlib import Path
from eco_common import BASIS,IDENTITY,PRIMITIVES,ROLES,config,data_file,digest,file_hash,header,identifier,read_json,require,text,uint
HERE=Path(__file__).resolve().parent
SOURCES=('design.v','cells.lef','cells.lib','models.sv','main.cpp','bindings.hpp','export_eco.tcl','config.tcl')
BASE=SOURCES+('graph.txt','consumed.sdc','design.odb','exported.v','logical.xml','Vtop','execution.json','native.command.json','build.command.json','xml.command.json','run.command.json','native.stdout.txt','native.stderr.txt','build.stdout.txt','build.stderr.txt','xml.stdout.txt','xml.stderr.txt','clock.stderr.txt','openroad-version.txt','verilator-version.txt')
BUILD=['--cc','--exe','--build','-j','1','-Wno-fatal','--top-module','top','--Mdir','obj','design.v','models.sv','main.cpp']
XML=['--xml-only','-Wno-fatal','--top-module','top','--xml-output','logical.xml','design.v','models.sv']

def context_check(ctx):
    require(ctx.get('format')=='opentools.eco-context.v1','Unsupported context')
    for k in IDENTITY:text(ctx.get(k),k)
    for k in BASIS:
        if ctx.get(k) is not None:text(ctx[k],k)
    require(set(ctx['ports'])==set(ROLES) and len(set(ctx['ports'].values()))==len(ROLES),'Complete distinct role map required')
    for value in ctx['ports'].values():identifier(value,'port')
    require(set(ctx['cells'])=={'allow','gate','buffer','launch','capture','invert_a','invert_reset'},'Unsupported instance roles')
    for value in ctx['cells'].values():
        if value is not None:identifier(value,'instance')
    require(type(ctx['wake']) is bool,'Explicit phase logic profile required')
    for key in ('reset_asserted','mode_a','mode_b'):uint(ctx[key],1,key)
    uint(ctx['cycles'],10000,'cycles');require(ctx['cycles']>0,'Empty phase')
    require(type(ctx['period']) is int and 0<ctx['period']<=100000,'Integer native ns period required');identifier(ctx['clock_name'],'clock name')

def graph(path,ctx):
    lines=path.read_text(encoding='utf-8').splitlines();require(lines[:2]==['FORMAT opentools.eco-graph.v1','RUN '+ctx['run_ref']] and lines[-1]=='END','Native graph scope/window incomplete')
    cells={};pins={};ports={};placement={}
    for line in lines[2:-1]:
        v=line.split();require(v,'Empty native graph row')
        if v[0]=='CELL':
            require(len(v)==3 and v[1] not in cells,'Duplicate/malformed native instance');identifier(v[1],'native instance');require(v[2] in (*PRIMITIVES,'ECO_DFF'),'Unqualified primitive');cells[v[1]]=v[2]
        elif v[0]=='PLACE':
            require(len(v)==6 and v[1] not in placement,'Native placement record malformed');placement[v[1]]={'orientation':v[2],'location':[int(v[3]),int(v[4])],'status':v[5]}
        elif v[0]=='PIN':
            require(len(v)==6 and v[1]+'/'+v[2] not in pins,'Duplicate/malformed native pin');identifier(v[2],'native pin');identifier(v[5],'native net');require(v[3] in ('INPUT','OUTPUT','INOUT'),'Native pin direction unknown')
            pins[v[1]+'/'+v[2]]={'cell':v[1],'pin':v[2],'direction':v[3],'signal_type':v[4],'net':v[5] if v[5]!='UNCONNECTED' else None}
        elif v[0]=='PORT':
            require(len(v)==4 and v[1] not in ports,'Duplicate/malformed native port');ports[v[1]]={'direction':v[2],'net':v[3]}
        else:raise ValueError('Unsupported native graph row')
    require(set(cells)==set(placement) and set(ports)==set(ctx['ports'].values()),'Native instance/port population mismatch')
    for cell,master in cells.items():
        expected=(*PRIMITIVES[master],'Y') if master in PRIMITIVES else ('CK','RN','D','Q')
        actual={p['pin'] for p in pins.values() if p['cell']==cell};require(actual==set(expected),'Native primitive pin census mismatch')
        for pin in expected:
            p=pins[cell+'/'+pin];require(p['direction']==('OUTPUT' if pin in ('Q','Y') else 'INPUT') and p['signal_type']==('CLOCK' if pin=='CK' else 'SIGNAL'),'Primitive native role mismatch')
    role_masters={'allow':'ECO_OR','gate':'ECO_AND','buffer':'ECO_BUF','launch':'ECO_DFF','capture':'ECO_DFF','invert_a':'ECO_INV','invert_reset':'ECO_INV'}
    selected={v:role_masters[k] for k,v in ctx['cells'].items() if v is not None}
    require(len(selected)==sum(v is not None for v in ctx['cells'].values()) and selected==cells,'Selected role/primitive correspondence unestablished')
    for role,name in ctx['ports'].items():require(ports[name]['direction']==('OUTPUT' if role in ('gclk','q0','q1') else 'INPUT'),'Selected root role mismatch')
    for role,cell,pin in [('gclk','gate','Y'),('q0','launch','Q'),('q1','capture','Q')]:require(pins[ctx['cells'][cell]+'/'+pin]['net']==ports[ctx['ports'][role]]['net'],'Selected observed output correspondence unestablished')
    return {'cells':cells,'placement':placement,'pins':pins,'ports':ports}

def xml_binding(path,g,ctx):
    require(path.stat().st_size<=64*1024*1024,'Logical XML exceeds bounded profile');source=path.read_text(encoding='utf-8');require('<!DOCTYPE' not in source and '<!ENTITY' not in source,'XML entities unsupported');root=ET.fromstring(source)
    modules={m.get('name'):m for m in root.findall('.//module')};tops=[m for m in modules.values() if m.get('topModule')=='1'];require(len(tops)==1 and tops[0].get('name')=='top','Native top ambiguous');top=tops[0]
    types={n.get('id'):n for n in root.find('.//typetable')};files={n.get('id'):Path(n.get('filename','')).name for n in root.findall('files/file')}
    def width(id):
        t=types[id]
        if t.tag=='refdtype':return width(t.get('sub_dtype_id'))
        require(t.tag=='basicdtype','Non-scalar native dtype unsupported');return abs(int(t.get('left','0'))-int(t.get('right','0')))+1
    require(all(n.tag in ('var','instance','contassign') for n in top),'Top-level behavior outside structural profile')
    variables={v.get('name'):v for v in top.findall('var')};aliases={name:name for name in variables}
    def net(name):
        require(name in aliases,'Unestablished scalar wire')
        while aliases[name]!=name:name=aliases[name]
        return name
    for v in variables.values():require(width(v.get('dtype_id'))==1,'Non-scalar top wire unsupported')
    for node in top.findall('contassign'):
        require(len(node)==2 and all(n.tag=='varref' for n in node),'Only direct scalar aliases qualified')
        aliases[net(node[1].get('name'))]=net(node[0].get('name'))
    topports={k:v for k,v in variables.items() if v.get('dir')};require(set(topports)==set(g['ports']),'Logical/physical root port census mismatch')
    for name,v in topports.items():require(width(v.get('dtype_id'))==1 and v.get('dir').upper()==g['ports'][name]['direction'],'Root port geometry/direction mismatch')
    insts={i.get('name'):i for i in top.findall('instance')};require(set(insts)==set(g['cells']),'Logical/native instance census mismatch')
    for name,instance in insts.items():
        unit=modules[instance.get('defName')];require(unit.get('origName')==g['cells'][name] and files.get(unit.get('loc','').split(',')[0])=='models.sv','Primitive implementation origin not qualified')
        variables={v.get('name'):v for v in unit.findall('var') if v.get('dir')};ports={p.get('name'):p for p in instance.findall('port')};require(set(variables)==set(ports),'Logical primitive port census mismatch')
        for pin,v in variables.items():
            require(width(v.get('dtype_id'))==1 and g['pins'][name+'/'+pin]['direction']==v.get('dir').upper(),'Logical/native primitive pin role mismatch')
            node=ports[pin];require(len(node)==1 and node[0].tag=='varref','Primitive expression connection unsupported')
            require(net(node[0].get('name'))==net(g['pins'][name+'/'+pin]['net']),'Logical/native pin connectivity mismatch')
    return {'root_ports':len(topports),'instances':len(insts),'scalar_primitive_binding':True}

def read_sta(path,ctx):
    lines=path.read_text(encoding='utf-8').splitlines();require(lines[:2]==['FORMAT opentools.eco-sta.v1','RUN '+ctx['run_ref']] and lines[-1]=='END','Incomplete native STA export')
    result={'paths':[],'cases':{}}
    for line in lines[2:-1]:
        v=line.split()
        if v[0]=='CLOCK':require(len(v)==4 and 'clock' not in result,'Malformed native clock');result['clock']={'name':v[1],'period':float(v[2]),'is_generated':v[3]}
        elif v[0]=='CLOCK_SOURCES':require(int(v[1])==len(v[2:]) and 'sources' not in result,'Native clock sources malformed');result['sources']=v[2:]
        elif v[0]=='PATH_COUNT':require('path_count' not in result,'Duplicate path count');result['path_count']=int(v[1])
        elif v[0]=='PATH':require(len(v)==4 and math.isfinite(float(v[1])),'Native path malformed');result['paths'].append({'slack_native_ns':v[1],'startpoint':v[2],'endpoint':v[3]})
        elif v[0]=='CASE':require(len(v)==3 and v[1] not in result['cases'],'Native case duplicated');result['cases'][v[1]]=v[2]
        elif v[0]=='REGISTER_CLOCK_PINS':require(int(v[1])==len(v[2:]) and 'clock_pins' not in result,'Clock pin census malformed');result['clock_pins']=sorted(v[2:])
        elif v[0]=='PATH_RESULT':require(len(v)==2 and v[1] in ('PASS','FAIL') and 'verdict' not in result,'Malformed path result');result['verdict']=v[1]
        else:raise ValueError('Unsupported native STA row')
    require(result['path_count']==len(result['paths']) and result['verdict']==('PASS' if result['path_count']==1 else 'FAIL'),'Native path observation criterion mismatch')
    require(result['clock']=={'name':ctx['clock_name'],'period':float(ctx['period']),'is_generated':'0'} and result['sources']==[ctx['ports']['clock']],'Native clock scope mismatch')
    p=ctx['ports'];require(result['cases']=={p['reset']:str(1-ctx['reset_asserted']),p['a']:str(ctx['mode_a']),p['b']:str(ctx['mode_b'])},'Native phase/case mismatch')
    return result

def read_clock(path,ctx,exit):
    lines=path.read_text(encoding='utf-8').splitlines();require(lines[:2]==['FORMAT opentools.eco-clock.v1','CONFIG '+' '.join(map(str,(ctx['cycles'],ctx['reset_asserted'],ctx['mode_a'],ctx['mode_b'])))],'Native clock config mismatch')
    samples=[];pulses=0;prior=0
    for index,line in enumerate(lines[2:-1]):
        v=line.split();require(len(v)==11 and v[0]=='SAMPLE','Native sample malformed');row=list(map(int,v[1:]));require(row[0]==index and all(x in (0,1) for x in row[1:]),'Native scalar/time sample malformed')
        require(row[2:5]==[1-ctx['reset_asserted'],ctx['mode_a'],ctx['mode_b']],'Observed native input phase mismatch');pulses+=int(not prior and row[7]);prior=row[7];samples.append(row)
    verdict='PASS' if pulses==ctx['cycles'] else 'FAIL';require(len(samples)==2*ctx['cycles'] and lines[-1]==f'CLOCK_RESULT {ctx["cycles"]} {pulses} {verdict}' and exit==int(verdict=='FAIL'),'Native terminal count/outcome mismatch')
    return {'samples':samples,'pulses':pulses,'expected':ctx['cycles'],'verdict':verdict,'native_status':lines[-1]}

def capture(run_dir,ctx):
    context_check(ctx);paths={n:data_file(run_dir,n) for n in BASE};hashes={n:file_hash(p) for n,p in paths.items()};execution=read_json(paths['execution.json'])
    for n in SOURCES:require(hashes[n]==execution['sources'][n],'Consumed source changed: '+n)
    for n in ('models.sv','main.cpp','cells.lib','cells.lef'):require(hashes[n]==file_hash(HERE/'examples'/n),'Unqualified primitive/library/logger profile: '+n)
    require(hashes['export_eco.tcl']==file_hash(HERE/'export_eco.tcl') and paths['config.tcl'].read_text()==config(ctx) and paths['bindings.hpp'].read_text()==header(ctx),'Native loader/driver scope not qualified')
    require(paths['openroad-version.txt'].read_text().strip()=='v2.0-17598-ga008522d8' and paths['verilator-version.txt'].read_text().strip().startswith('Verilator 5.020 '),'Unqualified native version')
    native_cmd=read_json(paths['native.command.json']);build_cmd=read_json(paths['build.command.json']);xml_cmd=read_json(paths['xml.command.json']);run_cmd=read_json(paths['run.command.json'])
    require(native_cmd[1:]==['-exit','-no_init','export_eco.tcl'] and build_cmd[1:]==BUILD and xml_cmd[1:]==XML and len(run_cmd)==1,'Native invocation differs from profile')
    require(all(execution[k]==0 for k in ('native_exit','build_exit','xml_exit')) and execution['clock_exit'] in (0,1),'Incomplete native stages')
    require(hashes['native.command.json']==execution['native_command_sha256'] and hashes['run.command.json']==execution['run_command_sha256'] and hashes['Vtop']==execution['binary_sha256'],'Native command/executable binding mismatch')
    with paths['Vtop'].open('rb') as binary:require(binary.read(4)==b'\x7fELF','Original native ELF required')
    for name in ('graph.txt','consumed.sdc','design.odb','exported.v','logical.xml'):require(hashes[name]==execution['artifacts'][name],'Native artifact changed: '+name)
    log=paths['native.stdout.txt'].read_text()+paths['native.stderr.txt'].read_text();require('OPENTOOLS_ECO_NATIVE_COMPLETE' in log and '[ERROR' not in log,'Native export incomplete')
    g=graph(paths['graph.txt'],ctx);binding=xml_binding(paths['logical.xml'],g,ctx);reports={};gaps=[]
    for kind,name in [('sta','sta.txt'),('clock','clock.stdout.txt')]:
        p=data_file(run_dir,name,optional=True);hashes[name]=file_hash(p) if p else None
        if hashes[name]!=execution['artifacts'][name]:reports[kind]=None;gaps.append({'report':kind,'kind':'raw_report_missing_or_changed'});continue
        reports[kind]=read_sta(p,ctx) if kind=='sta' else read_clock(p,ctx,execution['clock_exit'])
    if reports['sta'] is not None:require(reports['sta']['clock_pins']==sorted(ctx['cells'][k]+'/CK' for k in ('launch','capture')),'Native register clock population differs from selected scope')
    require(all(file_hash(p)==hashes[n] for n,p in paths.items()),'Native files changed during capture')
    return {'format':'opentools.eco-evidence.v1','context':ctx,'graph':g,'logical_binding':binding,'reports':reports,'report_gaps':gaps,'source_sha256':{n:hashes[n] for n in SOURCES},'file_sha256':hashes,'execution':execution,'commands':{'native':native_cmd,'build':build_cmd,'xml':xml_cmd,'run':run_cmd},
            'limits':'Owned flat primitive/endpoint-rewire scope. Native STA result means selected path presence, not timing signoff; clock result is finite Boolean delivery, not physical pulse quality. Declared relationships and hashes do not authenticate authority, provenance or equivalence.'}

def projection(evidence,kind):
    g=evidence['graph'];ctx=evidence['context'];drivers={};needed=set();external=set();visited=set();active=set();issues=[]
    for name,p in g['pins'].items():
        if p['direction']=='OUTPUT':require(p['net'] not in drivers,'Multiple-driver scope unsupported');drivers[p['net']]=name
    def walk(net,clock_path=False):
        if net is None:issues.append('unconnected_dependency');return
        if net in active:issues.append('combinational_cycle');return
        if net in visited:return
        visited.add(net);driver=drivers.get(net)
        if driver is None:
            external.add(net)
            if not any(p['net']==net and p['direction']=='INPUT' for p in g['ports'].values()):issues.append('unestablished_external_driver')
            return
        cell=g['pins'][driver]['cell'];master=g['cells'][cell];needed.update(k for k,p in g['pins'].items() if p['cell']==cell)
        if master=='ECO_DFF':
            if clock_path:issues.append('stateful_clock_dependency')
            return
        require(master in PRIMITIVES,'Opaque dependency primitive')
        active.add(net)
        for pin in PRIMITIVES[master]:walk(g['pins'][cell+'/'+pin]['net'],clock_path)
        active.remove(net)
    cells=ctx['cells'];clock_net=g['pins'][cells['gate']+'/Y']['net'];walk(clock_net,True);receivers=sorted([cells['launch']+'/CK',cells['capture']+'/CK']);needed.update(receivers)
    if any(g['pins'][pin]['net']!=clock_net for pin in receivers):issues.append('receiver_clock_transfer_not_observed')
    if kind=='sta':needed.add(cells['capture']+'/D');walk(g['pins'][cells['capture']+'/D']['net'])
    included={g['pins'][k]['cell'] for k in needed}
    return {'pins':{k:g['pins'][k] for k in sorted(needed)},'masters':{k:g['cells'][k] for k in sorted(included)},'placement':{k:g['placement'][k] for k in sorted(included)},'external_inputs':{k:p for k,p in sorted(g['ports'].items()) if p['net'] in external},'receiver_clock_pins':receivers,'unqualified_dependencies':sorted(set(issues))}
