"""Independent native population/class/constant truth table; no reader imports."""
def expected(family,case):
    if family=='block-interface':functional,diagnostic,constant='ack','trace','strap';enable='run_enable';clock='bus_clk';period=12.0;reset='reset_n';released=1;power='power_ok';delay=2.0
    else:functional,diagnostic,constant='ready','test_status','override_zero';enable='clock_enable';clock='macro_clk';period=20.0;reset='reset_active';released=0;power='macro_on';delay=1.5
    off=case=='unclocked';missing=case=='missing-output';fixed=case=='role-fixed';unconstrained={constant}
    if not fixed:unconstrained.add(diagnostic)
    if missing or off:unconstrained.add(functional)
    if off:
        unconstrained.add('capture/D')
        if family=='block-interface':unconstrained.add('launch/D')
    members=[] if off and family=='block-interface' else ['launch/CK'] if off else ['capture/CK','launch/CK']
    rows={name:{'kind':'output' if '/' not in name else 'data','unconstrained':name in unconstrained,'path_count':0 if name==constant else 1,'simulated':('1' if case=='wrong-constant' else '0') if name==constant else 'X'} for name in (functional,diagnostic,constant,'launch/D','capture/D')}
    if off:rows[functional]['path_count']=0
    if off and family=='block-interface':
        # With no clocked FF startpoint, the engine still reports these endpoints
        # but returns no FF-originated representative. The input-delay start remains.
        for name in (functional,diagnostic,'capture/D'):rows[name]['path_count']=0
    rows[functional]['output_margin']=None if missing or off else delay+(.5 if case=='wrong-delay' else 0)
    rows[diagnostic]['output_margin']=3.0 if fixed else None
    return {'unconstrained':sorted(unconstrained),'clock_sources':[clock],'period_ns':period,'clock_members':members,'clock_pins':['capture/CK','launch/CK'],'cases':{reset:released,power:1,enable:0 if off else None if case=='unknown-mode' else 1},'endpoints':rows}
