"""Separately expressed bounded fixture model; not a production oracle or product verdict."""
def expected(family,policy,scenario,fault):
    xor=90 if family=='stream' else 165;reset_active=int(family=='stream');busy=False;stored_id=stored_data=0;next_id=1;ledger={};edges=[];checks=[]
    for tick in range(11 if scenario=='short' else 32):
        resetting=tick in (0,1) or scenario=='reset' and tick==9
        mode=int(scenario!='no-mode1' and tick>=16);valid=int(2<=tick<24);take=int(scenario!='stalled' and tick%4!=0)
        ready=int(not busy);done=int(busy);data=(next_id*3+7)%65536
        observed=stored_data ^ int(fault=='fault' and mode==1)
        enabled=int(policy!='disabled' and not(policy=='mode0' and mode))
        edges.append({'tick':tick,'reset':reset_active if resetting else 1-reset_active,'mode':mode,'enabled':enabled,
                      'req_valid':valid,'req_ready':ready,'req_id':next_id,'req_data':data,'rsp_valid':done,'rsp_ready':take,'rsp_id':stored_id,'rsp_data':observed,'clock':0})
        if resetting:
            busy=False;stored_id=stored_data=0;ledger={};continue
        if enabled and policy=='stimulus' and valid:checks.append({'tick':tick,'id':next_id,'expected':data,'observed':data,'ok':1})
        elif enabled and done and take:
            want=ledger.get(stored_id,65535);checks.append({'tick':tick,'id':stored_id^int(policy=='wrong-id'),'expected':want,'observed':observed,'ok':int(want==observed)})
        if done and take:busy=False;ledger.pop(stored_id,None)
        if valid and ready:
            stored_id=next_id;stored_data=data^xor;busy=True;ledger[next_id]=stored_data;next_id+=1
    active=[v for v in edges if v['reset']!=reset_active]
    counts={'stimulus':sum(v['req_valid'] for v in active),'accepted':sum(v['req_valid']*v['req_ready'] for v in active),
            'completed':sum(v['rsp_valid']*v['rsp_ready'] for v in active),'checked':len(checks),'failures':sum(1-v['ok'] for v in checks)}
    return {'edges':edges,'checks':checks,'counts':counts,'method':'Independent finite-state fixture equations and declared checker controls, compared with complete native raw port/check journals. This is known-fixture validation, not general checker adequacy.'}
