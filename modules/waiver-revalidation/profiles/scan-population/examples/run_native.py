"""Collect actual native sequential census, scan insertion and connectivity on Linux."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
from fixture import CASES,FAMILIES,flow,seed,selections
HERE=Path(__file__).resolve().parent;VERSION='v2.0-17598-ga008522d8'
SOURCES=('seed.v','cells.lib','cells.lef','flow.tcl','population.json','exclusions.json')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2)+'\n')
def collect(output,openroad):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);exe=Path(openroad).resolve()
    version=subprocess.run([str(exe),'-version'],capture_output=True,text=True,check=True).stdout.strip()
    if version!=VERSION:raise ValueError('Qualified OpenROAD '+VERSION+' required')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='opentools-scan-population-') as temporary:
        base=Path(temporary)
        for family,c in FAMILIES.items():
            for case in CASES:
                name=family+'-'+case;work=base/name;work.mkdir();retained=out/name;retained.mkdir();run=retained/'run';context,population,exclusions,protected=selections(family,case)
                for n in ('cells.lib','cells.lef'):shutil.copy2(HERE/n,work/n)
                (work/'seed.v').write_text(seed(c,case));(work/'flow.tcl').write_text(flow(c,protected));save(work/'population.json',population);save(work/'exclusions.json',exclusions)
                before={n:sha(work/n) for n in SOURCES};command=[str(exe),'-exit','-no_init','flow.tcl'];save(work/'command.json',command);command_sha=sha(work/'command.json')
                result=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=90)
                (work/'stdout.txt').write_text(result.stdout);(work/'stderr.txt').write_text(result.stderr)
                if result.returncode or result.stdout.count('OPENTOOLS_NATIVE_SCAN_POPULATION_COMPLETE')!=1 or any(v in result.stdout+result.stderr for v in ('[ERROR','Error:','Signal 11')):raise ValueError('Native insertion incomplete: '+name+'\n'+result.stdout+result.stderr)
                for n,value in before.items():
                    if sha(work/n)!=value:raise ValueError('Pre-run source changed: '+n)
                (work/'version.txt').write_text(version+'\n');save(work/'execution.json',{'exit_code':result.returncode})
                shutil.copytree(work,run);save(retained/'context.json',context)
                rows.append({'case':name,'family':family,'selection':case,'protected':protected,'sources':before,'command_sha256':command_sha,'context':context})
                print(name+': native census/insertion complete',flush=True)
    record={'native_version':version,'native_runs':len(rows),'cases':rows,'limits':'Flat scalar sequential population, ideal owned functional library. Clock groups are native connectivity; logical power/role/exclusion intent is independently supplied. Membership is not ATPG/fault coverage.'};save(out/'collection.json',record);return record
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--openroad',required=True);p.add_argument('--raw-only',action='store_true');a=p.parse_args()
    if os.name!='posix':p.error('Native collection is qualified on Linux; saved-data review is portable')
    collect(a.output,a.openroad)
    if not a.raw_only:
        from create_example import from_native
        from_native(a.output)
if __name__=='__main__':main()
