"""Owned low-voltage wake and manufacturing-capture scenario obligations."""
import hashlib
from pathlib import Path
from scenario_common import PROFILE,sha
HERE=Path(__file__).resolve().parent
FAMILIES={'wake-sequence':{'other':'wake','required_corner':'low_voltage','period_ns':20.0,'power_state':'wake_active'},'capture-window':{'other':'capture','required_corner':'nominal','period_ns':2.0,'power_state':'test_capture'}}
CORNERS={'nominal':{'library':'owned_nominal','process':1.0,'voltage_V':1.0,'temperature_C':25.0},'low_voltage':{'library':'owned_low_voltage','process':1.0,'voltage_V':0.8,'temperature_C':125.0}}
CONTROLS=('normal','repeat','wrong-library','wrong-mode','unknown-mode','timing-failure')

def run_ref(family,mode,corner,control='normal'):return '-'.join((family,mode,corner,control))
def identity(family):return {'scope_ref':family+'/top','design_ref':family+'/netlist-v1','configuration_ref':family+'/scenario-matrix-v1'}
def context(family,mode,corner,control='normal'):
    f=FAMILIES[family];basis='owned/'+family+'/original-requirements';period=10.0 if mode=='functional' else f['period_ns'];cases={'reset_n':1,'power_ok':1,'mode_select':0 if mode=='functional' or control=='wrong-mode' else 1}
    if control=='unknown-mode':cases['mode_select']=None
    if control=='timing-failure':period=0.03
    return {'format':'opentools.sta-scenario-context.v1','run_ref':run_ref(family,mode,corner,control),**identity(family),'scenario_ref':family+'/'+mode+'/'+corner,
      'scenario':{'mode':mode,'corner':corner,'power_state':'active' if mode=='functional' else f['power_state'],'mode_basis_ref':basis+'#mode','corner_basis_ref':basis+'#corner','power_basis_ref':basis+'#power','rc_basis_ref':basis+'#unannotated-logical-model','clock_basis_ref':basis+'#clock'},
      'setup':{'clock_name':'root','clock_port':'clk','period_ns':period,'cases':cases,'operating_condition':'qualified','from_cell':'launch','to_cell':'capture'}}

def design(family):
    text='module top(input clk,input reset_n,input power_ok,input mode_select,input data,output qsource,output qcapture);\n'
    if family=='wake-sequence':
        text+='wire allow_clock,gclk,payload;\nECO_OR allow(.A(power_ok),.B(mode_select),.Y(allow_clock));\nECO_AND gate(.A(clk),.B(allow_clock),.Y(gclk));\nECO_BUF buffer(.A(qsource),.Y(payload));\n';clock='gclk'
    else:
        text+='wire payload,nmode,normal_data,test_mid,test_data,normal_leg,test_leg;\nECO_INV invert(.A(mode_select),.Y(nmode));\nECO_BUF normal_buffer(.A(qsource),.Y(normal_data));\nECO_BUF test_buffer0(.A(qsource),.Y(test_mid));\nECO_BUF test_buffer1(.A(test_mid),.Y(test_data));\nECO_AND normal_select(.A(normal_data),.B(nmode),.Y(normal_leg));\nECO_AND test_select(.A(test_data),.B(mode_select),.Y(test_leg));\nECO_OR data_mux(.A(normal_leg),.B(test_leg),.Y(payload));\n';clock='clk'
    return text+f'ECO_DFF launch(.CK({clock}),.RN(reset_n),.D(data),.Q(qsource));\nECO_DFF capture(.CK({clock}),.RN(reset_n),.D(payload),.Q(qcapture));\nendmodule\n'

def cases():
    for family,f in FAMILIES.items():
        for mode in ('functional',f['other']):
            for corner in CORNERS:yield family,mode,corner,'normal'
        yield family,'functional','nominal','repeat'
        for control in ('wrong-library','wrong-mode','unknown-mode','timing-failure'):yield family,f['other'],f['required_corner'],control

def expected_fields(family,mode,corner,period=None):
    f=FAMILIES[family];c=CORNERS[corner];pvt={k:c[k] for k in ('process','voltage_V','temperature_C')};basis='owned/'+family+'/original-requirements';fact=lambda v:{'value':v,'evidence_ref':basis}
    return {k:fact(v) for k,v in {'scope.identity':identity(family),'implementation.source_sha256':hashlib.sha256(design(family).encode()).hexdigest(),
      'library.source_sha256':sha(HERE/('cells.'+corner+'.lib')),'physical_library.source_sha256':sha(HERE/'cells.lef'),'library.pvt':{'library':c['library'],'min':pvt,'max':pvt},
      'scenario.mode':mode,'scenario.corner':corner,'power.state':'active' if mode=='functional' else f['power_state'],
      'native.cases':{'reset_n':1,'power_ok':1,'mode_select':0 if mode=='functional' else 1},
      'clock.definition':{'name':'root','period_ns':float(period if period is not None else 10.0 if mode=='functional' else f['period_ns']),'propagated':1,'sources':['clk'],'register_clock_pins':['capture/CK','launch/CK']},'rc.view':'unannotated','profile':PROFILE}.items()}

def plan(family,timing_failure=False):
    f=FAMILIES[family];basis='owned/'+family+'/original-requirements';rows=[]
    for mode,corner,applicable in [('functional','nominal',True),('functional','low_voltage',True),(f['other'],f['required_corner'],True),(f['other'],'nominal' if f['required_corner']=='low_voltage' else 'low_voltage',False)]:
        period=0.03 if timing_failure and mode!='functional' and applicable else None
        rows.append({'id':family+'/'+mode+'/'+corner,'applicability':'required' if applicable else 'not_applicable','reason':'Independent operating-mode requirement.' if applicable else 'Original operating recipe permits this mode only at its specified supply/model corner.','basis_ref':basis+'#applicability','exclusion_ref':None if applicable else basis+'#nonapplicable-recipe-combination','required_fields':expected_fields(family,mode,corner,period)})
    return {'format':'opentools.sta-scenario-plan.v1',**identity(family),'requirements_ref':basis,'owner_ref':'owned/'+family+'/scenario-review-owner','obligations':rows}

def corpus(family,variant):
    f=FAMILIES[family];runs=[run_ref(family,'functional','nominal'),run_ref(family,'functional','low_voltage')]
    if variant=='omitted':runs.append(run_ref(family,'functional','nominal','repeat'))
    else:runs.append(run_ref(family,f['other'],f['required_corner'],'normal' if variant=='complete' else variant))
    return {'format':'opentools.sta-scenario-corpus.v1','runs':runs}
