"""Independent versioned-image ledger for the owned scalar cache/handoff example."""
CASES=('dma-no-clean','dma-clean-complete','dma-coherent','dma-clean-pending',
       'dma-clean-wrong-alias','dma-write-while-consumer-owned','dma-completion-before-read',
       'shared-queue-coherent','shared-queue-noncoherent','dma-coherent-no-order','dma-consumer-wrong-map')
FIELDS=('cache_a','cache_b','memory_a','memory_b','pending_data','read_data','cache_epoch_a','cache_epoch_b',
        'memory_epoch_a','memory_epoch_b','pending_epoch','order_epoch','read_epoch','dirty_a','dirty_b','pending',
        'pending_line','order_seen','published','completed','owner_consumer','clean_done','read_valid','read_control')


def coherent(case):
    if case not in CASES:raise ValueError('Unknown example')
    return CASES.index(case) in (2,7,9,10)


def schedule(case):
    index=CASES.index(case);actions=[('initial',0,0,0),('payload-write',1,0,165)]
    if index in (1,3,4,5,6):
        actions.append(('clean-request',2,1 if index==4 else 0,0))
        if index!=3:actions.append(('clean-complete',3,0,0))
    if index!=9:actions.append(('release-order',5,0,0))
    actions.append(('publish-control',4,0,0))
    if index==5:actions.append(('unauthorized-write',1,0,60))
    if index==6:actions.extend([('consumer-complete',7,0,0),('producer-reclaim',8,0,0),('producer-reuse',1,0,60)])
    actions.append(('consumer-read',6,1 if index==10 else 0,0))
    if index==3:actions.append(('clean-complete',3,0,0))
    if index!=6:actions.extend([('consumer-complete',7,0,0),('producer-reclaim',8,0,0),('producer-reuse',1,0,60)])
    return actions


def trace(case):
    # Immutable (version,data) images separate producer cache from backing memory.
    private=[(0,17),(0,34)];backing=list(private);dirty=[False,False];writeback=None
    captured=(0,0);captured_line=0;ordered=(False,0);published=completed=owner=False;rows=[]
    for seq,(ref,op,line,data) in enumerate(schedule(case)):
        read=(0,0);read_valid=clean_done=read_control=False
        if op==1:private[line]=(private[line][0]+1,data);dirty[line]=True
        elif op==2:captured=private[line];captured_line=line;writeback=(line,captured)
        elif op==3 and writeback is not None:
            destination,image=writeback;backing[destination]=image
            if private[destination][0]==image[0]:dirty[destination]=False
            writeback=None;clean_done=True
        elif op==4:published=owner=True
        elif op==5:ordered=(True,private[0][0])
        elif op==6:
            read_control=read_valid=published
            if published:read=(private if coherent(case) else backing)[line]
        elif op==7:completed=True
        elif op==8:owner=False
        values=[private[0][1],private[1][1],backing[0][1],backing[1][1],captured[1],read[1],
            private[0][0],private[1][0],backing[0][0],backing[1][0],captured[0],ordered[1],read[0],
            int(dirty[0]),int(dirty[1]),int(writeback is not None),captured_line,int(ordered[0]),int(published),int(completed),int(owner),
            int(clean_done),int(read_valid),int(read_control)]
        rows.append(dict(seq=seq,event_ref=ref,op=op,line=line,data=data,**dict(zip(FIELDS,values))))
    return rows
