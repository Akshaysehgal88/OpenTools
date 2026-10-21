#!/usr/bin/env python3
"""Generate, elaborate and compile configuration pairs using the parent exporters."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

PROFILE=Path(__file__).resolve().parents[1];MODULE=PROFILE.parents[1];sys.path[:0]=[str(PROFILE),str(MODULE)]
from configuration_core import exit_code,require,review
from layout_capture import hardware,software
from create_example import CASES,contract_for,effective,fact_names,generate_pair,native_values,save

def run(output,compiler='gcc'):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False);summary=[]
    for case in CASES:
        folder=output/case;request=generate_pair(case,folder);hvalues,svalues=effective(request)
        h=hardware([str(folder/'configuration.sv')],[],'configuration_top','configuration_t',native_values(request,'hardware',request['hardware_parameters']),request['family'],case,True,folder/'hardware.evidence',observed_parameters=fact_names(request,'hardware'))
        s=software(str(folder/'configuration.h'),[str(folder/'selected_config.h'),str(folder/'defaults.h')],'configuration_probe',{'fields':[{'name':'anchor'}],'defines':{}},compiler,
            request['family'],case,True,True,folder/'software.evidence',constants=fact_names(request,'software'))
        require(h['provenance']['selected_integral_parameters']==native_values(request,'hardware',hvalues) and s['provenance']['selected_constants']==native_values(request,'software',svalues),'Native facts differ from independent effective-default reference: '+case)
        require(h['size_bits']==((hvalues['WORD_BITS']+7)//8)*8,'Resolved byte-rounded carrier differs from independent storage reference')
        probe=folder/'consumer.c'
        probe.write_text('#include <limits.h>\n#include <stdio.h>\n#include "configuration.h"\nint main(void){ printf("%lld %lld %lld %lld %d\\n", consumed_word_bytes(), consumed_depth(), consumed_feature(), consumed_mode(), CHAR_BIT); return 0; }\n',encoding='utf-8')
        command=[compiler,'-std=gnu11','-m64','-O0',str(probe),'-o',str(folder/'consumer')];save(folder/'consumer.command.json',command)
        built=subprocess.run(command,capture_output=True,text=True);(folder/'consumer.compile.txt').write_text(built.stdout+built.stderr,encoding='utf-8');require(built.returncode==0,'Consumer compilation failed')
        executed=subprocess.run([str(folder/'consumer')],capture_output=True,text=True);(folder/'consumer.stdout.txt').write_text(executed.stdout,encoding='utf-8');require(executed.returncode==0,'Consumer execution failed')
        require(list(map(int,executed.stdout.split()))==[svalues['WORD_BYTES'],svalues['DEPTH'],svalues['FEATURE'],svalues['MODE'],8],'Compiled consumer disagrees with constant export or octet basis')
        contract=contract_for(case,h,s,True);report=review(h,s,contract)
        expected=0 if case in ('payload-matched','storage-matched','storage-wide-matched') else 1
        require(exit_code(report)==expected,'Unexpected configuration disposition: '+case)
        for key,value in (('hardware',h),('software',s),('contract',contract),('report',report)):save(folder/(key+'.json'),value)
        summary.append({'case':case,'family':request['family'],'hardware':hvalues,'software':svalues,'status':report['status'],'parameters':report['parameters'],'findings':report['findings'],'gaps':report['gaps']})
    result={'cases':summary,'native':{'pyslang':'12.0.0','GCC':subprocess.run([compiler,'-dumpfullversion'],capture_output=True,text=True,check=True).stdout.strip()},
        'reference':'Effective default/override tables, resolved packed payload width, separate compiled consumer and CHAR_BIT observation. No binary layout or wire-encoding agreement inferred.'}
    save(output/'summary.json',result);return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--gcc',default='gcc');args=parser.parse_args()
    print(json.dumps(run(args.directory,args.gcc),indent=2))

if __name__=='__main__':main()
