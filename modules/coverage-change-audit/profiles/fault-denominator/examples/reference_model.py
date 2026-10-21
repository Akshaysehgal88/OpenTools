"""Independent gate equations for each native healthy/faulted response."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from fault_common import require

def response(family,value,mode,fault=None):
    a,b,c,d=[bool(value&(1<<i)) for i in range(4)]
    def force(index,bit):return bool(fault%2) if fault is not None and fault//2==index else bool(bit)
    if family==0:
        r0=a and b;v0=force(0,r0);r1=a or b;v1=force(1,r1)
        r2=(v0 and c) or (v1 and not c);v2=force(2,r2);r3=v2;v3=force(3,r3);r4=False;v4=force(4,r4)
        raw=[r0,r1,r2,r3,r4];driven=[v0,v1,v2,v3,v4];output=int(v0 if mode else v3)
    else:
        r0=(a or b) and not(a and b);v0=force(0,r0);r1=c and d;v1=force(1,r1)
        r2=v0 and v1;v2=force(2,r2);r3=v0 or v1;v3=force(3,r3);r4=v2;v4=force(4,r4);r5=False;v5=force(5,r5)
        raw=[r0,r1,r2,r3,r4,r5];driven=[v0,v1,v2,v3,v4,v5];output=int(v4)+2*int(v2 if mode else v3)
    pack=lambda bits:sum(2**i for i,bit in enumerate(bits) if bit)
    return pack(raw),pack(driven),output

def check(evidence):
    family=evidence['geometry']['family'];count=0
    for row in evidence['observations']:
        expected=response(family,row['vector'],row['mode'],row.get('fault_id'))
        require((row['raw_sites'],row['driven_sites'],row['observed'])==expected,'Independent response mismatch: '+str(row))
        if row['kind']=='fault':require(row['healthy']==response(family,row['vector'],row['mode'])[2],'Independent healthy result mismatch')
        count+=1
    # Recreate equivalence classes with independently computed complete signatures.
    legal=sorted({r['vector'] for r in evidence['observations']});groups={};representatives={}
    for f in evidence['faults']:
        signature=tuple(response(family,v,evidence['plan']['mode'],f['id'])[2] for v in legal)
        representative=groups.setdefault(signature,f['id']);representatives[f['id']]=representative
        require(f['representative']==representative,'Independent collapse-map mismatch')
    return {'native_observations_compared':count,'response_fields_compared':3*count,
            'native_original_faults':len(evidence['faults']),'native_collapsed_groups':len(groups),
            'method':'Separate Boolean gate equations, complete healthy/fault response and independently computed signature equivalence; no commercial ATPG assumptions.'}
