"""Bind independent owned objectives to original native campaign artifacts."""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from fault_common import IDENTITY,read_json,save
from native_fault import capture
from fault_core import compare
from fixture import FAMILIES

def binding(e):
    return {'identity':{k:e['context'][k] for k in IDENTITY},'source_sha256':e['source_sha256'],
            'plan_sha256':e['file_sha256']['plan.json'],'run_command_sha256':e['file_sha256']['run.command.json'],
            'binary_sha256':e['file_sha256']['Vtop']}

def policy(family,c,selection,a,b):
    base='owned/'+family
    reviewed=[]
    if selection=='valid-exclusion':
        reviewed=[{'fault_id':f,'source_ref':base+'/constant-unobserved-site-definition',
                   'reason_ref':base+'/approved-selected-objective-exclusion',
                   'owner_ref':base+'/receiving-test-owner'} for f in (2*(c['s']-1),2*c['s']-1)]
    return {'format':'opentools.fault-policy.v1','baseline':binding(a),'current':binding(b),
            'required_original_faults':[{'id':f,'site':f//2,'stuck':f%2,'source_ref':base+'/owned-site-definition/'+str(f//2)} for f in range(c['s']*2)],
            'reviewed_exclusions':reviewed,'inputs_complete':True,'source_ref':base+'/independent-original-objective',
            'owner_ref':base+'/receiving-test-owner'}

def from_native(directory):
    directory=Path(directory);collection=read_json(directory/'collection.json');evidence={};summary=[]
    for row in collection['cases']:
        folder=directory/row['case'];e=capture(folder/'run',read_json(folder/'context.json'));evidence[row['case']]=e;save(folder/'evidence.json',e)
    for row in collection['cases']:
        folder=directory/row['case'];a=evidence[row['family']+'-baseline'];b=evidence[row['case']];p=policy(row['family'],FAMILIES[row['family']],row['selection'],a,b);r=compare(a,b,p)
        save(folder/'policy.json',p);save(folder/'report.json',r);summary.append({'case':row['case'],'status':r['status'],'baseline_fraction':a['measurement'],'current_fraction':b['measurement'],'new_detected':r['newly_detected_faults'],'findings':r['findings'],'gaps':r['gaps']})
    save(directory/'review-summary.json',summary);return summary

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('native_directory',type=Path);a=p.parse_args()
    for r in from_native(a.native_directory):print(r['case']+': '+r['status'])
if __name__=='__main__':main()
