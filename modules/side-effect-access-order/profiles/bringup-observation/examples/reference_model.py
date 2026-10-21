"""Separate cause-set/response-receipt model,not a native export reader."""
def trace(cfg,commands):
    pending=set();epoch=0;captured=None;response=None;rows=[]
    for tick,op in [(0,'INIT'),*commands]:
        accepted=error=False
        if op in ('POR','WARM'):
            response=None
            if op=='POR' or cfg['warm_clears']:pending=set();epoch+=1
        elif op=='FAULT':pending.add('selected-cause')
        elif op in ('READ','MONITOR'):
            response=None
            if cfg['board_power']:
                response=(set(pending),epoch);accepted=True
                if cfg['read_clears']:pending=set();epoch+=1
            else:error=True
        elif op=='SAVE':
            if response is not None:captured=(set(response[0]),response[1]);accepted=True
        elif op=='RECORD':
            response=None
            if cfg['board_power']:
                if captured is not None:response=(set(captured[0]),captured[1]);accepted=True
            else:error=True
        rows.append({'tick':tick,'host_ns':1000+tick*cfg['clock_ns'],'op':op,'status':int(bool(pending)),'epoch':epoch,'saved':int(bool(captured and captured[0])),'saved_epoch':captured[1] if captured else 0,'saved_valid':int(captured is not None),'rd':int(bool(response and response[0])),'rd_epoch':response[1] if response else 0,'rd_valid':int(response is not None),'accepted':int(accepted),'error':int(error),'available':cfg['board_power']})
    return rows

# These are observation/condition conclusions,not machine execution results.
def disposition(family,case):
    if case in ('wrong-entry','wrong-image','wrong-revision','wrong-clock'):return 'INAPPLICABLE',1
    if case in ('late','monitor','unknown-correlation'):return 'INCONCLUSIVE',2
    return 'SUPPORTED_WITHIN_EMULATION',0
