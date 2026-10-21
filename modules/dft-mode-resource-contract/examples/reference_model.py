"""Independent finite register/serial model for the owned native qualification cases."""
import json
from pathlib import Path

def expected(width,positions,flags,load,capture):
    mask,mfg,debug,power,iso,drive,capture_correct,test=flags
    reset=int(not (1 and not(test and mfg and mask)))
    state=ideal=checks=failures=0;rows=[]
    config=dict(zip(('width','load_word','capture_word','test_mode','manufacturing','debug','functional_reset','power','isolation'),(width,load,capture,test,mfg,debug,1,power,iso)))
    phases=['shift']*width+['capture']+['unload']*width
    for tick,phase in enumerate(phases,1):
        serial=(load>>positions[-tick])&1 if phase=='shift' else 0
        enable=int(bool(test and mfg and (phase!='capture' or not capture_correct)))
        selected_clock=drive if test else 1-drive
        clock=int(bool(selected_clock and power and (not test or mfg)))
        before=(state>>positions[-1])&1 if not iso else 0
        expected_serial=(ideal>>positions[-1])&1
        def advance(old):
            cells=[(old>>bit)&1 for bit in positions]
            shifted=[serial]+cells[:-1]
            return sum(value<<bit for value,bit in zip(shifted,positions))
        ideal=(capture if phase=='capture' else advance(ideal)) if test and mfg else 0
        if not reset:state=0
        elif clock:state=advance(state) if enable else capture
        checks+=1;failures+=int(state!=ideal)
        if phase=='unload':checks+=1;failures+=int(before!=expected_serial)
        rows.append({'tick':tick,'phase':phase,'serial_in':serial,'parallel_data':capture,'tclk':drive,'fclk':1-drive,'reset_level':reset,'scan_enable':enable,'chain_clock':clock,'serial_before':before,'raw_state':state,'visible_state':0 if iso else state,'expected_state':ideal,'expected_serial':expected_serial,'failures':failures})
    return {'config':config,'steps':rows,'counts':{'steps':len(rows),'checks':checks,'failures':failures}}

def check_collection(root):
    root=Path(root);manifest=json.loads((root/'collection.json').read_text());totals={'steps':0,'checks':0,'failures':0}
    # Read original protocol independently of the production reader.
    keys=('serial_in','parallel_data','tclk','fclk','reset_level','scan_enable','chain_clock','serial_before','raw_state','visible_state','expected_state','expected_serial','failures')
    results=[]
    for case in manifest['cases']:
        lines=(root/case['case']/'run/run.stdout.txt').read_text().splitlines();config_keys=('width','load_word','capture_word','test_mode','manufacturing','debug','functional_reset','power','isolation')
        config=dict(zip(config_keys,map(int,lines[0].split()[1:])));rows=[]
        for line in lines[1:-1]:
            p=line.split();assert p[0]=='STEP' and len(p)==16
            rows.append({'tick':int(p[1]),'phase':p[2],**dict(zip(keys,map(int,p[3:])))})
        p=lines[-1].split();assert p[0]=='NATIVE_RESULT';counts=dict(zip(totals,map(int,p[1:])))
        ref=expected(case['width'],case['scan_bits'],case['flags'],config['load_word'],config['capture_word'])
        assert config==ref['config'] and rows==ref['steps'] and counts==ref['counts'],case['case']
        assert case['run_exit']==int(counts['failures']>0)
        (root/case['case']/'independent-reference.json').write_text(json.dumps(ref,indent=2)+'\n',encoding='utf-8')
        for k in totals:totals[k]+=counts[k]
        results.append(case['case'])
    return {'cases':results,'totals':totals,'limits':'Owned Boolean wrapper, reset-capable scalar cells and one complete serial cycle only; not a physical/timing/policy reference.'}
if __name__=='__main__':
    import sys
    print(json.dumps(check_collection(sys.argv[1]),indent=2))
