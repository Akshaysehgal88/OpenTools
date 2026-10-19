"""Generate a small synthetic checkpoint qualification with verifiable data files."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from replay_core import fingerprint


def example():
    profile={'format':'opentools.checkpoint-profile.v1','id':'synthetic-clocked-driver.v1',
             'mechanism':'serialized_model','boundary_ref':'synthetic:quiescent low clock after step 4',
             'evidence_ref':'synthetic:bounded state inventory',
             'state':[{'id':name,'requirement':'capture','evidence_ref':'synthetic:consumer inventory'}
                      for name in ('dut','time','rng','queue','reference','scoreboard')]+
                     [{'id':'external_io','requirement':'not_used','evidence_ref':'synthetic:no external I/O'}],
             'observables':['time','transaction','rng','queue','checker']}
    files={'model.bin':b'synthetic serialized state, not native simulator data\n',
           'sim.bin':b'synthetic binary, not executable\n','firmware.bin':b'synthetic prefix image\n'}
    hashes={name:hashlib.sha256(value).hexdigest() for name,value in files.items()}
    boundary={'step':4,'values':{'time':12,'transaction':[4,11],'rng':101,'queue':[[5,7]],'checker':{'checked':3,'failures':0}},
              'evidence_ref':'synthetic:captured-boundary sample'}
    context={'binary_sha256':hashes['sim.bin'],'configuration':{'top':'synthetic','assertions':True},
             'prefix_inputs':[{'id':'firmware','sha256':hashes['firmware.bin'],'evidence_ref':'synthetic:consumed image'}],
             'prefix_seed':17,'capture_point':{'step':4,'unit':'driver-step','definition_ref':'synthetic:one completed transaction'}}
    checkpoint={'format':'opentools.checkpoint.v1','checkpoint_ref':'synthetic:checkpoint-4',
                'profile_sha256':fingerprint(profile),'mechanism':'serialized_model','context':context,
                'reference_continuation':{'stimulus':'continue captured RNG'},
                'state_inventory':[{'id':item['id'],'status':'captured' if item['requirement']=='capture' else 'not_used',
                                    'method':'synthetic:declared recipe','capture_ref':'synthetic:save body','restore_ref':'synthetic:restore body'} for item in profile['state']],
                'state_inventory_complete':{'complete':True,'evidence_ref':'synthetic:complete bounded state inventory'},
                'capture':{'complete':True,'exit_code':0,'evidence_ref':'synthetic:completed capture'},
                'artifacts':[{'path':'model.bin','sha256':hashes['model.bin'],'evidence_ref':'synthetic:state file'}],
                'boundary_observation':copy.deepcopy(boundary)}
    request={'format':'opentools.replay-request.v1','request_ref':'synthetic:replay-4-to-6','checkpoint_ref':checkpoint['checkpoint_ref'],
             'profile_sha256':fingerprint(profile),'intent':'faithful','context':copy.deepcopy(context),
             'continuation':copy.deepcopy(checkpoint['reference_continuation']),
             'horizon':{'start_step':4,'end_step':6,'unit':'driver-step','definition_ref':'synthetic:one completed transaction','evidence_ref':'synthetic:requested horizon'},
             'binary':{'path':'sim.bin','sha256':hashes['sim.bin'],'evidence_ref':'synthetic:requested executable'},
             'prefix_files':[{'id':'firmware','path':'firmware.bin','sha256':hashes['firmware.bin'],'evidence_ref':'synthetic:current prefix image'}],
             'evidence_ref':'synthetic:replay request'}
    samples=[{'step':5,'values':{'time':14,'transaction':[5,7],'rng':202,'queue':[[6,9]],'checker':{'checked':4,'failures':0}}},
             {'step':6,'values':{'time':16,'transaction':[6,9],'rng':303,'queue':[[7,1]],'checker':{'checked':5,'failures':0}}}]
    control={'format':'opentools.replay-run.v1','run_ref':'synthetic:control','role':'control',
             'request_sha256':fingerprint(request),'checkpoint_sha256':fingerprint(checkpoint),'profile_sha256':fingerprint(profile),
             'horizon':copy.deepcopy(request['horizon']),
             'completion':{'complete':True,'exit_code':0,'evidence_ref':'synthetic:completed process'},
             'start':copy.deepcopy(boundary),'samples':samples,
             'end':{**copy.deepcopy(samples[-1]),'evidence_ref':'synthetic:final sample'},'observations_ref':'synthetic:ordered journal'}
    restored=copy.deepcopy(control)
    restored.update(run_ref='synthetic:restored',role='restored')
    return checkpoint,request,profile,control,restored,files


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    args=parser.parse_args()
    out=Path(args.directory)
    out.mkdir(exist_ok=False)
    *records,files=example()
    for name,value in zip(('checkpoint','request','profile','control','restored'),records):
        (out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    for name,value in files.items():
        (out/name).write_bytes(value)


if __name__=='__main__':
    main()
