"""Normalize retained owned trials; receiving policies remain separate from driver checks."""
import argparse
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from fixture import FAMILIES,desired_data
from handoff_core import review
from native_repair import capture
from repair_common import IDENTITY,exit_code,read_json,save

def from_native(directory):
    directory=Path(directory);collection=read_json(directory/'collection.json');summary=[]
    for case in collection['cases']:
        folder=directory/case['case'];context=read_json(folder/'context.json')
        evidence=capture(folder/'run',context);policy=read_json(folder/'policy.json')
        policy.update(format='opentools.repair-policy.v1',identity={k:context[k] for k in IDENTITY},
                      source_sha256=case['sources'],plan_sha256=case['plan_sha256'],
                      run_command_sha256=case['command_sha256'],binary_sha256=evidence['file_sha256']['Vtop'],
                      inputs_complete=True,required_init_data=[{'word':w,'data':value} for w,value in
                      enumerate(desired_data(FAMILIES[case['family']]))])
        # The owned fixture contract is intentionally fixed before inspection of readback.
        # Hashes bind this selected collection; they do not authenticate execution or acceptance.
        result=review(evidence,policy)
        for name,value in [('evidence',evidence),('receiving-policy',policy),('report',result)]:save(folder/(name+'.json'),value)
        summary.append({'case':case['case'],'status':result['status'],'native_result':evidence['native_result'],
                        'events':len(evidence['events']),'finding_kinds':sorted({f['kind'] for f in result['findings']}),
                        'gaps':result['gaps'],'exit':exit_code(result)})
    save(directory/'review-summary.json',summary)
    return summary

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('native_directory',type=Path);a=p.parse_args()
    for row in from_native(a.native_directory):print(row['case']+': '+row['status'])
if __name__=='__main__':main()
