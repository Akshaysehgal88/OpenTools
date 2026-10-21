"""Read original owned Verilator finite fault exports without running their commands."""
import re,xml.etree.ElementTree as ET
from pathlib import Path
from fault_common import BASIS,CLASSES,IDENTITY,MODEL,ROLES,file,read_json,require,sha,text,uint
HERE=Path(__file__).resolve().parent
SOURCES=('fault_network.sv','top.sv','main.cpp','plans.hpp')
BUILD=['--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','top','--Mdir','obj','fault_network.sv','top.sv','main.cpp']
XML=['--xml-only','-Wno-fatal','--top-module','top','--xml-output','model.xml','fault_network.sv','top.sv']
FILES=SOURCES+('model.xml','Vtop','version.txt','plan.json','execution.json','build.command.json','xml.command.json','run.command.json','build.stdout.txt','build.stderr.txt','xml.stdout.txt','xml.stderr.txt','run.stdout.txt','run.stderr.txt')

def constant(node):
    m=re.fullmatch(r"\d+'s?h([0-9a-f]+)",node.get('name',''));require(m is not None,'Unsupported XML constant');return int(m[1],16)

def native_geometry(source,context):
    require('<!DOCTYPE' not in source and '<!ENTITY' not in source,'XML entities unsupported')
    root=ET.fromstring(source);tops=root.findall('.//module[@topModule="1"]');require(len(tops)==1,'One native top required');top=tops[0]
    instances=[i for i in top.findall('instance') if i.get('name')==context['unit_instance']];require(len(instances)==1,'Unresolved native unit');instance=instances[0]
    units=[m for m in root.findall('.//module') if m.get('name')==instance.get('defName')];require(len(units)==1 and units[0].get('origName')==context['unit_type']=='fault_network','Unqualified native unit')
    unit=units[0];variables={v.get('name'):v for v in unit.findall('var')};types={v.get('id'):v for v in root.find('.//typetable')}
    def width(id):
        t=types[id]
        if t.tag=='refdtype':return width(t.get('sub_dtype_id'))
        require(t.tag=='basicdtype','Expected packed port');return abs(int(t.get('left',0))-int(t.get('right',0)))+1
    p={k:constant(variables[k].find('const')) for k in ('FAMILY','N','S','O')}
    require(p['FAMILY']==context['family'] in (0,1) and (p['N'],p['S'],p['O'])==((3,5,1) if p['FAMILY']==0 else (4,6,2)),'Unqualified native geometry')
    mapping=context['role_map'];require(set(mapping)==set(ROLES) and len(set(mapping.values()))==len(ROLES),'Distinct complete role map required')
    widths=[p['N'],1,1,4,1,p['S'],p['S'],p['O']];topvars={v.get('name'):v for v in top.findall('var') if v.get('dir')};ports={v.get('name'):v for v in instance.findall('port')}
    for index,(role,bits) in enumerate(zip(ROLES,widths)):
        port=ports[role];mapped=topvars[mapping[role]];native=variables[role];refs=port.findall('varref');direction='input' if index<5 else 'output'
        require(len(refs)==len(list(port))==1 and refs[0].get('name')==mapping[role] and port.get('direction')==('in' if index<5 else 'out') and native.get('dir')==mapped.get('dir')==direction and width(native.get('dtype_id'))==width(mapped.get('dtype_id'))==bits,'Native role/width mismatch: '+role)
    return {'input_bits':p['N'],'injection_sites':p['S'],'output_bits':p['O'],'original_faults':2*p['S'],'family':p['FAMILY']}

def capture(directory,context):
    require(context.get('format')=='opentools.fault-context.v1' and context.get('fault_model_ref')==MODEL,'Unqualified native context/model')
    for key in IDENTITY:text(context.get(key),key)
    for key in BASIS:
        if context.get(key) is not None:text(context[key],key)
    paths={k:file(directory,k) for k in FILES};hashes={k:sha(p) for k,p in paths.items()}
    require(paths['Vtop'].read_bytes()[:4]==b'\x7fELF' and paths['version.txt'].read_text().strip().startswith('Verilator 5.020 '),'Original qualified native binary/version required')
    for k in ('fault_network.sv','main.cpp'):require(hashes[k]==sha(HERE/'examples'/k),'Unqualified owned source/logger: '+k)
    build,xml,run=(read_json(paths[k+'.command.json']) for k in ('build','xml','run'))
    require(isinstance(build,list) and build[1:]==BUILD and isinstance(xml,list) and xml[1:]==XML and build[0]==xml[0],'Native build/XML command mismatch')
    plan=read_json(paths['plan.json']);g=native_geometry(paths['model.xml'].read_text(),context);header=paths['plans.hpp'].read_text();index=uint(plan['index'],1024,'selected plan')
    for k,v in [('N',g['input_bits']),('S',g['injection_sites']),('O',g['output_bits'])]:require(re.search('^#define '+k+' '+str(v)+'$',header,re.M),'Compiled geometry mismatch')
    for role,mapped in context['role_map'].items():require(re.search('^#define P_'+role.upper()+' '+re.escape(mapped)+'$',header,re.M),'Compiled role mismatch')
    table=re.search(r'static const Plan PLANS\[\]=\{\n(.*?)\n\};',header,re.S);require(table is not None,'Compiled plan table missing');rows=table[1].splitlines();keys=('mode','legal_mask','legal_value','patterns','budget','excluded','unknown_fault','metric','basis')
    require(index<len(rows) and rows[index]=='{'+','.join(str(plan[k]) for k in keys)+'},','Selected plan differs from compiled table')
    require(run[1:]==[str(index)] and len(run)==2 and isinstance(run[0],str) and Path(run[0]).name=='Vtop','Native run selection mismatch')
    execution=read_json(paths['execution.json']);require(execution['build_exit']==execution['xml_exit']==execution['run_exit']==0 and execution['binary_sha256']==hashes['Vtop'],'Native execution mismatch')
    n=g['input_bits'];s=g['injection_sites'];outmask=(1<<g['output_bits'])-1;site_mask=(1<<s)-1
    uint(plan['mode'],1,'mode');uint(plan['legal_mask'],(1<<n)-1,'constraint mask');uint(plan['legal_value'],(1<<n)-1,'constraint value');uint(plan['patterns'],(1<<(1<<n))-1,'pattern selection');uint(plan['budget'],1<<n,'pattern budget');uint(plan['excluded'],(1<<(2*s))-1,'exclusion mask');uint(plan['metric'],1,'metric');uint(plan['basis'],1,'population basis')
    require(type(plan['unknown_fault']) is int and -1<=plan['unknown_fault']<2*s,'Invalid unclassified fault')
    legal=[v for v in range(1<<n) if v&plan['legal_mask']==plan['legal_value']];selected=[v for v in legal if plan['patterns']&(1<<v)];sampled=selected[:plan['budget']];require(legal and selected,'Empty native scope/patterns')
    lines=iter(paths['run.stdout.txt'].read_text().splitlines())
    require(next(lines)=='FAULT_CAMPAIGN 1','Unsupported native export')
    require(next(lines)=='CONFIG '+' '.join(map(str,[index,n,s,g['output_bits'],*[plan[k] for k in keys]])),'Observed native configuration mismatch')
    def take(prefix,count):
        row=next(lines).split();require(len(row)==count+1 and row[0]==prefix,'Malformed '+prefix+' record');return row[1:]
    golden={};observations=[];faults=[]
    for v in legal:
        values=list(map(int,take('GOLD',5)));vector,mode,raw,driven,y=values
        require(vector==v and mode==plan['mode'] and 0<=raw<=site_mask and driven==raw and 0<=y<=outmask,'Invalid native healthy observation')
        golden[v]=y;observations.append(dict(kind='healthy',vector=v,mode=mode,raw_sites=raw,driven_sites=driven,observed=y))
    responses={};representatives={}
    for fid in range(2*s):
        response={}
        for v in legal:
            row=list(map(int,take('ORACLE',9)));f,site,stuck,vector,mode,raw,driven,y,healthy=row
            require((f,site,stuck,vector,mode)==(fid,fid//2,fid%2,v,plan['mode']) and 0<=raw<=site_mask and 0<=driven<=site_mask and 0<=y<=outmask and healthy==golden[v],'Invalid native injected observation')
            require(((driven>>site)&1)==stuck and (driven&~(1<<site))==(raw&~(1<<site)),'Native injection site mismatch')
            response[v]=y;observations.append(dict(kind='fault',fault_id=fid,site=site,stuck=stuck,vector=v,mode=mode,raw_sites=raw,driven_sites=driven,observed=y,healthy=healthy))
        raw=take('FAULT',7);f,classification,count,witness,detectable,representative,excluded=int(raw[0]),raw[1],*map(int,raw[2:])
        require(f==fid and classification in CLASSES,'Invalid native classification identity')
        responses[fid]=response;canonical=next((representatives[old] for old in range(fid) if responses[old]==response),fid);representatives[fid]=canonical
        actual_witness=next((v for v in sampled if response[v]!=golden[v]),-1);full_detectable=response!=golden
        expected='UNKNOWN' if fid==plan['unknown_fault'] else 'DT' if actual_witness>=0 else 'AB' if len(sampled)<len(selected) else 'UT' if not full_detectable else 'UD'
        require((classification,count,witness,detectable,representative,excluded)==(expected,len(sampled),actual_witness,int(full_detectable),canonical,int(bool(plan['excluded']&(1<<fid)))),'Native class/collapse/overlay mismatch')
        faults.append({'id':fid,'site':fid//2,'stuck':fid%2,'classification':classification,'sampled_patterns':count,'witness':None if witness<0 else witness,'finite_legal_detectable':bool(detectable),'representative':representative,'excluded':bool(excluded),'response':{str(v):y for v,y in response.items()}})
    groups=[]
    for rep in sorted(set(representatives.values())):
        members=[f for f in faults if f['representative']==rep];included=[f for f in members if not f['excluded']]
        expected=[rep,len(members),len(included),int(any(f['classification']=='DT' for f in included)),int(all(f['classification']=='UT' for f in included))]
        require(list(map(int,take('GROUP',5)))==expected,'Native collapsed group mismatch')
        groups.append({'representative':rep,'members':[f['id'] for f in members],'included_members':[f['id'] for f in included],'detected':bool(expected[3]),'all_untestable':bool(expected[4])})
    eligible=[f for f in faults if not f['excluded']];original_num=sum(f['classification']=='DT' for f in eligible);original_den=sum(not plan['metric'] or f['classification']!='UT' for f in eligible)
    collapsed_num=sum(g['detected'] for g in groups if g['included_members']);collapsed_den=sum((not plan['metric'] or not g['all_untestable']) for g in groups if g['included_members'])
    reported=(collapsed_num,collapsed_den) if plan['basis'] else (original_num,original_den)
    require(list(map(int,take('RESULT',8)))==[2*s,len(groups),original_num,original_den,collapsed_num,collapsed_den,*reported],'Native reported measurement mismatch')
    checks=len(legal)*(1+2*s);require(list(map(int,take('NATIVE_CHECKS',2)))==[checks,0],'Native assertion result mismatch')
    require(next(lines,None) is None,'Trailing native records')
    require(all(sha(p)==hashes[k] for k,p in paths.items()),'Native artifacts changed during capture')
    return {'format':'opentools.fault-evidence.v1','context':context,'geometry':g,'plan':plan,'source_sha256':{k:hashes[k] for k in SOURCES},'file_sha256':hashes,'observations':observations,'faults':faults,'groups':groups,
            'native_result':{'status':'PASS','checks':checks,'failures':0,'exit':0},
            'measurement':{'metric':'detected/nonexcluded' if not plan['metric'] else 'detected/nonexcluded-nonUT','population_basis':'collapsed' if plan['basis'] else 'original','numerator':reported[0],'denominator':reported[1],'original':{'numerator':original_num,'denominator':original_den},'collapsed':{'numerator':collapsed_num,'denominator':collapsed_den}},
            'limits':'Owned finite single-site stuck-at simulation. UT means no observable difference over this complete legal combinational input space only. Full-space observations also support bounded response equivalence, not commercial ATPG collapsing. Original classes and exclusions are preserved.'}
