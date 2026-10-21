"""Normalize original native example artifacts against pre-run source identities."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dft_common import read_json
from native_capture import BASES,capture
from resource_core import IDENTITY,markdown,review
from fixture import FAMILIES

def from_native(root):
    root=Path(root);manifest=read_json(root/'collection.json');results=[]
    for row in manifest['cases']:
        target=root/row['case'];c=FAMILIES[row['family']];w=c['width'];base='owned-example/'+row['family']
        chain={'module':c['module'],'scan_master':'SCANR_CELL','instances':[c['prefix']+str(i) for i in range(w)],'pin_map':{'clock':'CK','reset':'RN','enable':'SE','scan_in':'SI','scan_out':'Q','data':'D'},'clock_port':c['clock'],'reset_port':c['reset'],'enable_port':'scan_enable_1','scan_in_port':'scan_in_1','scan_out_port':row['stop'],'data_port':c['data'],'state_port':c['q'],'clock_name':'scan_clock','reset_released':1}
        ctx={'format':'opentools.dft-resource-context.v1','run_ref':row['case'],'scope_ref':base,'configuration_ref':base+'/fixture-r1','design_ref':base+'/scanned-netlist','mode_ref':base+'/manufacturing-shift-capture','domain_ref':base+'/single-domain','chain':chain,'role_map':row['role_map'],'wrapper_instance':'dut','dependencies_complete':True,**{k:base+'/'+k for k in BASES}}
        expected={k:ctx[k] for k in IDENTITY};expected.update({'sources':row['source_sha256'],'mode_sdc_sha256':row['mode_sdc_sha256'],'command_sha256':row['command_sha256'],'chain':chain,'role_map':row['role_map']})
        phases={p:{'min_steps':w if p!='capture' else 1,'clock_input':'tclk','reset_level':1,'scan_enable':int(p!='capture'),'test_mode':1,'manufacturing':1,'power':1,'isolation':0,'basis_ref':base+'/required-mode-table/'+p} for p in ('shift','capture','unload')}
        contract={'format':'opentools.dft-resource-contract.v1','expected':expected,'phases':phases,'clock_period':c['period'],'require_propagated_reset':False,'requirements_basis_ref':base+'/required-mode-table','owner_ref':base+'/fixture-owner',**{k:base+'/'+k for k in BASES}}
        e=capture(root,row['case']+'/run',ctx);r=review(contract,e,root)
        for name,value in [('context.json',ctx),('contract.json',contract),('evidence.json',e),('review.json',r)]: (target/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
        (target/'review.md').write_text(markdown(r),encoding='utf-8');results.append({'case':row['case'],'status':r['status'],'native':r['native_status'],'exit_code':r['exit_code']})
    (root/'reviews.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8');return results
if __name__=='__main__':print(json.dumps(from_native(sys.argv[1]),indent=2))
