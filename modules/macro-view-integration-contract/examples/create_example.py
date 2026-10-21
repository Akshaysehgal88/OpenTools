"""Bind original owned integration intent to each retained native view set."""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from macro_common import IDENTITY,read_json,save
from native_views import capture
from view_core import CLAIMS,review
from fixture import FAMILIES,boxes

def policy(family,c,evidence):
    base='owned/'+family;pins=[]
    for name,direction,kind in c['pins']:
        role='repair' if name=='REPAIR_LOAD' else 'test' if name==c['control'] or name=='TEST_EN' else 'clock' if kind=='CLOCK' else 'data-control'
        pins.append({'physical':name,'logical':name,'timing':name,'direction':direction,'signal_type':kind,'width':1,'net':c['logical'][name],'role':role,'source_ref':base+'/original-pin-correspondence'})
    for name,kind,net in [(c['supply'],'POWER','VDD_CORE'),(c['ground'],'GROUND','VSS_CORE')]:pins.append({'physical':name,'logical':None,'timing':None,'direction':'INOUT','signal_type':kind,'net':net,'role':'supply-owner','supply_owner_ref':base+'/power-domain-owner','source_ref':base+'/original-supply-contract'})
    box=boxes(c)[c['control']];window=[box[0]-50,box[1]-50,box[2]+50,box[3]+50]
    return {'format':'opentools.macro-policy.v1','identity':{k:evidence['context'][k] for k in IDENTITY},
            'selection':{'instance':'u_macro','logical_instance':'u_macro','logical_unit':c['cell'],'library_cell':c['library']+'/'+c['cell']},'source_sha256':evidence['source_sha256'],
            'database_sha256':evidence['file_sha256']['native.odb'],'native_export_sha256':evidence['file_sha256']['native.jsonl'],'logical_xml_sha256':evidence['file_sha256']['logical.xml'],
            'native_command_sha256':evidence['file_sha256']['native.command.json'],'logical_command_sha256':evidence['file_sha256']['logical.command.json'],
            'inputs_complete':True,'source_ref':base+'/independent-view-intake-contract','owner_ref':base+'/receiving-integration-owner','required_claims':dict.fromkeys(CLAIMS,False),
            'master':c['cell'],'library_cell':c['library']+'/'+c['cell'],'geometry':{'database_units_per_micron':1000,'width':c['width'],'height':c['height']},
            'allowed_orientations':['R0','MX','MY','R180'],'operating_point':{'process':1,'voltage':c['voltage'],'temperature':25},'pin_map':pins,
            'required_arcs':[{'from':c['from'],'to':c['to'],'source_ref':base+'/required-native-endpoints'}],
            'access_windows':[{'pin':c['control'],'layer':'metal1','box':window,'require_pin_intersection':True,'source_ref':base+'/selected-clear-access-window'}]}

def from_native(directory):
    directory=Path(directory);collection=read_json(directory/'collection.json');summary=[]
    for case in collection['cases']:
        folder=directory/case['case'];e=capture(folder,read_json(folder/'context.json'));p=policy(case['family'],FAMILIES[case['family']],e);r=review(e,p)
        for name,value in [('evidence',e),('policy',p),('report',r)]:save(folder/(name+'.json'),value)
        summary.append({'case':case['case'],'status':r['status'],'findings':r['findings'],'gaps':r['gaps']})
    save(directory/'review-summary.json',summary);return summary
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('native_directory',type=Path);a=p.parse_args()
    for r in from_native(a.native_directory):print(r['case']+': '+r['status'])
if __name__=='__main__':main()
