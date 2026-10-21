"""Independent observation questions and owned device/command recipes."""
from pathlib import Path
from bringup_common import IDENTITY,MODEL,sha
HERE=Path(__file__).resolve().parent
FAMILIES=('cold-start','wake-entry')
CASES=('early','late','monitor','fault-free','wrong-entry','wrong-image','wrong-revision','wrong-clock','unknown-correlation')
def config(family,case):
    cold=family=='cold-start'
    return {'revision':'B' if case=='wrong-revision' else 'A','fuse':0 if case=='wrong-revision' else 1,'clock_id':'device-timer','clock_ns':20 if case=='wrong-clock' else 10,'warm_clears':int(cold),'read_clears':int(cold),'board_power':1}
def config_text(family,case):return ''.join(k+' '+str(v)+'\n' for k,v in sorted(config(family,case).items()))
def program(family,case):
    entry='POR' if family=='cold-start' else 'WARM';recovery='WARM' if family=='cold-start' else 'POR'
    if case=='wrong-entry':entry='WARM' if entry=='POR' else 'POR'
    rows=[(1,entry)]
    if case!='fault-free':rows.append((2,'FAULT'))
    if case=='late':rows += [(5,recovery),(6,'READ')]
    elif case=='monitor':rows += [(3,'MONITOR'),(4,'READ'),(5,recovery)]
    else:rows += [(3,'READ'),(4,'SAVE'),(5,recovery),(6,'RECORD')]
    return rows
def program_text(family,case,actual=True):
    s='# owned observation command image\n'+''.join(str(t)+' '+op+'\n' for t,op in program(family,case))
    return s+('# alternate image revision\n' if case=='wrong-image' and actual else '')
def context(family,case):
    return {'format':'opentools.bringup-context.v1','run_ref':family+'-'+case,'scope_ref':family+'/observation','project_ref':'owned-bringup','configuration_ref':family+'/'+case,'mode_ref':'functional','board_ref':'owned-board-model','selection':{'target_epoch':1 if family=='cold-start' else 0,'required_through_tick':2,'selected_read_tick':4 if case=='monitor' else 6,'fault_mask':1},'recovery_kind':'WARM' if family=='cold-start' else 'POR','history_complete':True,'latching_complete':True}
def request(family,case,c,sources,command_sha,context_sha):
    import hashlib
    basis='owned/'+family+'/independent-observation-question';fact=lambda v:{'value':v,'evidence_ref':basis}
    values={'source.kind':MODEL,'source.model_sha256':sha(HERE/'device.cpp'),'silicon.revision':'A','silicon.fuses':1,'firmware.image_sha256':hashlib.sha256(program_text(family,case,False).encode()).hexdigest(),'board.power_on':True,'clock.identity':'device-timer','clock.period_ns':10,'reset.entry':'POR' if family=='cold-start' else 'WARM','reset.recovery':c['recovery_kind'],'diagnostic.effects':{'read_clear':family=='cold-start','recovery_status_clear':True,'capture_retention':'host'}}
    return {'format':'opentools.bringup-request.v1','claim_ref':family+'/'+case+'/compare','scope_ref':c['scope_ref'],'run_ref':c['run_ref'],'owner_ref':basis+'#bringup-owner','requirements_ref':basis,'expectation_ref':basis+'#pre-silicon-observation','clock_mapping_ref':None if case=='unknown-correlation' else basis+'#counter-to-expectation','binding':{'identity':{k:c[k] for k in IDENTITY},'sources':sources,'command_sha256':command_sha,'context_sha256':context_sha},'selection':c['selection'],'required_conditions':{k:fact(v) for k,v in values.items()},'window_ns':[19,21],'uncertainty_ns':0,'expected_answer':'absent_in_observed_prefix' if case=='fault-free' else 'present'}
