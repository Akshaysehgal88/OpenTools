"""Execute owned device/command images and preserve original observation evidence."""
import argparse,os,shutil,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROFILE=HERE.parent;sys.path.insert(0,str(PROFILE))
from bringup_common import context as validate_context,qualified_compiler,read_json,save,sha
from native_bringup import SOURCES,ARTIFACTS,capture
from fixture import CASES,FAMILIES,config,config_text,context,program,program_text,request
from reference_model import trace

def collect(output,cxx):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);compiler=Path(cxx).resolve();version=subprocess.run([str(compiler),'--version'],capture_output=True,text=True,check=True).stdout
    (out/'compiler-version.txt').write_text(version)
    if not qualified_compiler(version):raise ValueError('Native recipe qualified with GCC13.3.0')
    compiler_sha=sha(compiler);descriptors=[]
    # Freeze every independent question/selection and every consumed image/cfg
    # before building or executing the first model.
    with tempfile.TemporaryDirectory(prefix='opentools-bringup-') as tmp:
        tmp=Path(tmp);build=tmp/'build';build.mkdir();shutil.copy2(HERE/'device.cpp',build/'device.cpp')
        for family in FAMILIES:
            for case in CASES:
                c=context(family,case);validate_context(c);folder=out/c['run_ref'];folder.mkdir();work=tmp/c['run_ref'];work.mkdir()
                shutil.copy2(HERE/'device.cpp',work/'device.cpp');(work/'device.cfg').write_text(config_text(family,case));(work/'firmware.txt').write_text(program_text(family,case))
                for name in SOURCES:shutil.copy2(work/name,folder/name)
                sources={name:sha(work/name) for name in SOURCES};command=['./device','device.cfg','firmware.txt'];save(folder/'context.json',c);save(folder/'command.json',command);save(folder/'independent-reference.json',trace(config(family,case),program(family,case)))
                q=request(family,case,c,sources,sha(folder/'command.json'),sha(folder/'context.json'));save(folder/'capture-question.json',q)
                descriptors.append({'family':family,'case':case,'context':c,'folder':folder,'work':work,'sources':sources,'frozen':{name:sha(folder/name) for name in ('context.json','command.json','capture-question.json','independent-reference.json')},'command':command})
        build_command=[str(compiler),'-std=c++17','-O2','-Wall','-Wextra','-Werror','device.cpp','-o','device'];save(out/'build-command.json',build_command);p=subprocess.run(build_command,cwd=build,capture_output=True,text=True,timeout=60);(out/'build.stdout.txt').write_text(p.stdout);(out/'build.stderr.txt').write_text(p.stderr)
        if p.returncode:raise ValueError('Native model build failed: '+p.stderr)
        binary_sha=sha(build/'device');core_sha=sha(PROFILE.parent/'diagnostic-validity/diagnostic_core.py');rows=[]
        for d in descriptors:
            folder,work,c=d['folder'],d['work'],d['context'];shutil.copy2(build/'device',work/'device');shutil.copy2(build/'device',folder/'device')
            p=subprocess.run(d['command'],cwd=work,capture_output=True,text=True,timeout=10);(folder/'native.stdout.txt').write_text(p.stdout);(folder/'native.stderr.txt').write_text(p.stderr);(folder/'compiler-version.txt').write_text(version)
            if p.returncode or not p.stdout.endswith('OPENTOOLS_BRINGUP_RUN_COMPLETE\n'):raise ValueError('Native observation incomplete: '+c['run_ref'])
            if sha(compiler)!=compiler_sha or sha(work/'device')!=binary_sha or sha(build/'device.cpp')!=d['sources']['device.cpp'] or any(sha(work/name)!=value or sha(folder/name)!=value for name,value in d['sources'].items()) or any(sha(folder/name)!=value for name,value in d['frozen'].items()):raise ValueError('Original input/tool changed')
            x={'format':'opentools.bringup-execution.v1','native_exit':p.returncode,'source_sha256':d['sources'],'context_sha256':d['frozen']['context.json'],'command_sha256':d['frozen']['command.json'],'question_sha256':d['frozen']['capture-question.json'],'reference_sha256':d['frozen']['independent-reference.json'],'diagnostic_core_sha256':core_sha,'compiler_sha256':compiler_sha,'binary_sha256':binary_sha,'artifacts':{name:sha(folder/name) for name in ARTIFACTS}};save(folder/'execution.json',x);e=capture(folder,c);save(folder/'evidence.json',e)
            if e['native']['rows']!=read_json(folder/'independent-reference.json') or e['native']['meta']!=config(d['family'],d['case']):raise ValueError('Actual device readout/state differs from independent reference')
            rows.append({'family':d['family'],'case':d['case'],'run_ref':c['run_ref'],'source_sha256':d['sources'],'reference_sha256':d['frozen']['independent-reference.json'],'question_sha256':d['frozen']['capture-question.json'],'native_rows':len(e['native']['rows']),'all_native_fields_reference_checked':True});print(c['run_ref']+': native state/receipt checked',flush=True)
        save(out/'collection.json',{'native_executions':len(rows),'compiler':version.splitlines()[0],'compiler_sha256':compiler_sha,'binary_sha256':binary_sha,'cases':rows,'scope':'Owned C++ device emulation,not real silicon/instrument/firmware ISA qualification.'})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');p.add_argument('--cxx',required=True);a=p.parse_args()
    if os.name!='posix':p.error('Native collection qualified on Linux;saved-data review is portable')
    collect(a.output,a.cxx)
    from create_example import from_native
    from_native(a.output)
if __name__=='__main__':main()
