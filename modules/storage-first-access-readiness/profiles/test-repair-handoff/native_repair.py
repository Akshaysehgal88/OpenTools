"""Read retained Verilator 5.020 transactions; never execute retained commands."""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from repair_common import (BASIS,FIELDS,IDENTITY,INPUTS,OUTPUTS,PARENT,PROFILE,
                           STATE,contained,read_json,require,sha,text,uint)

HERE=Path(__file__).resolve().parent
SOURCES=('ecc_profile.sv','memory_bank.sv','top.sv','main.cpp','plans.hpp')
BUILD=['--cc','--exe','--build','-j','2','--timescale','1ns/1ns','-Wno-fatal',
       '--top-module','top','--Mdir','obj','ecc_profile.sv','memory_bank.sv','top.sv','main.cpp']
XML=['--xml-only','--timescale','1ns/1ns','-Wno-fatal','--top-module','top',
     '--xml-output','model.xml','ecc_profile.sv','memory_bank.sv','top.sv']
FILES=SOURCES+('model.xml','Vtop','version.txt','plan.json','build.command.json',
      'xml.command.json','run.command.json','execution.json','run.stdout.txt',
      'run.stderr.txt','build.stdout.txt','build.stderr.txt','xml.stdout.txt','xml.stderr.txt')

def constant(node):
    value=node.get('name','')
    match=re.fullmatch(r"\d+'s?h([0-9a-f]+)",value)
    require(match is not None, 'Unsupported XML constant')
    return int(match[1],16)

def geometry(xml, context):
    require('<!DOCTYPE' not in xml and '<!ENTITY' not in xml, 'XML entities unsupported')
    root=ET.fromstring(xml)
    tops=root.findall('.//module[@topModule="1"]')
    require(len(tops)==1, 'One native top required')
    top=tops[0]
    instances=[i for i in top.findall('instance') if i.get('name')==context['unit_instance']]
    require(len(instances)==1, 'Selected memory instance not found')
    instance=instances[0]
    units=[m for m in root.findall('.//module') if m.get('name')==instance.get('defName')]
    require(len(units)==1 and units[0].get('origName')=='memory_bank' and
            context['unit_type']=='memory_bank', 'Unsupported native unit')
    unit=units[0];types={n.get('id'):n for n in root.find('.//typetable')}
    def width(type_id):
        node=types[type_id]
        if node.tag=='refdtype':return width(node.get('sub_dtype_id'))
        require(node.tag=='basicdtype', 'Expected packed native port')
        return abs(int(node.get('left','0'))-int(node.get('right','0')))+1
    variables={v.get('name'):v for v in unit.findall('var')}
    params={name:constant(variables[name].find('const')) for name in
            ('WORDS','PHYSICAL','AW','PAW','RESET_ASSERTED')}
    n=uint(params['WORDS'],16,'native word count');physical=params['PHYSICAL']
    require(n>=2 and n&(n-1)==0 and physical==n+1, 'Owned one-spare power-of-two geometry required')
    require(params['AW']==(n-1).bit_length() and params['PAW']==n.bit_length(), 'Address geometry mismatch')
    require(params['RESET_ASSERTED']==context['reset_asserted'] in (0,1), 'Reset polarity mismatch')
    roles=context['role_map'];all_ports={**INPUTS,**OUTPUTS}
    require(set(roles)==set(all_ports) and len(set(roles.values()))==len(roles), 'Exact distinct role map required')
    top_ports={v.get('name'):v for v in top.findall('var') if v.get('dir')}
    ports={p.get('name'):p for p in instance.findall('port')}
    for role,bits in all_ports.items():
        bits={'aw':params['AW'],'paw':params['PAW'],'words':n,'physical':physical}.get(bits,bits)
        port=ports.get(role);mapped=top_ports.get(roles[role]);native=variables.get(role)
        direction='input' if role in INPUTS else 'output'
        require(port is not None and mapped is not None and native is not None,
                'Unresolved role: '+role)
        refs=port.findall('varref')
        require(len(refs)==1 and len(list(port))==1 and refs[0].get('name')==roles[role] and
                port.get('direction')==('in' if direction=='input' else 'out') and
                mapped.get('dir')==native.get('dir')==direction and
                width(mapped.get('dtype_id'))==width(native.get('dtype_id'))==bits,
                'Native role binding mismatch: '+role)
    require(context['memory_variable']=='memory','Owned memory array required')
    array=types[variables['memory'].get('dtype_id')]
    require(array.tag=='unpackarraydtype','Native unpacked memory required')
    bounds=[constant(c) for c in array.findall('range/const')]
    require(bounds==[0,physical-1] and width(array.get('sub_dtype_id'))==39, 'Native memory geometry mismatch')
    return {'logical_words':n,'physical_words':physical,'data_bits':32,'codeword_bits':39,
            'byte_lanes':4,'command_ports':1,'address_bits':params['AW'],
            'physical_address_bits':params['PAW'],'reset_asserted':params['RESET_ASSERTED']}

def bind_plan(header, plan, g, context):
    index=uint(plan['case_index'],1024,'case index')
    for name,value in [('WORDS',g['logical_words']),('PHYSICAL',g['physical_words']),
                       ('RESET_ASSERTED',g['reset_asserted'])]:
        require(re.search(r'^#define '+name+' '+str(value)+r'$',header,re.M), 'Compiled geometry mismatch')
    for role,mapped in context['role_map'].items():
        require(re.search(r'^#define P_'+role.upper()+' '+re.escape(mapped)+r'$',header,re.M), 'Compiled role mismatch')
    lines=[]
    require(isinstance(plan['steps'],list) and 0<len(plan['steps'])<=10000,'Invalid planned window')
    for s in plan['steps']:
        text(s['id'],'planned event')
        require(type(s['expect_accept']) is bool and type(plan['repair_required']) is bool,'Invalid plan flags')
        values=[json.dumps(s['id']),*map(str,(s['operation'],s['word'],s['physical'],s['write_data'],s['byte_enable'])),
                str(s['raw_input'])+'ull',str(s['repair_input']),str(s['expect_accept']).lower(),str(s['expect_release']),
                str(s['expected_after'] or 0)+'ull',str(s['expected_after'] is not None).lower(),str(s['expected_data'])]
        lines.append('{'+','.join(values)+'},')
    selected='static const Step STEPS_'+str(index)+'[]={\n'+'\n'.join(lines)+'\n};'
    require(selected in header,'Retained plan differs from compiled stimulus')
    tables=re.search(r'static const Plan PLANS\[\]=\{\n(.*?)\n\};',header,re.S)
    require(tables is not None,'Missing compiled plan selection')
    rows=tables[1].splitlines()
    expected='{'+','.join((json.dumps(plan['case']),str(plan['cfg']),str(plan['repair_required']).lower(),
                          str(plan['expected_payload']),'STEPS_'+str(index),str(len(lines))))+'},'
    require(index<len(rows) and rows[index]==expected,'Compiled selection mismatch')

def instrument_check(row, step, plan, g):
    """Recount driver assertions separately from the receiving contract."""
    before=lambda k:row['before_'+k]
    op=row['operation'];checks=[bool(row['accepted'])==step['expect_accept']]
    if not step['expect_accept']:checks.append(not row['committed'] and not row['address_valid'])
    else:
        target=(plan['expected_payload']>>1)&15 if plan['repair_required'] and row['word_address']==((plan['expected_payload']>>6)&15) else row['word_address']
        if op==1:checks.append(row['before_codeword']==step['raw_input'])
        elif op==2:checks.append(bool(row['test_done']))
        elif op==3:checks.append(row['repair_loaded'] and bool(row['repair_active'])==plan['repair_required'] and row['loaded_payload']==plan['expected_payload'] and (not plan['repair_required'] or (row['decoded_bad']==((plan['expected_payload']>>6)&15) and row['decoded_spare']==((plan['expected_payload']>>1)&15))))
        elif op==4:checks.append(bool(row['ecc_enabled']))
        elif op==5:checks.append(row['committed'] and row['actual_physical']==target and row['after_codeword']==step['expected_after'])
        elif op==6:
            prereq=all(before(k) for k in ('test_done','repair_loaded','ecc_enabled')) and before('initialized')==(1<<g['logical_words'])-1
            checks.append((not row['released'] and row['test_owner']) if step['expect_release']==0 else (row['released'] and prereq))
        elif op==7:checks.append(not row['error'] and row['read_data']==step['expected_data'] and row['actual_physical']==target and row['ecc_enabled'])
        elif op==8:
            checks.append((not row['committed'] and not row['internal_read'] and not row['error'] and row['after_codeword']==row['before_codeword']) if row['byte_enable']==0 else (row['committed'] and not row['error'] and row['actual_physical']==target and row['after_codeword']==step['expected_after'] and bool(row['internal_read'])==(row['byte_enable']!=15)))
        elif op==10:checks.append(not row['ecc_enabled'])
    return len(checks),sum(not c for c in checks)

def capture(directory, context):
    require(context.get('format')=='opentools.repair-context.v1','Unsupported context')
    for key in IDENTITY:text(context.get(key),key)
    for key in BASIS:
        if context.get(key) is not None:text(context[key],key)
    require(context.get('ecc_profile_ref')==PROFILE,'Unsupported codec profile')
    files={name:contained(directory,name,128*1024*1024 if name=='Vtop' else 16*1024*1024) for name in FILES}
    hashes={name:sha(path) for name,path in files.items()}
    require(files['Vtop'].read_bytes()[:4]==b'\x7fELF','Original ELF required')
    require(files['version.txt'].read_text().strip().startswith('Verilator 5.020 '),'Unqualified native version')
    for name,qualified in [('main.cpp',HERE/'examples/main.cpp'),('memory_bank.sv',HERE/'examples/memory_bank.sv'),('ecc_profile.sv',PARENT/'examples/ecc_profile.sv')]:
        require(hashes[name]==sha(qualified),'Unqualified source/instrumentation: '+name)
    build,xml,run=(read_json(files[k+'.command.json']) for k in ('build','xml','run'))
    require(isinstance(build,list) and build[1:]==BUILD and isinstance(xml,list) and xml[1:]==XML and build[0]==xml[0], 'Native compilation command mismatch')
    plan=read_json(files['plan.json']);g=geometry(files['model.xml'].read_text(),context)
    require(isinstance(run,list) and len(run)==2 and isinstance(run[0],str) and Path(run[0]).name=='Vtop' and run[1]==str(plan['case_index']),'Run selection mismatch')
    execution=read_json(files['execution.json'])
    require(execution['build_exit']==execution['xml_exit']==0 and execution['run_exit'] in (0,1) and execution['binary_sha256']==hashes['Vtop'],'Native execution binding mismatch')
    bind_plan(files['plans.hpp'].read_text(),plan,g,context)
    lines=files['run.stdout.txt'].read_text().splitlines()
    require(len(lines)>=5 and lines[0]=='TIME_UNITS -9 -9','Native time units missing')
    wanted=[plan['case_index'],plan['cfg'],g['logical_words'],g['physical_words'],32,39,4,12,g['reset_asserted'],plan['expected_payload'],int(plan['repair_required']),len(plan['steps'])]
    require(lines[1]=='CONFIG '+' '.join(map(str,wanted)),'Native configuration mismatch')
    initial=[1]+[0]*(len(STATE)-1)
    require(lines[2]=='INIT '+' '.join(map(str,initial)),'Unqualified initial state')
    rows=[];previous=dict(zip(STATE,initial));checks=failures=0;seen=set()
    widths={**INPUTS,**OUTPUTS}
    widths.update({'before_'+k:OUTPUTS[k] for k in STATE})
    for index,line in enumerate(lines[3:-1],1):
        parts=line.split();require(len(parts)==len(FIELDS)+4 and parts[0]=='TX','Invalid native transaction')
        require(index<=len(plan['steps']) and parts[1]==str(index) and parts[2]==str(index*3-1), 'Native sequence/time mismatch')
        require(parts[3] not in seen,'Duplicate native event');seen.add(parts[3])
        require(all(re.fullmatch(r'\d+',p) for p in parts[4:]),'Unknown/noninteger native field')
        row=dict(zip(FIELDS,map(int,parts[4:])));row.update(seq=index,time_tick=index*3-1,event_ref=parts[3])
        for key,bits in widths.items():
            if key not in row:continue
            bits={'aw':g['address_bits'],'paw':g['physical_address_bits'],'words':g['logical_words'],'physical':g['physical_words']}.get(bits,bits)
            uint(row[key],(1<<bits)-1,key)
        require(all(row['before_'+k]==previous[k] for k in STATE),'Native state history mismatch')
        step=plan['steps'][index-1]
        require(row['event_ref']==step['id'] and all(row[a]==step[b] for a,b in [('operation','operation'),('word_address','word'),('physical_address','physical'),('repair_input','repair_input'),('write_data','write_data'),('byte_enable','byte_enable'),('raw_input','raw_input')]),'Observed stimulus differs from compiled plan')
        add,failed=instrument_check(row,step,plan,g);checks+=add;failures+=failed
        require((row['checks'],row['failures'])==(checks,failures),'Native assertion counter mismatch')
        rows.append(row);previous={k:row[k] for k in STATE}
    require(len(rows)==len(plan['steps']) and lines[-1]==f'NATIVE_RESULT {len(rows)} {checks} {failures}' and execution['run_exit']==int(failures>0),'Native terminal result mismatch')
    require(all(sha(path)==hashes[name] for name,path in files.items()),'Native files changed during capture')
    return {'format':'opentools.repair-evidence.v1','context':context,'geometry':g,
            'source_sha256':{k:hashes[k] for k in SOURCES},'file_sha256':hashes,
            'initial_state':dict(zip(STATE,initial)),'events':rows,
            'native_result':{'transactions':len(rows),'checks':checks,'failures':failures,
                             'exit':execution['run_exit'],'status':'FAIL' if failures else 'PASS'},
            'limits':'Owned 32/39 SECDED command-port model only. Declarations and byte hashes bind supplied records; they do not authenticate execution, foundry repair, MBIST coverage or production approval.'}
