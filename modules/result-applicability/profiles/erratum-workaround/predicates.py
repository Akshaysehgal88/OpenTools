"""A bounded data-only all/any/equality/membership predicate with unknowns."""
from erratum_common import canonical,known,require,shape,text
def validate(tree):
    count=0
    def visit(t,depth):
        nonlocal count
        count+=1;require(depth<=5 and count<=48,'Predicate outside bounded profile')
        require(isinstance(t,dict),'Predicate node required');op=t.get('op')
        if op in ('all','any'):
            shape(t,{'op','terms','basis_ref'});require(isinstance(t['terms'],list) and 1<=len(t['terms'])<=8,'Bounded terms required')
            for term in t['terms']:visit(term,depth+1)
        else:
            shape(t,{'op','field','value','basis_ref'});require(op in ('equal','in') and text(t['field']) and len(t['field'])<=96,'Supported typed predicate required')
            values=t['value'] if op=='in' else [t['value']]
            require(isinstance(values,list) and 1<=len(values)<=16 and all(type(v) in (int,str,bool,type(None)) for v in values),'Scalar predicate values required')
        require(t['basis_ref'] is None or text(t['basis_ref']),'Predicate basis or null required')
    visit(tree,0)

def evaluate(tree,fields):
    validate(tree);nodes=[]
    def visit(t,path):
        op=t['op'];basis=t['basis_ref'];value=None;row={'path':path,'op':op,'basis_ref':basis}
        if op in ('all','any'):
            terms=[visit(v,path+'/'+str(i)) for i,v in enumerate(t['terms'])]
            value=(False if False in terms else None if None in terms else True) if op=='all' else (True if True in terms else None if None in terms else False)
            row['terms']=terms
        else:
            observed=fields.get(t['field']);row.update(field=t['field'],observed=observed,requested=t['value'])
            desired={'value':t['value'],'evidence_ref':basis}
            if known(observed) and known(desired):
                value=canonical(observed['value'])==canonical(t['value']) if op=='equal' else any(canonical(observed['value'])==canonical(v) for v in t['value'])
        if not text(basis):value=None
        row['truth']=value;nodes.append(row);return value
    truth=visit(tree,'root')
    return {'truth':truth,'state':'affected' if truth is True else 'unaffected_within_selected_conditions' if truth is False else 'unknown','nodes':nodes,'unknown_nodes':[v['path'] for v in nodes if v['truth'] is None]}
