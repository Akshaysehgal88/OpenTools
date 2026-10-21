"""Owned series and branched static supply scenarios; requests precede analysis."""
from copy import deepcopy
from pathlib import Path
HERE=Path(__file__).resolve().parent
CASES=('base','unchanged','loads','source-change','corner-change','connectivity-cut')
FAMILIES={
 'series':{'design':'series.def','base_power':{'load0':0.001,'load1':0.002},'heavy_power':{'load0':0.003,'load1':0.004},
           'voltage':1.0,'point':{'process':1.0,'voltage':1.0,'temperature':25.0},'sources':[[0.5,5.5,0.2,1.0]]},
 'branch':{'design':'branch.def','base_power':{'load0':0.0015,'load1':0.0005,'load2':0.002},'heavy_power':{'load0':0.003,'load1':0.002,'load2':0.004},
           'voltage':0.8,'point':{'process':1.0,'voltage':0.8,'temperature':85.0},'sources':[[0.5,5.5,0.2,0.8],[15,15,0.2,0.8]]}}
def setup(family,case):
    c=FAMILIES[family];voltage=round(c['voltage']-0.1,6) if case=='source-change' else c['voltage'];sources=deepcopy(c['sources'])
    if case=='source-change':sources=[[29.5,5.5,0.2,voltage]]
    powers=c['heavy_power'] if case in ('loads','source-change') else c['base_power']
    return {'net':'VDD','library_cell':'owned_supply/LOAD','corner':'default','net_voltage_V':round(voltage,6),
            'layer_resistance_argument':{'metal1':0.0001},'powers_W':powers,'source_rows_um_V':sources}
def point(family,case):
    p=deepcopy(FAMILIES[family]['point'])
    if case=='corner-change':p.update(temperature=p['temperature']+20,voltage=round(p['voltage']-0.05,6))
    return p
def library(family,case):
    p=point(family,case);template=(HERE/'cells.lib.in').read_text()
    return template.replace('@VOLTAGE@',str(p['voltage'])).replace('@TEMPERATURE@',str(p['temperature']))
def design(family,case):
    value=(HERE/FAMILIES[family]['design']).read_text()
    if case=='connectivity-cut':value=value.replace('+ ROUTED metal1 400 ( 500 5500 ) ( 30000 5500 )','+ ROUTED metal1 400 ( 500 5500 ) ( 14000 5500 ) NEW metal1 400 ( 18000 5500 ) ( 30000 5500 )')
    return value
def scenario(family,case):
    heavy=case in ('loads','source-change');base='owned/'+family
    return {'activity_ref':base+('/concurrent-static-loads' if heavy else '/base-static-loads'),
       'state_ref':base+'/steady-supply-on','concurrency_ref':base+('/simultaneous-static' if heavy else '/base-static'),
       'active_domains':['compute','peripheral'] if heavy else ['compute'],
       'instance_domains':{name:('peripheral' if i else 'compute') for i,name in enumerate(FAMILIES[family]['base_power'])},
       'time_basis':'static-power-overrides-at-declared-net-voltage; no transition waveform'}
def context(family,case):
    base='owned/'+family
    return {'format':'opentools.supply-context.v1','run_ref':family+'-'+case,'scope_ref':base,'design_ref':base+'/design-r1',
      'configuration_ref':base+'/configuration-r1','scenario_ref':base+('/concurrent-static' if case in ('loads','source-change') else '/base-static'),
      **{k:base+'/'+k for k in ('topology_basis_ref','sources_basis_ref','corner_basis_ref','activity_basis_ref','state_basis_ref','concurrency_basis_ref','load_mapping_ref','owner_ref')},
      'setup':setup(family,case),'scenario':scenario(family,case)}
