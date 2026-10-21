"""Independent Boolean state equations for the owned finite native controls."""
def expected(family,selection):
    scenario,variant,mode,checker=selection;old=want=0;frames=[];checks=[];bad=int(variant=='bug');retain=int(mode=='warm');active=int(family=='interrupt')
    for tick in range(5 if scenario=='short' else 32):
        reset=int(tick<2);enabled=int(checker=='on')
        if scenario=='separate':hold=int(2<=tick<=4);event=int(tick==10);ack=int(tick==12)
        elif scenario in ('arrive','short'):hold=int(2<=tick<=4);event=int(tick==3);ack=int(tick==8)
        elif scenario=='pending':hold=int(3<=tick<=5);event=int(tick==2);ack=int(tick==9)
        elif scenario=='ack-arrive':hold=0;event=int(tick in (2,4));ack=int(tick in (4,8))
        else:hold=int(2<=tick<=4 or 11<=tick<=13);event=int(tick in (3,10,19,21));ack=int(tick in (7,16,21,25))
        retire=ack and not hold
        next_want=int(not reset and not(hold and not retain) and (event or want and not retire))
        next_old=int(not reset and not(hold and (not retain or bad)) and not(bad and retire) and (event or old and not retire))
        frame={'tick':tick,'reset':active if reset else 1-active,'hold':hold,'event':event,'ack':ack,'retain':retain,
               'pre_pending':old,'pre_visible':int(old and not hold),'post_pending':next_old,'post_visible':int(next_old and not hold),'enabled':enabled,'pre_clock':0,'post_clock':1};frames.append(frame)
        if enabled:
            for label,w,o in [('state_model',next_want,next_old),('delivery_model',int(next_want and not hold),int(next_old and not hold))]:checks.append({'tick':tick,'id':label,'expected':w,'observed':o,'ok':int(w==o)})
        old,want=next_old,next_want
    return {'frames':frames,'checks':checks,'counts':{'frames':len(frames),'checks':len(checks),'failures':sum(1-c['ok'] for c in checks)},
            'method':'Independent finite Boolean state equations for each complete native pre/post trace and comparison action; example qualification only, not a general RTL oracle.'}
