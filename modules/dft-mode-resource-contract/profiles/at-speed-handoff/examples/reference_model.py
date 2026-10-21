"""Independent per-nanosecond controller/scan-state reference for owned qualification."""
import json
from pathlib import Path
def expected(period,reset_released,flags):
    shift,variant,se_kind,reset_hold=flags;source=period*(4 if shift else 1);half=source//2;cycles=9 if shift else 18;reset=1-reset_released if reset_hold else reset_released;rn=int(reset==reset_released);active=False;slot=0;l=c=ideal_l=ideal_c=0;checks=failures=0;pulses=[];last_se=0;se=int(bool(shift or se_kind));previous_g=0;previous_clock=0;previous_se=se;frames=[]
    for tick in range(cycles*source+1):
        clock=int(tick%source>=half) if tick else 0;start=int(tick<=source);serial=(tick//source)&1 if shift else 0
        se=1 if shift or se_kind==1 else int(tick<2*source+half-1) if se_kind==2 else int(tick<2*source) if se_kind==3 else 0
        if se!=previous_se:last_se=tick
        if not rn:active=False;slot=0;l=c=0
        elif previous_clock and not clock:
            if start:active=True;slot=0
            elif active:
                if slot==7:active=False
                else:slot+=1
        enable=int(bool(shift or active and (slot==1 or variant==0 and slot==2 or variant==1 and slot==3 or variant==3 and slot in (2,3))));g=clock&enable
        if g and not previous_g:
            pulses.append(tick);old_l=l
            if rn:l=serial if se else 1;c=old_l
            ideal_c=ideal_l;ideal_l=serial if shift else 1;checks+=3;failures+=int(l!=ideal_l)+int(c!=ideal_c)+int(reset!=reset_released or rn!=1 or se!=shift or tick-last_se<half or tick<half)
        frames.append({'tick_ns':tick,'clock':clock,'slot':slot,'enable':enable,'generated_clock':g,'reset':reset,'reset_n':rn,'scan_enable':se,'shift':shift,'variant':variant,'start':start,'data':1,'serial_in':serial,'launch':l,'capture':c,'expected_launch':ideal_l,'expected_capture':ideal_c,'checks':checks,'failures':failures});previous_g=g;previous_clock=clock;previous_se=se
    checks+=1;failures+=int(len(pulses)!=(9 if shift else 2))
    if shift:
        for a,b in zip(pulses,pulses[1:]):checks+=1;failures+=int(b-a!=source)
    elif len(pulses)==2:checks+=1;failures+=int(pulses[1]-pulses[0]!=source)
    return {'frames':frames,'pulses_ns':pulses,'counts':{'samples':len(frames),'checks':checks,'failures':failures,'pulses':len(pulses)}}
def check_collection(root):
    root=Path(root);manifest=json.loads((root/'collection.json').read_text());totals={'samples':0,'checks':0,'failures':0,'pulses':0}
    # Parse original measurements independently of native_occ.behavior.
    fields=('clock','slot','enable','generated_clock','reset','reset_n','scan_enable','shift','variant','start','data','serial_in','launch','capture','expected_launch','expected_capture','checks','failures')
    for row in manifest['cases']:
        folder=root/row['case'];lines=(folder/'run/run.stdout.txt').read_text().splitlines();assert lines[0]=='TIME_UNITS -9 -9';config=list(map(int,lines[1].split()[1:]));ref=expected(config[4],row['context']['reset_released'],row['flags']);observed=[]
        for line in lines[2:-2]:
            p=line.split();assert p[0]=='SAMPLE' and len(p)==20;observed.append({'tick_ns':int(p[1]),**dict(zip(fields,map(int,p[2:])))})
        assert observed==ref['frames'] and list(map(int,lines[-2].split()[2:]))==ref['pulses_ns'] and list(map(int,lines[-1].split()[1:]))==list(ref['counts'].values()),row['case']
        assert row['native_exit']==int(ref['counts']['failures']>0)
        (folder/'independent-reference.json').write_text(json.dumps(ref,indent=2)+'\n',encoding='utf-8')
        for k in totals:totals[k]+=ref['counts'][k]
    return {'cases':len(manifest['cases']),'totals':totals,'limits':'Independent owned ideal controller/cell/driver semantics only; not native ATPG, characterized timing or analog pulse quality.'}
if __name__=='__main__':
    import sys
    print(json.dumps(check_collection(sys.argv[1]),indent=2))
