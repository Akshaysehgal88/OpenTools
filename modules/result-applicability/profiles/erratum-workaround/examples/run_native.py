"""Compile one owned model and execute frozen command images and checker controls."""
import argparse,os,shutil,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROFILE=HERE.parent;sys.path.insert(0,str(PROFILE))
from erratum_common import compiler_ok,read_json,save,sha
from native_erratum import ARTIFACTS,SOURCES,capture,snapshot
from fixture import CASES,FAMILIES,config,config_text,context,notice,program,program_text,request
from reference_model import observe
def collect(output,cxx):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);compiler=Path(cxx).resolve();version=subprocess.run([str(compiler),'--version'],capture_output=True,text=True,check=True).stdout;(out/'compiler-version.txt').write_text(version)
    if not compiler_ok(version):raise ValueError('Native example qualified with Ubuntu GCC13.3.0')
    compiler_sha=sha(compiler);desc=[]
    with tempfile.TemporaryDirectory(prefix='opentools-erratum-') as tmp:
        tmp=Path(tmp);build=tmp/'build';build.mkdir();shutil.copy2(HERE/'device.cpp',build/'device.cpp')
        # Independent notice,questions,approval records and all sources are
        # frozen before the first build/model execution.
        for family in FAMILIES:
            for case in CASES:
                c=context(family,case);folder=out/c['run_ref'];folder.mkdir();work=tmp/c['run_ref'];work.mkdir();shutil.copy2(HERE/'device.cpp',work/'device.cpp');(work/'device.cfg').write_text(config_text(family,case));(work/'firmware.txt').write_text(program_text(family,case))
                for name in SOURCES:shutil.copy2(work/name,folder/name)
                sources={name:sha(work/name) for name in SOURCES};command=['./device','device.cfg','firmware.txt'];save(folder/'context.json',c);save(folder/'command.json',command);save(folder/'capture-notice.json',notice());save(folder/'capture-request.json',request(family,case,c,sources,sha(folder/'command.json'),sha(folder/'context.json')));save(folder/'independent-reference.json',observe(config(family,case),program(family,case)))
                frozen={name:sha(folder/name) for name in ('context.json','command.json','capture-notice.json','capture-request.json','independent-reference.json')};desc.append({'family':family,'case':case,'context':c,'folder':folder,'work':work,'sources':sources,'frozen':frozen,'command':command})
        command=[str(compiler),'-std=c++17','-O2','-Wall','-Wextra','-Werror','device.cpp','-o','device'];save(out/'build-command.json',command);p=subprocess.run(command,cwd=build,capture_output=True,text=True,timeout=60);(out/'build.stdout.txt').write_text(p.stdout);(out/'build.stderr.txt').write_text(p.stderr)
        if p.returncode:raise ValueError('Native model build failed: '+p.stderr)
        binary_sha=sha(build/'device');rows=[]
        for d in desc:
            folder,work,c=d['folder'],d['work'],d['context'];shutil.copy2(build/'device',work/'device');shutil.copy2(build/'device',folder/'device');p=subprocess.run(d['command'],cwd=work,capture_output=True,text=True,timeout=10);(folder/'native.stdout.txt').write_text(p.stdout);(folder/'native.stderr.txt').write_text(p.stderr);(folder/'compiler-version.txt').write_text(version)
            if p.returncode or not p.stdout.endswith('OPENTOOLS_ERRATUM_RUN_COMPLETE\n'):raise ValueError('Native model execution incomplete: '+c['run_ref'])
            if sha(compiler)!=compiler_sha or sha(work/'device')!=binary_sha or sha(build/'device.cpp')!=d['sources']['device.cpp'] or any(sha(work/name)!=value or sha(folder/name)!=value for name,value in d['sources'].items()) or any(sha(folder/name)!=value for name,value in d['frozen'].items()):raise ValueError('Original source/tool/question changed')
            frozen=d['frozen'];x={'format':'opentools.erratum-execution.v1','native_exit':p.returncode,'source_sha256':d['sources'],'compiler_sha256':compiler_sha,'binary_sha256':binary_sha,'context_sha256':frozen['context.json'],'command_sha256':frozen['command.json'],'notice_sha256':frozen['capture-notice.json'],'request_sha256':frozen['capture-request.json'],'reference_sha256':frozen['independent-reference.json'],'artifacts':{name:sha(folder/name) for name in ARTIFACTS}};save(folder/'execution.json',x);e=capture(folder,c);save(folder/'evidence.json',e);save(folder/'snapshot.json',snapshot(e));reference=read_json(folder/'independent-reference.json')
            if {k:e['native'][k] for k in reference}!=reference:raise ValueError('Actual trace/checker differs from independent payload/receiver-credit ledger')
            rows.append({'family':d['family'],'case':d['case'],'run_ref':c['run_ref'],'source_sha256':d['sources'],'reference_sha256':frozen['independent-reference.json'],'notice_sha256':frozen['capture-notice.json'],'request_sha256':frozen['capture-request.json'],'native_trace_rows':len(e['native']['trace']),'native_clock_ticks':len(e['native']['ticks']),'native_checker_outcome':snapshot(e)['result']['outcome'],'every_native_field_reference_checked':True});print(c['run_ref']+': native trace/checker checked',flush=True)
        save(out/'collection.json',{'native_executions':len(rows),'compiler':version.splitlines()[0],'compiler_sha256':compiler_sha,'binary_sha256':binary_sha,'cases':rows,'scope':'Owned synthetic notice and C++ event-delivery model,not real errata,silicon,firmware ISA or approval qualification.'})
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');p.add_argument('--cxx',required=True);a=p.parse_args()
    if os.name!='posix':p.error('Native collection qualified on Linux;saved-data review is portable')
    collect(a.output,a.cxx)
    from create_example import from_native
    from_native(a.output)
if __name__=='__main__':main()
