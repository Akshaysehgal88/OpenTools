"""Collect owned handshake/checker controls with an existing Linux Verilator runtime."""
import argparse,hashlib,json,os
from pathlib import Path
import shutil,subprocess,tempfile

HERE=Path(__file__).resolve().parent
ROLES={'stream':{'clock':'clk','reset':'reset','mode':'functional_mode','fault':'fault','req_valid':'req_valid','req_ready':'req_ready','req_id':'req_id','req_data':'req_data','rsp_valid':'rsp_valid','rsp_ready':'rsp_ready','rsp_id':'rsp_id','rsp_data':'rsp_data'},
       'mailbox':{'clock':'clock','reset':'rst_n','mode':'retained_mode','fault':'inject_error','req_valid':'submit','req_ready':'grant','req_id':'tag','req_data':'message','rsp_valid':'response_valid','rsp_ready':'retire','rsp_id':'response_tag','rsp_data':'response'}}
CASES={'good-clean':('good','normal','clean'), 'good-fault':('good','normal','fault'),
       'gated-clean':('mode0','normal','clean'),'gated-fault':('mode0','normal','fault'),
       'disabled':('disabled','normal','clean'),'stimulus':('stimulus','normal','clean'),'wrong-id':('wrong-id','normal','clean'),
       'stalled':('good','stalled','clean'),'reset':('good','reset','clean'),'short-window':('good','short','clean'),'no-mode1':('good','no-mode1','clean')}
SOURCES=('top.sv','ports.hpp','checker.hpp','main.cpp')
BUILD=['--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','top','--Mdir','obj','top.sv','main.cpp']
XML=['--xml-only','-Wno-fatal','--top-module','top','--xml-output','model.xml','top.sv']
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
def checksum(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('output',type=Path);ap.add_argument('--verilator',required=True);ap.add_argument('--verilator-root',required=True);ap.add_argument('--raw-only',action='store_true');args=ap.parse_args()
    if os.name!='posix':ap.error('Native recipe is qualified on Linux; saved-data review is portable')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    rows=[]
    with tempfile.TemporaryDirectory(prefix='opentools-observation-') as temp:
        temp=Path(temp);(temp/'runtime').symlink_to(Path(args.verilator_root).resolve(),target_is_directory=True);env=dict(os.environ,VERILATOR_ROOT=str(temp/'runtime'))
        version=subprocess.run([args.verilator,'--version'],env=env,capture_output=True,text=True,check=True).stdout.strip()
        if not version.startswith('Verilator 5.020 '):raise ValueError('Qualified Verilator5.020 required')
        for family,mapping in ROLES.items():
            work=temp/family;work.mkdir();retained=out/'builds'/family;retained.mkdir(parents=True)
            shutil.copy2(HERE/(family+'.sv'),work/'top.sv')
            for name in ('checker.hpp','main.cpp'):shutil.copy2(HERE/name,work/name)
            content=''.join('#define M_'+role.upper()+' '+name+'\n' for role,name in mapping.items())+'#define RESET_ACTIVE '+str(int(family=='stream'))+'\n#define NATIVE_XOR '+str(0x5a if family=='stream' else 0xa5)+'\n'
            (work/'ports.hpp').write_text(content,encoding='utf-8');before={p:checksum(work/p) for p in SOURCES}
            for label,command in [('build',BUILD),('xml',XML)]:
                cmd=[args.verilator]+command;r=subprocess.run(cmd,cwd=work,env=env,capture_output=True,text=True,timeout=180)
                save(retained/(label+'.command.json'),cmd);(retained/(label+'.stdout.txt')).write_text(r.stdout,encoding='utf-8');(retained/(label+'.stderr.txt')).write_text(r.stderr,encoding='utf-8')
                if r.returncode:raise ValueError(label+' failed: '+family)
            for p in SOURCES:
                assert checksum(work/p)==before[p];shutil.copy2(work/p,retained/p)
            shutil.copy2(work/'model.xml',retained/'model.xml');shutil.copy2(work/'obj/Vtop',retained/'Vtop');(retained/'version.txt').write_text(version+'\n',encoding='utf-8')
            for case,selection in CASES.items():
                folder=out/(family+'-'+case);run=folder/'run';shutil.copytree(retained,run)
                command=[str(retained/'Vtop'),*selection];r=subprocess.run(command,cwd=run,env=env,capture_output=True,text=True,timeout=30)
                (run/'run.stdout.txt').write_text(r.stdout,encoding='utf-8');(run/'run.stderr.txt').write_text(r.stderr,encoding='utf-8');save(run/'run.command.json',command)
                save(run/'execution.json',{'build_exit':0,'xml_exit':0,'run_exit':r.returncode,'binary_sha256':checksum(run/'Vtop')})
                if r.returncode not in (0,1):raise ValueError('Native execution incomplete: '+case)
                rows.append({'case':family+'-'+case,'family':family,'policy':selection[0],'scenario':selection[1],'fault':selection[2],'run_exit':r.returncode,'source_sha256':before})
                print(family+'-'+case+': native data retained',flush=True)
    save(out/'collection.json',{'version':version,'native_builds':2,'native_runs':len(rows),'cases':rows,'limits':'Owned single-clock bounded handshake observation controls; original C++ instrumentation must be reviewed. No verification completeness or general UVM semantic export claim.'})
    if not args.raw_only:
        from create_example import from_native
        from_native(out)
if __name__=='__main__':main()
