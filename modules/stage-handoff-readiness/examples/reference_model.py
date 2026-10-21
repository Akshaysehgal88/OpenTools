"""Independent address/value contract for the owned push/pop/store receiver."""
import hashlib

CODE=0x1000000;ALPHA=0x2000000;BETA=0x3000000;OUTPUT=0x4000000;PAGE=4096
CASES=('rom-early','rom-ready','rom-ready-late','firmware-valid','firmware-early',
       'firmware-wrong-image','firmware-wrong-stack','wrong-entry')

def config(case):
    if case not in CASES:raise ValueError('Unknown case')
    firmware=case.startswith('firmware');stage='firmware' if firmware else 'loader'
    return {'successor_ref':stage,'mode':'loader-to-firmware' if firmware else 'rom-to-loader',
        'required_image':stage,'loaded_image':'loader' if case=='firmware-wrong-image' else stage,
        'alpha_ready':case in ('rom-ready','wrong-entry'),'beta_ready':firmware and case!='firmware-early',
        'late_ready':case=='rom-ready-late','initial_sp':(BETA if firmware and case!='firmware-wrong-stack' else ALPHA)+PAGE,
        'entry':CODE+0x8000000 if case=='wrong-entry' else CODE}

def fixture_image(stage):
    code=bytes.fromhex('68a500000058488907f4' if stage=='firmware' else '6a5a58488907f4')
    return {'format':'opentools.stage.image.v1','machine':'x86_64','sha256':hashlib.sha256(code).hexdigest(),
        'entry':CODE,'segments':[{'start':CODE,'size':len(code),'permissions':['R','X'],'evidence_ref':'reference-receiver-bytes:'+stage}],
        'evidence_ref':'reference-receiver-bytes:'+stage}

def expected(case):
    cfg=config(case);address=cfg['initial_sp']-8
    ready=cfg['alpha_ready'] if ALPHA<=address<ALPHA+PAGE else cfg['beta_ready']
    marker=165 if cfg['loaded_image']=='firmware' else 90
    entered=cfg['entry']==CODE;success=entered and ready
    accesses=[]
    if entered:
        accesses.append({'operation':'write','address':address,'size':8,'value':marker,'successful':bool(ready),'purpose':'stack'})
        if ready:
            accesses.append({'operation':'read','address':address,'size':8,'value':marker,'successful':True,'purpose':'stack'})
            accesses.append({'operation':'write','address':OUTPUT,'size':8,'value':marker,'successful':True,'purpose':'data'})
    return {'accesses':accesses,'completed':bool(success),'value':marker if success else None,
        'fault':'unmapped-entry' if not entered else None if ready else 'unready-stack-protection'}
