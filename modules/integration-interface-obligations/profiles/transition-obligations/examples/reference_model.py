"""Independent set-based identities/permissions and state ledger for owned transfers."""
CASES=('directory-premature-grant','directory-complete','directory-data-late','directory-duplicate-count',
       'directory-stale-ack-ignored','ring-premature-completion','ring-complete','directory-backpressured-grant')
FIELDS=('active','data_valid','granted','writer_permission','offer_pending','offered','grant_accepted','message_accepted',
        'read_valid','write_committed','stable_label','old_permissions','pending_mask','pending_count','transfer_data',
        'new_cache','read_data','active_id','active_epoch','guard_mode')


def guard(case):
    index=CASES.index(case);return 1 if index in (0,2,5) else 2 if index==3 else 0


def schedule(case):
    index=CASES.index(case);actions=[('initial',0,4,1,0),('request',1,2,1,0)]
    if index!=2:actions.append(('data',2,3,1,0))
    if index==4:actions.append(('stale-release-0',3,0,0,0))
    actions.append(('release-0',3,0,1,0))
    if index==3:actions.append(('duplicate-release-0',3,0,1,0))
    if index in (1,2,4,6,7):actions.append(('release-1',3,1,1,0))
    if index==7:actions.extend([('grant-offered',4,4,1,0),('grant-held',0,4,1,0)])
    actions.extend([('grant',4,4,1,1),('new-read',5,2,1,0),('new-write',6,2,1,0),('old-read',7,1,1,0)])
    if index in (0,3,5):actions.append(('release-1',3,1,1,0))
    if index==2:actions.append(('data',2,3,1,0))
    actions.append(('finish',8,2,1,0));return actions


def trace(case):
    mode=guard(case);holders={0,1};pending=set();count=0;active=False;data=None;granted=False;queued=False;new=None;active_id=epoch=0;rows=[]
    for seq,(ref,op,source,msg_epoch,ready) in enumerate(schedule(case)):
        legal=mode==1 or data is not None and (count==0 if mode==2 else not pending)
        offered=active and not granted and legal and (queued or op==4)
        accepted=offered and bool(ready);matched=active and active_id==7 and epoch==msg_epoch
        message=False;read_valid=committed=False;read=0
        if accepted:granted=True;queued=False;new=0 if data is None else data
        elif op==4 and active and not granted:queued=True
        if op==1:active=True;active_id=7;epoch=msg_epoch;pending=set(holders);count=len(pending);message=True
        elif op==2 and matched:data=17;message=True
        elif op==3 and matched and source in (0,1):
            message=True;holders.discard(source)
            if mode==2:count=max(0,count-1)
            elif source in pending:count-=1
            pending.discard(source)
        elif op==5 and granted:read_valid=True;read=new
        elif op==6 and granted:new=165;committed=True
        elif op==7 and source in holders:read_valid=True;read=17
        elif op==8 and granted:active=False;message=True
        values=[int(active),int(data is not None),int(granted),int(granted),int(queued),int(offered),int(accepted),int(message),
                int(read_valid),int(committed),int(granted),sum(1<<s for s in holders),sum(1<<s for s in pending),count,
                0 if data is None else data,0 if new is None else new,read,active_id,epoch,mode]
        rows.append(dict(seq=seq,event_ref=ref,op=op,source=source,message_id=7,message_epoch=msg_epoch,ready=ready,**dict(zip(FIELDS,values))))
    return rows
