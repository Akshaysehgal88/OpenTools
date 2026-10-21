"""Independent expected geometry/placement outcomes for owned native experiments."""
from fixture import FAMILIES
EXPECTED={
 'horizontal-access':{'baseline':[5150,10150,22150,10150],'unchanged':[5150,10150,22150,10150],
   'preserving-control':[9150,10150,22150,10150],'drop-and-intrude':[12150,10150,22150,10150],'keep-and-intrude':[12150,10150,22150,10150]},
 'vertical-boundary':{'baseline':[10150,8150,10150,27150],'unchanged':[10150,8150,10150,27150],
   'preserving-control':[10150,12150,10150,27150],'drop-and-intrude':[10150,16150,10150,27150],'keep-and-intrude':[10150,16150,10150,27150]}}

def check(e,family,case):
    n=e['native'];c=FAMILIES[family];expected=EXPECTED[family][case];assert n['net_bbox']==expected and n['units']==1000
    assert n['net_terms']==sorted(c['terms']) and not n['net_bterms'];assert n['path_count']==1
    assert n['paths'][0]['startpoint']==('launch/Q' if family=='horizontal-access' else 'producer/Q') and n['paths'][0]['endpoint']==c['endpoint']
    assert n['placement_check']['return_code']==int(case=='keep-and-intrude')
    assert n['blockages']==([] if case=='drop-and-intrude' else [{'box':c['region'],'soft':False}])
    origins=dict(c['placements'])
    if case in ('preserving-control','drop-and-intrude','keep-and-intrude'):origins[c['moving']]=c['safe'] if case=='preserving-control' else c['intrude']
    assert set(n['instances'])==set(origins)
    for name,(x,y) in origins.items():assert n['instances'][name]['box']==[x,y,x+1000,y+1000] and n['instances'][name]['orientation']=='R0'
    for pin in n['pins'].values():
        x,y=origins[pin['instance']];assert pin['position_known'] and pin['xy']==[x+150,y+150]
    return {'native_records':n['record_count'],'instance_boxes_compared':len(origins),'pin_positions_compared':len(n['pins']),
            'selected_terminal_boxes_compared':1,'path_endpoints_compared':2,'native_placement_results_compared':1,
            'expected_half_perimeter_dbu':expected[2]-expected[0]+expected[3]-expected[1],
            'limits':'Independent fixed endpoint tables and LEF pin-center geometry ledger; native placement check provides a separate intrusion control. Not routed length, extraction, congestion, slack or functional proof.'}
