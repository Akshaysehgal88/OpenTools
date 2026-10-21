"""Independent pre-run truth table for selectors, masking and native clock routes."""
def expected(family,case):
    # A separate ledger: no report/parser/core imports.
    if family=='shift-window':
        original='capture_shift';renamed='capture_serial';source='root';destination='root';mode='shift_mode'
    elif family=='clock-boundary':
        original='capture_async';renamed='capture_boundary';source='launch_root';destination='capture_root';mode='independent_mode'
    else:raise ValueError('Unknown context')
    target=renamed if case=='renamed' else 'capture_func' if case=='retarget' else original
    targets=sorted([target,'capture_func']) if case=='expanded' else [target]
    cases={'reset_n':'1',mode:'0' if case=='wrong-mode' else 'X' if case=='unknown-mode' else '1'}
    membership={'launch/CK':[source]}
    for name in targets:
        membership[name+'/CK']=([source] if name=='capture_func' or case=='wrong-mode' else sorted([source,destination]) if family=='clock-boundary' and case=='unknown-mode' else [destination])
    return {'from':['launch'],'to':targets,'before':sorted('launch/Q->'+t+'/D' for t in targets),'after':[],'cases':cases,'membership':membership,'data_pins':sorted([t+'/D' for t in ['launch',*targets]]),'output_pins':sorted([t+'/Q' for t in ['launch',*targets]]),'application_count':0 if case=='untraced' else 1}
