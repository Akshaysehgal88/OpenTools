"""Independent explicit-state oracle for the owned two-actor finite episode."""
from collections import deque

CASES=('coherence-opposite','coherence-escape','coherence-release-before-wait',
       'accelerator-opposite','accelerator-ordered','coherence-serialized',
       'coherence-starved-escape','coherence-external-reclaim','coherence-open-environment')
FIELDS=('phase_a','phase_b','held_a','held_b','request_a','request_b','release_a','release_b',
        'enabled_a','enabled_b','external_enabled','done_a','done_b')
INITIAL=(0,0,0,0)


def config(case):
    if case not in CASES: raise ValueError('Unknown example case')
    index=CASES.index(case)
    return (1 if index in (1,6) else 2 if index==2 else 3 if index==4 else 0,index==7)


def requests(strategy,actor,phase):
    first=1 if actor==0 or strategy==3 else 2
    second=2 if actor==0 or strategy==3 else 4 if strategy==1 else 1
    return first if phase==0 else second if phase==2 or phase==1 and not(strategy==2 and actor==0) else 0


def observations(state,cfg):
    strategy,external=cfg;phases=state[:2];held=state[2:];occupied=held[0]|held[1]
    request=[requests(strategy,a,p) for a,p in enumerate(phases)]
    release=[phases[a]==3 or a==0 and phases[a]==1 and strategy==2 for a in range(2)]
    enabled=[release[a] or request[a]!=0 and occupied&request[a]==0 for a in range(2)]
    values=list(state)+request+list(map(int,release))+list(map(int,enabled))+[int(external and phases[0]==1 and held[0]!=0)]+[int(p==4) for p in phases]
    return dict(zip(FIELDS,values))


def transition(state,cfg,actor):
    obs=observations(state,cfg)
    if actor==3:return state
    if actor==2:
        return (2,state[1],0,state[3]) if obs['external_enabled'] else state
    if actor not in (0,1):raise ValueError('Unknown action')
    if not obs['enabled_a' if actor==0 else 'enabled_b']:return state
    phases=list(state[:2]);held=list(state[2:]);phase=phases[actor]
    if phase==3:phases[actor]=4;held[actor]=0
    elif phase==1 and actor==0 and cfg[0]==2:phases[actor]=2;held[actor]=0
    else:
        held[actor] |= requests(cfg[0],actor,phase)
        phases[actor]=1 if phase==0 else 3
    return tuple(phases+held)


def selected(case,step):
    if step==0:return 3
    index=CASES.index(case)
    if index==5:return 0 if step<=3 else 1 if step<=6 else 3
    if index==6 and step>2:return 0
    if index==7 and step==3:return 2
    return (step-1)%2


def trace(case):
    cfg=config(case);state=INITIAL;rows=[]
    for step in range(13):
        action=selected(case,step)
        if step:state=transition(state,cfg,action)
        rows.append(dict(seq=step,selected=action,**observations(state,cfg)))
    return rows


def explore(cfg):
    """Enumerate every enabled non-idle interleaving of this finite, monotone model."""
    queue=deque([INITIAL]);paths={INITIAL:[]};arcs=[];blocked=[];completed=[]
    while queue:
        state=queue.popleft();obs=observations(state,cfg);enabled=[]
        for actor,key in enumerate(('enabled_a','enabled_b','external_enabled')):
            if obs[key]:enabled.append(actor)
        if not enabled:
            (completed if state[0]==state[1]==4 else blocked).append({'state':list(state),'actions':paths[state]})
        for action in enabled:
            following=transition(state,cfg,action)
            if following==state:raise AssertionError('Enabled action must advance the finite episode')
            arcs.append([list(state),action,list(following)])
            if following not in paths:paths[following]=paths[state]+[action];queue.append(following)
    return {'states':len(paths),'transitions':len(arcs),'blocked':blocked,'completed':completed,
            'reachable_states':[list(s) for s in paths],
            'semantics':'All enabled actor/external-reclaim transitions, two fixed transactions and single-slot resources; scheduler idle excluded. Not RTL formal equivalence or general liveness.'}
