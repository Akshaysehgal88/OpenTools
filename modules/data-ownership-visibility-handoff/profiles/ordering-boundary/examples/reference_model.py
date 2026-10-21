"""Owned path schedules and independent topological publication-outcome enumeration."""
from itertools import permutations

CASES=('ram-no-control','ram-ww','mmio-no-control','mmio-ww','mmio-wo','mmio-full',
       'mmio-wrong-predecessor','mmio-late-control','mmio-early-control','ram-selected-good')
DOMAINS={'W':1,'R':2,'O':4,'I':8}
FIELDS=('payload_issued','data_pending','flag_pending','fence_seen','fence_has_predecessor','flag_guarded',
        'payload_memory','publication_visible','consumed','rflag','rpayload','rpayload_valid','step_enabled')
SCHEDULES=((4,5,6),(4,6,5),(5,4,6),(5,6,4),(6,4,5),(6,5,4))


def config(case):
    index=CASES.index(case);none=index in (0,2,9)
    return {'flag_io':2<=index<=8,'pred':0 if none else 15 if index==5 else 4 if index==6 else 1,
            'succ':0 if none else 15 if index==5 else 1 if index in (1,3) else 4,
            'placement':0 if none else 2 if index==7 else 3 if index==8 else 1}


def prefix(case):
    place=config(case)['placement'];ops=[0]
    if place==3:ops.append(2)
    ops.append(1)
    if place==1:ops.append(2)
    ops.append(3)
    if place==2:ops.append(2)
    return ops


def covers(case):
    cfg=config(case);program=prefix(case)
    return 2 in program and program.index(1)<program.index(2)<program.index(3) and bool(cfg['pred']&DOMAINS['W']) and bool(cfg['succ']&DOMAINS['O' if cfg['flag_io'] else 'W'])


def enumerate_outcomes(case):
    """All successful three-event linearizations of the fixed owned implementation."""
    records=[]
    for order in permutations(('payload-commit','publication-commit','observe')):
        if covers(case) and order.index('publication-commit')<order.index('payload-commit'):continue
        flag=int(order.index('publication-commit')<order.index('observe'))
        payload=int(order.index('payload-commit')<order.index('observe')) if flag else None
        records.append({'order':list(order),'flag':flag,'payload':payload})
    outcomes=sorted({(r['flag'],-1 if r['payload'] is None else r['payload']) for r in records})
    return {'linearizations':records,'outcomes':[{'flag':f,'payload':None if p==-1 else p} for f,p in outcomes],
            'bad_witness':next((r for r in records if r['flag']==1 and r['payload']==0),None)}


def trace(case,run):
    queue={};visible={'payload':0,'publication':0};issued=[];fence_predecessors=None;guarded=False
    captured=(0,None);consumed=False;rows=[]
    for seq,op in enumerate(prefix(case)+list(SCHEDULES[run])):
        enabled=False
        if op==1:issued.append('payload');queue['payload']=1;enabled=True
        elif op==2:fence_predecessors=set(issued);enabled=True
        elif op==3:issued.append('publication');queue['publication']=1;guarded=covers(case);enabled=True
        elif op==4 and 'payload' in queue:visible['payload']=queue.pop('payload');enabled=True
        elif op==5 and 'publication' in queue and (not guarded or 'payload' not in queue):visible['publication']=queue.pop('publication');enabled=True
        elif op==6 and not consumed:
            captured=(visible['publication'],visible['payload'] if visible['publication'] else None);consumed=True;enabled=True
        values=[int('payload' in issued),int('payload' in queue),int('publication' in queue),int(fence_predecessors is not None),
                int(fence_predecessors is not None and 'payload' in fence_predecessors),int(guarded),visible['payload'],visible['publication'],
                int(consumed),captured[0],0 if captured[1] is None else captured[1],int(captured[1] is not None),int(enabled)]
        rows.append(dict(seq=seq,command=op,**dict(zip(FIELDS,values))))
    return rows
