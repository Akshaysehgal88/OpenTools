"""Independent native netlist/census and serial-graph reference for the owned fixtures."""
import json,re
from pathlib import Path
def cells(source):
    result={}
    for master,name,body in re.findall(r'\b(DFFR_CELL|SCANR_CELL)\s+(\w+)\s*\((.*?)\);',source,re.S):
        pairs=re.findall(r'\.(\w+)\s*\(\s*([^()\s]+)\s*\)',body);assert name not in result and len(pairs)==len(dict(pairs));result[name]={'master':master,'pins':dict(pairs)}
    return result
def check_collection(root):
    root=Path(root);manifest=json.loads((root/'collection.json').read_text());totals={'native_runs':0,'sequential_states':0,'scan_members':0,'unscanned':0,'chains':0,'functional_pin_checks':0};results=[]
    for row in manifest['cases']:
        folder=root/row['case'];run=folder/'run';original=cells((run/'seed.v').read_text());pre=cells((run/'pre.v').read_text());post=cells((run/'post.v').read_text());protected=set(row['protected'])
        assert original==pre and set(pre)==set(post)
        assert {n for n,v in post.items() if v['master']=='DFFR_CELL'}==protected
        observed_scan={n for n,v in post.items() if v['master']=='SCANR_CELL'};assert observed_scan==set(pre)-protected
        for name in pre:
            assert {k:post[name]['pins'][k] for k in ('CK','RN','D','Q')}==pre[name]['pins'];totals['functional_pin_checks']+=4
        for name,expected in [('pre.txt',pre),('post.txt',post)]:
            lines=(run/name).read_text().splitlines();sequential={line.split()[1] for line in lines if line.startswith('SEQ ')};masters={p[1]:p[2] for line in lines if (p:=line.split()) and p[0]=='CELL'}
            assert sequential==set(expected) and masters=={n:v['master'] for n,v in expected.items()}
        # Walk the serialized SI/Q graph without the product reader or preview parser.
        by_output={v['pins']['Q']:n for n,v in post.items() if n in observed_scan};next_cell={};starts=[]
        for name in observed_scan:
            predecessor=by_output.get(post[name]['pins']['SI'])
            if predecessor is None:starts.append(name)
            else:assert predecessor not in next_cell;next_cell[predecessor]=name
        chains=[];seen=set()
        for start in sorted(starts):
            order=[];name=start
            while name:
                assert name not in seen;seen.add(name);order.append(name);name=next_cell.get(name)
            assert len({post[n]['pins']['CK'] for n in order})==1;chains.append(order)
        assert seen==observed_scan
        serialized={'sequential':sorted(pre),'scan_members':sorted(observed_scan),'unscanned':sorted(protected),'chain_orders':chains,'clock_nets':{n:v['pins']['CK'] for n,v in post.items()}}
        evidence=json.loads((folder/'evidence.json').read_text());assert evidence['membership']['members']==serialized['scan_members'] and evidence['membership']['unscanned']==serialized['unscanned']
        assert {tuple(v['order']) for v in evidence['membership']['chains'].values()}=={tuple(v) for v in chains}
        (folder/'independent-reference.json').write_text(json.dumps(serialized,indent=2)+'\n',encoding='utf-8')
        totals['native_runs']+=1;totals['sequential_states']+=len(pre);totals['scan_members']+=len(observed_scan);totals['unscanned']+=len(protected);totals['chains']+=len(chains);results.append(row['case'])
    return {'cases':results,'totals':totals,'limits':'Owned flat reset-capable scalar cells only; native membership/correspondence, not ATPG or physical role/power semantics.'}
if __name__=='__main__':
    import sys
    print(json.dumps(check_collection(sys.argv[1]),indent=2))
