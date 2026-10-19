#!/usr/bin/env python3
"""Create synthetic inputs, an advisory selection and explicit campaign feedback."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from selection_core import fingerprint,plan


def example():
    ids=['soc_smoke','dma_directed','fabric_integration','soc_stress']
    universe={'format':'opentools.test-universe.v1','universe_ref':'synthetic:independent-manifest','revision_ref':'synthetic:rev-B',
        'scope_ref':'synthetic:config-A','source_ref':'synthetic:native full manifest export','complete':True,
        'tests':[{'id':key,'name':key,'configuration_ref':'synthetic:config-A/seed-1','execution_ref':'synthetic:existing runner '+key,
                  'available':True,'evidence_ref':'synthetic:full manifest row'} for key in ids]}
    changes={'format':'opentools.regression-change.v1','change_ref':'synthetic:local-dma-edit','base_revision_ref':'synthetic:rev-A',
        'revision_ref':'synthetic:rev-B','scope_ref':universe['scope_ref'],'diff_ref':'synthetic:retained diff','complete':True,
        'items':[{'id':'dma-edit','path':'rtl/dma.sv','category':'rtl','evidence_ref':'synthetic:actual change review'}]}
    mapping={'format':'opentools.test-mapping.v1','mapping_ref':'synthetic:reviewed explicit map','scope_ref':universe['scope_ref'],
        'source_ref':'synthetic:current dependency review','universe_sha256':fingerprint(universe),'change_sha256':fingerprint(changes),
        'entries':[{'change_id':'dma-edit','test_ids':['dma_directed'],'complete':True,'evidence_ref':'synthetic:scoped dependency map'}]}
    policy={'format':'opentools.regression-policy.v1','policy_ref':'synthetic:local policy','scope_ref':universe['scope_ref'],'source_ref':'synthetic:maintained stage policy',
        'universe_sha256':fingerprint(universe),'stage':'fast-feedback','mandatory_ids':['soc_smoke','fabric_integration'],'required_ids':ids,
        'defer_ids':['soc_stress'],'later_stage_ref':'synthetic:required qualification stage','broaden_categories':['shared','configuration','toolchain','generator'],
        'unknown_impact':'broaden_all'}
    selection=plan(universe,changes,mapping,policy)
    def results(kind,names):
        return {'format':'opentools.regression-results.v1','campaign_ref':'synthetic:'+kind,'kind':kind,'scope_ref':universe['scope_ref'],
            'source_ref':'synthetic:retained native checker results','universe_sha256':fingerprint(universe),'change_sha256':fingerprint(changes),
            'selection_sha256':fingerprint(selection) if kind=='targeted' else None,'complete':True,
            'attempts':[{'attempt_ref':'synthetic:'+kind+':'+key,'test_id':key,'state':'pass','run_ref':'synthetic:run:'+key,
                         'evidence_ref':'synthetic:checker output '+key,'wall_ns':None} for key in names]}
    targeted=results('targeted',selection['selected_ids']);full=results('full',ids)
    full['attempts'][-1]['state']='fail'
    return universe,changes,mapping,policy,targeted,full


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');args=parser.parse_args()
    out=Path(args.directory);out.mkdir(parents=True,exist_ok=False)
    for name,value in zip(('universe','changes','mapping','policy','targeted-results','full-results'),example()):
        (out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Created synthetic example; no jobs executed.')


if __name__=='__main__':main()
