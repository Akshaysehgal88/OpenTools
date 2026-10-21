"""Independent cause-set and captured-response ledger for the owned controls."""
CASES=('pre-reset-snapshot','post-reset-zero','post-reset-undetermined','monitor-consumes',
       'clock-unavailable','no-fault-control','old-crash-record','snapshot-cleared-by-reset',
       'engine-retains-status','engine-local-clear','engine-fault-free')
FIELDS=('status','epoch','saved_value','saved_epoch','saved_valid','rd_data','rd_epoch','rd_valid',
        'accepted','access_error','path_available','save_done','recovery_seen','clear_seen')

def config(case):
    index=CASES.index(case)
    return {'cause_mask':4 if index>=8 else 1,'read_clears':index<8,'status_reset_clears':index not in (8,10),'saved_reset_clears':index==7}

def commands(case):
    index=CASES.index(case)
    if index in (0,7):return (0,1,2,3,4,7)
    if index in (1,2,8,9):return (0,1,4,2)
    if index==3:return (0,1,8,2)
    if index==4:return (0,1,5,2)
    if index==5:return (0,0,2)
    if index==6:return (0,9,4,7)
    return (0,0,4,2)

def trace(case):
    cfg=config(case);bit=2 if cfg['cause_mask']==4 else 0
    causes=set();epoch=0;record=(set(),0,False);response=(set(),0);response_valid=False;available=True;rows=[]
    value=lambda cause_set:sum(2**b for b in cause_set)
    for seq,op in enumerate(commands(case)):
        accepted=error=saved=recovery=cleared=False
        if op==1:causes.add(bit)
        elif op in (2,8):
            response_valid=available
            if available:
                response=(causes.copy(),epoch);accepted=True
                if cfg['read_clears']:causes.clear();epoch+=1;cleared=True
            else:error=True
        elif op==3 and response_valid and available:record=(response[0].copy(),response[1],True);accepted=saved=True
        elif op==4:
            recovery=True;response=(set(),0);response_valid=False
            if cfg['status_reset_clears']:causes.clear();epoch+=1;cleared=True
            if cfg['saved_reset_clears']:record=(set(),0,False)
        elif op==5:available=False
        elif op==6:available=True
        elif op==7:
            response_valid=available
            if available:response=(record[0].copy(),record[1]);accepted=True
            else:error=True
        elif op==9:record=({bit},99,True)
        values=(value(causes),epoch,value(record[0]),record[1],int(record[2]),value(response[0]),response[1],
            int(response_valid),int(accepted),int(error),int(available),int(saved),int(recovery),int(cleared))
        rows.append(dict(seq=seq,command=op,**dict(zip(FIELDS,values))))
    return rows
