"""Independent expected object tables for the owned native view controls."""
from macro_common import require

def check(evidence,family,selection):
    storage=family=='storage';n=evidence['native'];logical=evidence['logical'];bad=selection
    if storage:
        cell='OWNED_STORE';library='owned_storage_r1';width,height=4000,2000;voltage=0.8
        pins=['CLK','D0','Q0','TEST_EN','REPAIR_LOAD'];directions=['INPUT','INPUT','OUTPUT','INPUT','INPUT'];types=['CLOCK','SIGNAL','SIGNAL','SIGNAL','SIGNAL']
        nets=['clock','data','result','test_mode','repair_load'];power,ground='VDD','VSS';control='REPAIR_LOAD';arc=('CLK','Q0');alternate='D0'
    else:
        cell='OWNED_CLOCK';library='owned_clock_r1';width,height=6000,3000;voltage=1.2
        pins=['REFCLK','ENABLE','RESET_N','TEST_MODE','CLKOUT','LOCKED'];directions=['INPUT','INPUT','INPUT','INPUT','OUTPUT','OUTPUT'];types=['CLOCK','SIGNAL','SIGNAL','SIGNAL','CLOCK','SIGNAL']
        nets=['ref_input','gate_enable','reset_n','mode_select','clock_output','ready_output'];power,ground='VDDA','VSSA';control='TEST_MODE';arc=('REFCLK','CLKOUT');alternate='ENABLE'
    expected_orient='R90' if bad=='wrong-orientation' else 'MX' if bad=='valid-mirror' else 'R0'
    actual_width=width+1000 if bad=='footprint-change' else width
    require(n['database_units_per_micron']==1000,'Independent DB units mismatch')
    require(n['master']=={'width':actual_width,'height':height,'symmetry':{'X':True,'Y':True,'R90':False}},'Independent master mismatch')
    require(n['instance']['name']=='u_macro' and n['instance']['master']==cell and n['instance']['orientation']==expected_orient and n['instance']['placement_status']=='PLACED','Independent instance mismatch')
    placed_w,placed_h=(height,actual_width) if expected_orient=='R90' else (actual_width,height)
    require(n['instance']['location']==[10000,20000] and n['instance']['box']==[10000,20000,10000+placed_w,20000+placed_h],'Independent placed box mismatch')
    require(set(n['physical_pins'])==set(pins+[power,ground]),'Independent physical census mismatch')
    checked=0
    for i,(pin,direction,kind,net) in enumerate(zip(pins,directions,types,nets)):
        expected_direction='OUTPUT' if bad=='wrong-direction' and pin==control else direction
        require(n['physical_pins'][pin]=={'direction':expected_direction,'signal_type':kind,'boxes':[{'layer':'metal1','box':[100,200+300*i,200,300+300*i]}]},'Independent physical pin mismatch: '+pin)
        actual_net=nets[1] if bad=='wrong-connection' and pin==control else net
        require(n['instance_terminals'][pin]=={'signal_type':kind,'net':actual_net,'net_signal_type':'SIGNAL'},'Independent native net mismatch: '+pin)
        require(logical['ports'][pin]=={'direction':direction.lower(),'width':1,'connection':{'kind':'varref','name':net,'width':1}},'Independent logical binding mismatch: '+pin)
        require(n['timing_library']['pins'][pin]=={'direction':direction.lower(),'is_bus':False},'Independent timing pin mismatch: '+pin);checked+=1
    for pin,kind,net,box in [(power,'POWER','VDD_AUX' if bad=='wrong-supply' else 'VDD_CORE',[1000,100,1100,200]),(ground,'GROUND','VSS_CORE',[2000,100,2100,200])]:
        require(n['physical_pins'][pin]=={'direction':'INOUT','signal_type':kind,'boxes':[{'layer':'metal1','box':box}]},'Independent PG geometry mismatch')
        require(n['instance_terminals'][pin]=={'signal_type':kind,'net':net,'net_signal_type':kind},'Independent PG owner mismatch');checked+=1
    idx=pins.index(control);obs=[50,150+300*idx,250,350+300*idx] if bad=='blocked-window' else [2500,400,3500,700]
    require(n['obstructions']==[{'layer':'metal1','box':obs}],'Independent obstruction mismatch')
    lib=n['timing_library'];point=lib['operating_point'];require(lib['library']==library and lib['cell']==cell,'Independent timing view identity mismatch')
    require(point['process']==1 and point['temperature']==25 and abs(point['voltage']-(voltage+(0.2 if bad=='voltage-change' else 0)))<1e-6,'Independent native operating point mismatch')
    observed_arcs={(a['from'],a['to']) for a in lib['arcs']};require(observed_arcs=={(alternate if bad=='arc-change' else arc[0],arc[1])},'Independent native timing endpoints mismatch')
    require(logical['unit']==cell and logical['instance']=='u_macro' and set(logical['ports'])==set(pins),'Independent logical geometry mismatch')
    require(evidence['qualified_batch_loader'],'Independent loader binding missing')
    return {'physical_pins_compared':checked,'logical_bindings_compared':len(pins),'timing_signal_pins_compared':len(pins),
            'native_records':n['native_record_count'],'model':'Independent expected object tables, placed geometry, connectivity, source pin order, PVT and timing endpoints; no LEF/Liberty parser or DRC/timing model.'}
