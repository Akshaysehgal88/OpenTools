"""Independent DC solution of retained native components, used only for validation."""
import csv
from pathlib import Path
from fixture import point

def solve_spice(path):
    resistors=[];sinks={};fixed={'0':0.0};nodes=set()
    for raw in path.read_text().splitlines():
        s=raw.split()
        if not s or s[0][0] in ('*','.'):continue
        if s[0][0]=='R':
            assert len(s)==4 and s[3].startswith('R=');resistors.append((s[1],s[2],float(s[3][2:])));nodes.update(s[1:3])
        elif s[0][0]=='I':
            assert s[2]=='0' and s[3]=='DC';sinks[s[1]]=sinks.get(s[1],0)+float(s[4]);nodes.add(s[1])
        elif s[0][0]=='V':
            assert s[2]=='0' and s[3]=='DC';fixed[s[1]]=float(s[4]);nodes.add(s[1])
        else:raise ValueError('Unknown native circuit element')
    unknown=sorted(nodes-set(fixed));index={n:i for i,n in enumerate(unknown)};a=[[0.0]*(len(unknown)+1) for _ in unknown]
    for n,i in index.items():a[i][-1]=-sinks.get(n,0)
    for n,m,r in resistors:
        assert r>0
        for lhs,rhs in ((n,m),(m,n)):
            if lhs not in index:continue
            i=index[lhs];a[i][i]+=1/r
            if rhs in index:a[i][index[rhs]]-=1/r
            else:a[i][-1]+=fixed[rhs]/r
    for col in range(len(a)):
        pivot=max(range(col,len(a)),key=lambda i:abs(a[i][col]));assert abs(a[pivot][col])>1e-12,'Floating DC reference';a[col],a[pivot]=a[pivot],a[col]
        factor=a[col][col];a[col]=[v/factor for v in a[col]]
        for row in range(len(a)):
            if row==col:continue
            factor=a[row][col]
            for j in range(col,len(a)+1):a[row][j]-=factor*a[col][j]
    solution={**fixed,**{n:a[i][-1] for n,i in index.items()}}
    return solution,len(resistors),len(sinks)

def check(e,root,family,case):
    folder=Path(root)/e['context']['run_ref'];expected_point=point(family,case)
    assert all(abs(e['native']['point'][k]-v)<=1e-6 for k,v in expected_point.items())
    expected={'load0/VDD':[11000,5500],'load1/VDD':[21000,5500]}
    if family=='branch':expected['load2/VDD']=[15000,15000]
    assert {k:v['xy_dbu'] for k,v in e['native']['iterms'].items()}==expected
    if case=='connectivity-cut':
        assert e['native_status']['connectivity']['tcl_catch']==1 and e['native_status']['analysis']['tcl_catch']==1
        assert e['reports']['voltage.csv'] is None and not (folder/'voltage.csv').exists()
        return {'native_failed_connectivity_controls':1,'compared_instance_points':0,'native_records':e['native']['record_count'],'physical_terminals':len(expected),'independent_resistors':0,'independent_sinks':0}
    assert e['native_status']['connectivity']=={'tcl_catch':0,'native_result':'1'}
    solution,resistors,sinks=solve_spice(folder/'network.sp');count=0;comparisons=[]
    with (folder/'voltage.csv').open(newline='') as stream:
        for r in csv.DictReader(stream):
            terminal=r['Instance']+'/'+r['Terminal'];xy=[round(float(r[k])*1000) for k in ('X location','Y location')];assert expected[terminal]==xy
            node='ITermNode_'+r['Layer']+'_'+'_'.join(map(str,xy));native=float(r['Voltage']);reference=solution[node];assert abs(native-reference)<=2e-6,(terminal,native,reference)
            comparisons.append({'terminal':terminal,'native_voltage_V':native,'independent_DC_voltage_V':reference,'tolerance_V':2e-6});count+=1
    assert count==len(expected)
    return {'native_failed_connectivity_controls':0,'compared_instance_points':count,'native_records':e['native']['record_count'],
            'physical_terminals':len(expected),'independent_resistors':resistors,'independent_sinks':sinks,'comparisons':comparisons,
            'limits':'Independent nodal solution of original native SPICE values and explicit terminal coordinate tables. Not a separate extraction model, dynamic solver, load validation or signoff check.'}
