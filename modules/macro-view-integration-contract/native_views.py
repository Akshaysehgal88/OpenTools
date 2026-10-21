"""Read original OpenROAD object exports and actual Verilator logical bindings."""
import math,re,xml.etree.ElementTree as ET
from pathlib import Path
from macro_common import BASIS,IDENTITY,file,parse,read_json,require,sha,text
HERE=Path(__file__).resolve().parent
OPENROAD_VERSION='v2.0-17598-ga008522d8'
SOURCES=('macro.lef','macro.lib','netlist.v','wrapper.sv','macro_model.sv','export_views.tcl','select.tcl')
FILES=SOURCES+('native.jsonl','native.odb','native.command.json','native.stdout.txt','native.stderr.txt','logical.xml','logical.command.json','logical.stdout.txt','logical.stderr.txt','openroad-version.txt','verilator-version.txt','execution.json')
XML_ARGS=['--xml-only','-Wno-fatal','--top-module','top','--xml-output','logical.xml','wrapper.sv','macro_model.sv']

def native_integer(value):
    require(re.fullmatch(r'-?\d+',value) is not None,'Invalid native integer')
    result=int(value);require(-(1<<63)<=result<(1<<63),'Native integer out of bounds');return result
def native_float(value):
    result=float(value);require(math.isfinite(result),'Nonfinite native number');return result
def rectangle(values):
    box=list(map(native_integer,values));require(len(box)==4 and box[0]<box[2] and box[1]<box[3],'Invalid native rectangle');return box

def logical_geometry(xml,context):
    require('<!DOCTYPE' not in xml and '<!ENTITY' not in xml,'XML entities unsupported')
    root=ET.fromstring(xml);tops=root.findall('.//module[@topModule="1"]');require(len(tops)==1,'One selected logical top required');top=tops[0]
    instances=[i for i in top.findall('instance') if i.get('name')==context['logical_instance']];require(len(instances)==1,'Selected direct logical instance unresolved');instance=instances[0]
    units=[m for m in root.findall('.//module') if m.get('name')==instance.get('defName')];require(len(units)==1 and units[0].get('origName')==context['logical_unit'],'Logical unit mismatch');unit=units[0]
    types={n.get('id'):n for n in root.find('.//typetable')}
    def width(id,seen=()):
        require(id not in seen,'Recursive native dtype');node=types[id]
        if node.tag=='refdtype':return width(node.get('sub_dtype_id'),(*seen,id))
        if node.tag!='basicdtype':return None
        return abs(int(node.get('left','0'))-int(node.get('right','0')))+1
    ports={p.get('name'):p for p in instance.findall('port')};result={}
    for var in unit.findall('var'):
        if not var.get('dir'):continue
        name=var.get('name');require(name not in result and name in ports,'Logical port census mismatch');port=ports[name];children=list(port)
        connection={'kind':'unsupported','native_tag':children[0].tag if len(children)==1 else 'expression'}
        if len(children)==1 and children[0].tag=='varref':connection={'kind':'varref','name':children[0].get('name'),'width':width(children[0].get('dtype_id'))}
        require(port.get('direction')=={'input':'in','output':'out','inout':'inout'}[var.get('dir')],'Native logical direction binding mismatch')
        result[name]={'direction':var.get('dir'),'width':width(var.get('dtype_id')),'connection':connection}
    require(set(result)==set(ports),'Unresolved logical port binding')
    return {'top':top.get('name'),'unit':unit.get('origName'),'instance':instance.get('name'),'ports':result}

def read_native(path):
    require(path.stat().st_size<=32*1024*1024,'Selected native export exceeds 32MiB')
    rows=[parse(line) for line in path.read_text(encoding='utf-8').splitlines()]
    require(rows and rows[0]==['HEADER','opentools.macro-native.v1'] and rows[-1]==['END'],'Incomplete native macro export')
    sizes={'HEADER':2,'UNITS':2,'INSTANCE':7,'MASTER':6,'INSTANCE_BOX':5,'MTERM':4,'PIN_BOX':7,'OBS':6,'ITERM':5,'LIBRARY':3,'OPERATING_POINT':4,'NO_OPERATING_POINT':1,'LIBPIN':4,'ARC':4,'LIMIT':3,'END':1}
    grouped={key:[] for key in sizes}
    for row in rows:
        require(isinstance(row,list) and row and all(isinstance(v,str) for v in row) and row[0] in sizes and len(row)==sizes[row[0]],'Unsupported/malformed native record')
        grouped[row[0]].append(row[1:])
    for key in ('HEADER','UNITS','INSTANCE','MASTER','INSTANCE_BOX','LIBRARY','END'):require(len(grouped[key])==1,'Native singleton missing/duplicated: '+key)
    require(len(grouped['OPERATING_POINT'])+len(grouped['NO_OPERATING_POINT'])==1,'Native operating point ambiguous')
    instance=grouped['INSTANCE'][0];master=list(map(native_integer,grouped['MASTER'][0]));require(master[0]>0 and master[1]>0 and all(v in (0,1) for v in master[2:]),'Invalid native master geometry')
    units=native_integer(grouped['UNITS'][0][0]);require(units>0,'Native DB units missing')
    terms={};terminals={};library_pins={}
    for name,direction,kind in grouped['MTERM']:
        text(name,'native pin');require(name not in terms and direction in ('INPUT','OUTPUT','INOUT','FEEDTHRU'),'Duplicate/unsupported physical pin')
        terms[name]={'direction':direction,'signal_type':kind,'boxes':[]}
    for name,layer,*values in grouped['PIN_BOX']:
        require(name in terms,'Geometry for unknown native pin');text(layer,'native layer');terms[name]['boxes'].append({'layer':layer,'box':rectangle(values)})
    for name,kind,net,net_type in grouped['ITERM']:
        require(name in terms and name not in terminals and kind==terms[name]['signal_type'],'Native terminal binding mismatch')
        terminals[name]={'signal_type':kind,'net':net or None,'net_signal_type':net_type or None}
    require(set(terminals)==set(terms),'Native instance/master pin census mismatch')
    for name,direction,bus in grouped['LIBPIN']:
        require(name not in library_pins and direction in ('input','output','inout','internal','ground','power') and bus in ('0','1'),'Invalid native library port')
        library_pins[name]={'direction':direction,'is_bus':bool(int(bus))}
    arcs=[]
    for from_pin,to_pin,full_name in grouped['ARC']:
        require((not from_pin or from_pin in library_pins) and (not to_pin or to_pin in library_pins),'Native arc references unknown library pin')
        arcs.append({'from':from_pin or None,'to':to_pin or None,'native_name':full_name})
    limits={}
    for name,value in grouped['LIMIT']:require(name not in limits,'Duplicate native limit');limits[name]=value
    require(limits=={'timing_role':'not_exported','liberty_pg_associations':'not_exported'},'Native support bounds changed')
    return {'database_units_per_micron':units,'instance':{'name':instance[0],'master':instance[1],'orientation':instance[2],'location':list(map(native_integer,instance[3:5])),'placement_status':instance[5],'box':rectangle(grouped['INSTANCE_BOX'][0])},
            'master':{'width':master[0],'height':master[1],'symmetry':dict(zip(('X','Y','R90'),map(bool,master[2:])))},'physical_pins':terms,'instance_terminals':terminals,
            'obstructions':[{'layer':layer,'box':rectangle(box)} for layer,*box in grouped['OBS']],
            'timing_library':{'library':grouped['LIBRARY'][0][0],'cell':grouped['LIBRARY'][0][1],'operating_point':dict(zip(('process','voltage','temperature'),map(native_float,grouped['OPERATING_POINT'][0]))) if grouped['OPERATING_POINT'] else None,'pins':library_pins,'arcs':arcs},'support_limits':limits,'native_record_count':len(rows)}

def qualified_loader(source,native):
    """Recognize the small batch loader; other session setups need source review."""
    supplies=[p for p,v in native['physical_pins'].items() if v['signal_type']=='POWER']
    grounds=[p for p,v in native['physical_pins'].items() if v['signal_type']=='GROUND']
    if len(supplies)!=1 or len(grounds)!=1:return False
    inst=native['instance'];lib=native['timing_library'];power=supplies[0];ground=grounds[0]
    pn=native['instance_terminals'][power]['net'];gn=native['instance_terminals'][ground]['net']
    values=[inst['name'],lib['library'],lib['cell'],power,ground,pn,gn,inst['orientation']]
    if not all(isinstance(v,str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_./-]*',v) for v in values):return False
    expected='\n'.join(['read_lef macro.lef','read_verilog netlist.v','read_liberty macro.lib','link_design top',
       'add_global_connection -net '+pn+' -inst_pattern '+inst['name']+' -pin_pattern '+power+' -power',
       'add_global_connection -net '+gn+' -inst_pattern '+inst['name']+' -pin_pattern '+ground+' -ground','global_connect',
       'set inst [[ord::get_db_block] findInst '+inst['name']+']','$inst setOrient '+inst['orientation'],
       '$inst setLocation '+' '.join(map(str,inst['location'])),'$inst setPlacementStatus PLACED','source export_views.tcl',
       'opentools_export_macro '+inst['name']+' '+lib['library']+'/'+lib['cell']+' native.jsonl native.odb',''])
    return source==expected

def capture(directory,context):
    require(context.get('format')=='opentools.macro-context.v1','Unsupported macro context')
    for k in (*IDENTITY,'instance','logical_instance','logical_unit','library_cell'):text(context.get(k),k)
    for k in BASIS:
        if context.get(k) is not None:text(context[k],k)
    paths={k:file(directory,k) for k in FILES};hashes={k:sha(p) for k,p in paths.items()}
    require(hashes['export_views.tcl']==sha(HERE/'export_views.tcl'),'Unqualified native exporter source')
    require(paths['openroad-version.txt'].read_text().strip()==OPENROAD_VERSION and paths['verilator-version.txt'].read_text().strip().startswith('Verilator 5.020 '),'Unqualified native version')
    native_command=read_json(paths['native.command.json']);logical_command=read_json(paths['logical.command.json'])
    require(isinstance(native_command,list) and len(native_command)==4 and isinstance(native_command[0],str) and native_command[1:]==['-exit','-no_init','select.tcl'],'Unsupported native invocation record')
    require(isinstance(logical_command,list) and isinstance(logical_command[0],str) and logical_command[1:]==XML_ARGS,'Unsupported logical elaboration invocation')
    execution=read_json(paths['execution.json']);require(execution['native_exit']==execution['logical_exit']==0 and execution['database_sha256']==hashes['native.odb'],'Native execution/database binding mismatch')
    stdout=paths['native.stdout.txt'].read_text(encoding='utf-8');stderr=paths['native.stderr.txt'].read_text(encoding='utf-8')
    require('OPENTOOLS_MACRO_EXPORT_COMPLETE' in stdout and not any(line.startswith(('[ERROR','Error:','Signal 11')) for line in (stdout+'\n'+stderr).splitlines()),'Native intake/export incomplete')
    require(paths['logical.xml'].stat().st_size<=128*1024*1024,'Logical export exceeds profile bounds')
    native=read_native(paths['native.jsonl']);logical=logical_geometry(paths['logical.xml'].read_text(encoding='utf-8'),context)
    require(native['instance']['name']==context['instance'],'Native selected instance mismatch')
    require(native['timing_library']['library']+'/'+native['timing_library']['cell']==context['library_cell'],'Native selected library cell mismatch')
    require(all(sha(path)==hashes[name] for name,path in paths.items()),'Capture files changed while reading')
    return {'format':'opentools.macro-evidence.v1','context':context,'native':native,'logical':logical,'qualified_batch_loader':qualified_loader(paths['select.tcl'].read_text(encoding='utf-8'),native),'source_sha256':{k:hashes[k] for k in SOURCES},'file_sha256':hashes,'native_result':{'OpenROAD':'complete','logical_elaboration':'PASS','native_exit':0,'logical_exit':0},
            'limits':'Original native object exports and logical binding, with supplied byte/provenance bindings. This does not authenticate execution, revision, freshness, source correspondence or approval. No binary ODB/LEF/Liberty parser, characterization, DRC/LVS or routability proof.'}
