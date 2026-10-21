"""Independent Boolean/edge ledger and endpoint tables for the owned examples."""
from pathlib import Path
from fixture import FAMILIES,mode

def expected_samples(family,case):
    c=FAMILIES[family];a,b=mode(c,case);q0=q1=prior=0;rows=[]
    pattern=(0,1,1,0,1,0,0,1)
    for tick in range(2*c['cycles']):
        clk=tick%2;da=pattern[(tick//2)%8];db=1-da
        active=(1-a) if family=='wake-control' else a
        qualified=active if case=='control-eco' else int(bool(active or b))
        gate=clk & qualified
        if gate and not prior:q0,q1=da,db if case=='data-eco' else q0
        rows.append([tick,clk,1-c['reset_asserted'],a,b,da,db,gate,q0,q1]);prior=gate
    return rows

def check(e,family,case):
    c=FAMILIES[family];n=c['cells'];p=c['ports'];g=e['graph'];samples=expected_samples(family,case)
    assert e['reports']['clock']['samples']==samples
    assert e['reports']['clock']['pulses']==(0 if case=='control-eco' else c['cycles'])
    edges={n['allow']+'/A': 'active_base' if c['wake'] else p['a'],n['allow']+'/B':p['b'],
           n['allow']+'/Y':'qualified_enable',n['gate']+'/A':p['clock'],
           n['gate']+'/B':('active_base' if c['wake'] else p['a']) if case=='control-eco' else 'qualified_enable',
           n['gate']+'/Y':p['gclk'],n['buffer']+'/A':p['db'] if case=='data-eco' else p['q0'],n['buffer']+'/Y':'data_buffer'}
    for role,q,d in [('launch','q0',p['da']),('capture','q1','data_buffer')]:
        for pin,net in [('CK',p['gclk']),('RN','reset_released' if c['wake'] else p['reset']),('D',d),('Q',p[q])]:edges[n[role]+'/'+pin]=net
    if c['wake']:
        edges.update({n['invert_a']+'/A':p['a'],n['invert_a']+'/Y':'active_base',n['invert_reset']+'/A':p['reset'],n['invert_reset']+'/Y':'reset_released'})
    assert {k:v['net'] for k,v in g['pins'].items()}==edges
    sta=e['reports']['sta'];assert sta['clock_pins']==sorted(n[k]+'/CK' for k in ('launch','capture'))
    assert sta['path_count']==(0 if case=='control-eco' else 1)
    if sta['paths']:
        assert sta['paths'][0]['startpoint']==(p['db'] if case=='data-eco' else n['launch']+'/Q')
        assert sta['paths'][0]['endpoint']==n['capture']+'/D'
    return {'samples_compared':len(samples),'numeric_values_compared':sum(map(len,samples)),
            'native_pin_connections_compared':len(edges),'native_path_endpoints_compared':2*len(sta['paths']),
            'limits':'Independent finite Boolean edge ledger and explicit connection/endpoint tables; no independent STA slack or physical timing proof.'}
