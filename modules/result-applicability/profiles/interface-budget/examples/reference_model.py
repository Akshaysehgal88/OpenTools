"""Independent scalar budgets for actual native three-view comparisons."""
def expected(family,case,view):
    n=5 if case in ('permissive','coherent-slow') else 3;period=1.0 if family=='rising-cycle' else 2.0;fall=family=='opposite-edge';target=1.0;transition='fall' if fall else 'rise';input_delay=.02 if view=='upstream' else .45;output_delay=.55 if view=='upstream' else .02;cell_delay=.06 if case=='wrong-model' and view=='upstream' else .11
    if case=='permissive':input_delay=.05;output_delay=.10
    if case=='wrong-reference' and view=='downstream':transition='rise' if fall else 'fall';target=2.0 if fall else .5
    if view=='top':arrival=.02+2*n*.11;required=.98;margin=.02;input_delay=None;load=None;output=False;check=True
    else:arrival=input_delay+n*cell_delay;required=target-output_delay;margin=output_delay;load=.10 if case=='wrong-load' and view=='upstream' else .05;output=True;check=False
    return {'period_ns':period,'source_time_ns':0.0,'source_transition':'rise','target_time_ns':target,'target_transition':transition,'arrival_ns':round(arrival,6),'required_ns':round(required,6),'margin_ns':margin,'slack_ns':round(required-arrival,6),'input_delay_ns':input_delay,'load_pF':load,'output_delay':output,'check':check,'buffer_cells':2*n if view=='top' else n,'cases':{'mode':None if case=='unknown-mode' and view=='top' else 1,**({'reset_n':1} if view=='top' else {})}}
