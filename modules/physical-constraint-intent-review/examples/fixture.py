"""Owned placed experiments and separate original region requirements."""
from copy import deepcopy
FAMILIES={
 'horizontal-access':{'design':'horizontal.v','region':[10000,9000,15000,12000],
  'placements':{'allow':[2000,2000],'gate':[4000,2000],'launch':[2000,10000],'capture':[22000,10000],'buffer':[5000,10000]},
  'moving':'buffer','safe':[9000,10000],'intrude':[12000,10000],'endpoint':'capture/D','clock':'clk','period':10,
  'case_values':{'reset_n':1,'fun_enable':0,'test_mode':1},'data_ports':['da','db'],'terms':['buffer/Y','capture/D']},
 'vertical-boundary':{'design':'vertical.v','region':[9000,14000,12000,20000],
  'placements':{'wake_join':[2000,2000],'clock_switch':[4000,2000],'producer':[4000,8000],'consumer':[10000,27000],
                'data_forward':[10000,8000],'sleep_inverse':[6000,2000],'reset_inverse':[8000,2000]},
  'moving':'data_forward','safe':[10000,12000],'intrude':[10000,16000],'endpoint':'consumer/D','clock':'ref_clock','period':16,
  'case_values':{'reset':0,'sleep_req':1,'wake_test':1},'data_ports':['source_a','source_b'],'terms':['data_forward/Y','consumer/D']}
}
CASES=('baseline','unchanged','preserving-control','drop-and-intrude','keep-and-intrude')

def context(family,case):
    c=FAMILIES[family];base='owned/'+family;placements=deepcopy(c['placements'])
    if case in ('preserving-control','drop-and-intrude','keep-and-intrude'):placements[c['moving']]=c['safe'] if case=='preserving-control' else c['intrude']
    return {'format':'opentools.physical-context.v1','run_ref':family+'-'+case,'scope_ref':base,'design_ref':base+'/design-r1',
      'configuration_ref':base+'/config-r1','phase_ref':base+'/override-phase',
      **{k:base+'/'+k for k in ('intent_basis_ref','constraint_rationale_ref','region_basis_ref','clock_domain_basis_ref','performance_basis_ref','power_basis_ref','correspondence_ref','owner_ref')},
      'setup':{'top':'top','die_um':[0,0,40,40],'core_um':[1,1,39,39],'site':'core',
        'placements':{k:{'xy_dbu':v,'orientation':'R0'} for k,v in placements.items()},
        'blockages':[] if case=='drop-and-intrude' else [c['region']],
        'clock':{'name':'root','port':c['clock'],'period_ns':c['period']},'case_values':c['case_values'],'data_ports':c['data_ports'],
        'endpoint':c['endpoint'],'selected_net':'data_buffer','interconnect':'none'}}

def original_intent(family):
    c=FAMILIES[family]
    return {'format':'owned.physical-intent.v1','scope_ref':'owned/'+family,'region_dbu':c['region'],
            'moving_instance':c['moving'],'selected_net':'data_buffer','required_clear_region':True,'required_hard_blockage':True,
            'required_claim':'Review the selected placed intervention against this clear region and retained native evidence; no routing, congestion, timing or functional benefit claim.',
            'endpoint_names':c['terms'],'source_ref':'owned/'+family+'/original-integration-intent-r1','owner_ref':'owned/'+family+'/receiving-owner',
            'limitations':'Scalar primitive layouts exercise physical review only; not actual memory/macro, isolation or clock functional signoff.'}
