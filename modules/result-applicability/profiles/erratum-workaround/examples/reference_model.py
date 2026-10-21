"""Independent pending payload/receiver-credit ledger and expected predicates."""
def observe(cfg,commands):
    payload_pending=None;published=None;baseline_receipt=wa_receipt=False;hold=0;forced=False;accepted=False;observed=-1;active=0;trace=[];ticks=[]
    capture_wait=list(range(cfg['guard_need'])) if cfg['feature'] and cfg['fast_mode'] and cfg['revision']==1 and not cfg['actual_fuse'] else []
    for seq,(op,arg) in enumerate(commands,1):
        if op=='WRITE':payload_pending=arg
        elif op=='BASE_FENCE':published=payload_pending;baseline_receipt=True
        elif op=='WA_FENCE':published=payload_pending;wa_receipt=True
        elif op=='WA_GUARD':hold=arg;forced=True
        elif op=='ISSUE':
            for tick in range(max(hold,1)):
                clock=forced or tick==0
                if clock:
                    active+=1
                    if capture_wait:capture_wait.pop()
                if not capture_wait and cfg['power_on']:accepted=True
                ticks.append([tick,int(clock),active,int(accepted),published or 0])
            if accepted:observed=(published or 0) if cfg['feature'] and cfg['fast_mode'] else payload_pending
        check=accepted and observed==42
        trace.append({'seq':seq,'op':op,'arg':arg,'visible':published or 0,'pending':payload_pending or 0,'base_ordered':int(baseline_receipt),'wa_ordered':int(wa_receipt),'guard':hold,'force_clock':int(forced),'active_ticks':active,'ack':int(accepted),'data':observed,'check':int(check)})
    meta={k:cfg[k] for k in ('revision','feature','fast_mode','guard_need','exception_enabled','power_on')};meta['fuse']=cfg['actual_fuse'] if cfg['fuse_readable'] else None
    return {'meta':meta,'trace':trace,'ticks':ticks,'result':{'ack':int(accepted),'data':observed,'check':int(accepted and observed==42),'interaction_violation':int(cfg['exception_enabled'] and forced),'active_ticks':active}}
def applicability(case):
    if case=='unknown-fuse':return None
    return case not in ('unaffected','feature-disabled','feature-disabled-unknown-fuse','fuse-repaired','normal-mode')
def disposition(family,case):
    if case=='unknown-fuse':return 'INCOMPLETE',2
    if case in ('affected-unmitigated','fixed-base-vulnerable','interaction-conflict','too-short-guard') or case=='ported-guard' and family=='reset-boundary':return 'REVIEW_REQUIRED',1
    return 'REVIEW_PACKET_ACCOUNTED',0
