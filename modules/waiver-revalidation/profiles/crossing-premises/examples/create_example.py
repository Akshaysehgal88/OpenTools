"""Synthetic structural population and an owned crossing event journal."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

PROFILE = Path(__file__).resolve().parents[1]
MODULE = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(PROFILE))
sys.path.insert(0,str(MODULE))
from crossing_capture import capture
from waiver_core import digest, require

CASES=("stable","live-update","ordered-reset","early-reset")


def population_for(case):
    require(case in CASES,"Unknown owned case")
    return {"format":"opentools.waiver-snapshot.v1","run_id":"owned-"+case,"scope":"crossing-example/configuration-channel",
        "configuration_ref":"owned-mode:"+case,"identity_basis":"owned-selected-crossing-v1","configuration_basis":"owned-explicit-crossing-population",
        "tool":{"name":"owned-synthetic-crossing-report","version":"1","ruleset":"declared-configuration-bus-crossing"},
        "population_complete":True,"configuration":{},"waivers":[{"id":"cfg-exception","definition_sha256":hashlib.sha256((Path(__file__).parent/'exception.txt').read_bytes()).hexdigest(),"complete":True,
            "findings":[{"id":"cfg-bus","object":"source_cfg[3:0] -> destination_cfg[3:0]","rule":"SYNTHETIC_SELECTED_CROSSING",
            "message":"Owned synthetic structural population; inspect observed stability and reset-readiness premises.","evidence_ref":"crossing_path.sv:declared-endpoints",
            "crossing":{"source":"source_cfg","destination":"destination_cfg","source_clock":"source_clk","destination_clock":"destination_clk",
                         "source_reset":"source_reset","destination_reset":"destination_reset","width":4,"evidence_ref":"crossing_path.sv:source-to-destination"}}]}]}


def journal_for(population,events):
    return {"format":"opentools.crossing-premise-journal.v1", "population_sha256":digest(population),
        **{k:population[k] for k in ('run_id','scope','configuration_ref','identity_basis')},"inputs_complete":True,
        "sampling_basis":"settled-events-closed-window-v1","waiver_id":"cfg-exception","finding_id":"cfg-bus",
        "crossing":copy.deepcopy(population['waivers'][0]['findings'][0]['crossing']),"events":events}


def example(case='stable'):
    population=population_for(case);events=[]
    for seq in range(8):
        events.append({'seq':seq,'time_tick':seq,'window':3<=seq<=6,'source_value':7 if case=='live-update' and seq>=5 else 3,
            'source_reset':seq==0,'destination_active':seq>=3 or case=='early-reset' and seq>=1,
            'source_ready':seq>=2,'destination_sample':seq in (4,6),'evidence_ref':'owned-example:event-'+str(seq)})
    journal=journal_for(population,events)
    return population,journal,capture(population,journal)


def policy():
    return {'format':'opentools.waiver-policy.v1','waivers':[{'id':'cfg-exception','premises':[
        {'key':'crossing:cfg-exception:cfg-bus:'+name,'equals':True,'evidence_ref':'exception.txt:'+name}
        for name in ('stable_in_window','source_ready_before_destination')]}]}


def save(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--case',choices=CASES,default='live-update');args=parser.parse_args()
    output=Path(args.directory);output.mkdir(parents=True,exist_ok=False)
    baseline=example('stable')[2]
    for name,value in zip(('population','journal','current'),example(args.case)):save(output/(name+'.json'),value)
    save(output/'baseline.json',baseline);save(output/'policy.json',policy())


if __name__=='__main__':main()
