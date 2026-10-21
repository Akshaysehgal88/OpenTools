"""Read a complete original OpenROAD sequential census and stitched chain export."""
import re
from scan_common import canonical,read_json,relative,require,sha,shape,text
PROFILE='openroad-a008522d8-flat-scalar-reset-scan.v1';VERSION='v2.0-17598-ga008522d8'
IDENTITY=('run_ref','scope','design_ref','configuration_ref','population_ref')
SOURCES=('seed.v','cells.lib','cells.lef','flow.tcl','population.json','exclusions.json')
BASES=('mapping_basis_ref','library_basis_ref','power_basis_ref')
def context(c):
    shape(c,{'format','module','functional_master','scan_master','pins',*IDENTITY,*BASES})
    require(c['format']=='opentools.scan-context.v1' and all(text(c[k]) for k in IDENTITY),'Explicit native context required')
    for k in ('module','functional_master','scan_master'):require(isinstance(c[k],str) and re.fullmatch(r'[A-Za-z_]\w*',c[k]),'Simple native identifier required')
    require(c['functional_master']!=c['scan_master'],'Distinct functional/scan masters required')
    shape(c['pins'],{'clock','reset','data','state','scan_in','enable'});require(len(set(c['pins'].values()))==6 and all(text(v) for v in c['pins'].values()),'Explicit distinct cell pin roles required')
    require(all(c[k] is None or text(c[k]) for k in BASES),'Invalid mapping references')
def inventory(content,stage):
    lines=content.splitlines();require(lines and lines[0]=='FORMAT opentools.openroad-scan-inventory.v1 '+stage and lines[-1]=='OPENTOOLS_NATIVE_INVENTORY_COMPLETE','Native inventory boundaries missing')
    result={'sequential':[],'cells':{},'pins':{},'ports':{}}
    for line in lines[1:-1]:
        p=line.split();require(p,'Empty native inventory row')
        if p[0]=='SEQ':require(len(p)==2 and p[1] not in result['sequential'],'Duplicate native sequential identity');result['sequential'].append(p[1])
        elif p[0]=='CELL':require(len(p)==3 and p[1] not in result['cells'],'Duplicate native cell');result['cells'][p[1]]=p[2];result['pins'][p[1]]={}
        elif p[0]=='PIN':require(len(p)==4 and p[1] in result['pins'] and p[2] not in result['pins'][p[1]],'Duplicate/foreign native pin');result['pins'][p[1]][p[2]]=p[3]
        elif p[0]=='PORT':require(len(p)==4 and p[1] not in result['ports'] and p[2] in ('INPUT','OUTPUT'),'Invalid native port');result['ports'][p[1]]={'direction':p[2],'net':p[3]}
        else:raise ValueError('Unknown native inventory record')
    require(1<=len(result['sequential'])<=256 and set(result['sequential'])==set(result['cells']),'Profile requires a flat1..256scalar-sequential-cell census; other native cells need a qualified profile')
    return result
def netlist_binding(inv,source,c,stage):
    require(re.findall(r'\bmodule\s+([A-Za-z_]\w*)\s*\(',source)==[c['module']],'Native serialized module differs')
    for name,master in inv['cells'].items():
        require(master in (c['functional_master'],c['scan_master']) and (stage=='POST' or master==c['functional_master']),'Unsupported native sequential master')
        pattern=r'\b'+re.escape(master)+r'\s+'+re.escape(name)+r'\s*\((.*?)\);';blocks=re.findall(pattern,source,re.S);require(len(blocks)==1,'Native serialized instance absent/ambiguous')
        pins=re.findall(r'\.([A-Za-z_]\w*)\s*\(\s*([A-Za-z_]\w*(?:\[\d+\])?)\s*\)',blocks[0]);required={c['pins'][k] for k in ('clock','reset','data','state')}
        if master==c['scan_master']:required|={c['pins'][k] for k in ('scan_in','enable')}
        require(len(pins)==len(required) and set(inv['pins'][name])==required and dict(pins)==inv['pins'][name],'Native ODB/serialized pin map differs or is outside scalar profile')
def chain_members(pre,post,c,log):
    require(set(pre['cells'])==set(post['cells']),'Native insertion changed functional state identities outside this profile')
    p=c['pins'];members={n for n,m in post['cells'].items() if m==c['scan_master']};ordinary=set(post['cells'])-members
    for name in pre['cells']:
        require(all(pre['pins'][name][p[k]]==post['pins'][name][p[k]] for k in ('clock','reset','data','state')),'Insertion changed original functional pin connection')
    scan_inputs=[post['pins'][n][p['scan_in']] for n in members];require(len(scan_inputs)==len(set(scan_inputs)),'Native scan branches/duplicate inputs outside profile')
    blocks=re.findall(r"Scan chain '([^']+)' has (\d+) cells \((\d+) bits\)(.*?)(?=Scan chain '|OPENTOOLS_NATIVE_SCAN_POPULATION_COMPLETE)",log,re.S)
    counts=re.findall(r'Number of chains:\s*(\d+)',log);require(len(counts)==1 and int(counts[0])==len(blocks),'Native plan chain count differs')
    chains={};seen=set()
    for chain_id,count,bits,body in blocks:
        require(chain_id not in chains and int(count)==int(bits),'Ambiguous/native multibit plan outside profile')
        order=[];clock_label=edge=None
        for line in body.splitlines():
            m=re.fullmatch(r'\s+([A-Za-z_]\w*)(?:\s+\(([^,]+),\s*(\w+)\))?\s*',line)
            if m and m[1] in post['cells']:
                order.append(m[1])
                if m[2]:require(clock_label is None,'Multiple clock labels in no_mix plan');clock_label=m[2];edge=m[3]
        require(len(order)==int(count) and len(set(order))==len(order) and not(seen&set(order)) and set(order)<=members and edge=='rising','Native plan membership/edge differs')
        require(order and clock_label is not None,'Native clock group missing');clock_net=post['pins'][order[0]][p['clock']];enable=post['pins'][order[0]][p['enable']]
        require(all(post['pins'][n][p['clock']]==clock_net and post['pins'][n][p['enable']]==enable for n in order),'Native no_mix chain crosses mapped clock/enable roots')
        start=post['pins'][order[0]][p['scan_in']];end=post['pins'][order[-1]][p['state']]
        for previous,following in zip(order,order[1:]):require(post['pins'][previous][p['state']]==post['pins'][following][p['scan_in']],'Native preview order disagrees with stitched chain')
        inputs=[n for n,v in post['ports'].items() if v=={'direction':'INPUT','net':start}];outputs=[n for n,v in post['ports'].items() if v=={'direction':'OUTPUT','net':end}]
        require(inputs and outputs,'Stitched chain does not reach native serial boundaries');seen.update(order);chains[chain_id]={'order':order,'clock_label':clock_label,'clock_net':clock_net,'edge':edge,'enable_net':enable,'input_ports':inputs,'output_ports':outputs}
    require(seen==members,'Native scan census differs from complete chain plan');return {'chains':chains,'members':sorted(members),'unscanned':sorted(ordinary)}
def capture(root,workdir,c):
    context(c);hashes={}
    def read(name,json=False):
        path=relative(root,workdir+'/'+name);require(path.is_file(),'Missing original native artifact: '+name);hashes[workdir+'/'+name]=sha(path);return read_json(path) if json else path.read_text(encoding='utf-8')
    require(read('version.txt').strip()==VERSION,'Unqualified native DFT version');sources={}
    for name in SOURCES:read(name);sources[name]=hashes[workdir+'/'+name]
    command=read('command.json',True);require(isinstance(command,list) and len(command)==4 and all(text(v) for v in command) and command[1:]==['-exit','-no_init','flow.tcl'],'Native insertion command differs')
    execution=read('execution.json',True);shape(execution,{'exit_code'});require(type(execution['exit_code']) is int and execution['exit_code']==0,'Native insertion did not complete')
    log=read('stdout.txt');errors=read('stderr.txt');require(log.count('OPENTOOLS_NATIVE_SCAN_POPULATION_COMPLETE')==1 and not any(v in log+errors for v in ('[ERROR','Error:','Signal 11','initialization failed')),'Native task completion unresolved')
    pre=inventory(read('pre.txt'),'PRE');post=inventory(read('post.txt'),'POST');netlist_binding(pre,read('pre.v'),c,'PRE');netlist_binding(pre,read('seed.v'),c,'PRE');netlist_binding(post,read('post.v'),c,'POST')
    for name in ('pre.odb','post.odb'):
        path=relative(root,workdir+'/'+name);require(path.is_file(),'Original native database missing');hashes[workdir+'/'+name]=sha(path)
    chains=chain_members(pre,post,c,log);population=read('population.json',True);exclusions=read('exclusions.json',True)
    return {'format':'opentools.scan-evidence.v1','context':c,'sources':sources,'command_sha256':hashes[workdir+'/command.json'],'pre':pre,'post':post,'membership':chains,'population':population,'exclusions':exclusions,'native':{'status':'COMPLETE','version':VERSION,'execution':execution},'provenance':{'reader':PROFILE,'workdir':workdir,'integrity_files':hashes,'source_roles':{'native_tool_inputs':list(SOURCES[:4]),'independent_intent_inputs':list(SOURCES[4:])},'limits':'Native sequential census/ODB nets and plan membership; current state intent, power grouping and exclusions are supplied separately. A derived review packet may pair unchanged native artifacts with independently applicable current intent; retain the original packet and identify the new intent basis. No ATPG/fault coverage or physical power claim; saved artifacts are not authenticated execution attestations.'}}
def revalidate(e,root):
    p=e.get('provenance',{});require(p.get('reader')==PROFILE and isinstance(p.get('integrity_files'),dict),'Unsupported native inventory receipt')
    for name,value in p['integrity_files'].items():require(sha(relative(root,name))==value,'Changed original artifact: '+name)
    require(canonical(capture(root,p.get('workdir'),e.get('context')))==canonical(e),'Normalized scan evidence differs from original artifacts')
