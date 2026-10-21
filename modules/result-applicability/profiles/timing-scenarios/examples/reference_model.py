"""Independent model-value, mode and scalar timing table, without reader imports."""
def expected(family,mode,corner,control):
    actual_corner=('nominal' if corner=='low_voltage' else 'low_voltage') if control=='wrong-library' else corner
    if actual_corner=='nominal':library='owned_nominal';voltage=1.0;temperature=25.0;scale=1
    else:library='owned_low_voltage';voltage=0.8;temperature=125.0;scale=4
    period=10.0 if mode=='functional' else 20.0 if family=='wake-sequence' else 2.0
    if control=='timing-failure':period=0.03
    selector=None if control=='unknown-mode' else 0 if mode=='functional' or control=='wrong-mode' else 1
    budget=0.04 if family=='wake-sequence' else 0.08 if selector==0 else 0.10
    pvt={'process':1.0,'voltage_V':voltage,'temperature_C':temperature}
    return {'library':library,'pvt':pvt,'cases':{'reset_n':1,'power_ok':1,'mode_select':selector},'period_ns':period,'startpoint':'launch/Q','endpoint':'capture/D','slack_ns':round(period-budget*scale,6),'register_clock_pins':['capture/CK','launch/CK'],'data_pins':['capture/D','launch/D'],'output_pins':['capture/Q','launch/Q']}
