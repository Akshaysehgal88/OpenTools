"""Independent period/Boolean-route tables for owned native clock fixtures."""
from fixture import FAMILIES
def check(e,family,case):
    c=FAMILIES[family];n=e['native'];names=c['names'][:-1] if case=='missing-generated' else c['names']
    periods={'root':float(c['period'])};targets={'root':[c['root']]};members={'root':['divider0/CK']};events=[]
    for i,name in enumerate(names):
        ratio=3 if case=='wrong-divide' and i==c['stages']-1 else 2
        parent='root' if i==0 else c['names'][i-1];periods[name]=periods[parent]*ratio;targets[name]=['divider'+str(i)+'/Q'];members[name]=[]
        if i<c['stages']-1:members[name].append('divider'+str(i+1)+'/CK')
        if case!='untraced':events.append({'name':name,'master':None if case=='auto-master' and i==c['stages']-1 else parent,
          'reference_source':c['root'] if i==0 else 'divider'+str(i-1)+'/Q','divide_by':ratio,'targets':targets[name]})
    leaf_pins=['capture/CK','launch/CK']
    if case=='wrong-mode':members['root']+=leaf_pins
    elif case=='unknown-case':members['root']+=leaf_pins;members[c['names'][-1]]+=leaf_pins
    elif case not in ('missing-generated','gate-off'):members[c['names'][-1]]+=leaf_pins
    assert set(n['clocks'])==set(periods)
    for name,p in periods.items():
        clock=n['clocks'][name];assert clock['period_ns']==p and clock['targets']==targets[name] and clock['is_generated']==int(name!='root')
        assert clock['is_propagated']==int(case!='ideal') and clock['waveform_valid']==1 and clock['waveform_ns']==[0.0,p/2]
        assert clock['clock_pins']==sorted(members[name])
    actual=[{k:event[k] for k in ('name','master','reference_source','divide_by','targets')} for event in n['generated_events']];assert actual==events
    assert n['register_clock_pins']==sorted(leaf_pins+['divider'+str(i)+'/CK' for i in range(c['stages'])])
    expected_cases={c['reset']:str(c['reset_value']),c['enable']:'0' if case=='gate-off' else '1',c['mode']:'X' if case=='unknown-case' else str(1-c['select'] if case=='wrong-mode' else c['select'])};assert n['cases']==expected_cases
    expected_paths=0 if case in ('missing-generated','gate-off') else 2 if case=='unknown-case' else 1;assert n['path_count']==expected_paths
    assert all(p['startpoint']=='launch/Q' and p['endpoint']=='capture/D' for p in n['paths'])
    return {'native_records':n['record_count'],'native_clocks_compared':len(periods),'register_clock_pins_compared':len(n['register_clock_pins']),
            'clock_endpoint_associations_compared':sum(map(len,members.values())),'resolved_creation_events_compared':len(events),
            'native_case_values_compared':len(expected_cases),'native_path_endpoints_compared':2*expected_paths,
            'limits':'Independent fixed period/clock-target tables and Boolean mux/gate route ledger for the owned fixture; not a hardware waveform, clock-availability or timing-slack proof.'}
