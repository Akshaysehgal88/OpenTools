"""Independent owned objectives, selected plans and logic equations."""
import json

FAMILIES={'select-network':{'family':0,'n':3,'s':5,'o':1},
          'qualifier-network':{'family':1,'n':4,'s':6,'o':2}}
CASES=('baseline','same','denominator-only','valid-exclusion','more-patterns',
       'mode-change','metric-change','aborted','unknown-class','collapsed-score')
ROLES=('stimulus','test_mode','fault_enable','fault_site','stuck_value','raw_sites','driven_sites','observed')

def roles(family):return {k:k if family=='select-network' else 'probe_'+k for k in ROLES}

def equation(c,vector,mode,fault=-1):
    bits=[(vector>>i)&1 for i in range(c['n'])];raw=[];driven=[]
    def node(value):
        i=len(raw);raw.append(value);driven.append((fault%2) if fault>=0 and fault//2==i else value)
    if not c['family']:
        node(bits[0] and bits[1]);node(bits[0] or bits[1]);node(driven[0] if bits[2] else driven[1]);node(driven[2]);node(0)
        output=driven[0] if mode else driven[3]
    else:
        node(bits[0]!=bits[1]);node(bits[2] and bits[3]);node(driven[0] and driven[1]);node(driven[0] or driven[1]);node(driven[2]);node(0)
        output=int(driven[4])|(int(driven[2] if mode else driven[3])<<1)
    pack=lambda values:sum(int(v)<<i for i,v in enumerate(values))
    return pack(raw),pack(driven),int(output)

def plan(c,case):
    full=(1<<(1<<c['n']))-1;p={'case':case,'index':CASES.index(case),'mode':0,'legal_mask':0,'legal_value':0,'patterns':1,'budget':1<<c['n'],'excluded':0,'unknown_fault':-1,'metric':0,'basis':0}
    if case=='more-patterns':p['patterns']=full
    if case=='mode-change':p.update(mode=1,legal_mask=1<<(c['n']-1),legal_value=0)
    if case=='metric-change':p['metric']=1
    if case=='aborted':p.update(patterns=full,budget=1)
    if case=='unknown-class':p['unknown_fault']=0
    if case=='collapsed-score':p['basis']=1
    if case=='denominator-only':
        # Pre-run owned stimulus/logic oracle deliberately chooses missed faults.
        missed=[f for f in range(c['s']*2) if equation(c,0,0,f)[2]==equation(c,0,0)[2]]
        p['excluded']=sum(1<<f for f in missed[:2])
    if case=='valid-exclusion':p['excluded']=3<<((c['s']-1)*2)
    return p

def top(family,c):
    r=roles(family);ports=[]
    widths=[c['n'],1,1,4,1,c['s'],c['s'],c['o']]
    for i,(k,bits) in enumerate(zip(ROLES,widths)):
        ports.append(('input' if i<5 else 'output')+' logic '+(f'[{bits-1}:0] ' if bits>1 else '')+r[k])
    return 'module top('+',\n'.join(ports)+');\nfault_network #(.FAMILY('+str(c['family'])+')) dut('+','.join('.'+k+'('+r[k]+')' for k in ROLES)+');\nendmodule\n'

def header(family,c):
    lines=['#define N '+str(c['n']),'#define S '+str(c['s']),'#define O '+str(c['o'])]
    lines+=['#define P_'+k.upper()+' '+v for k,v in roles(family).items()]
    lines+=['struct Plan {unsigned mode,legal_mask,legal_value,patterns,budget,excluded;int unknown_fault;unsigned metric,basis;};','static const Plan PLANS[]={']
    for case in CASES:
        p=plan(c,case);lines.append('{'+','.join(str(p[k]) for k in ('mode','legal_mask','legal_value','patterns','budget','excluded','unknown_fault','metric','basis'))+'},')
    return '\n'.join(lines+['};',''])

def context(family,c,case):
    base='owned/'+family
    return {'format':'opentools.fault-context.v1','run_ref':family+'-'+case,'scope_ref':base,
            'design_ref':base+'/logic-r1','configuration_ref':base+'/variant-r1',
            'fault_model_ref':'opentools.owned-site-stuck-at.v1','objective_ref':base+'/selected-site-detection',
            'unit_instance':'dut','unit_type':'fault_network','family':c['family'],'role_map':roles(family),
            'model_basis_ref':base+'/owned-injection-sites','constraint_basis_ref':base+'/mode-and-input-mask',
            'pattern_basis_ref':base+'/compiled-vector-selection','exclusion_basis_ref':base+'/original-objective',
            'owner_ref':base+'/receiving-test-owner'}
